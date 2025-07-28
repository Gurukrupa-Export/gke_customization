# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    filters = filters or {}
    data = get_data(filters)
    columns = get_columns()

    if data:
        total_row = {
            "customer_category": "Total",
            "sof_draft": sum(row["sof_draft"] for row in data),
            "sof_submitted": sum(row["sof_submitted"] for row in data),
            "sof_cancelled": sum(row["sof_cancelled"] for row in data),
            "so_draft": sum(row["so_draft"] for row in data),
            "so_submitted": sum(row["so_submitted"] for row in data),
            "so_cancelled": sum(row["so_cancelled"] for row in data),
            "customers": "",  
        }
        data.append(total_row)

    return columns, data
    # return get_columns(), get_data(filters)

def get_columns():
    return [
        {"label": "Customer Group", "fieldname": "customer_category", "fieldtype": "Data", "width": 150},
        # {"label": "Customer Code", "fieldname": "customer_codes", "fieldtype": "Data", "width": 150},
        # {"label": "Customers", "fieldname": "customers", "fieldtype": "Data", "width": 300},
        {"label": "Sketch OF Draft", "fieldname": "sof_draft", "fieldtype": "Int", "width": 170},
        {"label": "Sketch OF Submitted", "fieldname": "sof_submitted", "fieldtype": "Int", "width": 170},
        {"label": "Sketch OF Cancelled", "fieldname": "sof_cancelled", "fieldtype": "Int", "width": 170},
        {"label": "Sketch Order Draft", "fieldname": "so_draft", "fieldtype": "Int", "width": 170},
        {"label": "Sketch Order Submitted", "fieldname": "so_submitted", "fieldtype": "Int", "width": 190},
        {"label": "Sketch Order Cancelled", "fieldname": "so_cancelled", "fieldtype": "Int", "width": 190},
    ]

def get_data(filters):
    conditions = []

    if filters.get("branch"):
        conditions.append("sof.branch = %(branch)s")

    if filters.get("from_date"):
        conditions.append("sof.order_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("sof.order_date <= %(to_date)s")

    if filters.get("customer_group"):
        conditions.append("cg.customer_group_name = %(customer_group)s")
        
    if filters.get("customer"):
        conditions.append("c.name = %(customer)s")

    condition_sql = " AND ".join(conditions)
    if condition_sql:
        condition_sql = "WHERE " + condition_sql

    query = f"""
        SELECT 
            CASE 
                WHEN cg.customer_group_name IN ('Groups', 'Individual', 'Common Party', 'Wholesale') THEN 'Wholesale'
                WHEN cg.customer_group_name = 'Internal' THEN 'Internal'
                WHEN cg.customer_group_name = 'Retail' THEN 'Retail'
                ELSE 'Other-Groups'
            END AS customer_category,

            COUNT(DISTINCT CASE WHEN sof.docstatus = 0 THEN sof.name END) AS sof_draft,
            COUNT(DISTINCT CASE WHEN sof.docstatus = 1 THEN sof.name END) AS sof_submitted,
            COUNT(DISTINCT CASE WHEN sof.docstatus = 2 THEN sof.name END) AS sof_cancelled,

            COUNT(DISTINCT CASE WHEN so.docstatus = 0 THEN so.name END) AS so_draft,
            COUNT(DISTINCT CASE WHEN so.docstatus = 1 THEN so.name END) AS so_submitted,
            COUNT(DISTINCT CASE WHEN so.workflow_state = 'Cancelled' THEN so.name END) AS so_cancelled,
            
            GROUP_CONCAT(DISTINCT c.customer_name SEPARATOR ', ') AS customers,
            GROUP_CONCAT(DISTINCT c.name SEPARATOR ',') AS customer_codes,
            COUNT(DISTINCT c.customer_name) AS customer_count

        FROM `tabSketch Order Form` sof
        LEFT JOIN `tabSketch Order` so ON so.sketch_order_form = sof.name
        LEFT JOIN `tabCustomer` c ON sof.customer_code = c.name
        LEFT JOIN `tabCustomer Group` cg ON c.customer_group = cg.name
        {condition_sql}
        GROUP BY customer_category
        ORDER BY customer_category
    """

    return frappe.db.sql(query, filters, as_dict=True)




            # SUM(CASE WHEN sof.docstatus = 0 THEN 1 ELSE 0 END) AS sof_draft,
            # COUNT(DISTINCT CASE WHEN sof.docstatus = 1 THEN sof.name END) AS sof_submitted,
            # SUM(CASE WHEN sof.docstatus = 2 THEN 1 ELSE 0 END) AS sof_cancelled,

            # SUM(CASE WHEN so.docstatus = 0 THEN 1 ELSE 0 END) AS so_draft,
            # SUM(CASE WHEN so.docstatus = 1 THEN 1 ELSE 0 END) AS so_submitted,
            # SUM(CASE WHEN so.workflow_state = 'Cancelled' THEN 1 ELSE 0 END) AS so_cancelled,
            
