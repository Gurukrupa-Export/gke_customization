# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt


GROUPS = {
    "gold": "Metal - V",
    "diamond": "Diamond - V",
    "stone": "Gemstone - V",
}


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    enforce_company_filter(filters)
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def validate_filters(filters):
    if filters.get("from_date") and filters.get("to_date"):
        if getdate(filters["from_date"]) > getdate(filters["to_date"]):
            frappe.throw(_("From Date cannot be greater than To Date"))


def enforce_company_filter(filters):
    if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
        return

    default_company = frappe.defaults.get_user_default("Company")
    if not default_company:
        frappe.throw(_("No default Company set for your user. Please contact your administrator."))

    filters["company"] = default_company


def get_columns():
    return [
        {"fieldname": "department", "label": _("Department"), "fieldtype": "Data", "width": 220},

        {"fieldname": "opening", "label": _("Opening"), "fieldtype": "Float", "width": 120},
        {"fieldname": "issue", "label": _("Issue"), "fieldtype": "Float", "width": 120},
        {"fieldname": "receive", "label": _("Receive"), "fieldtype": "Float", "width": 120},
        {"fieldname": "closing", "label": _("Closing"), "fieldtype": "Float", "width": 120},

        {"fieldname": "opening_pure", "label": _("Opening Pure"), "fieldtype": "Float", "width": 120},
        {"fieldname": "issue_pure", "label": _("Issue Pure"), "fieldtype": "Float", "width": 120},
        {"fieldname": "receive_pure", "label": _("Receive Pure"), "fieldtype": "Float", "width": 120},
        {"fieldname": "closing_pure", "label": _("Closing Pure"), "fieldtype": "Float", "width": 120},
    ]


def get_data(filters):
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    filter_department = filters.get("department")

    departments = get_departments(company, filter_department)
    rows = []

    for d in departments:
        department = d.department
        wo_warehouse = get_department_wo_warehouse(company, department)

        if not wo_warehouse:
            continue

        gold = get_ledger_stock(company, from_date, to_date, wo_warehouse, GROUPS["gold"])
        diamond = get_ledger_stock(company, from_date, to_date, wo_warehouse, GROUPS["diamond"])
        stone = get_ledger_stock(company, from_date, to_date, wo_warehouse, GROUPS["stone"])

        wo_count = get_department_wo_count(company, from_date, to_date, department)

        row = frappe._dict({
            "department": department,

            "opening": flt(gold.get("opening_qty")),
            "issue": flt(gold.get("out_qty")),
            "receive": flt(gold.get("in_qty")),
            "closing": flt(gold.get("closing_qty")),

            "opening_pure": flt(gold.get("opening_qty")) * 0.92,
            "issue_pure": flt(gold.get("out_qty")) * 0.92,
            "receive_pure": flt(gold.get("in_qty")) * 0.92,
            "closing_pure": flt(gold.get("closing_qty")) * 0.92,

            "gold_opening": flt(gold.get("opening_qty")),
            "gold_issue": flt(gold.get("out_qty")),
            "gold_receive": flt(gold.get("in_qty")),
            "gold_closing": flt(gold.get("closing_qty")),

            "gold_opening_pure": flt(gold.get("opening_qty")) * 0.92,
            "gold_issue_pure": flt(gold.get("out_qty")) * 0.92,
            "gold_receive_pure": flt(gold.get("in_qty")) * 0.92,
            "gold_closing_pure": flt(gold.get("closing_qty")) * 0.92,

            "diamond_opening": flt(diamond.get("opening_qty")),
            "diamond_issue": flt(diamond.get("out_qty")),
            "diamond_receive": flt(diamond.get("in_qty")),
            "diamond_closing": flt(diamond.get("closing_qty")),

            "stone_opening": flt(stone.get("opening_qty")),
            "stone_issue": flt(stone.get("out_qty")),
            "stone_receive": flt(stone.get("in_qty")),
            "stone_closing": flt(stone.get("closing_qty")),

            "count_opening": flt(wo_count.get("opening_count")),
            "count_issue": flt(wo_count.get("issue_count")),
            "count_receive": flt(wo_count.get("receive_count")),
            "count_closing": flt(wo_count.get("closing_count")),
        })

        keep = any(round(flt(v), 3) != 0 for v in [
            row.opening, row.issue, row.receive, row.closing,
            row.diamond_opening, row.diamond_issue, row.diamond_receive, row.diamond_closing,
            row.stone_opening, row.stone_issue, row.stone_receive, row.stone_closing,
            row.count_opening, row.count_issue, row.count_receive, row.count_closing,
        ])

        if keep or filter_department:
            rows.append(row)

    return rows


def get_departments(company, department=None):
    conditions = ["company = %(company)s"]
    values = {"company": company}

    if department:
        conditions.append("name = %(department)s")
        values["department"] = department

    return frappe.db.sql("""
        SELECT name AS department
        FROM `tabDepartment`
        WHERE {conditions}
        ORDER BY name
    """.format(conditions=" AND ".join(conditions)), values, as_dict=True)


def get_department_wo_warehouse(company, department):
    rows = frappe.db.sql("""
        SELECT name
        FROM `tabWarehouse`
        WHERE company = %(company)s
          AND department = %(department)s
          AND name LIKE %(warehouse_pattern)s
        ORDER BY name
        LIMIT 1
    """, {
        "company": company,
        "department": department,
        "warehouse_pattern": "%WO%",
    }, as_dict=True)

    return rows[0].name if rows else None


def get_ledger_stock(company, from_date, to_date, warehouse, item_group):
    rows = frappe.db.sql("""
        SELECT
            SUM(CASE
                WHEN sle.posting_date < %(from_date)s
                THEN sle.actual_qty
                ELSE 0
            END) AS opening_qty,

            SUM(CASE
                WHEN sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
                 AND sle.actual_qty > 0
                THEN sle.actual_qty
                ELSE 0
            END) AS in_qty,

            SUM(CASE
                WHEN sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
                 AND sle.actual_qty < 0
                THEN ABS(sle.actual_qty)
                ELSE 0
            END) AS out_qty,

            SUM(CASE
                WHEN sle.posting_date <= %(to_date)s
                THEN sle.actual_qty
                ELSE 0
            END) AS closing_qty
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.company = %(company)s
          AND sle.is_cancelled = 0
          AND sle.warehouse = %(warehouse)s
          AND i.item_group = %(item_group)s
    """, {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "warehouse": warehouse,
        "item_group": item_group,
    }, as_dict=True)

    return rows[0] if rows else {
        "opening_qty": 0.0,
        "in_qty": 0.0,
        "out_qty": 0.0,
        "closing_qty": 0.0,
    }


def get_department_wo_count(company, from_date, to_date, department):
    rows = frappe.db.sql("""
        SELECT
            opening.opening_count,
            period_issue.issue_count,
            period_receive.receive_count,
            (opening.opening_count + period_issue.issue_count - period_receive.receive_count) AS closing_count
        FROM
        (
            SELECT COUNT(*) AS opening_count
            FROM (
                SELECT eir.scan_mwo
                FROM `tabEmployee IR` eir
                WHERE eir.docstatus = 1
                  AND eir.company = %(company)s
                  AND eir.department = %(department)s
                  AND IFNULL(eir.scan_mwo, '') != ''
                  AND eir.date_time < %(from_date)s
                GROUP BY eir.scan_mwo
                HAVING
                    SUM(CASE WHEN eir.type = 'Issue' THEN 1 ELSE 0 END) >
                    SUM(CASE WHEN eir.type = 'Receive' THEN 1 ELSE 0 END)
            ) x
        ) opening
        CROSS JOIN
        (
            SELECT COUNT(DISTINCT eir.scan_mwo) AS issue_count
            FROM `tabEmployee IR` eir
            WHERE eir.docstatus = 1
              AND eir.company = %(company)s
              AND eir.department = %(department)s
              AND IFNULL(eir.scan_mwo, '') != ''
              AND eir.type = 'Issue'
              AND DATE(eir.date_time) BETWEEN %(from_date)s AND %(to_date)s
        ) period_issue
        CROSS JOIN
        (
            SELECT COUNT(DISTINCT eir.scan_mwo) AS receive_count
            FROM `tabEmployee IR` eir
            WHERE eir.docstatus = 1
              AND eir.company = %(company)s
              AND eir.department = %(department)s
              AND IFNULL(eir.scan_mwo, '') != ''
              AND eir.type = 'Receive'
              AND DATE(eir.date_time) BETWEEN %(from_date)s AND %(to_date)s
        ) period_receive
    """, {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "department": department,
    }, as_dict=True)

    return rows[0] if rows else {
        "opening_count": 0,
        "issue_count": 0,
        "receive_count": 0,
        "closing_count": 0,
    }