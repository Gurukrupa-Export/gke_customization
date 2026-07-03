# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

DEPARTMENTS = [
    "Casting - KGJPL",
    "Central - KGJPL",
    "Computer Aided Designing - KGJPL",
    "Computer Aided Manufacturing - KGJPL",
    "Diamond Setting - KGJPL",
    "Final Polish - KGJPL",
    "Manufacturing Plan & Management  - KGJPL",
    "Model Making - KGJPL",
    "Pre Polish - KGJPL",
    "Product Certification - KGJPL",
    "Sub Contracting - KGJPL",
    "Tagging - KGJPL",
    "Waxing - KGJPL",
]


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


@frappe.whitelist()
def get_setting_type_options():
    return frappe.db.sql(
        """
        SELECT DISTINCT i.sub_setting_type
        FROM `tabItem` i
        WHERE IFNULL(i.sub_setting_type, '') != ''
        ORDER BY i.sub_setting_type
        """,
        as_dict=True,
    )


def get_columns():
    columns = [
        {
            "label": _("Setting Type"),
            "fieldname": "sub_setting_type",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Item Category"),
            "fieldname": "item_category",
            "fieldtype": "Data",
            "width": 200,
        },
    ]

    for dept in DEPARTMENTS:
        short_name = dept.replace(" - KGJPL", "").strip()
        columns.append(
            {
                "label": _(short_name),
                "fieldname": frappe.scrub(dept),
                "fieldtype": "Int",
                "width": 160,
            }
        )

    columns.append(
        {
            "label": _("Row Total"),
            "fieldname": "row_total",
            "fieldtype": "Int",
            "width": 120,
        }
    )

    return columns


def get_data(filters):
    conditions, values = get_conditions(filters)

    dept_case_list = [
        f"SUM(CASE WHEN mo.department = %(dept_{i})s THEN 1 ELSE 0 END) AS `{frappe.scrub(dept)}`"
        for i, dept in enumerate(DEPARTMENTS)
    ]
    dept_cases = ",\n            ".join(dept_case_list)

    row_total_expr = " + ".join(
        [f"SUM(CASE WHEN mo.department = %(dept_{i})s THEN 1 ELSE 0 END)" for i, dept in enumerate(DEPARTMENTS)]
    )

    for i, dept in enumerate(DEPARTMENTS):
        values[f"dept_{i}"] = dept

    query = f"""
        SELECT
            i.sub_setting_type AS raw_setting_type,
            i.item_category AS raw_category,
            {dept_cases},
            ({row_total_expr}) AS row_total
        FROM `tabManufacturing Operation` mo
        LEFT JOIN `tabItem` i
            ON mo.item_code = i.name
        WHERE 1=1
            {conditions}
        GROUP BY i.sub_setting_type, i.item_category WITH ROLLUP
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)

    rows = []
    last_index = len(raw_data) - 1

    for idx, row in enumerate(raw_data):
        raw_setting_type = row.get("raw_setting_type")
        raw_cat = row.get("raw_category")
        row_total = row.get("row_total") or 0

        is_grand_total = idx == last_index and raw_setting_type is None and raw_cat is None

        if is_grand_total:
            if row_total > 0:
                row["sub_setting_type"] = ""
                row["item_category"] = "Grand Total"
                row["bold"] = 1
                row["is_grand_total"] = 1
                rows.append(row)
            continue

        if row_total == 0:
            continue

        setting_type_label = raw_setting_type or "No Setting Type"

        if raw_cat is None:
            row["sub_setting_type"] = setting_type_label
            row["item_category"] = f"{setting_type_label} Total"
            row["bold"] = 1
            row["is_total"] = 1
        else:
            row["sub_setting_type"] = setting_type_label
            row["item_category"] = raw_cat

        rows.append(row)

    grand_total_row = rows[-1] if rows and rows[-1].get("item_category") == "Grand Total" else None
    body_rows = rows[:-1] if grand_total_row else rows

    def sort_key(r):
        st = r.get("sub_setting_type") or ""
        is_no_setting = 1 if st == "No Setting Type" else 0
        is_subtotal = 1 if r.get("bold") else 0
        cat = r.get("item_category") or ""
        is_no_cat = 1 if cat == "No Category" else 0
        return (is_no_setting, st.lower(), is_subtotal, is_no_cat, cat.lower())

    body_rows.sort(key=sort_key)

    if grand_total_row:
        body_rows.append(grand_total_row)

    return body_rows


def get_conditions(filters):
    conditions = ""
    values = {}

    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    conditions += " AND mo.company = %(company)s"
    values["company"] = company

    if filters.get("from_date"):
        conditions += " AND DATE(mo.creation) >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions += " AND DATE(mo.creation) <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    if filters.get("item_category"):
        conditions += " AND i.item_category = %(item_category)s"
        values["item_category"] = filters["item_category"]

    if filters.get("setting_type"):
        conditions += " AND i.sub_setting_type = %(setting_type)s"
        values["setting_type"] = filters["setting_type"]

    return conditions, values