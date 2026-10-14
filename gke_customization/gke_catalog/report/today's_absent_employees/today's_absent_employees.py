# Copyright (c) 2026, Gurukrupa Export and contributors
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
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 130,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 130,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch_name",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Mobile No"),
            "fieldname": "cell_number",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Attendance"),
            "fieldname": "attendance",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100,
        },
    ]


def get_data(filters):
    
    date = filters.get("date") or frappe.utils.nowdate()

    data = frappe.db.sql(
        """
        SELECT
            e.employee AS employee,
            e.employee_name AS employee_name,
            e.department AS department,
            e.designation AS designation,
            e.company AS company,
            e.branch_name AS branch_name,
            e.cell_number AS cell_number,
            'Absent' AS attendance,
            %(date)s AS date
        FROM
            `tabEmployee` e
        LEFT JOIN
            `tabEmployee Checkin` ec
            ON e.employee = ec.employee
            AND DATE(ec.time) = %(date)s
        WHERE
            e.status = 'Active'
            AND ec.employee IS NULL
        """,
        {"date": date},
        as_dict=1,
    )

    return data