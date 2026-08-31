# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Main Slip No"), "fieldname": "main_slip_no", "fieldtype": "Link", "options": "Main Slip", "width": 150},
        {"label": _("Slip Touch"), "fieldname": "slip_touch", "fieldtype": "Data", "width": 90},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 140, "hidden": 1},
        {"label": _("Manager"), "fieldname": "manager", "fieldtype": "Data", "width": 120},
        {"label": _("Emp Code"), "fieldname": "emp_code", "fieldtype": "Data", "width": 110},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 160},
        {"label": _("Batch Issue GoldWt"), "fieldname": "batch_issue_goldwt", "fieldtype": "Float", "width": 120},
        {"label": _("Extra Issue GoldWt"), "fieldname": "extra_issue_goldwt", "fieldtype": "Float", "width": 120},
        {"label": _("Total Issue Wt"), "fieldname": "total_issue_wt", "fieldtype": "Float", "width": 110},
        {"label": _("Batch Return GoldWt"), "fieldname": "batch_return_goldwt", "fieldtype": "Float", "width": 120},
        {"label": _("Extra Return GoldWt"), "fieldname": "extra_return_goldwt", "fieldtype": "Float", "width": 120},
        {"label": _("Total Return Wt"), "fieldname": "total_return_wt", "fieldtype": "Float", "width": 110},
        {"label": _("Model"), "fieldname": "model", "fieldtype": "Data", "width": 120},
        {"label": _("Average"), "fieldname": "average", "fieldtype": "Float", "width": 100},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Float", "width": 100},
        {"label": _("View Details"), "fieldname": "view_details", "fieldtype": "HTML", "width": 100},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("ms.creation >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("ms.creation <= %(to_date)s")
        values["to_date"] = filters.to_date
    if filters.get("company"):
        conditions.append("ms.company = %(company)s")
        values["company"] = filters.company
    if filters.get("branch"):
        conditions.append("ms.branch = %(branch)s")
        values["branch"] = filters.branch
    if filters.get("department"):
        conditions.append("ms.department = %(department)s")
        values["department"] = filters.department
    if filters.get("manager"):
        conditions.append("ms.employee IN (SELECT name FROM `tabEmployee` WHERE reporting_employee_name_ = %(manager)s OR name = %(manager)s)")
        values["manager"] = filters.manager
    if filters.get("employee"):
        conditions.append("ms.employee = %(employee)s")
        values["employee"] = filters.employee
    if filters.get("main_slip_id"):
        conditions.append("ms.name = %(main_slip_id)s")
        values["main_slip_id"] = filters.main_slip_id
    if filters.get("manufacturer"):
        conditions.append("ms.manufacturer = %(manufacturer)s")
        values["manufacturer"] = filters.manufacturer

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    issue_sql = """
        SELECT
            parent,
            SUM(
                CASE
                    WHEN parentfield = 'batch_details'
                    THEN qty
                    ELSE 0
                END
            ) AS batch_issue_goldwt,
            SUM(
                CASE
                    WHEN parentfield = 'batch_details' AND employee_qty != qty
                    THEN employee_qty
                    ELSE 0
                END
            ) AS extra_issue_goldwt,
            SUM(
                CASE
                    WHEN parentfield = 'stock_details' AND qty > 0
                    THEN qty
                    ELSE 0
                END
            ) AS batch_return_goldwt,
            SUM(
                CASE
                    WHEN parentfield = 'stock_details' AND qty = 0 AND employee_qty > 0
                    THEN employee_qty
                    ELSE 0
                END
            ) AS extra_return_goldwt
        FROM `tabMain Slip SE Details`
        GROUP BY parent
    """

    wo_sql = """
        SELECT
            op.parent AS main_slip_no,
            GROUP_CONCAT(DISTINCT mwo.item_code ORDER BY op.idx SEPARATOR ', ') AS model
        FROM `tabMain Slip Operation` op
        LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = op.manufacturing_work_order
        GROUP BY op.parent
    """

    sql = f"""
        SELECT
            ms.name AS main_slip_no,
            ms.metal_touch AS slip_touch,
            ms.department AS department,
            emp.reporting_employee_name_ AS manager,
            emp.employee AS emp_code,
            emp.employee_name AS employee,
            COALESCE(iss.batch_issue_goldwt, 0) AS batch_issue_goldwt,
            COALESCE(iss.extra_issue_goldwt, 0) AS extra_issue_goldwt,
            COALESCE(iss.batch_issue_goldwt, 0) + COALESCE(iss.extra_issue_goldwt, 0) AS total_issue_wt,
            COALESCE(iss.batch_return_goldwt, 0) AS batch_return_goldwt,
            COALESCE(iss.extra_return_goldwt, 0) AS extra_return_goldwt,
            COALESCE(iss.batch_return_goldwt, 0) + COALESCE(iss.extra_return_goldwt, 0) AS total_return_wt,
            wo.model AS model,
            ms.computed_gold_wt AS average,
            ms.pending_metal AS balance
        FROM `tabMain Slip` ms
        LEFT JOIN `tabEmployee` emp ON emp.name = ms.employee
        LEFT JOIN ({issue_sql}) iss ON iss.parent = ms.name
        LEFT JOIN ({wo_sql}) wo ON wo.main_slip_no = ms.name
        {where_clause}
        ORDER BY ms.creation DESC, ms.name
    """

    rows = frappe.db.sql(sql, values, as_dict=True)

    for row in rows:
        row["view_details"] = (
            '<button class="btn btn-sm" style="background:white;border:1px solid #d1d8dd;color:#333;padding:4px 12px;font-size:12px;border-radius:4px;cursor:pointer;" '
            'onclick="show_main_slip_details(\'{0}\')">View</button>'
        ).format(row["main_slip_no"])

    return rows


@frappe.whitelist()
def get_main_slip_detail_popup(main_slip_no):
    ops = frappe.db.sql("""
        SELECT
            op.idx,
            op.manufacturing_work_order,
            op.manufacturing_operation,
            mwo.item_code AS model,
            mwo.posting_date,
            mwo.delivery_date,
            mwo.status,
            mwo.company,
            mwo.branch,
            mwo.manufacturer,
            mwo.metal_touch,
            mwo.gross_wt,
            mwo.net_wt
        FROM `tabMain Slip Operation` op
        LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = op.manufacturing_work_order
        WHERE op.parent = %s
        ORDER BY op.idx
    """, (main_slip_no,), as_dict=True)

    return {"operations_list": ops}