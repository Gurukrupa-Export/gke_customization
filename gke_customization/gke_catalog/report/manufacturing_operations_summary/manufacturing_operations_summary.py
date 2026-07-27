# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    departments = get_active_departments(filters)
    return get_columns(departments), get_data(filters, departments)


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


def get_active_departments(filters):
    conditions, values = get_conditions(filters)

    query = f"""
        SELECT
            mo.department AS department,
            COUNT(*) AS qty
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY manufacturing_work_order
                    ORDER BY creation DESC, name DESC
                ) AS rn
            FROM `tabManufacturing Operation`
        ) mo
        LEFT JOIN `tabItem` i
            ON mo.item_code = i.name
        WHERE mo.rn = 1
            AND IFNULL(mo.department, '') != ''
            {conditions}
        GROUP BY mo.department
        HAVING COUNT(*) > 0
        ORDER BY mo.department
    """

    rows = frappe.db.sql(query, values, as_dict=True)
    return [row["department"] for row in rows]


def get_columns(departments):
    columns = [
        {
            "label": _("Item Category"),
            "fieldname": "item_category",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Setting Type"),
            "fieldname": "setting_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Sub Setting Type"),
            "fieldname": "sub_setting_type",
            "fieldtype": "Data",
            "width": 160,
        },
    ]

    for dept in departments:
        short_name = dept.rsplit(" - ", 1)[0].strip() if " - " in dept else dept
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


def get_data(filters, departments):
    conditions, values = get_conditions(filters)

    query = f"""
        SELECT
            COALESCE(i.setting_type, '') AS setting_type,
            COALESCE(i.sub_setting_type, 'No Setting Type') AS sub_setting_type,
            COALESCE(i.item_category, 'No Category') AS item_category,
            mo.department,
            COUNT(*) AS qty
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY manufacturing_work_order
                    ORDER BY creation DESC, name DESC
                ) AS rn
            FROM `tabManufacturing Operation`
        ) mo
        LEFT JOIN `tabItem` i
            ON mo.item_code = i.name
        WHERE mo.rn = 1
            {conditions}
        GROUP BY
            COALESCE(i.setting_type, ''),
            COALESCE(i.sub_setting_type, 'No Setting Type'),
            COALESCE(i.item_category, 'No Category'),
            mo.department
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)

    detail_map = {}
    subtotal_map = {}
    grand_total = {frappe.scrub(d): 0 for d in departments}
    grand_row_total = 0

    for row in raw_data:
        setting_type = row["setting_type"]
        sub_setting_type = row["sub_setting_type"]
        item_category = row["item_category"]
        department = row["department"]
        qty = row["qty"] or 0

        dept_field = frappe.scrub(department)
        if dept_field not in grand_total:
            continue

        detail_key = (sub_setting_type, item_category)
        if detail_key not in detail_map:
            detail_map[detail_key] = {
                "setting_type": setting_type,
                "sub_setting_type": sub_setting_type,
                "item_category": item_category,
                "bold": 0,
                "is_total": 0,
                "is_grand_total": 0,
                "row_total": 0,
            }
            for d in departments:
                detail_map[detail_key][frappe.scrub(d)] = 0

        detail_map[detail_key][dept_field] += qty
        detail_map[detail_key]["row_total"] += qty

        if sub_setting_type not in subtotal_map:
            subtotal_map[sub_setting_type] = {
                "setting_type": setting_type,
                "sub_setting_type": sub_setting_type,
                "item_category": f"{sub_setting_type} Total",
                "bold": 1,
                "is_total": 1,
                "is_grand_total": 0,
                "row_total": 0,
            }
            for d in departments:
                subtotal_map[sub_setting_type][frappe.scrub(d)] = 0

        subtotal_map[sub_setting_type][dept_field] += qty
        subtotal_map[sub_setting_type]["row_total"] += qty

        grand_total[dept_field] += qty
        grand_row_total += qty

    rows = []

    setting_order = list(subtotal_map.keys())

    for st in setting_order:
        for k, v in detail_map.items():
            if k[0] == st:
                rows.append(v)
        rows.append(subtotal_map[st])

    grand = {
        "setting_type": "",
        "sub_setting_type": "",
        "item_category": "Grand Total",
        "bold": 1,
        "is_total": 0,
        "is_grand_total": 1,
        "row_total": grand_row_total,
    }
    for d in departments:
        grand[frappe.scrub(d)] = grand_total[frappe.scrub(d)]

    rows.append(grand)

    return rows

def get_conditions(filters):
    conditions = ""
    values = {}

    default_company = frappe.defaults.get_user_default("Company")
    if default_company:
        conditions += " AND mo.company = %(company)s"
        values["company"] = default_company

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
        conditions += " AND i.setting_type = %(setting_type)s"
        values["setting_type"] = filters["setting_type"]

    if filters.get("sub_setting_type"):
        conditions += " AND i.sub_setting_type = %(sub_setting_type)s"
        values["sub_setting_type"] = filters["sub_setting_type"]

    return conditions, values