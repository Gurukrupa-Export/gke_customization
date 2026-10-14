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
        WITH latest_txn AS (
            -- For every manufacturing_work_order, rank its Issue/Receive
            -- transactions by recency. Only the most recent one reflects
            -- who currently holds it (a work order is issued, received,
            -- re-issued, received again, etc. many times over its life).
            SELECT
                eo.parent                  AS ir_name,
                eo.manufacturing_work_order,
                eo.diamond_pcs,
                eo.diamond_wt,
                eo.gemstone_wt,
                eo.net_wt,
                ir.employee,
                ir.type,
                ir.department,
                ir.date_time,
                ir.docstatus,
                ROW_NUMBER() OVER (
                    PARTITION BY eo.manufacturing_work_order
                    ORDER BY ir.date_time DESC, ir.creation DESC
                ) AS rn
            FROM `tabEmployee IR Operation` eo
            JOIN `tabEmployee IR` ir
                ON eo.parent = ir.name
            WHERE
                ir.docstatus = 1
                AND eo.manufacturing_work_order IS NOT NULL
        )
        SELECT
            lt.employee                                AS employee,
            ee.employee_name                           AS employee_name,
            COUNT(DISTINCT lt.manufacturing_work_order) AS total_orders,
            COALESCE(SUM(lt.diamond_pcs), 0)            AS dia_pcs,
            COALESCE(SUM(lt.diamond_wt),  0)            AS dia_wt,
            COALESCE(SUM(lt.gemstone_wt), 0)            AS stone_wt,
            COALESCE(SUM(lt.net_wt),      0)            AS gold_wt
        FROM latest_txn lt
        JOIN `tabEmployee` ee
            ON ee.employee = lt.employee
        WHERE
            lt.rn = 1
            AND lt.type = 'Issue'
            {conditions}
        GROUP BY
            lt.employee, ee.employee_name
        HAVING
            COALESCE(SUM(lt.diamond_pcs), 0) != 0
            OR COALESCE(SUM(lt.diamond_wt), 0) != 0
            OR COALESCE(SUM(lt.gemstone_wt), 0) != 0
            OR COALESCE(SUM(lt.net_wt),      0) != 0
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
        conditions.append("lt.employee = %(employee)s")
        values["employee"] = filters["employee"]

    if filters.get("department"):
        conditions.append("lt.department = %(department)s")
        values["department"] = filters["department"]

    if filters.get("from_date"):
        conditions.append("DATE(lt.date_time) >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("DATE(lt.date_time) <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("status"):
        # Map label to docstatus integer: Draft=0, Submitted=1
        status_map = {"Draft": 0, "Submitted": 1}
        if filters["status"] in status_map:
            conditions.append("lt.docstatus = %(status)s")
            values["status"] = status_map[filters["status"]]

    cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
    return cond_str, values


# ── WHITELISTED API – called by JS detail dialog ──────────────────────────────

@frappe.whitelist()
def get_employee_ir_details(employee):
    """
    Returns row-wise breakdown for the given employee: exactly the
    manufacturing_work_order rows currently in their hands (i.e. whose
    most recent submitted transaction is an Issue to this employee).
    These are the same rows that feed the summary report row totals.
    Called from the JS detail dialog via frappe.call().
    """
    rows = frappe.db.sql(
        """
        WITH latest_txn AS (
            SELECT
                eo.parent                  AS ir_name,
                eo.manufacturing_work_order,
                eo.diamond_pcs,
                eo.diamond_wt,
                eo.gemstone_wt,
                eo.net_wt,
                ir.employee,
                ir.type,
                ir.date_time,
                ir.docstatus,
                ROW_NUMBER() OVER (
                    PARTITION BY eo.manufacturing_work_order
                    ORDER BY ir.date_time DESC, ir.creation DESC
                ) AS rn
            FROM `tabEmployee IR Operation` eo
            JOIN `tabEmployee IR` ir
                ON eo.parent = ir.name
            WHERE
                ir.docstatus = 1
                AND eo.manufacturing_work_order IS NOT NULL
        )
        SELECT
            lt.manufacturing_work_order AS Mfg_Work_Order,
            lt.ir_name                  AS ir_name,
            lt.date_time                AS posting_date,
            lt.docstatus                AS status,
            COALESCE(lt.diamond_pcs, 0) AS dia_pcs,
            COALESCE(lt.diamond_wt,  0) AS dia_wt,
            COALESCE(lt.gemstone_wt, 0) AS stone_wt,
            COALESCE(lt.net_wt,      0) AS gold_wt
        FROM latest_txn lt
        WHERE
            lt.rn = 1
            AND lt.type = 'Issue'
            AND lt.employee = %(employee)s
        ORDER BY
            lt.date_time DESC
        """,
        {"employee": employee},
        as_dict=True,
    )
    return rows