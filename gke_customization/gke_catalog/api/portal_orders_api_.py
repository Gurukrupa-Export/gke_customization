from dataclasses import field
import json
from os import name
from warnings import filters
import frappe
from frappe import _
from werkzeug.wrappers import request
from gke_customization.gke_catalog.api.item_price_list import get_item_price


# ── Helpers ────────────────────────────────────────────────────────────────────


def _serialize_items(items, status_filter=None):
    """
    Child table rows ko clean dict list mein convert karo.
 
    status_filter:
        - Pass karo toh sirf us status ki rows aayengi  (e.g. "Add To Cart")
        - None ho toh sab aayengi except "Cancel Order" wali rows
    """
    result = []
    for row in items:
        row_status = getattr(row, "status", "Add To Cart") or "Add To Cart"
 
        # ── Status filter ──────────────────────────────────────────────────────
        if status_filter:
            if row_status != status_filter:
                continue
        else:
            if row_status in ("Cancel Order", "Cancelled"):
                continue
 
        # ── Item & BOM extra data ──────────────────────────────────────────────
        item_data = frappe.db.get_value(
            "Item",
            row.item_code,
            ["image", "name", "item_group"],
            as_dict=True,
        ) or {}
 
        bom_data = frappe.db.get_value(
            "BOM",
            row.bom,
            ["gross_weight", "metal_and_finding_weight", "total_diamond_weight_in_gms", "metal_touch"],
            as_dict=True,
        ) or {}
 
        result.append({
            "name"                        : row.name,
            "item_code"                   : row.item_code or "",
            "bom"                         : row.bom or "",
            "uom"                         : row.uom or "",
            "quantity"                    : row.quantity or 0,
            "rate"                        : row.rate or 0,
            "amount"                      : (row.quantity or 0) * (row.rate or 0),
            "image"                       : item_data.get("image") or "",
            "category"                    : item_data.get("item_group") or "",
            "gross_weight"                : bom_data.get("gross_weight") or "",
            "net_weight"                  : bom_data.get("metal_and_finding_weight") or "",
            "total_diamond_weight_in_gms" : bom_data.get("total_diamond_weight_in_gms") or "",
            "metal_touch"                 : bom_data.get("metal_touch") or "",
            "user"                        : getattr(row, "user", "") or "",
            "status"                      : row_status,
            "design"                      : "Customized" if (getattr(row, "as_per_customization", 0) or 0) else "As Per Design",
            "as_per_design"               : getattr(row, "as_per_design", 0) or 0,
            "as_per_customization"        : getattr(row, "as_per_customization", 0) or 0,
            "customized_data"             : row.customized_data or "",
            "job_work"                    : getattr(row, "job_work", 0) or 0,
            "out_right"                   : getattr(row, "out_right", 0) or 0,
            "hybrid"                      : getattr(row, "hybrid", 0) or 0,
        })
    return result


def _normalize_json(val):
    """JSON string ko normalize karo taaki comparison consistent rahe."""
    v = (val or "").strip()
    if not v:
        return ""
    try:
        parsed = json.loads(v)
        return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
    except Exception:
        return v


# def _recalculate_totals(doc):
#     """Total quantity aur total amount recalculate karo."""
#     total_qty    = 0
#     total_amount = 0
#     for row in doc.items:
#         total_qty    += (row.quantity or 0)
#         total_amount += (row.amount   or 0)
#     doc.total_quantity = total_qty
#     doc.total_amount   = total_amount
  
  
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
 
# -- Helper: Cart totals recalculate -----------------------------------------------
def _recalculate_cart_totals(cart):
    """
    Cart ke active items se total_quantity aur total_amount compute karo.
    cancelled wali rows skip hongi.
    cart.save() se pehle call karo.
    """
    total_qty    = 0.0
    total_amount = 0.0

    for row in cart.items:
        row_status = (getattr(row, "status", "Add To Cart") or "Add To Cart")
        if row_status == "Cancelled":
            continue

        row_qty  = float(row.quantity or 0)
        row_rate = float(row.rate or 0)

        total_qty    += row_qty
        total_amount += row_qty * row_rate

    cart.total_quantity = total_qty
    cart.total_amount   = total_amount 
  
  
  
# def _recalculate_totals(doc):
#     """Total quantity, sub total, GST aur total amount recalculate karo (Cancelled rows exclude)."""
#     total_qty = 0
#     sub_total = 0

#     for row in doc.items:
#         if (row.status or "") == "Cancelled":
#             continue
#         total_qty += (row.quantity or 0)
#         sub_total += (row.amount   or 0)

#     gst_amount = round(sub_total * 0.03, 2)   

#     doc.total_quantity = total_qty
#     doc.sub_total       = sub_total                        
#     doc.gst_amount       = gst_amount                       
#     doc.total_amount   = round(sub_total + gst_amount, 2)   


# # ── Helper: Cart totals recalculate ───────────────────────────────────────────
# def _recalculate_cart_totals(cart):
#     """
#     Cart ke active items se total_quantity, sub_total, GST(3%) aur
#     total_amount compute karo. cancelled wali rows skip hongi.
#     cart.save() se pehle call karo.
#     """
#     total_qty = 0.0
#     sub_total = 0.0

#     for row in cart.items:
#         row_status = (getattr(row, "status", "Add To Cart") or "Add To Cart")
#         if row_status == "Cancelled":
#             continue

#         row_qty  = float(row.quantity or 0)
#         row_rate = float(row.rate or 0)

#         total_qty += row_qty
#         sub_total += row_qty * row_rate

#     gst_amount = round(sub_total * 0.03, 2)   # ← added: 3% GST

#     cart.total_quantity = total_qty
#     cart.sub_total       = sub_total                        # ← added
#     cart.gst_amount       = gst_amount                       # ← added
#     cart.total_amount   = round(sub_total + gst_amount, 2)   # ← GST included    



def _get_active_cart(customer):
    """Customer ka existing 'Add To Cart' status wala doc dhundta hai."""
    cart_name = frappe.db.get_value(
        "Add To Cart Portal Item",
        {"customer": customer, "status": "Add To Cart"},
        "name",
        order_by="creation asc",
    )
    if cart_name:
        return frappe.get_doc("Add To Cart Portal Item", cart_name)
    return None

  

# ── Main API ───────────────────────────────────────────────────────────────────

# @frappe.whitelist()
# def add_to_cart(
#     customer,
#     item_code,
#     quantity=1,
#     rate=0,
#     bom=None,
#     uom=None,
#     user=None,
#     as_per_design=0,         # checkbox → 0 or 1
#     as_per_customization=0,  # checkbox → 0 or 1
#     customized_data=None,    # JSON string
#     job_work=0,
#     out_right=0,
#     hybrid=0,
#     added_by=None,
#     added_date=None,):
#     """
#     Smart Add To Cart API — 'Add To Cart Portal Item' doctype ke liye.
 
#     Fingerprint (match ke liye ye fields same hone chahiye):
#         item_code + as_per_design + as_per_customization
#         + job_work + out_right + hybrid + customized_data (JSON normalized) + bom
 
#       Sab same  → existing row ki quantity badha do
#       Kuch alag → naya row add karo
 
#     Params:
#         customer              : Customer name (required)
#         item_code             : Item code (required)
#         quantity              : Quantity to add (default 1)
#         rate                  : Rate (0 ho toh 0 hi rahega)
#         bom                   : BOM name (auto-fetched if not passed)
#         uom                   : Unit of measure (auto-fetched from Item if not passed)
#         user                  : User (default: session user)
#         as_per_design         : checkbox 0/1 (default 0)
#         as_per_customization  : checkbox 0/1 (default 0)
#         customized_data       : JSON string with customization details
#         job_work              : checkbox 0/1 (default 0)
#         out_right             : checkbox 0/1 (default 0)
#         hybrid                : checkbox 0/1 (default 0)
#         added_by              : Added by (default: session user)
#         added_date            : Date (default: today)
#     """
 
#     if not customer:
#         frappe.throw(_("Customer required hai."))
#     if not item_code:
#         frappe.throw(_("Item Code required hai."))
 
#     qty             = int(quantity or 1)
#     calculated_rate = float(rate or 0)
 
#     # ── BOM auto-fetch ─────────────────────────────────────────────────────────
#     if not bom:
#         bom = frappe.db.get_value(
#             "BOM",
#             {"item": item_code, "is_active": 1, "is_default": 1},
#             "name",
#             order_by="creation desc",
#         )
 
#     # ── UOM auto-fetch ─────────────────────────────────────────────────────────
#     if not uom:
#         uom = frappe.db.get_value("Item", item_code, "stock_uom") or ""
 
#     # ── Item image ─────────────────────────────────────────────────────────────
#     item_image = frappe.db.get_value("Item", item_code, "image") or ""
 
#     # ── Checkbox flags ─────────────────────────────────────────────────────────
#     is_as_per_design        = int(as_per_design        or 0)
#     is_as_per_customization = int(as_per_customization or 0)
#     is_job_work             = int(job_work             or 0)
#     is_out_right            = int(out_right            or 0)
#     is_hybrid               = int(hybrid               or 0)
 
#     # ── User validate ──────────────────────────────────────────────────────────
#     raw_user     = user or frappe.session.user
#     current_user = raw_user if frappe.db.exists("User", raw_user) else ""
 
#     # ── Normalize incoming values ──────────────────────────────────────────────
#     incoming_customized_data = _normalize_json(customized_data)
#     incoming_bom             = (bom or "").strip()
 
#     # ── Get or create cart ─────────────────────────────────────────────────────
#     doc    = _get_active_cart(customer)
#     is_new = False
 
#     if not doc:
#         is_new         = True
#         doc            = frappe.new_doc("Add To Cart Portal Item")
#         doc.customer   = customer
#         doc.added_by   = added_by or frappe.session.user
#         doc.added_date = added_date or frappe.utils.today()
#         doc.status     = "Add To Cart"
#         doc.company    = (
#             frappe.defaults.get_user_default("company")
#             or frappe.db.get_single_value("Global Defaults", "default_company")
#         )
#         doc.currency   = frappe.defaults.get_user_default("currency") or "INR"
 
#     # ── Match existing row using fingerprint ───────────────────────────────────
#     item_found = False
 
#     for row in doc.items:
#         if row.item_code != item_code:
#             continue
 
#         if (
#             int(row.as_per_design        or 0) == is_as_per_design
#             and int(row.as_per_customization or 0) == is_as_per_customization
#             and int(row.job_work             or 0) == is_job_work
#             and int(row.out_right            or 0) == is_out_right
#             and int(row.hybrid               or 0) == is_hybrid
#             and _normalize_json(row.customized_data) == incoming_customized_data
#             and (row.bom or "").strip()              == incoming_bom
#         ):
#             # Match mila → quantity badha do
#             row.quantity = (row.quantity or 0) + qty
#             row.rate     = calculated_rate
#             row.amount   = row.quantity * calculated_rate
#             row.user     = current_user
#             item_found   = True
#             break
 
#     # ── Naya row ───────────────────────────────────────────────────────────────
#     if not item_found:
#         doc.append("items", {
#             "item_code"             : item_code,
#             "bom"                   : bom or "",
#             "uom"                   : uom,
#             "quantity"              : qty,
#             "rate"                  : calculated_rate,
#             "amount"                : qty * calculated_rate,
#             "image"                 : item_image,
#             "user"                  : current_user,
#             "status"                : "Add To Cart",
#             "as_per_design"         : is_as_per_design,
#             "as_per_customization"  : is_as_per_customization,
#             "job_work"              : is_job_work,
#             "out_right"             : is_out_right,
#             "hybrid"                : is_hybrid,
#             "customized_data"       : customized_data or "",
#         })
 
#     # ── Save ───────────────────────────────────────────────────────────────────
#     _recalculate_totals(doc)
 
#     if is_new:
#         doc.insert(ignore_permissions=True)
#     else:
#         doc.save(ignore_permissions=True)
 
#     frappe.db.commit()
 
#     return {
#         "success"        : True,
#         "action"         : "created" if is_new else "updated",
#         "item_action"    : "row_added" if not item_found else "qty_updated",
#         "order"          : doc.name,
#         "total_quantity" : doc.total_quantity,
#         "total_amount"   : doc.total_amount,
#         "item_rate"      : calculated_rate,
#     }


@frappe.whitelist()
def add_to_cart(
    customer,
    item_code,
    quantity=1,
    rate=0,
    bom=None,
    uom=None,
    user=None,
    as_per_design=0,
    as_per_customization=0,
    customized_data=None,
    job_work=0,
    out_right=0,
    hybrid=0,
    added_by=None,
    added_date=None,
    diamond_quality=None,   # ← added
    metal_touch=None,       # ← added
):
    if not customer:
        frappe.throw(_("Customer required hai."))
    if not item_code:
        frappe.throw(_("Item Code required hai."))

    qty             = int(quantity or 1)
    calculated_rate = float(rate or 0)

    # ── BOM auto-fetch ─────────────────────────────────────────────────────────
    if not bom:
        bom = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1, "is_default": 1, "bom_type": "Finish Goods"},  # ← added
            "name",
            order_by="creation desc",
        )

    # ── diamond_quality auto-fetch ─────────────────────────────────────────────
    if bom and not diamond_quality:
        diamond_quality = frappe.db.get_value("BOM", bom, "diamond_quality")

    # ── metal_touch auto-fetch ─────────────────────────────────────────────────
    if bom and not metal_touch:
        metal_touch = frappe.db.get_value("BOM", bom, "metal_touch")

    # ── UOM auto-fetch ─────────────────────────────────────────────────────────
    if not uom:
        uom = frappe.db.get_value("Item", item_code, "stock_uom") or ""

    # ── Item image ─────────────────────────────────────────────────────────────
    item_image = frappe.db.get_value("Item", item_code, "image") or ""

    # ── Checkbox flags ─────────────────────────────────────────────────────────
    is_as_per_design        = int(as_per_design        or 0)
    is_as_per_customization = int(as_per_customization or 0)
    is_job_work             = int(job_work             or 0)
    is_out_right            = int(out_right            or 0)
    is_hybrid               = int(hybrid               or 0)

    # ── User validate ──────────────────────────────────────────────────────────
    raw_user     = user or frappe.session.user
    current_user = raw_user if frappe.db.exists("User", raw_user) else ""

    # ── Price calculate (rate 0 ho toh auto-calculate) ─────────────────────────
    if bom and (not rate or float(rate) == 0):
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
            calculated_rate = round(dia_amount + gem_amount + metal_total + finding_total, 2)
        except Exception as e:
            frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
            calculated_rate = float(rate or 0)

    # ── Normalize incoming values ──────────────────────────────────────────────
    incoming_customized_data = _normalize_json(customized_data)
    incoming_bom             = (bom or "").strip()

    # ── Get or create cart ─────────────────────────────────────────────────────
    doc    = _get_active_cart(customer)
    is_new = False

    if not doc:
        is_new         = True
        doc            = frappe.new_doc("Add To Cart Portal Item")
        doc.customer   = customer
        doc.added_by   = added_by or frappe.session.user
        doc.added_date = added_date or frappe.utils.today()
        doc.status     = "Add To Cart"
        doc.company    = (
            frappe.defaults.get_user_default("company")
            or frappe.db.get_single_value("Global Defaults", "default_company")
        )
        doc.currency   = frappe.defaults.get_user_default("currency") or "INR"

    # ── Match existing row using fingerprint ───────────────────────────────────
    item_found = False

    for row in doc.items:
        if row.item_code != item_code:
            continue
        
        if (row.status or "") != "Add To Cart":
            continue

        if (
            int(row.as_per_design        or 0) == is_as_per_design
            and int(row.as_per_customization or 0) == is_as_per_customization
            and int(row.job_work             or 0) == is_job_work
            and int(row.out_right            or 0) == is_out_right
            and int(row.hybrid               or 0) == is_hybrid
            and _normalize_json(row.customized_data) == incoming_customized_data
            and (row.bom or "").strip()              == incoming_bom
        ):
            row.quantity = (row.quantity or 0) + qty
            row.rate     = calculated_rate
            row.amount   = row.quantity * calculated_rate
            row.user     = current_user
            item_found   = True
            break

    # ── Naya row ───────────────────────────────────────────────────────────────
    if not item_found:
        doc.append("items", {
            "item_code"            : item_code,
            "bom"                  : bom or "",
            "uom"                  : uom,
            "quantity"             : qty,
            "rate"                 : calculated_rate,
            "amount"               : qty * calculated_rate,
            "image"                : item_image,
            "user"                 : current_user,
            "status"               : "Add To Cart",
            "as_per_design"        : is_as_per_design,
            "as_per_customization" : is_as_per_customization,
            "job_work"             : is_job_work,
            "out_right"            : is_out_right,
            "hybrid"               : is_hybrid,
            "customized_data"      : customized_data or "",
        })

    # ── Save ───────────────────────────────────────────────────────────────────
    _recalculate_totals(doc)

    if is_new:
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success"        : True,
        "action"         : "created" if is_new else "updated",
        "item_action"    : "row_added" if not item_found else "qty_updated",
        "order"          : doc.name,
        "total_quantity" : doc.total_quantity,
        "total_amount"   : doc.total_amount,
        "item_rate"      : calculated_rate,
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


# ── Cart ke items ka rate/amount live pricing se refresh karo ──────────────

def _refresh_cart_prices(cart):
    """
    Har row ka bom se diamond_quality/metal_touch nikaal ke get_item_price
    call karta hai aur rate + amount live update karta hai (in-memory only,
    DB me save nahi karta — response fresh dikhane ke liye).
    """
    changed = False

    for row in cart.items:
        if not row.bom:
            continue

        diamond_quality = frappe.db.get_value("BOM", row.bom, "diamond_quality")
        metal_touch     = frappe.db.get_value("BOM", row.bom, "metal_touch")

        live_rate = _get_live_rate(
            customer=cart.customer,
            item_code=row.item_code,
            bom=row.bom,
            diamond_quality=diamond_quality,
            metal_touch=metal_touch,
            fallback_rate=row.rate or 0,
        )

        if live_rate and live_rate != row.rate:
            row.rate   = live_rate
            row.amount = (row.quantity or 0) * live_rate
            changed    = True

    if changed:
        # _recalculate_totals(cart)
        _recalculate_cart_totals(cart)

    return cart


@frappe.whitelist(methods=["GET", "POST"])
def get_cart_orders(customer=None, user=None, status_filter=None):
    """
    Cart orders fetch karo — customer ya user se.

    Case 1 — customer pass karo:
        Us customer ka active 'Add To Cart' doc return karega.

    Case 2 — user pass karo:
        Us user ke saare assigned customers ke active carts return karega.

    status_filter (optional):
        Sirf us status ki item rows return karega.
        None ho toh "Cancelled" wali rows automatically skip hongi.

    Postman:
        GET .../get_cart_orders?customer=Rajan Shah
        GET .../get_cart_orders?user=rajan@example.com
        GET .../get_cart_orders?customer=Rajan Shah&status_filter=Add To Cart
    """

    # ── Case 1: Customer se fetch ──────────────────────────────────────────────
    if customer:
        active_cart = frappe.db.get_value(
            "Add To Cart Portal Item",
            {"customer": customer, "status": "Add To Cart"},
            "name",
            order_by="creation asc",
        )

        if not active_cart:
            return {"success": True, "orders": []}

        cart  = frappe.get_doc("Add To Cart Portal Item", active_cart)
        cart  = _refresh_cart_prices(cart)  
        items = _serialize_items(cart.items, status_filter=status_filter or "Add To Cart")

        return {
            "success": True,
            "orders": [{
                "name"           : cart.name,
                "customer"       : cart.customer,
                "added_by"       : cart.added_by or "",
                "added_date"     : str(cart.added_date or ""),
                "status"         : cart.status,
                "company"        : cart.company or "",
                "currency"       : cart.currency or "",
                "total_quantity" : cart.total_quantity or 0,
                "total_amount"   : cart.total_amount or 0,
                "items"          : items,
            }]
        }

    # ── Case 2: User se fetch (assigned customers ke carts) ───────────────────
    if user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent",
        )

        if not assigned_customers:
            return {"success": True, "orders": []}

        result = []
        for cust in assigned_customers:
            active_cart = frappe.db.get_value(
                "Add To Cart Portal Item",
                {"customer": cust, "status": "Add To Cart"},
                "name",
                order_by="creation asc",
            )

            if not active_cart:
                continue

            cart  = frappe.get_doc("Add To Cart Portal Item", active_cart)
            cart  = _refresh_cart_prices(cart)  
            items = _serialize_items(cart.items, status_filter=status_filter)

            if not items:
                continue

            result.append({
                "name"           : cart.name,
                "customer"       : cart.customer,
                "added_by"       : cart.added_by or "",
                "added_date"     : str(cart.added_date or ""),
                "status"         : cart.status,
                "company"        : cart.company or "",
                "currency"       : cart.currency or "",
                "total_quantity" : cart.total_quantity or 0,
                "total_amount"   : cart.total_amount or 0,
                "items"          : items,
            })

        return {"success": True, "orders": result}

    frappe.throw(_("Customer or User required."))


# @frappe.whitelist(methods=["GET", "POST"])
# def get_cart_orders(customer=None, user=None, status_filter=None):
#     """
#     Cart orders fetch karo — customer ya user se.
 
#     Case 1 — customer pass karo:
#         Us customer ka active 'Add To Cart' doc return karega.
 
#     Case 2 — user pass karo:
#         Us user ke saare assigned customers ke active carts return karega.
 
#     status_filter (optional):
#         Sirf us status ki item rows return karega.
#         None ho toh "Cancelled" wali rows automatically skip hongi.
 
#     Postman:
#         GET .../get_cart_orders?customer=Rajan Shah
#         GET .../get_cart_orders?user=rajan@example.com
#         GET .../get_cart_orders?customer=Rajan Shah&status_filter=Add To Cart
#     """
 
#     # ── Case 1: Customer se fetch ──────────────────────────────────────────────
#     if customer:
#         active_cart = frappe.db.get_value(
#             "Add To Cart Portal Item",
#             {"customer": customer, "status": "Add To Cart"},
#             "name",
#             order_by="creation asc",
#         )
 
#         if not active_cart:
#             return {"success": True, "orders": []}
 
#         cart  = frappe.get_doc("Add To Cart Portal Item", active_cart)
#         items = _serialize_items(cart.items, status_filter=status_filter or "Add To Cart")
 
#         return {
#             "success": True,
#             "orders": [{
#                 "name"           : cart.name,
#                 "customer"       : cart.customer,
#                 "added_by"       : cart.added_by or "",
#                 "added_date"     : str(cart.added_date or ""),
#                 "status"         : cart.status,
#                 "company"        : cart.company or "",
#                 "currency"       : cart.currency or "",
#                 "total_quantity" : cart.total_quantity or 0,
#                 "total_amount"   : cart.total_amount or 0,
#                 "items"          : items,
#             }]
#         }
 
#     # ── Case 2: User se fetch (assigned customers ke carts) ───────────────────
#     if user:
#         assigned_customers = frappe.get_all(
#             "Customer Representatives",
#             filters={"user_id": user},
#             pluck="parent",
#         )
 
#         if not assigned_customers:
#             return {"success": True, "orders": []}
 
#         result = []
#         for cust in assigned_customers:
#             active_cart = frappe.db.get_value(
#                 "Add To Cart Portal Item",
#                 {"customer": cust, "status": "Add To Cart"},
#                 "name",
#                 order_by="creation asc",
#             )
 
#             if not active_cart:
#                 continue
 
#             cart  = frappe.get_doc("Add To Cart Portal Item", active_cart)
#             items = _serialize_items(cart.items, status_filter=status_filter)
 
#             if not items:
#                 continue
 
#             result.append({
#                 "name"           : cart.name,
#                 "customer"       : cart.customer,
#                 "added_by"       : cart.added_by or "",
#                 "added_date"     : str(cart.added_date or ""),
#                 "status"         : cart.status,
#                 "company"        : cart.company or "",
#                 "currency"       : cart.currency or "",
#                 "total_quantity" : cart.total_quantity or 0,
#                 "total_amount"   : cart.total_amount or 0,
#                 "items"          : items,
#             })
 
#         return {"success": True, "orders": result}
 
#     frappe.throw(_("Customer or User required."))


# ── Remove Row ─────────────────────────────────────────────────────────────────

# @frappe.whitelist()
# def remove_from_cart(customer, row_name):
#     """
#     Cart ki specific row ka status 'Cancelled' karo.
#     row_name = child table row ka unique 'name' field
#     """
#     if not customer:
#         frappe.throw(_("Customer required hai."))

#     doc = _get_active_cart(customer)
#     if not doc:
#         frappe.throw(_("Koi active cart nahi hai."))

#     # ── Row dhundo aur status Cancelled karo ──────────────────────────────────
#     row_found = False
#     for row in doc.items:
#         if row.name == row_name:
#             row.status = "Cancelled"
#             row_found  = True
#             break

#     if not row_found:
#         frappe.throw(_(f"Row '{row_name}' can't find item."))

#     _recalculate_cart_totals(doc)
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "success": True,
#         "message": "Cancelled Item.",
#         "name"   : doc.name,
#     }

@frappe.whitelist()
def cancel_cart_item(order_name, item_code, row_name=None, user=None):
    doc = frappe.get_doc("Add To Cart Portal Item", order_name)

    found = False

    for row in doc.items:
        if row.item_code != item_code:
            continue

        if getattr(row, "status", "Add To Cart") != "Add To Cart":
            continue

        if row_name and row.name != row_name:
            continue

        row.status = "Cancelled"
        found = True
        break

    if not found:
        frappe.throw(_("Item not found in cart"))

    # Sirf Add To Cart wale items
    active_items = [
        r for r in doc.items
        if getattr(r, "status", "Add To Cart") == "Add To Cart"
    ]

    # Agar saare items cancel ho gaye to order bhi cancel kar do
    # if not active_items:
    #     doc.status = "Cancel Order"   # Agar parent order me ye status hai
        # Ya doc.status = "Cancelled" agar parent me Cancelled hai

    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "remaining_active_items": len(active_items),
    }

# ── confirm cart order ─────────────────────────────────────────────────────────────────

# @frappe.whitelist()
# def confirm_cart_orders(customer, order_date=None, notes=None, user=None, row_names=None):
#     """
#     Cart ke selected ya saare "Add To Cart" items ko Portal Order mein place karo.
 
#     Flow:
#         1. Customer ka active cart dhundo (Add To Cart Portal Item)
#         2. row_names pass kiye hain -> sirf wo items place karo
#            row_names nahi pass kiye -> saare "Add To Cart" items place karo
#         3. Naya Portal Order doc banao un items ke saath
#         4. Cart ke wo items delete karo (status change nahi, directly remove)
#         5. Cart ke totals recalculate karo
 
#     Postman - Saare items:
#         { "customer": "Rajan Shah", "order_date": "2024-06-27" }
 
#     Postman - Selected items:
#         { "customer": "Rajan Shah", "row_names": ["abc123", "def456"] }
#     """
 
#     if not customer:
#         frappe.throw(_("Customer required hai."))
 
#     # ── Active cart dhundo ─────────────────────────────────────────────────────
#     cart_name = frappe.db.get_value(
#         "Add To Cart Portal Item",
#         {"customer": customer, "status": "Add To Cart"},
#         "name",
#         order_by="creation asc",
#     )
 
#     if not cart_name:
#         frappe.throw(_("Koi active cart nahi mila."))
 
#     cart = frappe.get_doc("Add To Cart Portal Item", cart_name)
 
#     # ── row_names parse karo (string se list) ─────────────────────────────────
#     if isinstance(row_names, str):
#         row_names = json.loads(row_names)
 
#     # ── Items filter karo ─────────────────────────────────────────────────────
#     if row_names:
#         # Sirf selected rows lo — "Add To Cart" status bhi check karo
#         selected = set(row_names)
#         active_items = [
#             r for r in cart.items
#             if r.name in selected
#             and (getattr(r, "status", "") or "") == "Add To Cart"
#         ]
#         if not active_items:
#             frappe.throw(_("Selected items cart mein nahi mile ya already placed hain."))
#     else:
#         # Saare "Add To Cart" status wale items lo
#         active_items = [r for r in cart.items if (getattr(r, "status", "") or "") == "Add To Cart"]
#         if not active_items:
#             frappe.throw(_("Cart mein koi active item nahi hai."))
 
#     final_order_date = frappe.utils.getdate(order_date) if order_date else frappe.utils.today()
#     current_user     = user or frappe.session.user
 
#     # ── Naya Portal Order banao ────────────────────────────────────────────────
#     portal_order            = frappe.new_doc("Portal Order")
#     portal_order.customer   = customer
#     portal_order.order_by   = current_user
#     portal_order.order_date = final_order_date
#     portal_order.status     = "Ordered"
#     portal_order.company    = cart.company or (
#         frappe.defaults.get_user_default("company")
#         or frappe.db.get_single_value("Global Defaults", "default_company")
#     )
#     portal_order.currency   = cart.currency or "INR"
 
#     if notes:
#         portal_order.notes = notes
 
#     # ── Cart items → Portal Order items ───────────────────────────────────────
#     for row in active_items:
#         portal_order.append("items", {
#             "item_code"         : row.item_code,
#             "bom"               : row.bom or "",
#             "uom"               : row.uom or "",
#             "quantity"          : row.quantity or 0,
#             "rate"              : row.rate or 0,
#             "amount"            : (row.quantity or 0) * (row.rate or 0),
#             "user"              : getattr(row, "user", "") or "",
#             "status"            : "Ordered",
#             "as_per_design"     : getattr(row, "as_per_design", 0) or 0,
#             "as_per_customization"        : getattr(row, "as_per_customization", 0) or 0,
#             "job_work"           : getattr(row, "job_work", 0) or 0,
#             "out_right"          : getattr(row, "out_right", 0) or 0,
#             "hybrid"            : getattr(row, "hybrid", 0) or 0,
#             "customized_data"   : getattr(row, "customized_data", "") or "",
#         })
 
#     portal_order.insert(ignore_permissions=True)
 
#     # ── Placed items cart se hata do (status change nahi, delete karo) ──────────
#     placed_item_names = {row.name for row in active_items}
#     cart.items = [row for row in cart.items if row.name not in placed_item_names]
 
#     # ── Cart totals recalculate karo ───────────────────────────────────────────
#     _recalculate_totals(cart)
#     cart.save(ignore_permissions=True)
    
#     # if not cart.items:
#     #     frappe.delete_doc("Add To Cart Portal Item", cart.name, ignore_permissions=True)
 
#     frappe.db.commit()
 
#     return {
#         "success"       : True,
#         "message"       : "Your Order has been Placed!",
#         "portal_order"  : portal_order.name,
#         "cart"          : cart.name,
#         "order_date"    : str(final_order_date),
#         "order_by"      : current_user,
#         "total_quantity": portal_order.total_quantity or 0,
#         "total_amount"  : portal_order.total_amount or 0,
#         "items_ordered" : len(active_items),
#     }
    
# Confirm Cart order---------------


# @frappe.whitelist()
# def confirm_cart_orders(customer, order_date=None, notes=None, user=None, row_names=None):
#     """
#     Cart ke selected ya saare "Add To Cart" items ko Portal Order mein place karo.
 
#     Flow:
#         1. Customer ka active cart dhundo (Add To Cart Portal Item)
#         2. row_names pass kiye hain -> sirf wo items place karo
#            row_names nahi pass kiye -> saare "Add To Cart" items place karo
#         3. Naya Portal Order doc banao un items ke saath
#         4. Cart ke wo items delete karo (status change nahi, directly remove)
#         5. Cart ke totals recalculate karo
 
#     Postman - Saare items:
#         { "customer": "Rajan Shah", "order_date": "2024-06-27" }
 
#     Postman - Selected items:
#         { "customer": "Rajan Shah", "row_names": ["abc123", "def456"] }
#     """
 
#     if not customer:
#         frappe.throw(_("Customer required hai."))
 
#     # ── Active cart dhundo ─────────────────────────────────────────────────────
#     cart_name = frappe.db.get_value(
#         "Add To Cart Portal Item",
#         {"customer": customer, "status": "Add To Cart"},
#         "name",
#         order_by="creation asc",
#     )
 
#     if not cart_name:
#         frappe.throw(_("Koi active cart nahi mila."))
 
#     cart = frappe.get_doc("Add To Cart Portal Item", cart_name)
 
#     # ── row_names parse karo (string se list) ─────────────────────────────────
#     if isinstance(row_names, str):
#         row_names = json.loads(row_names)
 
#     # ── Items filter karo ─────────────────────────────────────────────────────
#     if row_names:
#         # Sirf selected rows lo — "Add To Cart" status bhi check karo
#         selected = set(row_names)
#         active_items = [
#             r for r in cart.items
#             if r.name in selected
#             and (getattr(r, "status", "") or "") == "Add To Cart"
#         ]
#         if not active_items:
#             frappe.throw(_("Selected items cart mein nahi mile ya already placed hain."))
#     else:
#         # Saare "Add To Cart" status wale items lo
#         active_items = [r for r in cart.items if (getattr(r, "status", "") or "") == "Add To Cart"]
#         if not active_items:
#             frappe.throw(_("Cart mein koi active item nahi hai."))
 
#     final_order_date = frappe.utils.getdate(order_date) if order_date else frappe.utils.today()
#     current_user     = user or frappe.session.user
 
#     # ── Naya Portal Order banao ────────────────────────────────────────────────
#     portal_order            = frappe.new_doc("Portal Order")
#     portal_order.customer   = customer
#     portal_order.order_by   = current_user
#     portal_order.order_date = final_order_date
#     portal_order.status     = "Ordered"
#     portal_order.company    = cart.company or (
#         frappe.defaults.get_user_default("company")
#         or frappe.db.get_single_value("Global Defaults", "default_company")
#     )
#     portal_order.currency   = cart.currency or "INR"
 
#     if notes:
#         portal_order.notes = notes
 
#     # ── Cart items → Portal Order items ───────────────────────────────────────
#     for row in active_items:
#         row_qty    = row.quantity or 0
#         row_rate   = row.rate or 0
#         row_amount = round(row_qty * row_rate, 2)
 
#         portal_order.append("items", {
#             "item_code"         : row.item_code,
#             "bom"               : row.bom or "",
#             "uom"               : row.uom or "",
#             "quantity"          : row_qty,
#             "rate"              : row_rate,
#             "amount"            : row_amount,
#             "user"              : getattr(row, "user", "") or "",
#             "status"            : "Ordered",
#             "as_per_design"     : getattr(row, "as_per_design", 0) or 0,
#             "as_per_customization"        : getattr(row, "as_per_customization", 0) or 0,
#             "job_work"           : getattr(row, "job_work", 0) or 0,
#             "out_right"          : getattr(row, "out_right", 0) or 0,
#             "hybrid"            : getattr(row, "hybrid", 0) or 0,
#             "customized_data"   : getattr(row, "customized_data", "") or "",
#         })
 
#     portal_order.insert(ignore_permissions=True)
 
#     # ── Portal Order totals directly DB mein set karo (controller override se bachne ke liye) ──
#     total_qty    = sum(row.quantity or 0 for row in active_items)
#     total_amount = round(sum((row.quantity or 0) * (row.rate or 0) for row in active_items), 2)
 
#     frappe.db.set_value(
#         "Portal Order",
#         portal_order.name,
#         {
#             "total_quantity" : total_qty,
#             "total_amount"   : total_amount,
#         },
#         update_modified=False,
#     )
 
#     # ── Placed items cart se hata do (status change nahi, delete karo) ──────────
#     placed_item_names = {row.name for row in active_items}
#     cart.items = [row for row in cart.items if row.name not in placed_item_names]
 
#     # ── Cart totals recalculate karo ───────────────────────────────────────────
#     _recalculate_totals(cart)
#     cart.save(ignore_permissions=True)
 
#     frappe.db.commit()
 
#     return {
#         "success"       : True,
#         "message"       : "Order successfully place ho gaya!",
#         "portal_order"  : portal_order.name,
#         "cart"          : cart.name,
#         "order_date"    : str(final_order_date),
#         "order_by"      : current_user,
#         "total_quantity": portal_order.total_quantity or 0,
#         "total_amount"  : portal_order.total_amount or 0,
#         "items_ordered" : len(active_items),
#     }
 
 
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

    return {
        "success"       : True,
        "message"       : "Order successfully place ho gaya!",
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
 
 
# @frappe.whitelist(methods=["POST"])
# def update_order_item_qty(cart_name=None, customer=None, row_name=None, item_code=None, quantity=None):
#     """
#     Cart item ki quantity update karo.

#     Params:
#         cart_name   (optional) : Direct cart doc name
#         customer    (optional) : Customer name se active cart dhundhega
#         row_name    (optional) : Child row ka name (sabse accurate)
#         item_code   (optional) : item_code se row dhundho (row_name nahi ho toh)
#         quantity    (required) : Naya quantity (0 = row delete)

#     Priority: row_name > item_code

#     Postman:
#         POST .../update_cart_item_qty
#         Body: { "cart_name": "ATC-0001", "row_name": "ATC-0001-1", "quantity": 5 }
#     """

#     # ── Validation ─────────────────────────────────────────────────────────────
#     if not row_name and not item_code:
#         frappe.throw(_("row_name ya item_code required hai."))

#     if quantity is None:
#         frappe.throw(_("quantity required hai."))

#     try:
#         quantity = float(quantity)
#     except (ValueError, TypeError):
#         frappe.throw(_("quantity valid number hona chahiye."))

#     if quantity < 0:
#         frappe.throw(_("quantity negative nahi ho sakti."))

#     # ── Cart resolve karo ──────────────────────────────────────────────────────
#     if not cart_name and not customer:
#         frappe.throw(_("cart_name ya customer required hai."))

#     if not cart_name:
#         cart_name = frappe.db.get_value(
#             "Add To Cart Portal Item",
#             {"customer": customer, "status": "Add To Cart"},
#             "name",
#             order_by="creation asc",
#         )
#         if not cart_name:
#             frappe.throw(_("Customer '{0}' ka koi active cart nahi mila.").format(customer))

#     # ── Doc load karo ─────────────────────────────────────────────────────────
#     cart = frappe.get_doc("Add To Cart Portal Item", cart_name)

#     if cart.status != "Add To Cart":
#         frappe.throw(
#             _("Sirf active carts update ho sakte hain. Current status: {0}").format(cart.status)
#         )

#     # ── Target row dhundho ────────────────────────────────────────────────────
#     target_row = None

#     if row_name:
#         # Direct name se — most accurate
#         for row in cart.items:
#             if row.name == row_name:
#                 target_row = row
#                 break
#         if not target_row:
#             frappe.throw(_("Row '{0}' cart '{1}' mein nahi mila.").format(row_name, cart_name))

#     else:
#         # item_code se — pehla match lega
#         for row in cart.items:
#             if row.item_code == item_code:
#                 target_row = row
#                 break
#         if not target_row:
#             frappe.throw(_("item_code '{0}' cart mein nahi mila.").format(item_code))

#     # ── Update ya Delete ───────────────────────────────────────────────────────
#     if quantity == 0:
#         cart.remove(target_row)
#         action = "deleted"

#         # Cart empty ho gayi toh status update karo
#         active_rows = [
#             r for r in cart.items
#             if (getattr(r, "status", "Add To Cart") or "Add To Cart") != "Cancelled"
#         ]
#         if not active_rows:
#             cart.status = "Empty"

#     else:
#         target_row.quantity = quantity
#         action = "updated"

#     # ── Cart totals recalculate karo ──────────────────────────────────────────
#     _recalculate_cart_totals(cart)

#     # ── Save ───────────────────────────────────────────────────────────────────
#     cart.save(ignore_permissions=True)
#     frappe.db.commit()

#     # ── Response ───────────────────────────────────────────────────────────────
#     items = _serialize_items(cart.items, status_filter=None)

#     return {
#         "success"        : True,
#         "action"         : action,        
#         "cart_name"      : cart.name,
#         "customer"       : cart.customer,
#         "total_quantity" : cart.total_quantity or 0,
#         "total_amount"   : cart.total_amount or 0,
#         "items"          : items,
#     }


@frappe.whitelist()
def update_order_item_qty(order_name, item_code, quantity, row_name=None, user=None):
    qty = float(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))

    max_retries = 3
    for attempt in range(max_retries):
        try:
            doc = frappe.get_doc("Portal Order", order_name)

            if doc.status == "Cancel Order":
                frappe.throw(_("Cannot modify a cancelled order"))

            found   = False
            old_qty = None

            for row in doc.items:
                if row.item_code != item_code:
                    continue

                row_status = getattr(row, "status", "Draft")
                if row_status == "Cancel Order":
                    continue

                # row_name se exact row match
                if row_name and row.name != row_name:
                    continue

                old_qty      = row.quantity
                row.quantity = qty
                row.amount   = qty * (row.rate or 0)
                found        = True
                break

            if not found:
                frappe.throw(_("Item not found in order"))

            _recalculate_totals_draft_only(doc)
            doc.save(ignore_permissions=True)

            changed_by = user or frappe.session.user
            if old_qty is not None and old_qty != qty and doc.status == "Ordered":
                doc.add_comment(
                    comment_type="Info",
                    text=f"<b>{changed_by}</b> changed quantity of <b>{item_code}</b> from <b>{int(old_qty)}</b> to <b>{int(qty)}</b>"
                )

            frappe.db.commit()

            return {
                "success":        True,
                "order":          doc.name,
                "total_quantity": doc.total_quantity,
                "total_amount":   doc.total_amount,
            }

        except frappe.exceptions.TimestampMismatchError:
            if attempt == max_retries - 1:
                frappe.throw(_("Too many simultaneous updates. Please try again."))
            import time
            time.sleep(0.1 * (attempt + 1))
            continue


@frappe.whitelist()
def update_cart_item_qty(order_name, item_code, quantity, row_name=None, user=None):
    qty = float(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))

    max_retries = 3
    for attempt in range(max_retries):
        try:
            doc = frappe.get_doc("Add To Cart Portal Item", order_name)

            if doc.status == "Cancelled":
                frappe.throw(_("Cannot modify a cancelled order"))

            found   = False
            old_qty = None

            for row in doc.items:
                if row.item_code != item_code:
                    continue

                row_status = getattr(row, "status", "Draft")
                if row_status == "Cancelled":
                    continue

                #exact match with row_name to row
                if row_name and row.name != row_name:
                    continue

                old_qty      = row.quantity
                row.quantity = qty
                row.amount   = qty * (row.rate or 0)
                found        = True
                break

            if not found:
                frappe.throw(_("Item not found in order"))

            _recalculate_totals_draft_only(doc)
            doc.save(ignore_permissions=True)

            changed_by = user or frappe.session.user
            if old_qty is not None and old_qty != qty and doc.status == "Ordered":
                doc.add_comment(
                    comment_type="Info",
                    text=f"<b>{changed_by}</b> changed quantity of <b>{item_code}</b> from <b>{int(old_qty)}</b> to <b>{int(qty)}</b>"
                )

            frappe.db.commit()

            return {
                "success":        True,
                "order":          doc.name,
                "total_quantity": doc.total_quantity,
                "total_amount":   doc.total_amount,
            }

        except frappe.exceptions.TimestampMismatchError:
            if attempt == max_retries - 1:
                frappe.throw(_("Too many simultaneous updates. Please try again."))
            import time
            time.sleep(0.1 * (attempt + 1))
            continue


# Getting cancelled Item from add to cart___________________________________________________

# ── Helper: Sirf cancelled rows serialize karo ────────────────────────────────
def _serialize_cancelled_items(items):
    """
    Sirf "Cancel Order" ya "Cancelled" status wali rows return karo.
    Same structure as _serialize_items.
    """
    result = []
    for row in items:
        row_status = getattr(row, "status", "") or ""

        # Dono variations handle karo
        if row_status not in ("Cancel Order", "Cancelled"):
            continue

        item_data = frappe.db.get_value(
            "Item",
            row.item_code,
            ["image", "name", "item_group"],
            as_dict=True,
        ) or {}

        bom_data = frappe.db.get_value(
            "BOM",
            row.bom,
            ["gross_weight", "metal_and_finding_weight", "total_diamond_weight_in_gms", "metal_touch"],
            as_dict=True,
        ) or {}

        result.append({
            "name"                        : row.name,
            "item_code"                   : row.item_code or "",
            "bom"                         : row.bom or "",
            "uom"                         : row.uom or "",
            "quantity"                    : row.quantity or 0,
            "rate"                        : row.rate or 0,
            "amount"                      : (row.quantity or 0) * (row.rate or 0),
            "image"                       : item_data.get("image") or "",
            "category"                    : item_data.get("item_group") or "",
            "gross_weight"                : bom_data.get("gross_weight") or "",
            "net_weight"                  : bom_data.get("metal_and_finding_weight") or "",
            "total_diamond_weight_in_gms" : bom_data.get("total_diamond_weight_in_gms") or "",
            "metal_touch"                 : bom_data.get("metal_touch") or "",
            "user"                        : getattr(row, "user", "") or "",
            "status"                      : row_status,
            "design"                      : "Customized" if (getattr(row, "as_per_customization", 0) or 0) else "As Per Design",
            "as_per_design"               : getattr(row, "as_per_design", 0) or 0,
            "as_per_customization"        : getattr(row, "as_per_customization", 0) or 0,
            "customized_data"             : row.customized_data or "",
            "job_work"                    : getattr(row, "job_work", 0) or 0,
            "out_right"                   : getattr(row, "out_right", 0) or 0,
            "hybrid"                      : getattr(row, "hybrid", 0) or 0,
        })

    return result 
    

@frappe.whitelist(methods=["GET"])
def get_cancelled_cart_items(customer=None, user=None):
    """
    Cancelled items fetch karo — customer ya user se.

    Postman:
        GET .../get_cancelled_cart_items?customer=Rajan Shah
        GET .../get_cancelled_cart_items?user=rajan@example.com
    """

    # ── Case 1: Customer se ───────────────────────────────────────────────────
    if customer:
        cart_name = frappe.db.get_value(
            "Add To Cart Portal Item",
            {"customer": customer, "status": "Add To Cart"},
            "name",
            order_by="creation asc",
        )

        if not cart_name:
            return {"success": True, "cancelled_items": []}

        cart  = frappe.get_doc("Add To Cart Portal Item", cart_name)
        items = _serialize_cancelled_items(cart.items)

        return {
            "success"         : True,
            "cart_name"       : cart.name,
            "customer"        : cart.customer,
            "cancelled_items" : items,
        }

    # ── Case 2: User se (assigned customers ke carts) ────────────────────────
    if user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent",
        )

        if not assigned_customers:
            return {"success": True, "cancelled_items": []}

        result = []
        for cust in assigned_customers:
            cart_name = frappe.db.get_value(
                "Add To Cart Portal Item",
                {"customer": cust, "status": "Add To Cart"},
                "name",
                order_by="creation asc",
            )

            if not cart_name:
                continue

            cart  = frappe.get_doc("Add To Cart Portal Item", cart_name)
            items = _serialize_cancelled_items(cart.items)

            if not items:
                continue

            result.append({
                "cart_name"       : cart.name,
                "customer"        : cart.customer,
                "cancelled_items" : items,
            })

        return {"success": True, "cancelled_items": result}

    frappe.throw(_("Customer ya User required hai."))


@frappe.whitelist(methods=["POST"])
def restore_cancelled_item_from_cart(customer,row_name):
    """return the Cancelled item in add to cart
    Params:
        customer : Customer name
        Body : Child table row unique 'name' field
    
    Postman:
           POST ../restore_cancelled_item_from_cart
           Body: {"customer": "Rajan Kumar", "row_name": "abc123"}
    """
    
    if not customer:
        frappe.throw(_("Customer required"))
        
    if not row_name:
        frappe.throw(_("row_name is required"))
        
    # Please search Active cart
    cart_name = frappe.db.get_value(
        "Add To Cart Portal Item",
        {"customer" : customer, "status": "Add To Cart"},
        "name",
        order_by="creation asc"
    )
    
    if not cart_name:
        frappe.throw(_("Customer '{0} there is no active cart'").format(customer))
        
    cart = frappe.get_doc("Add To Cart Portal Item", cart_name)
    
    # search Row
    target_row = None
    for row in cart.items:
        if row.name == row_name:
            target_row = row
            break
    if not target_row:
        frappe.throw(_("Row '{0}' cart not found"))  
    
    # please Restore the Cancelled Item Only
    row_status = getattr(target_row, "status", "") or ""
    if row_status !="Cancelled":
        frappe.throw(_("Only 'Cancelled' item will be restore. Current status: '{0}'").format(row_status))
        
    # Restore
    target_row.status = "Add To Cart"
    
    # Totals reclculate
    _recalculate_cart_totals(cart)
    
    cart.save(ignore_permissions = True)
    frappe.db.commit()
    
    # Response
    items = _serialize_items(cart.items, status_filter=None)
    
    return{
        "success"         :  True,
        "message"         :  "Restore Your cart Item",
        "cart_name"       :  cart.name,
        "customer"        :  cart.customer,
        "total_quantity"  :  cart.total_quantity or 0,
        "total_amount"    :  cart.total_amount or 0,
        "items"           :  items     
    }
    
  
  # ─────────────────────────────────────────────





# Helper Function for Placed order-----------------------------------------
# def _recalculate_totals_draft_only(doc):
#     """only Draft items total calculate"""
#     total_qty = 0
#     total_amt = 0
#     for row in doc.items:
#         # cancelled items Skip
#         if getattr(row, "status", "Draft") == "Cancel Order":
#             continue
#         total_qty += row.quantity or 0
#         total_amt += (row.quantity or 0) * (row.rate or 0)
#     doc.total_quantity = total_qty
#     doc.total_amount = total_amt


# @frappe.whitelist()
# def get_placed_orders(customer=None, user=None):
#     # --case 1: customer login-
#     if customer:
#         filters = {"customer": customer, "status": "Ordered"}
#         orders = frappe.get_all(
#             "Portal Order",
#             filters  = filters,
#             fields = ["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
#             order_by = "order_date desc"
#         )   
    
#     # case 2: Rep/User Login
#     elif user:
#         assigned_customers = frappe.get_all(
#             "Customer Representatives",
#             filters={"user_id", user},
#             pluck="parent"
#         )
        
#         if not assigned_customers:
#             return {"success":True, "count":0, "orders": []}
        
#         orders = frappe.db.get_all(
#             "Portal Order",
#             filters={
#                 "customer": ["in", assigned_customers],
#                 "status": "Ordered"
#             }
#             fields = ["name", "Customer", "user", "order_date", "status", "total_quantity", "total_amount"],
#             order_by="order_date desc"
#         )
#     else:
#         frappe.throw(_("Customer or User Required"))
    
#     if not orders:
#         return {"success": True, "count":0, "orders": []}
    
#     result = []
#     for order in orders:
#         doc = frappe.get_doc("Portal Order", order["name"])
#         result.append({
#             "name": doc.name,
#             "customer": doc.customer,
#             "order_by": getattr(doc, "order_by", "") or "",
#             "order_date": str(doc.order_date) if doc.order_date else "",
#             "status": doc.status,
#             "total_quantity": doc.total_quantity,
#             "total_amount": doc.total_amount,
#             "items": _serialize_items(doc.items, status_filter="Ordered"), 
#         })
#     return {"success": True, "count": len(result), "orders": result}
    


# # --------------------------------------------------------------------------------------------
# #  GET PLACED ORDERS  (Ordered)
# # ─────────────────────────────────────────────
def _recalculate_totals_draft_only(doc):
    """Only Draft items total calculate """
    total_qty = 0
    total_amt = 0
    for row in doc.items:
        # Cancelled items skip 
        if getattr(row, "status", "Draft") == "Cancel Order":
            continue
        total_qty += row.quantity or 0
        total_amt += (row.quantity or 0) * (row.rate or 0)
    doc.total_quantity = total_qty
    doc.total_amount = total_amt


@frappe.whitelist()
def get_placed_orders(customer=None, user=None):

    # ── CASE 1: Customer login ──
    if customer:
        filters = {"customer": customer, "status": "Ordered"}
        orders = frappe.get_all(
            "Portal Order",
            filters=filters,
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    # ── CASE 2: Rep/User login ──
    elif user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )

        if not assigned_customers:
            return {"success": True, "count": 0, "orders": []}

        orders = frappe.get_all(
            "Portal Order",
            filters={
                "customer": ["in", assigned_customers],
                "status": "Ordered"
            },
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    else:
        frappe.throw(_("Customer or User required"))

    if not orders:
        return {"success": True, "count": 0, "orders": []}

    result = []
    for order in orders:
        doc = frappe.get_doc("Portal Order", order["name"])
        result.append({
            "name": doc.name,
            "customer": doc.customer,
            "order_by": getattr(doc, "order_by", "") or "",
            "order_date": str(doc.order_date) if doc.order_date else "",
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            "items": _serialize_items(doc.items, status_filter="Ordered"), 
        })

    return {"success": True, "count": len(result), "orders": result}

@frappe.whitelist()
def cancel_order(order_name):
    """Cancel complete Portal Order"""

    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order already cancelled"))

    doc.status = "Cancel Order"

    customer_item_array = []

    for row in doc.items:
        row.status = "Cancel Order"

        customer_item_array.append({
            "item_code": row.item_code,
            "bom": row.bom,
            "quantity": row.quantity
        })

    send_customer_order_notification(
        user=doc.customer,
        order_id=doc.name,
        customer_item_array=customer_item_array
    )

    _recalculate_totals_draft_only(doc)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "message": "Order cancelled successfully"
    }
    
@frappe.whitelist()
def cancel_order_item(order_name, item_code, row_name=None):
    """Cancel only one item from Portal Order"""

    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order is already cancelled"))

    canc_item = []
    found = False

    for row in doc.items:

        if row.item_code != item_code:
            continue

        row_status = getattr(row, "status", "Draft")

        if row_status == "Cancel Order":
            continue

        if row_name and row.name != row_name:
            continue

        # Cancel the selected row
        row.status = "Cancel Order"
        found = True

        # Prepare notification data (DICT, not SET)
        canc_item.append({
            "item_code": row.item_code,
            "bom": row.bom,
            "quantity": row.quantity
        })

        break

    if not found:
        frappe.throw(_("Item not found in order"))

    # Send notification
    if canc_item:
        send_customer_order_notification(
            user=doc.customer,
            order_id=doc.name,
            customer_item_array=canc_item
        )

    # If all items are cancelled, cancel the order
    all_cancelled = all(
        getattr(r, "status", "") == "Cancel Order"
        for r in doc.items
    )

    if all_cancelled:
        doc.status = "Cancel Order"

    # Recalculate totals
    _recalculate_totals_draft_only(doc)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "message": f"Item {item_code} cancelled successfully"
    }
    
    
@frappe.whitelist(allow_guest=True)
def send_customer_order_notification(user, order_id, customer_item_array):
    """
    Send order update mail notification to user

    user: user email/id
    order_id: order reference
    customer_item_array: list of items
    """

    items_html = ""
        
    for item in customer_item_array:
        
        items_html += build_item_row(
            item.get('item_code'),
            item.get('bom'),
            item.get('quantity')
    )


    # find representative of the customer
    
    customer = frappe.get_doc("Customer", user)
    
    representatives = customer.custom_customer_representatives
    
    customer = customer.customer_name

    users = [u.user_id for u in representatives]

    message = get_email_template(customer, order_id, items_html)
    
    frappe.sendmail(
        recipients=users,
        sender="customer_portal@gkexport.com",
        subject=f"Order Update - {order_id}",
        message=message
    )


    return {
        "status": "sent",
        "user": user,
        "order_id": order_id
    }

    
def get_email_template(customer, order_id, items_html):
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
      
      <!-- Header -->
      <div style="background: #1a1a2e; padding: 32px 32px 24px; text-align: center;">
        <span style="display: inline-block; background: #fee2e2; color: #b91c1c; font-size: 12px; font-weight: 600; padding: 4px 14px; border-radius: 99px; margin-bottom: 12px;">&#x2715; Order Cancelled</span>
        <h2 style="color: #ffffff; font-size: 22px; font-weight: 600; margin: 0 0 4px;">Order Update</h2>
      </div>

      <!-- Body -->
      <div style="padding: 32px;">
        <p style="font-size: 15px; color: #111827; margin: 0 0 8px;">Hello,</p>
        <p style="font-size: 14px; color: #6b7280; margin: 0 0 24px; line-height: 1.6;">
          {customer} Your order <strong style="color: #111827;">{order_id}</strong> has been 
          <strong style="color: #b91c1c;">cancelled successfully.</strong>
        </p>

        <!-- Order info strip -->
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; display: flex; justify-content: space-between; margin-bottom: 24px;">
          <div>
            <div style="font-size: 11px; color: #9ca3af;">Order ID</div>
            <div style="font-size: 15px; font-weight: 600; color: #111827;">{order_id}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; color: #9ca3af;">Status</div>
            <div style="font-size: 15px; font-weight: 600; color: #b91c1c;">Cancelled</div>
          </div>
        </div>

        <!-- Items heading -->
        <div style="font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;">Items in order</div>

        <!-- Items table -->
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <thead>
            <tr style="border-bottom: 1px solid #e5e7eb;">
              <th style="font-size: 11px; color: #9ca3af; text-align: left; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">Item</th>
              <th style="font-size: 11px; color: #9ca3af; text-align: left; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">BOM</th>
              <th style="font-size: 11px; color: #9ca3af; text-align: right; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">Qty</th>
            </tr>
          </thead>
          <tbody>
            {items_html}
          </tbody>
        </table>
      </div>

      <!-- Footer -->
      <div style="border-top: 1px solid #e5e7eb; background: #f9fafb; padding: 20px 32px; text-align: center;">
        <p style="font-size: 13px; color: #9ca3af; margin: 0;">Thank you — <strong style="color: #6b7280;">GK Export</strong></p>
      </div>

    </div>
    """
    
    
def build_item_row(item_code, bom, qty):
    return f"""
    <tr style="border-bottom: 1px solid #f3f4f6;">
      <td style="padding: 12px;">
        <span style="font-family: monospace; font-size: 12px; color: #1d4ed8; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">{item_code}</span>
      </td>
      <td style="padding: 12px; font-size: 13px; color: #6b7280;">{bom}</td>
      <td style="padding: 12px; text-align: right;">
        <span style="display: inline-block; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; font-weight: 600; padding: 2px 10px; color: #111827;">{qty}</span>
      </td>
    </tr>
    """
    