# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_summary_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Total Orders"),
            "fieldname": "total_orders",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": _("Dia Pcs"),
            "fieldname": "dia_pcs",
            "fieldtype": "Float",
            "width": 100,
            "precision": 2,
        },
        {
            "label": _("Dia Wt"),
            "fieldname": "dia_wt",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3,
        },
        {
            "label": _("Stone Wt"),
            "fieldname": "stone_wt",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3,
        },
        {
            "label": _("Gold Wt"),
            "fieldname": "gold_wt",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3,
        },
        {
            "label": _("Details"),
            "fieldname": "details",
            "fieldtype": "HTML",
            "width": 100,
        },
    ]


# ── SUMMARY DATA (one row per employee) ───────────────────────────────────────

def get_summary_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql(
        """
        SELECT
            ir.employee                              AS employee,
            ee.employee_name                         AS employee_name,
            COUNT(DISTINCT CASE WHEN eo_agg.parent IS NOT NULL THEN ir.name END) AS total_orders,
            COALESCE(SUM(eo_agg.dia_pcs),     0)    AS dia_pcs,
            COALESCE(SUM(eo_agg.dia_wt),      0)    AS dia_wt,
            COALESCE(SUM(eo_agg.gemstone_wt), 0)    AS stone_wt,
            COALESCE(SUM(eo_agg.net_wt),      0)    AS gold_wt
        FROM `tabEmployee IR` ir
        JOIN `tabEmployee` ee
            ON ir.employee = ee.employee
        LEFT JOIN (
            -- Only aggregate operations whose manufacturing_work_order
            -- has NOT yet been received (no docstatus=1 Receive IR for it).
            SELECT
                eo.parent,
                SUM(eo.diamond_pcs) AS dia_pcs,
                SUM(eo.diamond_wt)  AS dia_wt,
                SUM(eo.gemstone_wt) AS gemstone_wt,
                SUM(eo.net_wt)      AS net_wt
            FROM `tabEmployee IR Operation` eo
            WHERE
                eo.manufacturing_work_order IS NOT NULL
                AND eo.manufacturing_work_order NOT IN (
                    SELECT DISTINCT eo_r.manufacturing_work_order
                    FROM `tabEmployee IR Operation` eo_r
                    JOIN `tabEmployee IR` ir_r
                        ON eo_r.parent = ir_r.name
                    WHERE
                        ir_r.docstatus = 1
                        AND ir_r.type   = 'Receive'
                        AND eo_r.manufacturing_work_order IS NOT NULL
                )
            GROUP BY eo.parent
        ) eo_agg
            ON eo_agg.parent = ir.name
        WHERE
            ir.docstatus = 1
            AND ir.type = 'Issue'
            {conditions}
        GROUP BY
            ir.employee, ee.employee_name
        HAVING
            COUNT(DISTINCT CASE WHEN eo_agg.parent IS NOT NULL THEN ir.name END) > 0
        ORDER BY
            ee.employee_name
        """.format(conditions=conditions),
        values,
        as_dict=True,
    )

    for row in rows:
        emp   = frappe.utils.escape_html(row["employee"])
        ename = frappe.utils.escape_html(row["employee_name"])
        row["details"] = (
            '<button'
            ' class="btn btn-xs btn-primary ir-detail-btn"'
            ' data-employee="{emp}"'
            ' data-empname="{ename}"'
            ' style="white-space:nowrap">'
            ' <i class="fa fa-list"></i> View'
            '</button>'
        ).format(emp=emp, ename=ename)

    return rows


# ── FILTERS → SQL CONDITIONS ──────────────────────────────────────────────────

def build_conditions(filters):
    conditions = []
    values = {}

    if filters.get("employee"):
        conditions.append("ir.employee = %(employee)s")
        values["employee"] = filters["employee"]

    if filters.get("department"):
        conditions.append("ir.department = %(department)s")
        values["department"] = filters["department"]

    if filters.get("from_date"):
        conditions.append("DATE(ir.date_time) >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("DATE(ir.date_time) <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("status"):
        # Map label to docstatus integer: Draft=0, Submitted=1
        status_map = {"Draft": 0, "Submitted": 1}
        if filters["status"] in status_map:
            conditions.append("ir.docstatus = %(status)s")
            values["status"] = status_map[filters["status"]]

    cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
    return cond_str, values


# ── WHITELISTED API – called by JS detail dialog ──────────────────────────────

@frappe.whitelist()
def get_employee_ir_details(employee):
    """
    Returns row-wise breakdown for the given employee.
    Only includes Issue IRs whose manufacturing_work_order has no
    corresponding Receive IR entry.
    Called from the JS detail dialog via frappe.call().
    """
    rows = frappe.db.sql(
        """
        SELECT
            eo.manufacturing_work_order AS Mfg_Work_Order,
            ir.name                     AS ir_name,
            ir.date_time                AS posting_date,
            ir.docstatus                AS status,
            COALESCE(SUM(eo.diamond_pcs), 0) AS dia_pcs,
            COALESCE(SUM(eo.diamond_wt),  0) AS dia_wt,
            COALESCE(SUM(eo.gemstone_wt), 0) AS stone_wt,
            COALESCE(SUM(eo.net_wt),      0) AS gold_wt
        FROM `tabEmployee IR` ir
        LEFT JOIN `tabEmployee IR Operation` eo
            ON eo.parent = ir.name
        WHERE
            ir.docstatus = 1
            AND ir.type = 'Issue'
            AND ir.employee = %(employee)s
            -- Exclude operations whose MFG order already has a Receive IR
            AND (
                eo.manufacturing_work_order IS NULL
                OR eo.manufacturing_work_order NOT IN (
                    SELECT DISTINCT eo_r.manufacturing_work_order
                    FROM `tabEmployee IR Operation` eo_r
                    JOIN `tabEmployee IR` ir_r
                        ON eo_r.parent = ir_r.name
                    WHERE
                        ir_r.docstatus = 1
                        AND ir_r.type   = 'Receive'
                        AND eo_r.manufacturing_work_order IS NOT NULL
                )
            )
        GROUP BY
            ir.name, ir.date_time, eo.manufacturing_work_order
        ORDER BY
            ir.date_time DESC
        """,
        {"employee": employee},
        as_dict=True,
    )
    return rows