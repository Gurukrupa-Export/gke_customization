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

    for i, dept in enumerate(DEPARTMENTS):
        values[f"dept_{i}"] = dept

    query = f"""
        SELECT
            COALESCE(i.sub_setting_type, 'No Setting Type') AS setting_type,
            COALESCE(i.item_category, 'No Category') AS item_category,
            mo.department,
            COUNT(*) AS qty
        FROM (
            SELECT mo1.*
            FROM `tabManufacturing Operation` mo1
            INNER JOIN (
                SELECT
                    manufacturing_work_order,
                    MAX(creation) AS latest_creation
                FROM `tabManufacturing Operation`
                GROUP BY manufacturing_work_order
            ) latest
                ON latest.manufacturing_work_order = mo1.manufacturing_work_order
            AND latest.latest_creation = mo1.creation
        ) mo
        LEFT JOIN `tabItem` i
            ON mo.item_code = i.name
        WHERE 1=1
            {conditions}
        GROUP BY
            COALESCE(i.sub_setting_type, 'No Setting Type'),
            COALESCE(i.item_category, 'No Category'),
            mo.department
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)

    detail_map = {}
    subtotal_map = {}
    grand_total = {frappe.scrub(d): 0 for d in DEPARTMENTS}
    grand_row_total = 0

    for row in raw_data:
        setting_type = row["setting_type"]
        item_category = row["item_category"]
        department = row["department"]
        qty = row["qty"] or 0

        dept_field = frappe.scrub(department)
        if dept_field not in grand_total:
            continue

        detail_key = (setting_type, item_category)
        if detail_key not in detail_map:
            detail_map[detail_key] = {
                "sub_setting_type": setting_type,
                "item_category": item_category,
                "bold": 0,
                "is_total": 0,
                "is_grand_total": 0,
                "row_total": 0,
            }
            for d in DEPARTMENTS:
                detail_map[detail_key][frappe.scrub(d)] = 0

        detail_map[detail_key][dept_field] += qty
        detail_map[detail_key]["row_total"] += qty

        if setting_type not in subtotal_map:
            subtotal_map[setting_type] = {
                "sub_setting_type": setting_type,
                "item_category": f"{setting_type} Total",
                "bold": 1,
                "is_total": 1,
                "is_grand_total": 0,
                "row_total": 0,
            }
            for d in DEPARTMENTS:
                subtotal_map[setting_type][frappe.scrub(d)] = 0

        subtotal_map[setting_type][dept_field] += qty
        subtotal_map[setting_type]["row_total"] += qty

        grand_total[dept_field] += qty
        grand_row_total += qty

    rows = []

    setting_order = []
    for r in raw_data:
        st = r["setting_type"]
        if st not in setting_order:
            setting_order.append(st)

    for st in setting_order:
        for k, v in detail_map.items():
            if k[0] == st:
                rows.append(v)
        rows.append(subtotal_map[st])

    grand = {
        "sub_setting_type": "",
        "item_category": "Grand Total",
        "bold": 1,
        "is_total": 0,
        "is_grand_total": 1,
        "row_total": grand_row_total,
    }
    for d in DEPARTMENTS:
        grand[frappe.scrub(d)] = grand_total[frappe.scrub(d)]

    rows.append(grand)

    return rows

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