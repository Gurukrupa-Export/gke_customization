import frappe
import json
from frappe import _
from gke_customization.gke_catalog.api.item_price_list import get_item_price
# from gke_customization.gke_catalog.api.item_price import get_item_price


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _get_customer_assigned_users(customer):
    users = frappe.get_all(
        "Customer Representatives",
        filters={"parent": customer},
        pluck="user_id",
    )
    return [u for u in users if u]


def _get_full_name(user):
    if not user:
        return ""
    return frappe.db.get_value("User", user, "full_name") or user


# def _serialize_items(items, status_filter=None):
#     result = []
#     for row in items:
#         row_status = getattr(row, "status", "Draft") or "Draft"

#         if status_filter:
#             if row_status != status_filter:
#                 continue
#         else:
#             if row_status == "Cancelled":
#                 continue

#         image = frappe.db.get_value("Item", row.item_code, "image") or ""
#         result.append({
#             "item_code": row.item_code,
#             "quantity": row.quantity or 0,
#             "rate": row.rate or 0,
#             "amount": (row.quantity or 0) * (row.rate or 0),
#             "bom": row.bom or "",
#             "image": image,
#             "user": getattr(row, "user", "") or "",
#             "status": row_status,
#             "metal_touch": getattr(row, "metal_touch", "") or "",
#             "weight": getattr(row, "weight", 0) or 0,
#         })
#     return result



def _serialize_items(items, status_filter=None):
    result = []
    for row in items:
        row_status = getattr(row, "status", "Draft") or "Draft"

        if status_filter:
            if row_status != status_filter:
                continue
        else:
            if row_status == "Cancelled":
                continue

        item_data = frappe.db.get_value("Item", row.item_code, ["image", "name"], as_dict=True) or {}
        bom_data = frappe.db.get_value("BOM", row.bom, ["gross_weight","metal_and_finding_weight","total_diamond_weight_in_gms","metal_touch"], as_dict=True) or {}
        result.append({
            "item_code": row.item_code,
            "quantity": row.quantity or 0,
            "rate": row.rate or 0,
            "amount": (row.quantity or 0) * (row.rate or 0),
            "bom": row.bom or "",
            "image": item_data.get("image") or "",
            "gross_Weight":bom_data.get("gross_weight") or "",
            "net_weight":bom_data.get("metal_and_finding_weight") or "",
            "total_diamond_weight_in_gms":bom_data.get("total_diamond_weight_in_gms") or "",
            "metal_touch":bom_data.get("metal_touch") or "",
            "user": getattr(row, "user", "") or "",
            "status": row_status,
            # "metal_touch": getattr(row, "metal_touch", "") or "",
            "weight": getattr(row, "weight", 0) or 0,
        })
    return result



def _recalculate_totals(doc):
    doc.total_quantity = sum(row.quantity or 0 for row in doc.items)
    doc.total_amount = sum((row.quantity or 0) * (row.rate or 0) for row in doc.items)


# ─────────────────────────────────────────────
#  ADD TO CART
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def add_to_cart1(customer, item_code, quantity=1, rate=0, bom=None, user=None):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     qty = int(quantity or 0)
#     rate = float(rate or 0)

#     current_user = user or frappe.session.user

#     # Item image
#     item_image = frappe.db.get_value("Item", item_code, "image") or ""

#     active_cart = frappe.db.get_value(
#         "Portal Order",
#         {
#             "customer": customer,
#             # "status": ["!=", "Ordered"]
#             "status": "Draft" 
#         },
#         "name",
#         order_by="creation asc"
#     )

#     if active_cart:
#         doc = frappe.get_doc("Portal Order", active_cart)
#     else:
#         doc = frappe.new_doc("Portal Order")
#         doc.customer = customer
#         doc.status = "Draft"
#         doc.company = frappe.defaults.get_user_default("Company")
#         doc.currency = "INR"

#     # Item already ? → quantity increment
#     item_found = False
#     for row in doc.items:
#         if row.item_code == item_code:
#             row.quantity += qty
#             row.user = current_user
#             item_found = True
#             break

#     if not item_found:
#         doc.append("items", {
#             "item_code": item_code,
#             "quantity": qty,
#             "rate": rate,
#             "bom": bom or "",
#             "image": item_image,
#             "user": current_user,
#             "status": "Draft",
#         })

#     _recalculate_totals(doc)
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "success": True,
#         "order": doc.name,
#         "total_quantity": doc.total_quantity,
#         "total_amount": doc.total_amount,
#     }


@frappe.whitelist(allow_guest=True)
def add_to_cart1(customer, item_code, quantity=1, rate=0, bom=None, user=None,
                  diamond_quality=None, metal_touch=None):
    if not customer:
        frappe.throw(_("Customer required"))

    qty = int(quantity or 0)
    calculated_rate = float(rate or 0)

    # ── BOM auto-fetch (latest default) ───────────────────
    if not bom:
        bom = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1, "bom_type": "Finish Goods", "is_default": 1},
            "name",
            order_by="creation desc"  
        )

    # ── diamond_quality auto-fetch ─────────────────────────
    if bom and not diamond_quality:
        diamond_quality = frappe.db.get_value("BOM", bom, "diamond_quality")

    # ── metal_touch auto-fetch ─────────────────────────────
    if bom and not metal_touch:
        metal_touch = frappe.db.get_value("BOM", bom, "metal_touch")

    # ── Price calculate ────────────────────────────────────
    if bom and (not rate or float(rate) == 0):
        try:
            price_data = get_item_price(
                customer=customer,
                item_code=item_code,
                bom=bom,
                diamond_quality=diamond_quality,
                metal_touch=metal_touch
            )
            dia_amount    = price_data["dia_overall_summary"]["total_amount"]
            gem_amount    = price_data["gem_summary"]["total_gemstone_amount"]
            metal_total   = sum(v.get("gold_amount", 0) + v.get("making_charge", 0) for v in price_data["metal_price_data"].values())
            finding_total = sum(v.get("finding_amount", 0) + v.get("finding_making_charge", 0) for v in price_data["finding_price_data"].values())
            calculated_rate = round(dia_amount + gem_amount + metal_total + finding_total, 2)
        except Exception as e:
            frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
            calculated_rate = float(rate or 0)

    current_user = user or frappe.session.user
    item_image   = frappe.db.get_value("Item", item_code, "image") or ""

    active_cart = frappe.db.get_value(
        "Portal Order",
        {"customer": customer, "status": "Draft"},
        "name",
        order_by="creation asc"
    )

    if active_cart:
        doc = frappe.get_doc("Portal Order", active_cart)
    else:
        doc = frappe.new_doc("Portal Order")
        doc.customer = customer
        doc.status   = "Draft"
        doc.company  = frappe.defaults.get_user_default("Company")
        doc.currency = "INR"

    item_found = False
    for row in doc.items:
        if row.item_code == item_code:
            row.quantity += qty
            row.rate      = calculated_rate
            row.user      = current_user
            item_found    = True
            break

    if not item_found:
        doc.append("items", {
            "item_code":   item_code,
            "quantity":    qty,
            "rate":        calculated_rate,
            "bom":         bom or "",
            "image":       item_image,
            "user":        current_user,
            "status":      "Draft",
            "metal_touch": metal_touch or "",
        })

    _recalculate_totals(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success":        True,
        "order":          doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount":   doc.total_amount,
        "item_rate":      calculated_rate,
    }

# ─────────────────────────────────────────────
#  GET CART ORDERS  (Draft)
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_cart_orders(customer=None, user=None):
    
    if customer:
        active_cart = frappe.db.get_value(
            "Portal Order",
            {
                "customer": customer,
                "status": ["in", ["Draft"]] 
            },
            "name"
        )

        if not active_cart:
            return {"success": True, "orders": []}

        cart = frappe.get_doc("Portal Order", active_cart)
        return {
            "success": True,
            "orders": [{
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": _serialize_items(cart.items),  
            }]
        }

    if user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )

        if not assigned_customers:
            return {"success": True, "orders": []}

        result = []
        for cust in assigned_customers:
            active_cart = frappe.db.get_value(
                "Portal Order",
                {"customer": cust, "status": "Draft"}, 
                "name"
            )

            if not active_cart:
                continue

            cart = frappe.get_doc("Portal Order", active_cart)
            draft_items = _serialize_items(cart.items)  

            if not draft_items:
                continue

            result.append({
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": _serialize_items(cart.items),
            })

        return {"success": True, "orders": result}

    frappe.throw(_("Customer or User required"))

# ─────────────────────────────────────────────
#  GET CART COUNT
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
# def get_cart_count(customer=None):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     active_cart = frappe.db.get_value(
#         "Portal Order",
#         {"customer": customer, "status": ["!=", "Ordered"]},
#         "name"
#     )

#     if not active_cart:
#         return {"success": True, "count": 0, "total_qty": 0}

#     cart = frappe.get_doc("Portal Order", active_cart)

#     return {
#         "success": True,
#         "count": len(cart.items),
#         "total_qty": cart.total_quantity or 0,
#     }


# ─────────────────────────────────────────────
#  UPDATE CART ITEM QTY
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def update_cart_item_qty(order_name, item_code, quantity, user=None):
    qty = float(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))

    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancelled":
        frappe.throw(_("Cannot modify a cancelled order"))

    found = False
    old_qty = None  

    for row in doc.items:
        if row.item_code == item_code:
            if row.status == "Cancelled":
                frappe.throw(_("Cannot modify a cancelled item"))
            
            old_qty = row.quantity  
            row.quantity = qty
            row.amount = qty * (row.rate or 0)
            found = True
            break

    if not found:
        frappe.throw(_("Item not found in order"))

    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)

    changed_by = user or frappe.session.user

    if old_qty is not None and old_qty != qty and doc.status == "Ordered":
        doc.add_comment(
            comment_type="Info",
            text=f" <b>{changed_by}</b> changed quantity of <b>{item_code}</b> from <b>{int(old_qty)}</b> to <b>{int(qty)}</b>"
        )

    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }
# ─────────────────────────────────────────────
#  REMOVE CART ITEM
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def cancel_cart_item(order_name, item_code, user=None):
    doc = frappe.get_doc("Portal Order", order_name)

    for row in doc.items:
        if row.item_code == item_code:
            row.status = "Cancelled"
            break

    # Check karo - check there is any draft is here?
    draft_items = [r for r in doc.items if getattr(r, "status", "Draft") == "Draft"]
    
    if not draft_items:
        # every items cancel → whole Order cancel 
        doc.status = "Cancelled"
    
    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancelled",
        "remaining_draft_items": len(draft_items),
    }


def _recalculate_totals_draft_only(doc):
    """Only Draft items total calculate """
    total_qty = 0
    total_amt = 0
    for row in doc.items:
        # Cancelled items skip 
        if getattr(row, "status", "Draft") == "Cancelled":
            continue
        total_qty += row.quantity or 0
        total_amt += (row.quantity or 0) * (row.rate or 0)
    doc.total_quantity = total_qty
    doc.total_amount = total_amt
# ─────────────────────────────────────────────
#  PLACE ORDER  (Draft → Ordered + new cart)
# ─────────────────────────────────────────────


@frappe.whitelist(allow_guest=True)
def confirm_cart_orders(customer, order_date=None, notes=None):
    if not customer:
        frappe.throw(_("Customer required"))

    active_cart = frappe.db.get_value(
        "Portal Order",
        {"customer": customer, "status": "Draft"},
        "name"
    )

    if not active_cart:
        frappe.throw(_("No active cart found"))

    cart = frappe.get_doc("Portal Order", active_cart)


    draft_items = [r for r in cart.items if getattr(r, "status", "Draft") == "Draft"]

    if not draft_items:
        frappe.throw(_("No active items in cart"))


    cart.status = "Ordered"
    cart.order_date = order_date or frappe.utils.today()
    if notes:
        cart.notes = notes
        
    # for row in cart.items:
    #     if getattr(row, "status", "Draft") == "Draft":
    #         row.status = "Ordered"
    for row in cart.items:
        if row.status == "Draft":
            frappe.db.set_value(
                "Portal Order Item",   # child doctype name
                row.name,              # child row name (primary key)
                "status",
                "Ordered"
            )

    cart.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "ordered_cart": cart.name,
        "order_date": str(cart.order_date),
        "message": "Order placed successfully!",
    }


# ─────────────────────────────────────────────
#  GET PLACED ORDERS  (Ordered)
# ─────────────────────────────────────────────
@frappe.whitelist(allow_guest=True)
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
            "user": doc.user,
            "user_full_name": _get_full_name(doc.user),
            "order_date": str(doc.order_date) if doc.order_date else "",
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            "items": _serialize_items(doc.items),
            "items": _serialize_items(doc.items, status_filter="Ordered")
        })

    return {"success": True, "count": len(result), "orders": result}

@frappe.whitelist(allow_guest=True)
def cancel_order(order_name):
    """Whole Order cancel"""
    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancelled":
        frappe.throw(_("Order already cancelled"))

    doc.status = "Cancelled"
    for row in doc.items:
        row.status = "Cancelled"

    _recalculate_totals_draft_only(doc)  
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "message": "Order cancelled successfully",
    }

@frappe.whitelist(allow_guest=True)
def cancel_order_item(order_name, item_code):
    """Only one item cancel"""
    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancelled":
        frappe.throw(_("Order is already cancelled"))

    found = False
    for row in doc.items:
        if row.item_code == item_code:
            if row.status == "Cancelled":
                frappe.throw(_("Item already cancelled"))
            row.status = "Cancelled"
            found = True
            break

    if not found:
        frappe.throw(_("Item not found in order"))

    all_cancelled = all(
        getattr(r, "status", "") == "Cancelled" for r in doc.items
    )
    if all_cancelled:
        doc.status = "Cancelled"

    _recalculate_totals_draft_only(doc) 
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancelled",
        "message": f"Item {item_code} cancelled successfully",
    }
    # -----------------------------------------
    
#@frappe.whitelist()
# def subcategory_count(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             sql_query = """
#                 SELECT 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type,

#                     COUNT(DISTINCT CASE
#                         WHEN tav.is_subcategory = 1  
#                             AND ti.item_subcategory IS NOT NULL
#                             AND fbom.bom_type = 'Finish Goods' 
#                             AND fbom.is_active = 1  
#                         THEN IFNULL(ti.variant_of, ti.item_code)
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN tav.is_subcategory = 1 
#                             AND ti.item_subcategory IS NOT NULL 
#                             AND fbom.bom_type = 'Finish Goods' 
#                             AND fbom.is_active = 1 
#                         THEN IFNULL(ti.variant_of, ti.item_code)
#                     END) AS serial_count,

#                     ( 
#                         SELECT item.image
#                         FROM `tabItem` AS item 
#                         INNER JOIN ( 
#                             SELECT 
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             LEFT JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item.item_code = first_variant.first_item_code
#                         WHERE 
#                             item.item_subcategory = ti.item_subcategory
#                             AND item.image IS NOT NULL
#                             AND (item.front_view IS NULL OR item.image != item.front_view)
#                         ORDER BY item.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabCataloge Item Details` AS tci

#                 LEFT JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent

#                 LEFT JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code

#                 LEFT JOIN `tabBOM` AS tb 
#                     ON ti.name = tb.item

#                 LEFT JOIN `tabBOM` AS fbom 
#                     ON fbom.item = ti.name  

#                 JOIN `tabAttribute Value` AS tav 
#                     ON ti.item_subcategory = tav.name  

#                 WHERE  
#                     (
#                         (tav.is_subcategory = 1 AND ti.item_subcategory IS NOT NULL)
#                         OR 
#                         (fbom.bom_type = 'Finish Goods' AND fbom.is_active = 1)
#                     )
#                     AND tcm.customer = %s
#                     AND tb.is_active = 1
#                     AND ti.item_category = %s

#                 GROUP BY 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type

#                 ORDER BY 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type
#             """

#             result = frappe.db.sql(sql_query, (customer, categoryName), as_dict=True)

#         else:
#             sql_query = """
#                 SELECT
#                     item.item_subcategory,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.item_code)
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.item_code)
#                     END) AS serial_count,

#                     (
#                         SELECT item2.image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             LEFT JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item2.item_code = first_variant.first_item_code
#                         WHERE 
#                             item2.item_subcategory = item.item_subcategory
#                             AND item2.image IS NOT NULL
#                             AND (item2.front_view IS NULL OR item2.image != item2.front_view)
#                         ORDER BY item2.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name

#                 LEFT JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item

#                 WHERE 
#                     tav.is_subcategory = 1
#                     AND item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """

#             result = frappe.db.sql(sql_query, (categoryName,), as_dict=True)

#         return result

#     except Exception as e:
#         return {"error": str(e)}



# ----------------------------

# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     # ✅ company filter sirf where_clause mein, sub_where se hataya
#     if company:
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#         company_join_condition = "AND idf3.company = %(company)s"
#     else:
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"
#         company_join_condition = "AND idf3.company = 'Gurukrupa Export Private Limited'"

#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,
#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,
#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,
#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,
#             item.variant_of,
#             CASE 
#                 WHEN vc.variant_count > 1 THEN 1 
#                 ELSE 0 
#             END AS rn,
#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,
#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item

#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             LEFT JOIN `tabItem Default` AS idf3
#                 ON i.item_name = idf3.parent
#                 {company_join_condition}
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     # -------- SIMILAR ITEMS TABLE --------
#     if item_codes:
#         similar_links = frappe.db.sql("""
#             SELECT sit.parent AS main_item_code, sit.item_code AS similar_item_code
#             FROM `tabSimilar Item Table` AS sit
#             WHERE sit.parenttype = 'Item'
#             AND sit.parent IN %(item_codes)s
#         """, {"item_codes": tuple(item_codes)}, as_dict=True)
#     else:
#         similar_links = []

#     all_similar_codes = list({lnk["similar_item_code"] for lnk in similar_links})

#     if all_similar_codes:
#         sim_rows = frappe.db.sql("""
#             SELECT
#                 item.name,
#                 bom.name AS bom_name,
#                 idf.company,
#                 tci.trending,
#                 0 AS wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view AS cad_image,
#                 CASE WHEN item.front_view = item.image THEN 'CAD Image' ELSE 'FG Image' END AS image_remark,
#                 item.item_subcategory,
#                 item.stylebio,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_colour,
#                 bom.metal_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna, bom.lock_type, bom.feature, bom.enamal, bom.rhodium, bom.sizer_type,
#                 bom.height, bom.length, bom.width, bom.breadth, bom.product_size,
#                 bom.design_style, bom.nakshi_from, bom.vanki_type, bom.total_length,
#                 bom.detachable, bom.back_side_size, bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs, bom.total_other_pcs, bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM `tabItem` AS item
#             LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#             LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#             LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#             LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#             LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#             LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#             LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#             LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#             LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
#             WHERE item.item_code IN %(similar_codes)s
#             GROUP BY item.item_code, item.variant_of
#         """, {"similar_codes": tuple(all_similar_codes)}, as_dict=True)

#         sim_item_codes = [r.item_code for r in sim_rows]
#         if sim_item_codes:
#             sim_attr_res = frappe.db.sql("""
#                 SELECT parent, parentfield,
#                 GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#                 FROM `tabDesign Attribute - Multiselect`
#                 WHERE parent IN %(data)s
#                 GROUP BY parent, parentfield
#             """, {"data": tuple(sim_item_codes)}, as_dict=True)
#             sim_attr_map = {}
#             for r in sim_attr_res:
#                 sim_attr_map.setdefault(r["parent"], {})[r["parentfield"].replace("custom_", "")] = r["design_attributes"]
#             for r in sim_rows:
#                 for k, v in sim_attr_map.get(r.item_code, {}).items():
#                     r[k] = v
#                 r["custom_collection"] = r.get("custom_collection") or None
#                 r["custom_language"] = r.get("custom_language") or None
#                 r["custom_zodiac"] = r.get("custom_zodiac") or None
#                 r["custom_animalbirds"] = r.get("custom_animalbirds") or None
#                 r["custom_alphabetnumber"] = r.get("custom_alphabetnumber") or None
#                 r["religious"] = r.get("religious") or None

#         # ✅ FIXED - similar items nested, flat extend nahi
#         existing_item_codes = {row.item_code for row in db_data}
#         sim_row_map = {r["item_code"]: r for r in sim_rows}

#         sim_map = {}
#         for lnk in similar_links:
#             main = lnk["main_item_code"]
#             sim_code = lnk["similar_item_code"]
#             if sim_code not in existing_item_codes and sim_code in sim_row_map:
#                 sim_map.setdefault(main, []).append(sim_row_map[sim_code])

#         for row in db_data:
#             row["similar_items"] = sim_map.get(row.item_code, [])

#     else:
#         for row in db_data:
#             row["similar_items"] = []

#     return db_data



# ---------------
# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     # ✅ company filter SIRF where_clause mein, sub_where se HATAYA
#     if company:
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#         company_join_condition = "AND idf3.company = %(company)s"
#     else:
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"
#         company_join_condition = "AND idf3.company = 'Gurukrupa Export Private Limited'"

#     # wishlist
#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,

#             CASE 
#                 WHEN vc.variant_count > 1 THEN 1 
#                 ELSE 0 
#             END AS rn,

#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,

#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item

#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             LEFT JOIN `tabItem Default` AS idf3
#                 ON i.item_name = idf3.parent
#                 {company_join_condition}
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     # -------- SIMILAR ITEMS TABLE --------
#     if item_codes:
#         similar_links = frappe.db.sql("""
#             SELECT sit.parent AS main_item_code, sit.item_code AS similar_item_code
#             FROM `tabSimilar Item Table` AS sit
#             WHERE sit.parenttype = 'Item'
#             AND sit.parent IN %(item_codes)s
#         """, {"item_codes": tuple(item_codes)}, as_dict=True)
#     else:
#         similar_links = []

#     all_similar_codes = list({lnk["similar_item_code"] for lnk in similar_links})

#     if all_similar_codes:
#         sim_rows = frappe.db.sql("""
#             SELECT
#                 item.name,
#                 bom.name AS bom_name,
#                 idf.company,
#                 tci.trending,
#                 0 AS wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view AS cad_image,
#                 CASE WHEN item.front_view = item.image THEN 'CAD Image' ELSE 'FG Image' END AS image_remark,
#                 item.item_subcategory,
#                 item.stylebio,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_colour,
#                 bom.metal_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna, bom.lock_type, bom.feature, bom.enamal, bom.rhodium, bom.sizer_type,
#                 bom.height, bom.length, bom.width, bom.breadth, bom.product_size,
#                 bom.design_style, bom.nakshi_from, bom.vanki_type, bom.total_length,
#                 bom.detachable, bom.back_side_size, bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs, bom.total_other_pcs, bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM `tabItem` AS item
#             LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#             LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#             LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#             LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#             LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#             LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#             LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#             LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#             LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
#             WHERE item.item_code IN %(similar_codes)s
#             GROUP BY item.item_code, item.variant_of
#         """, {"similar_codes": tuple(all_similar_codes)}, as_dict=True)

#         # Apply multiselect attributes to similar items
#         sim_item_codes = [r.item_code for r in sim_rows]
#         if sim_item_codes:
#             sim_attr_res = frappe.db.sql("""
#                 SELECT parent, parentfield,
#                 GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#                 FROM `tabDesign Attribute - Multiselect`
#                 WHERE parent IN %(data)s
#                 GROUP BY parent, parentfield
#             """, {"data": tuple(sim_item_codes)}, as_dict=True)
#             sim_attr_map = {}
#             for r in sim_attr_res:
#                 sim_attr_map.setdefault(r["parent"], {})[r["parentfield"].replace("custom_", "")] = r["design_attributes"]
#             for r in sim_rows:
#                 for k, v in sim_attr_map.get(r.item_code, {}).items():
#                     r[k] = v
#                 r["custom_collection"] = r.get("custom_collection") or None
#                 r["custom_language"] = r.get("custom_language") or None
#                 r["custom_zodiac"] = r.get("custom_zodiac") or None
#                 r["custom_animalbirds"] = r.get("custom_animalbirds") or None
#                 r["custom_alphabetnumber"] = r.get("custom_alphabetnumber") or None
#                 r["religious"] = r.get("religious") or None

#         # ✅ FIXED - similar items nested karo, flat extend nahi
#         existing_item_codes = {row.item_code for row in db_data}

#         # sim_code -> full sim row map
#         sim_row_map = {r["item_code"]: r for r in sim_rows}

#         # main item ke saath similar items attach karo
#         sim_map = {}
#         for lnk in similar_links:
#             main = lnk["main_item_code"]
#             sim_code = lnk["similar_item_code"]
#             if sim_code not in existing_item_codes and sim_code in sim_row_map:
#                 sim_map.setdefault(main, []).append(sim_row_map[sim_code])

#         for row in db_data:
#             row["similar_items"] = sim_map.get(row.item_code, [])

#     else:
#         # similar items koi nahi toh empty list
#         for row in db_data:
#             row["similar_items"] = []

#     return db_data