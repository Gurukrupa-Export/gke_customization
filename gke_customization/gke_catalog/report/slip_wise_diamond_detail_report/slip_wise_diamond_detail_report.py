# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"fieldname": "action", "label": _("Action"), "fieldtype": "Data", "width": 120},
        {"fieldname": "main_slip", "label": _("Main Slip"), "fieldtype": "Link", "options": "Main Slip", "width": 220},
        {"fieldname": "creation_date", "label": _("Main Slip Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 100},
        {"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 220, "hidden": 1},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 180, "hidden": 1},
        {"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department", "width": 180, "hidden": 1},
        {"fieldname": "manufacturer", "label": _("Manufacturer"), "fieldtype": "Link", "options": "Manufacturer", "width": 180, "hidden": 1},
        {"fieldname": "issue_wt", "label": _("Issue Wt"), "fieldtype": "Float", "precision": 3, "width": 110},
        {"fieldname": "receive_wt", "label": _("Receive Wt"), "fieldtype": "Float", "precision": 3, "width": 110},
        {"fieldname": "extra_issue_wt", "label": _("Extra Issue Wt"), "fieldtype": "Float", "precision": 3, "width": 130},
        {"fieldname": "extra_receive_wt", "label": _("Extra Receive Wt"), "fieldtype": "Float", "precision": 3, "width": 140},
        {"fieldname": "total_issue_wt", "label": _("Total Issue Wt"), "fieldtype": "Float", "precision": 3, "width": 130},
        {"fieldname": "total_receive_wt", "label": _("Total Receive Wt"), "fieldtype": "Float", "precision": 3, "width": 140},
    ]


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("ms.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("mwo.branch = %(branch)s")
        values["branch"] = filters.get("branch")

    if filters.get("department"):
        conditions.append("ms.department = %(department)s")
        values["department"] = filters.get("department")

    if filters.get("manufacturer"):
        conditions.append("ms.manufacturer = %(manufacturer)s")
        values["manufacturer"] = filters.get("manufacturer")

    if filters.get("main_slip"):
        conditions.append("ms.name = %(main_slip)s")
        values["main_slip"] = filters.get("main_slip")

    if filters.get("from_date"):
        conditions.append("DATE(ms.creation) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(ms.creation) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    return conditions, values


def get_data(filters):
    conditions, values = get_conditions(filters)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        WITH eir_op_summary AS (
            SELECT
                eiro.manufacturing_work_order,
                SUM(CASE WHEN eir.type = 'Issue' THEN COALESCE(eiro.diamond_wt, 0) ELSE 0 END) AS issue_wt,
                SUM(CASE WHEN eir.type = 'Receive' THEN COALESCE(eiro.diamond_wt, 0) ELSE 0 END) AS receive_wt
            FROM `tabEmployee IR Operation` eiro
            INNER JOIN `tabEmployee IR` eir
                ON eir.name = eiro.parent
               AND eir.docstatus < 2
            WHERE COALESCE(eiro.diamond_wt, 0) > 0
            GROUP BY eiro.manufacturing_work_order
        ),
        slip_mwo AS (
            SELECT DISTINCT
                ms.name AS main_slip,
                DATE(ms.creation) AS creation_date,
                ms.metal_touch AS metal_touch,
                ms.company AS company,
                mwo.branch AS branch,
                ms.department AS department,
                ms.manufacturer AS manufacturer,
                mop.manufacturing_work_order
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip Operation` mso
                ON mso.parent = ms.name
            LEFT JOIN `tabManufacturing Operation` mop
                ON mop.name = mso.manufacturing_operation
            LEFT JOIN `tabManufacturing Work Order` mwo
                ON mwo.name = mop.manufacturing_work_order
            {where_clause}
        ),
        ir_summary AS (
            SELECT
                sm.main_slip,
                sm.creation_date,
                sm.metal_touch,
                sm.company,
                MAX(sm.branch) AS branch,
                sm.department,
                sm.manufacturer,
                SUM(COALESCE(eos.issue_wt, 0)) AS issue_wt,
                SUM(COALESCE(eos.receive_wt, 0)) AS receive_wt
            FROM slip_mwo sm
            LEFT JOIN eir_op_summary eos
                ON eos.manufacturing_work_order = sm.manufacturing_work_order
            GROUP BY
                sm.main_slip,
                sm.creation_date,
                sm.metal_touch,
                sm.company,
                sm.department,
                sm.manufacturer
        ),
        extra_summary AS (
            SELECT
                ms.name AS main_slip,
                SUM(
                    CASE
                        WHEN COALESCE(msd.mop_qty, 0) > COALESCE(msd.mop_consume_qty, 0)
                        THEN COALESCE(msd.mop_qty, 0) - COALESCE(msd.mop_consume_qty, 0)
                        ELSE 0
                    END
                ) AS extra_issue_wt,
                SUM(
                    CASE
                        WHEN COALESCE(msd.mop_consume_qty, 0) > COALESCE(msd.mop_qty, 0)
                        THEN COALESCE(msd.mop_consume_qty, 0) - COALESCE(msd.mop_qty, 0)
                        ELSE 0
                    END
                ) AS extra_receive_wt
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip SE Details` msd
                ON msd.parent = ms.name
            WHERE msd.variant_of = 'D'
            GROUP BY ms.name
        )
        SELECT
            'View Details' AS action,
            ir.main_slip,
            ir.creation_date,
            ir.metal_touch,
            ir.company,
            ir.branch,
            ir.department,
            ir.manufacturer,
            ROUND(COALESCE(ir.issue_wt, 0), 3) AS issue_wt,
            ROUND(COALESCE(ir.receive_wt, 0), 3) AS receive_wt,
            ROUND(COALESCE(ex.extra_issue_wt, 0), 3) AS extra_issue_wt,
            ROUND(COALESCE(ex.extra_receive_wt, 0), 3) AS extra_receive_wt,
            ROUND(COALESCE(ir.issue_wt, 0) + COALESCE(ex.extra_issue_wt, 0), 3) AS total_issue_wt,
            ROUND(COALESCE(ir.receive_wt, 0) + COALESCE(ex.extra_receive_wt, 0), 3) AS total_receive_wt
        FROM ir_summary ir
        LEFT JOIN extra_summary ex
            ON ex.main_slip = ir.main_slip
        WHERE
            COALESCE(ir.issue_wt, 0) > 0
            OR COALESCE(ir.receive_wt, 0) > 0
            OR COALESCE(ex.extra_issue_wt, 0) > 0
            OR COALESCE(ex.extra_receive_wt, 0) > 0
        ORDER BY
            ir.creation_date DESC,
            ir.main_slip
    """

    return frappe.db.sql(query, values, as_dict=True)


@frappe.whitelist()
def get_row_details(main_slip):
    details = frappe.db.sql("""
        WITH eir_detail AS (
            SELECT
                eiro.manufacturing_work_order,
                eir.employee,
                eir.type AS ir_type,
                ROUND(SUM(COALESCE(eiro.diamond_wt, 0)), 3) AS diamond_wt
            FROM `tabEmployee IR Operation` eiro
            INNER JOIN `tabEmployee IR` eir
                ON eir.name = eiro.parent
               AND eir.docstatus < 2
            WHERE COALESCE(eiro.diamond_wt, 0) > 0
            GROUP BY
                eiro.manufacturing_work_order,
                eir.employee,
                eir.type
        )
        SELECT
            ms.name AS main_slip,
            DATE(ms.creation) AS creation_date,
            ms.department AS department,
            ed.employee,
            mop.manufacturing_work_order AS batch_no,
            ed.ir_type,
            ed.diamond_wt
        FROM `tabMain Slip` ms
        INNER JOIN `tabMain Slip Operation` mso
            ON mso.parent = ms.name
        INNER JOIN `tabManufacturing Operation` mop
            ON mop.name = mso.manufacturing_operation
        INNER JOIN eir_detail ed
            ON ed.manufacturing_work_order = mop.manufacturing_work_order
        WHERE ms.name = %(main_slip)s
        ORDER BY
            ms.department,
            ed.employee,
            mop.manufacturing_work_order,
            ed.ir_type
    """, {
        "main_slip": main_slip
    }, as_dict=True)

    extra_details = frappe.db.sql("""
        SELECT
            msd.batch_no,
            ROUND(COALESCE(msd.mop_qty, 0), 3) AS mop_qty,
            ROUND(COALESCE(msd.mop_consume_qty, 0), 3) AS mop_consume_qty,
            ROUND(
                CASE
                    WHEN COALESCE(msd.mop_qty, 0) > COALESCE(msd.mop_consume_qty, 0)
                    THEN COALESCE(msd.mop_qty, 0) - COALESCE(msd.mop_consume_qty, 0)
                    ELSE 0
                END, 3
            ) AS extra_issue_wt,
            ROUND(
                CASE
                    WHEN COALESCE(msd.mop_consume_qty, 0) > COALESCE(msd.mop_qty, 0)
                    THEN COALESCE(msd.mop_consume_qty, 0) - COALESCE(msd.mop_qty, 0)
                    ELSE 0
                END, 3
            ) AS extra_receive_wt
        FROM `tabMain Slip SE Details` msd
        WHERE msd.parent = %(main_slip)s
          AND msd.variant_of = 'D'
          AND (
                COALESCE(msd.mop_qty, 0) > COALESCE(msd.mop_consume_qty, 0)
                OR COALESCE(msd.mop_consume_qty, 0) > COALESCE(msd.mop_qty, 0)
          )
        ORDER BY msd.batch_no
    """, {
        "main_slip": main_slip
    }, as_dict=True)

    return {
        "details": details,
        "extra_details": extra_details
    }