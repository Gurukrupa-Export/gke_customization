# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data


def get_columns():
    return [
        {"label": "Creation Date", "fieldname": "creation_date", "fieldtype": "Date", "width": 160},
        {"label": "Sales Order ID", "fieldname": "sales_order_id", "fieldtype": "Link", "options": "Sales Order", "width": 180},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 120},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
        {"label": "Updated Delivery Date", "fieldname": "custom_updated_delivery_date", "fieldtype": "Date", "width": 150},
        {"label": "Total Quantity", "fieldname": "total_quantity", "fieldtype": "Float", "width": 120},
    ]


def get_data(filters):
    condition_sql, values = get_conditions(filters)

    raw_data = frappe.db.sql(f"""
        SELECT
            so.company,
            so.branch,
            so.name AS sales_order_id,
            so.customer,
            so.order_type,
            so.creation AS creation_date,
            so.delivery_date,
            so.custom_updated_delivery_date,
            SUM(soi.qty) AS total_quantity
        FROM 
            `tabSales Order` so
        LEFT JOIN 
            `tabSales Order Item` soi ON soi.parent = so.name
        LEFT JOIN 
            `tabQuotation` q ON soi.prevdoc_docname = q.name
        LEFT JOIN 
            `tabManufacturing Plan Sales Order` mps ON mps.sales_order = so.name
        WHERE 
            so.docstatus = 1
            AND q.name IS NOT NULL
            AND mps.name IS NULL
            {condition_sql}
        GROUP BY 
            so.name
        ORDER BY 
            so.creation DESC
    """, values, as_dict=True)

    return raw_data


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("so.company IN %(company)s")
        values["company"] = tuple(filters["company"])

    if filters.get("branch"):
        conditions.append("so.branch IN %(branch)s")
        values["branch"] = tuple(filters["branch"])

    if filters.get("sales_order_id"):
        conditions.append("so.name IN %(sales_order_id)s")
        values["sales_order_id"] = tuple(filters["sales_order_id"])

    if filters.get("customer"):
        conditions.append("so.customer IN %(customer)s")
        values["customer"] = tuple(filters["customer"])

    if filters.get("order_type"):
        conditions.append("so.order_type IN %(order_type)s")
        values["order_type"] = tuple(filters["order_type"])

    if filters.get("date"):
        conditions.append("DATE(so.creation) = %(date)s")
        values["date"] = filters["date"]

    return " AND " + " AND ".join(conditions) if conditions else "", values

