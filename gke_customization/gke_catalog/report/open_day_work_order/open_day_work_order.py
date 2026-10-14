# Copyright (c) 2026, Your Company
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Current Process", "fieldname": "current_process", "fieldtype": "Data", "width": 130},
        {"label": "Worker Code", "fieldname": "worker_code", "fieldtype": "Link", "options": "Employee", "width": 110},
        {"label": "Worker", "fieldname": "worker", "fieldtype": "Data", "width": 140},
        {"label": "Issue Date", "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": "MWO", "fieldname": "batch_no", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 140},
        # {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 110},
        {"label": "PMO", "fieldname": "g_order_no", "fieldtype": "Data", "width": 120},
        {"label": "Party Code", "fieldname": "party_code", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "PO Number", "fieldname": "po_number", "fieldtype": "Data", "width": 100},
        {"label": "Gold wt", "fieldname": "gold_wt", "fieldtype": "Float", "width": 90, "precision": 3},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": "Dept Due Date", "fieldname": "dept_due_date", "fieldtype": "Date", "width": 110},
        {"label": "Day Pending", "fieldname": "day_pending", "fieldtype": "Int", "width": 100},
        {"label": "Metal Type", "fieldname": "metal_type", "fieldtype": "Data", "width": 100},
        {"label": "Due date", "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": "Pending day", "fieldname": "pending_day", "fieldtype": "Int", "width": 100},
        {"label": "Order type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
    ]


def get_data(filters):
    conditions, values = get_conditions(filters)

    return frappe.db.sql(
        f"""
        SELECT
            ir.operation                    AS current_process,
            ir.employee                     AS worker_code,
            emp.employee_name               AS worker,
            mwo.posting_date                AS issue_date,
            mwo.name                        AS batch_no,
            mwo.item_code                   AS item_code,
            item.image                      AS item_image,
            mwo.item_category               AS category,
            mwo.manufacturing_order         AS g_order_no,
            mwo.customer                    AS party_code,
            NULL                            AS po_number,
            mwo.metal_weight                AS gold_wt,
            mwo.diamond_pcs                 AS diamond_pcs,
            mwo.diamond_wt                  AS diamond_wt,
            NULL                            AS dept_due_date,
            mwo.due_days                    AS day_pending,
            mwo.metal_touch                 AS metal_type,
            mwo.delivery_date               AS due_date,
            DATEDIFF(CURDATE(), mwo.delivery_date) AS pending_day,
            mwo.order_type                  AS order_type

        FROM
            `tabEmployee IR` ir

        LEFT JOIN `tabEmployee` emp
            ON emp.name = ir.employee

        LEFT JOIN `tabManufacturing Work Order` mwo
            ON mwo.name = ir.scan_mwo

        LEFT JOIN `tabItem` item
            ON item.name = mwo.item_code

        WHERE 1=1
            {conditions}

        ORDER BY
            mwo.posting_date DESC
        """,
        values,
        as_dict=1,
    )


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("mwo.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("mwo.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("employee"):
        conditions.append("ir.employee in %(employee)s")
        values["employee"] = as_list(filters["employee"])

    if filters.get("customer"):
        conditions.append("mwo.customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("order_type"):
        conditions.append("mwo.order_type = %(order_type)s")
        values["order_type"] = filters["order_type"]

    if filters.get("operation"):
        conditions.append("ir.operation in %(operation)s")
        values["operation"] = as_list(filters["operation"])

    if filters.get("manufacturing_work_order"):
        conditions.append("ir.scan_mwo in %(manufacturing_work_order)s")
        values["manufacturing_work_order"] = as_list(filters["manufacturing_work_order"])

    return (" AND " + " AND ".join(conditions)) if conditions else "", values


def as_list(value):
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = frappe.parse_json(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

        return [value]

    return [value]