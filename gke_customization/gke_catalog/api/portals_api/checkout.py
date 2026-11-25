from dataclasses import field
import json
from os import name
from warnings import filters
import frappe
from frappe import _
from werkzeug.wrappers import request
from gke_customization.gke_catalog.api.portals_api.item_price import get_item_price

ORDER_PLACED_TEMPLATE = "gke_customization/templates/emails/order_placed.html"

# ── confirm cart order ─────
@frappe.whitelist()
def confirm_cart_orders(customer, order_date=None, notes=None, user=None, row_names=None):
    """
    Cart ke selected ya saare "Add To Cart" items ko Portal Order mein place karo.

    Flow:
        1. Customer ka active cart dhundo (Add To Cart Portal Item)
        2. row_names pass kiye hain -> sirf wo items place karo
           row_names nahi pass kiye -> saare "Add To Cart" items place karo
        3. Har item ka rate LIVE recalculate karo (bom se diamond_quality/metal_touch
           nikaal ke get_item_price call karo) — cart ka stale/saved rate ignore karo
        4. Naya Portal Order doc banao un items ke saath (fresh rate ke saath)
        5. Cart ke wo items delete karo (status change nahi, directly remove)
        6. Cart ke totals recalculate karo

    Postman - Saare items:
        { "customer": "Rajan Shah", "order_date": "2024-06-27" }

    Postman - Selected items:
        { "customer": "Rajan Shah", "row_names": ["abc123", "def456"] }
    """

    if not customer:
        frappe.throw(_("Customer required hai."))

    # ── Active cart dhundo ─────────────────────────────────────────────────────
    cart_name = frappe.db.get_value(
        "Add To Cart Portal Item",
        {"customer": customer, "status": "Add To Cart"},
        "name",
        order_by="creation asc",
    )

    if not cart_name:
        frappe.throw(_("Koi active cart nahi mila."))

    cart = frappe.get_doc("Add To Cart Portal Item", cart_name)

    # ── row_names parse karo (string se list) ─────────────────────────────────
    if isinstance(row_names, str):
        row_names = json.loads(row_names)

    # ── Items filter karo ─────────────────────────────────────────────────────
    if row_names:
        # Sirf selected rows lo — "Add To Cart" status bhi check karo
        selected = set(row_names)
        active_items = [
            r for r in cart.items
            if r.name in selected
            and (getattr(r, "status", "") or "") == "Add To Cart"
        ]
        if not active_items:
            frappe.throw(_("Selected items cart mein nahi mile ya already placed hain."))
    else:
        # Saare "Add To Cart" status wale items lo
        active_items = [r for r in cart.items if (getattr(r, "status", "") or "") == "Add To Cart"]
        if not active_items:
            frappe.throw(_("Cart mein koi active item nahi hai."))

    final_order_date = frappe.utils.getdate(order_date) if order_date else frappe.utils.today()
    current_user     = user or frappe.session.user

    # ── Naya Portal Order banao ────────────────────────────────────────────────
    portal_order            = frappe.new_doc("Portal Order")
    portal_order.customer   = customer
    portal_order.order_by   = current_user
    portal_order.order_date = final_order_date
    portal_order.status     = "Ordered"
    portal_order.company    = cart.company or (
        frappe.defaults.get_user_default("company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )
    portal_order.currency   = cart.currency or "INR"

    if notes:
        portal_order.notes = notes

    # ── Cart items → Portal Order items (LIVE rate ke saath) ──────────────────
    order_rates = {}   # row.name -> live_rate, totals calc ke liye reuse karenge

    for row in active_items:
        row_qty = row.quantity or 0

        # ── Live rate recalculate — order place hone ke exact moment ka price ──
        live_rate = row.rate or 0   # fallback: agar bom na ho ya calc fail ho jaye

        if row.bom:
            diamond_quality = frappe.db.get_value("BOM", row.bom, "diamond_quality")
            metal_touch     = frappe.db.get_value("BOM", row.bom, "metal_touch")

            live_rate = _get_live_rate(
                customer=customer,
                item_code=row.item_code,
                bom=row.bom,
                diamond_quality=diamond_quality,
                metal_touch=metal_touch,
                fallback_rate=row.rate or 0,
            )

        row_amount = round(row_qty * live_rate, 2)
        order_rates[row.name] = live_rate

        portal_order.append("items", {
            "item_code"                    : row.item_code,
            "bom"                          : row.bom or "",
            "uom"                          : row.uom or "",
            "quantity"                     : row_qty,
            "rate"                         : live_rate,     # ← fresh rate
            "amount"                       : row_amount,     # ← fresh amount
            "user"                         : getattr(row, "user", "") or "",
            "status"                       : "Ordered",
            "as_per_design"                : getattr(row, "as_per_design", 0) or 0,
            "as_per_customization"         : getattr(row, "as_per_customization", 0) or 0,
            "job_work"                     : getattr(row, "job_work", 0) or 0,
            "out_right"                    : getattr(row, "out_right", 0) or 0,
            "hybrid"                       : getattr(row, "hybrid", 0) or 0,
            "customized_data"              : getattr(row, "customized_data", "") or "",
        })

    portal_order.insert(ignore_permissions=True)
    
    frappe.db.set_value(
        "Portal Order",
        portal_order.name,
        {
            "status"         : "Ordered",
            "workflow_state" : "Ordered",
        },
        update_modified=False,
    )


    # ── Portal Order totals directly DB mein set karo (controller override se bachne ke liye) ──
    total_qty    = sum(row.quantity or 0 for row in active_items)
    total_amount = round(
        sum((row.quantity or 0) * order_rates.get(row.name, row.rate or 0) for row in active_items),
        2,
    )

    frappe.db.set_value(
        "Portal Order",
        portal_order.name,
        {
            "total_quantity" : total_qty,
            "total_amount"   : total_amount,
        },
        update_modified=False,
    )

    # ── Placed items cart se hata do (status change nahi, delete karo) ──────────
    placed_item_names = {row.name for row in active_items}
    cart.items = [row for row in cart.items if row.name not in placed_item_names]

    # ── Cart totals recalculate karo ───────────────────────────────────────────
    _recalculate_totals(cart)
    cart.save(ignore_permissions=True)

    frappe.db.commit()
    
        # ── Order placed emails ───────────────────────────────────────────────────
    _send_order_placed_emails(
        customer=customer,
        portal_order=portal_order,
        user=current_user,
        active_items=active_items,
        order_rates=order_rates,
        total_qty=total_qty,
        total_amount=total_amount,
        order_date=final_order_date,
        notes=notes,
    )

    return {
        "success"       : True,
        "message"       : "Order successfully placed",
        "portal_order"  : portal_order.name,
        "cart"          : cart.name,
        "order_date"    : str(final_order_date),
        "order_by"      : current_user,
        # "total_quantity": portal_order.total_quantity or 0,
        # "total_amount"  : portal_order.total_amount or 0,
        "total_quantity": total_qty,     
        "total_amount"  : total_amount,
        "items_ordered" : len(active_items),
    } 


# ── Get Cart ───────────────────────────────────────────────────────────────────
# ── Live rate helper (add_to_cart wala hi price-calc logic) ────────────────

def _get_live_rate(customer, item_code, bom, diamond_quality, metal_touch, fallback_rate=0):
    """
    get_item_price se live rate nikalo — add_to_cart wale price-calc block jaisa.
    Fail ho jaye ya bom na ho toh fallback_rate return karega.
    """
    if not bom:
        return fallback_rate

    try:
        price_data = get_item_price(
            customer=customer,
            item_code=item_code,
            bom=bom,
            diamond_quality=diamond_quality,
            metal_touch=metal_touch,
        )
        dia_amount    = price_data["dia_overall_summary"]["total_amount"]
        gem_amount    = price_data["gem_summary"]["total_gemstone_amount"]
        metal_total   = sum(
            v.get("gold_amount", 0) + v.get("making_charge", 0)
            for v in price_data["metal_price_data"].values()
        )
        finding_total = sum(
            v.get("finding_amount", 0) + v.get("finding_making_charge", 0)
            for v in price_data["finding_price_data"].values()
        )
        return round(dia_amount + gem_amount + metal_total + finding_total, 2)
    except Exception as e:
        frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
        return fallback_rate

 
def _recalculate_totals(doc):
    """Total quantity aur total amount recalculate karo (Cancelled rows exclude)."""
    total_qty    = 0
    total_amount = 0
    for row in doc.items:
        if (row.status or "") == "Cancelled":   
            continue
        total_qty    += (row.quantity or 0)
        total_amount += (row.amount   or 0)
    doc.total_quantity = total_qty
    doc.total_amount   = total_amount  


def _get_customer_emails(customer_name):
    return [
        "bhavika_p@gkexport.com",
        "mansi_g@gkexport.com",
    ]

def _get_order_team_emails():
    return [
        "rajan_m@gkexport.com",
    ]

def _render_order_email(context, items, internal=False, show_rate=False):
    return frappe.render_template(
        ORDER_PLACED_TEMPLATE,
        {**context, "items": items, "internal": internal, "show_rate": show_rate},
    )

def _send_order_placed_emails(customer, portal_order, user, active_items, order_rates,
                              total_qty, total_amount, order_date, notes=None):
    try:
        customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
        sender = "customer_portal@gkexport.com"

        items = []
        for row in active_items:
            rate = order_rates.get(row.name, row.rate or 0)
            amount = round((row.quantity or 0) * rate, 2)
            items.append({
                "item_code": row.item_code,
                "bom": row.bom,
                "quantity": row.quantity,
                "rate_fmt": f"{rate:,.2f}",
                "amount_fmt": f"{amount:,.2f}",
            })

        context = {
            "customer_name": customer_name,
            "order_id": portal_order.name,
            "order_date": str(order_date),
            "order_by": user,
            "notes": notes,
            "total_qty": total_qty,
            "total_amount_fmt": f"{total_amount:,.2f}",
            "currency": portal_order.currency,
        }

        # Email 1: To user, CC customer
        frappe.sendmail(
            recipients=[user],
            cc=[e for e in _get_customer_emails(customer) if e != user],
            sender=sender,
            subject=f"Order Placed - {portal_order.name}",
            message=_render_order_email(context, items, internal=False, show_rate=False),
            reference_doctype="Portal Order",
            reference_name=portal_order.name,
        )

        # Email 2: To user, CC order team
        frappe.sendmail(
            recipients=[user],
            cc=[e for e in _get_order_team_emails() if e != user],
            sender=sender,
            subject=f"[Internal] New Order - {portal_order.name} ({customer_name})",
            message=_render_order_email(context, items, internal=True, show_rate=True),
            reference_doctype="Portal Order",
            reference_name=portal_order.name,
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Order email failed: {portal_order.name}")
        