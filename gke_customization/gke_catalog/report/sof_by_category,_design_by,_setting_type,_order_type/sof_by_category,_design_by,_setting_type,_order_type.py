# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    # group_label = "Category" if filters.get("group_by") == "Category" else "Order Type"
    group_by = filters.get("group_by")

    if group_by == "Category":
        group_label = "Category"
    elif group_by == "Order Type":
        group_label = "Order Type"
    elif group_by == "Design By":
        group_label = "Design By"
    elif group_by == "Setting Type":
        group_label = "Setting Type"
    elif group_by == "Customer Group":
        group_label = "Customer Group"
    else:
        group_label = "Group"

    return [
        {"label": group_label, "fieldname": "label", "fieldtype": "Data", "width": 180},
        {"label": "Total Orders", "fieldname": "total_orders", "fieldtype": "Int", "width": 130},
        {"label": "Submitted", "fieldname": "submitted_orders", "fieldtype": "Int", "width": 130},
        {"label": "Pending", "fieldname": "pending_orders", "fieldtype": "Int", "width": 130},
        {"label": "Cancelled", "fieldname": "cancelled_orders", "fieldtype": "Int", "width": 130},
    ]


def get_data(filters):
    conditions = []
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(f"DATE(skf.creation) BETWEEN '{filters.get('from_date')}' AND '{filters.get('to_date')}'")

    if filters.get("company"):
        conditions.append(f"skf.company = '{filters.get('company')}'")

    if filters.get("branch"):
        conditions.append(f"skf.branch = '{filters.get('branch')}'")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    group_by = filters.get("group_by") or "Category"

    if group_by == "Category":
        group_field = "skfd.category"
        join_clause = "LEFT JOIN `tabSketch Order Form Detail` skfd ON skfd.parent = skf.name"
    elif group_by == "Order Type":
        group_field = "skf.order_type"
        join_clause = ""
    elif group_by == "Design By":
        group_field = "skf.design_by"
        join_clause = ""
    elif group_by == "Setting Type":
        group_field = "skfd.setting_type"
        join_clause = "LEFT JOIN `tabSketch Order Form Detail` skfd ON skfd.parent = skf.name"
    elif group_by == "Customer Group":
        join_clause = """
            LEFT JOIN `tabCustomer` ct ON skf.customer_code = ct.name
            LEFT JOIN `tabCustomer Group` cc ON ct.customer_group = cc.name
        """
        select_label = """
            CASE 
                WHEN cc.customer_group_name IN ('Groups', 'Individual', 'Common Party', 'Wholesale') THEN 'Wholesale'
                WHEN cc.customer_group_name = 'Internal' THEN 'Internal'
                WHEN cc.customer_group_name = 'Retail' THEN 'Retail'
                ELSE 'Other-Groups'
            END
        """
        group_field = select_label
    else:
          # fallback
        group_field = "skfd.category"
        join_clause = "LEFT JOIN `tabSketch Order Form Detail` skfd ON skfd.parent = skf.name"

    query = f"""
        SELECT 
            {group_field} AS label,
            COUNT(distinct skf.name) AS total_orders,
            COUNT(DISTINCT CASE WHEN skf.docstatus = 1 THEN skf.name END) AS submitted_orders,
            COUNT(DISTINCT CASE WHEN skf.docstatus = 0 THEN skf.name END) AS pending_orders,
            COUNT(DISTINCT CASE WHEN skf.docstatus = 2 THEN skf.name END) AS cancelled_orders
        FROM `tabSketch Order Form` skf
        {join_clause}
        {where_clause}
        GROUP BY {group_field}
    """

    return frappe.db.sql(query, as_dict=True)

