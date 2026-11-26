from dataclasses import field
import json
from os import name
from warnings import filters
import frappe
from frappe import _
from werkzeug.wrappers import request
from gke_customization.gke_catalog.api.portals_api.item_price import get_item_price
from gke_customization.gke_catalog.api.portal_access import allowed_customers, allowed_document, allowed_user


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
    diamond_quality=None,   
    metal_touch=None,       
):
    if not customer:
        frappe.throw(_("Customer required."))
    if not item_code:
        frappe.throw(_("Item Code required."))
    allowed_customers(customer)

    qty             = int(quantity or 1)
    calculated_rate = float(rate or 0)

    # ── BOM auto-fetch ─────────────────────────────────────────────────────────
    if not bom:
        bom = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1}, 
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
    # custom_catalogue_image = frappe.db.get_value("custom_catalogue_image", item_code, "custom_silver_image") or ""
    # custom_silver_image = frappe.db.get_value("custom_silver_image", item_code, "custom_silver_image") or ""

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

    #  Match existing row using fingerprint
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

    #  New row 
    if not item_found:
        doc.append("items", {
            "item_code"            : item_code,
            "bom"                  : bom or "",
            "uom"                  : uom,
            "quantity"             : qty,
            "rate"                 : calculated_rate,
            "amount"               : qty * calculated_rate,
            "image"                : item_image,
            # "custom_catalogue_image"  : custom_catalogue_image,
            # "custom_silver_image"  :custom_silver_image,
            "user"                 : current_user,
            "status"               : "Add To Cart",
            "as_per_design"        : is_as_per_design,
            "as_per_customization" : is_as_per_customization,
            "job_work"             : is_job_work,
            "out_right"            : is_out_right,
            "hybrid"               : is_hybrid,
            "customized_data"      : customized_data or "",
        })

    #  Save 
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
 
    if customer:
        allowed_customers(customer)
    else:
        allowed_user(user)

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
            ["image", "name", "item_group","custom_catalogue_image", "custom_silver_image","sketch_image", "front_view"],
            as_dict=True,
        ) or {}
        
        # item_image = (
        #     item_data.get("custom_catalogue_image")
        #     or
        #     item_data.get("custom_silver_image")
        # )
        
        # if not item_image:
        #     continue 
            
 
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
            "custom_catalogue_image"      : item_data.get("custom_catalogue_image") or "",
            "custom_silver_image"         : item_data.get("custom_silver_image") or "",
            "image"                       : item_data.get("image") or "",
            "cad_image"                   : item_data.get("front_view") or "",
            "sketch_image"                : item_data.get("sketch_image") or "",
            
            # "custom_catalogue_image"      : (item_data.get("custom_catalogue_image") or item_data.get("custom_silver_image")),
            # "custom_catalogue_image"      : item_image,
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


@frappe.whitelist()
def update_cart_item_qty(order_name, item_code, quantity, row_name=None, user=None):
    qty = float(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))
    allowed_document("Add To Cart Portal Item", order_name)

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

# ── Remove Row ───

@frappe.whitelist()
def cancel_cart_item(order_name, item_code, row_name=None, user=None):
    allowed_document("Add To Cart Portal Item", order_name)
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

    # if all item has been cancel then cancel the order automatically
    # if not active_items:
    #     doc.status = "Cancel Order"   
        # Ya doc.status = "Cancelled" 

    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "remaining_active_items": len(active_items),
    }