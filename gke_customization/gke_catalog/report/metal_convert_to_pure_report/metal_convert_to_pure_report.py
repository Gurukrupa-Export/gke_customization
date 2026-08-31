# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": "Slip No",
            "fieldname": "slip_no",
            "fieldtype": "Link",
            "options": "Metal Conversions",
            "width": 150
        },
        {
            "label": "Date",
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": "From Touch",
            "fieldname": "from_touch",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "To Touch",
            "fieldname": "to_touch",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Comments",
            "fieldname": "comments",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": "Net Wt",
            "fieldname": "base_wt",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": "Alloy Wt",
            "fieldname": "mix_wt",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": "Gold Wt",
            "fieldname": "total_wt",
            "fieldtype": "Float",
            "width": 120
        }
    ]


def get_data(filters):
    conditions = [
        "mc.source_qty > mc.target_qty",
        "mc.target_alloy IS NOT NULL"
    ]

    values = {}

    if filters.get("from_date"):
        conditions.append("mc.date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("mc.date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("department"):
        conditions.append("mc.department = %(department)s")
        values["department"] = filters.get("department")

    if filters.get("slip_no"):
        conditions.append("mc.name = %(slip_no)s")
        values["slip_no"] = filters.get("slip_no")

    if filters.get("employee"):
        conditions.append("mc.employee = %(employee)s")
        values["employee"] = filters.get("employee")

    if filters.get("from_touch"):
        conditions.append("mc.source_item = %(from_touch)s")
        values["from_touch"] = filters.get("from_touch")

    if filters.get("to_touch"):
        conditions.append("mc.target_item = %(to_touch)s")
        values["to_touch"] = filters.get("to_touch")

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            mc.name AS slip_no,
            mc.date,
            mc.source_item AS from_touch,
            mc.target_item AS to_touch,
            mc._comments AS comments,
            mc.source_qty AS base_wt,
            mc.target_alloy_qty AS mix_wt,
            mc.target_qty AS total_wt
        FROM `tabMetal Conversions` mc
        WHERE {where_clause}
        ORDER BY mc.date DESC, mc.name DESC
        """,
        values=values,
        as_dict=True
    )   
