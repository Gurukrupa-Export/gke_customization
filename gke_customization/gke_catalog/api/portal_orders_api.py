import frappe
import json
from frappe import _


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _get_customer_assigned_users(customer):
    """Return all user_ids assigned to this customer via Customer Representatives child table."""
    users = frappe.get_all(
        "Customer Representatives",
        filters={"parent": customer},
        pluck="user_id",
    )
    return [u for u in users if u]


def _get_customer_visible_users(customer, user=None):
    """
    Validate that the current user is allowed to act on behalf of this customer,
    then return (current_user, list_of_visible_users).

    'visible_users' = all assigned reps → any rep can see every other rep's orders
    for the same customer.  If no reps are configured, only the caller sees their own orders.

    If user is None (Guest/portal token user), skip permission check and return
    all assigned users so customer can see all orders placed for them.
    """
    assigned_users = _get_customer_assigned_users(customer)

    # Guest / token-based portal user — no session user available
    if not user:
        visible_users = assigned_users if assigned_users else []
        return None, visible_users

    current_user = user

    if (
        assigned_users
        and current_user not in assigned_users
        and current_user != "Administrator"
    ):
        frappe.throw(
            _("User {0} is not assigned to customer {1}").format(current_user, customer),
            frappe.PermissionError,
        )

    # If no reps configured, scope to just the caller
    visible_users = assigned_users if assigned_users else [current_user]
    return current_user, visible_users


# ─────────────────────────────────────────────
#  CREATE PORTAL ORDER  (direct / one-shot)
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def create_portal_order(customer, items, order_date=None, company=None, currency="INR", user=None):
    """Create a brand-new Portal Order with all items in one call."""

    if isinstance(items, str):
        items = json.loads(items)

    if not customer:
        frappe.throw(_("Customer required"))
    if not items:
        frappe.throw(_("At least one Item required"))

    current_user, _ = _get_customer_visible_users(customer, user)

    doc = frappe.new_doc("Portal Order")
    doc.customer = customer
    doc.order_date = order_date or frappe.utils.today()
    doc.posting_date = doc.order_date
    doc.company = company or frappe.defaults.get_user_default("Company")
    doc.currency = currency
    doc.user = current_user
    doc.status = "Draft"

    total_qty = 0
    total_amt = 0

    for row in items:
        qty = row.get("quantity") or 0
        rate = float(row.get("rate") or 0)
        amt = qty * rate
        total_qty += qty
        total_amt += amt

        doc.append("items", {
            "item_code": row.get("item_code"),
            "quantity": qty,
            "rate": rate,
            "bom": row.get("bom", ""),
            "amount": amt,
        })

    doc.total_quantity = total_qty
    doc.total_amount = total_amt
    doc.run_method("validate")
    doc.insert()
    frappe.db.commit()

    return {
        "success": True,
        "name": doc.name,
        "status": doc.status,
        "customer": doc.customer,
        "order_date": doc.order_date,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }


# ─────────────────────────────────────────────
#  ADD TO CART  (simple – no per-user isolation)
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def add_to_cart(customer, item_code, quantity=1, rate=0, bom=None, user=None):
    """
    Add an item to the customer's current Draft order.
    Any assigned rep can see / modify the shared Draft.
    """
    if not customer:
        frappe.throw(_("Customer required"))

    qty = int(quantity or 0)
    rate = float(rate or 0)

    assigned_users = _get_customer_assigned_users(customer)
    is_rep = user and assigned_users and user in assigned_users

    if is_rep:
        # Rep → scope to all assigned reps' shared pool
        current_user = user
        draft_filter = {"customer": customer, "user": ["in", assigned_users], "status": "Draft"}
    else:
        # Customer → only their own orders, never mix with rep orders
        current_user = user or "Guest"
        draft_filter = {"customer": customer, "user": current_user, "status": "Draft"}

    # Find existing Draft order
    order = frappe.get_all(
        "Portal Order",
        filters=draft_filter,
        fields=["name"],
        limit=1,
    )

    if order:
        doc = frappe.get_doc("Portal Order", order[0].name)
    else:
        doc = frappe.new_doc("Portal Order")
        doc.customer = customer
        doc.status = "Draft"
        doc.user = current_user
        doc.posting_date = frappe.utils.today()
        doc.company = frappe.defaults.get_user_default("Company")
        doc.currency = "INR"

    # Increment if item already present, else append
    found = False
    for row in doc.items:
        if row.item_code == item_code:
            row.quantity += qty
            found = True
            break

    if not found:
        doc.append("items", {
            "item_code": item_code,
            "quantity": qty,
            "rate": rate,
            "bom": bom or "",
        })

    _recalculate_totals(doc)
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }


# ─────────────────────────────────────────────
#  ADD TO CART v2  (item dedup across orders)
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def add_to_cart1(customer, item_code, quantity=1, rate=0, bom=None, user=None):
#     """
#     Smart cart:
#     - If the item already exists in ANY visible Draft order → increment quantity there.
#     - Otherwise → add to today's Draft order (create one if needed).
#     All reps assigned to this customer share the same pool of Draft orders.
#     """
#     if not customer:
#         frappe.throw(_("Customer required"))

#     qty = int(quantity or 0)
#     rate = float(rate or 0)
#     today = frappe.utils.today()

#     assigned_users = _get_customer_assigned_users(customer)
#     is_rep = user and assigned_users and user in assigned_users

#     if is_rep:
#         # Rep → scope to ALL assigned reps' orders (shared pool)
#         current_user = user
#         draft_filter = {"customer": customer, "user": ["in", assigned_users], "status": "Draft"}
#         todays_filter = {"customer": customer, "user": ["in", assigned_users], "status": "Draft", "posting_date": today}
#     else:
#         # Customer portal user → ONLY their own orders, never mix with rep orders
#         current_user = user or "Guest"
#         draft_filter = {"customer": customer, "user": current_user, "status": "Draft"}
#         todays_filter = {"customer": customer, "user": current_user, "status": "Draft", "posting_date": today}

#     # Step 1: Does this item already exist in caller's Draft orders?
#     all_draft_orders = frappe.get_all(
#         "Portal Order",
#         filters=draft_filter,
#         fields=["name"],
#     )

#     existing_doc = None
#     for o in all_draft_orders:
#         d = frappe.get_doc("Portal Order", o.name)
#         for row in d.items:
#             if row.item_code == item_code:
#                 existing_doc = d
#                 break
#         if existing_doc:
#             break

#     if existing_doc:
#         # Item found — increment in place
#         for row in existing_doc.items:
#             if row.item_code == item_code:
#                 row.quantity += qty
#                 break
#         doc = existing_doc

#     else:
#         # Item not found — use today's Draft or create a new one
#         todays_order = frappe.get_all(
#             "Portal Order",
#             filters=todays_filter,
#             fields=["name"],
#             limit=1,
#         )

#         if todays_order:
#             doc = frappe.get_doc("Portal Order", todays_order[0].name)
#         else:
#             doc = frappe.new_doc("Portal Order")
#             doc.customer = customer
#             doc.status = "Draft"
#             doc.user = current_user
#             doc.posting_date = today
#             doc.company = frappe.defaults.get_user_default("Company")
#             doc.currency = "INR"

#         doc.append("items", {
#             "item_code": item_code,
#             "quantity": qty,
#             "rate": rate,
#             "bom": bom or "",
#         })

#     _recalculate_totals(doc)
#     doc.save()
#     frappe.db.commit()

#     return {
#         "success": True,
#         "order": doc.name,
#         "total_quantity": doc.total_quantity,
#         "total_amount": doc.total_amount,
#     }


@frappe.whitelist(allow_guest=True)
def add_to_cart1(customer, item_code, quantity=1, rate=0, bom=None, user=None):
    if not customer:
        frappe.throw(_("Customer required"))

    qty = int(quantity or 0)
    rate = float(rate or 0)
    today = frappe.utils.today()

    assigned_users = _get_customer_assigned_users(customer)
    is_rep = user and assigned_users and user in assigned_users

    if is_rep:
        current_user = user
        draft_filter = {"customer": customer, "user": ["in", assigned_users], "status": "Draft"}
        todays_filter = {"customer": customer, "user": ["in", assigned_users], "status": "Draft", "posting_date": today}
    else:
        current_user = user or "Guest"
        draft_filter = {"customer": customer, "user": current_user, "status": "Draft"}
        todays_filter = {"customer": customer, "user": current_user, "status": "Draft", "posting_date": today}

    # Fetch image once
    item_image = frappe.db.get_value("Item", item_code, "image") or ""

    # Step 1: Does this item already exist in caller's Draft orders?
    all_draft_orders = frappe.get_all(
        "Portal Order",
        filters=draft_filter,
        fields=["name"],
    )

    existing_doc = None
    for o in all_draft_orders:
        d = frappe.get_doc("Portal Order", o.name)
        for row in d.items:
            if row.item_code == item_code:
                existing_doc = d
                break
        if existing_doc:
            break

    if existing_doc:
        # Item found — increment in place
        for row in existing_doc.items:
            if row.item_code == item_code:
                row.quantity += qty
                break
        doc = existing_doc

    else:
        # Item not found — use today's Draft or create a new one
        todays_order = frappe.get_all(
            "Portal Order",
            filters=todays_filter,
            fields=["name"],
            limit=1,
        )

        if todays_order:
            doc = frappe.get_doc("Portal Order", todays_order[0].name)
        else:
            doc = frappe.new_doc("Portal Order")
            doc.customer = customer
            doc.status = "Draft"
            doc.user = current_user
            doc.posting_date = today
            doc.company = frappe.defaults.get_user_default("Company")
            doc.currency = "INR"

        doc.append("items", {
            "item_code": item_code,
            "quantity": qty,
            "rate": rate,
            "bom": bom or "",
            "image": item_image,  
        })

    _recalculate_totals(doc)
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }

# ─────────────────────────────────────────────
#  UPDATE CART ITEM QTY
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def update_cart_item_qty(order_name, item_code, quantity, user=None):
    qty = int(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))

    doc = frappe.get_doc("Portal Order", order_name)
    # Permission check:
    # - If user is an assigned rep → allow only reps of this customer
    # - If user is customer portal user (not a rep) → allow freely
    # - If no user passed (Guest token) → allow freely
    assigned_users = _get_customer_assigned_users(doc.customer)
    if user and assigned_users and user in assigned_users:
        # Caller is a rep — valid, allow
        pass
    elif user and assigned_users and user not in assigned_users and user == "Administrator":
        # Administrator — allow
        pass
    # All other cases (customer portal user, no user) → allow

    found = False
    for row in doc.items:
        if row.item_code == item_code:
            row.quantity = qty
            row.amount = qty * (row.rate or 0)
            found = True
            break

    if not found:
        frappe.throw(_("Item not found in order"))

    _recalculate_totals(doc)
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
    }


# ─────────────────────────────────────────────
#  CONFIRM CART ORDERS
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def confirm_cart_orders(customer, order_date=None, user=None, notes=None):
    """Mark all visible Draft orders for this customer as Ordered."""
    if not customer:
        frappe.throw(_("Customer required"))

    assigned_users = _get_customer_assigned_users(customer)
    final_date = order_date or frappe.utils.today()

    # Rep → scope to assigned users | Customer/Guest → all drafts for this customer
    if user and assigned_users and user in assigned_users:
        filters = {"customer": customer, "user": ["in", assigned_users], "status": "Draft"}
    else:
        filters = {"customer": customer, "status": "Draft"}

    draft_orders = frappe.get_all(
        "Portal Order",
        filters=filters,
        fields=["name"],
    )

    if not draft_orders:
        frappe.throw(_("No draft orders found"))

    confirmed_names = []
    for o in draft_orders:
        doc = frappe.get_doc("Portal Order", o.name)
        doc.status = "Ordered"
        doc.order_date = final_date
        if notes:
            doc.notes = notes
        doc.save()
        confirmed_names.append(doc.name)

    frappe.db.commit()

    return {
        "success": True,
        "confirmed_orders": confirmed_names,
        "order_date": final_date,
    }


# ─────────────────────────────────────────────
#  GET CART ORDERS  (Draft)
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def get_cart_orders(customer=None, user=None):
#     """
#     Return all Draft orders for this customer.

#     Two modes:
#     - Called by rep (user = rep email)     → show only that rep's visible orders
#     - Called by customer portal (user = customer email or None)
#       → show ALL draft orders for this customer regardless of which rep created them
#     """
#     if not customer:
#         frappe.throw(_("Customer required"))

#     assigned_users = _get_customer_assigned_users(customer)

#     if user and user in assigned_users:
#         filters = {
#             "customer": customer,
#             "user": ["in", assigned_users],
#             "status": "Draft",
#         }
#     else:
#         # Customer portal user — show all draft orders for this customer
#         filters = {
#             "customer": customer,
#             "status": "Draft",
#         }

#     orders = frappe.get_all(
#         "Portal Order",
#         filters=filters,
#         fields=["name", "customer", "user", "posting_date", "status", "total_quantity", "total_amount"],
#         order_by="posting_date desc",
#     )

#     if not orders:
#         return {"success": True, "orders": [], "message": "No cart orders found"}

#     result = []
#     for order in orders:
#         doc = frappe.get_doc("Portal Order", order["name"])
#         result.append({
#             "name": doc.name,
#             "customer": doc.customer,
#             "user": doc.user,
#             "user_full_name": _get_full_name(doc.user),
#             "posting_date": doc.posting_date,
#             "status": doc.status,
#             "total_quantity": doc.total_quantity,
#             "total_amount": doc.total_amount,
#             "items": _serialize_items(doc.items),
#         })

#     return {"success": True, "orders": result}


# @frappe.whitelist(allow_guest=True)
# def get_cart_orders(customer=None, user=None):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     # Everyone sees ALL draft orders for this customer
#     orders = frappe.get_all(
#         "Portal Order",
#         filters={
#             "customer": customer,
#             "status": "Draft",
#         },
#         fields=["name", "customer", "user", "posting_date", "status", "total_quantity", "total_amount"],
#         order_by="posting_date desc",
#     )

#     if not orders:
#         return {"success": True, "orders": [], "message": "No cart orders found"}

#     result = []
#     for order in orders:
#         doc = frappe.get_doc("Portal Order", order["name"])
#         result.append({
#             "name": doc.name,
#             "customer": doc.customer,
#             "user": doc.user,
#             "user_full_name": _get_full_name(doc.user),
#             "posting_date": doc.posting_date,
#             "status": doc.status,
#             "total_quantity": doc.total_quantity,
#             "total_amount": doc.total_amount,
#             "items": _serialize_items(doc.items),
#         })

#     return {"success": True, "orders": result}

@frappe.whitelist(allow_guest=True)
def get_cart_orders(customer=None, user=None):
    if not customer:
        frappe.throw(_("Customer required"))

    orders = frappe.get_all(
        "Portal Order",
        filters={"customer": customer, "status": "Draft"},
        fields=["name", "customer", "user", "posting_date", "status", "total_quantity", "total_amount"],
        order_by="posting_date desc",
    )

    if not orders:
        return {"success": True, "orders": [], "message": "No cart orders found"}

    seen = set()
    result = []
    for order in orders:
        if order["name"] in seen:
            continue
        seen.add(order["name"])

        doc = frappe.get_doc("Portal Order", order["name"])
        result.append({
            "name": doc.name,
            "customer": doc.customer,
            "user": doc.user,
            "user_full_name": _get_full_name(doc.user),
            "posting_date": doc.posting_date,
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            "items": _serialize_items(doc.items),
        })

    return {"success": True, "orders": result}

# ─────────────────────────────────────────────
#  GET PLACED ORDERS  (Ordered)
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_placed_orders(customer=None, user=None):
    """
    Return all Ordered orders for this customer.

    Two modes:
    - Called by rep (user = rep email)     → show only that rep's visible orders
    - Called by customer portal (user = customer email or None)
      → show ALL orders for this customer regardless of which rep placed them
    """
    if not customer:
        frappe.throw(_("Customer required"))

    assigned_users = _get_customer_assigned_users(customer)

    # If caller is an assigned rep → scope to visible users
    # If caller is the customer themselves (not a rep) → show all orders for customer
    if user and user in assigned_users:
        filters = {
            "customer": customer,
            "user": ["in", assigned_users],
            "status": "Ordered",
        }
    else:
        # Customer portal user — show all orders placed for this customer
        filters = {
            "customer": customer,
            "status": "Ordered",
        }

    orders = frappe.get_all(
        "Portal Order",
        filters=filters,
        fields=["name", "customer", "user", "posting_date", "order_date", "status", "total_quantity", "total_amount"],
        order_by="posting_date desc",
    )

    if not orders:
        return {"success": True, "count": 0, "orders": [], "message": "No placed orders found"}

    result = []
    for order in orders:
        doc = frappe.get_doc("Portal Order", order["name"])
        result.append({
            "name": doc.name,
            "customer": doc.customer,
            "user": doc.user,
            "user_full_name": _get_full_name(doc.user),
            "posting_date": str(doc.posting_date),
            "order_date":str(doc.order_date),
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            "items": _serialize_items(doc.items),
        })

    return {"success": True, "count": len(result), "orders": result}

# ------------------------------------------------
# Remove item from add to cart
# ------------------------------------------------
@frappe.whitelist()
def remove_cart_item(order_name, item_code, user=None):
    doc = frappe.get_doc("Portal Order", order_name)

    original_len = len(doc.items)
    doc.items = [row for row in doc.items if row.item_code != item_code]

    if len(doc.items) == original_len:
        frappe.throw(_("Item not found in order"))

    _recalculate_totals(doc)
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount": doc.total_amount,
        "items_remaining": len(doc.items),
    }

# ─────────────────────────────────────────────
#  PRIVATE UTILITIES
# ─────────────────────────────────────────────

def _get_full_name(user_email):
    """Return full name for a user email. Falls back to email if not found."""
    if not user_email:
        return ""
    return frappe.db.get_value("User", user_email, "full_name") or user_email


def _recalculate_totals(doc):
    """Recalculate amount per row and set totals on the doc."""
    total_qty = 0
    total_amt = 0
    for row in doc.items:
        amt = (row.quantity or 0) * (row.rate or 0)
        row.amount = amt
        total_qty += row.quantity or 0
        total_amt += amt
    doc.total_quantity = total_qty
    doc.total_amount = total_amt


def _serialize_items(items):
    result = []
    for row in items:
        # Always fetch fresh from tabItem
        image = frappe.db.get_value("Item", row.item_code, "image") or ""
        result.append({
            "item_code": row.item_code,
            "quantity": row.quantity,
            "rate": row.rate,
            "amount": row.amount,
            "bom": row.bom or "",
            "image": image,
        })
    return result
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