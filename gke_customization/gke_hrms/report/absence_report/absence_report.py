# Copyright (c) 2024, Gurukrupa Export
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))

    columns = get_columns()
    data = get_data(filters)
    return columns, data


# -------------------------------------------------------
# Columns
# -------------------------------------------------------

def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 180,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150,
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
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Attendance"),
            "fieldname": "attendance",
            "fieldtype": "Data",
            "width": 100,
        },
    ]


# -------------------------------------------------------
# Data
# -------------------------------------------------------

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        WITH RECURSIVE date_series AS (
            SELECT %(from_date)s AS attendance_date
            UNION ALL
            SELECT DATE_ADD(attendance_date, INTERVAL 1 DAY)
            FROM date_series
            WHERE attendance_date < %(to_date)s
        )
        SELECT
            ds.attendance_date,
            e.employee,
            e.employee_name,
            e.company,
            e.department,
            e.designation,
            'Absent' AS attendance
        FROM
            date_series ds
        CROSS JOIN tabEmployee e
        LEFT JOIN `tabEmployee Checkin` ec
            ON ec.employee = e.employee
            AND DATE(ec.time) = ds.attendance_date
        WHERE
            ec.employee IS NULL
            AND e.status = 'Active'
            {conditions}
        ORDER BY
            ds.attendance_date,
            e.department,
            e.employee
    """

    return frappe.db.sql(query, filters, as_dict=True)


# -------------------------------------------------------
# Conditions
# -------------------------------------------------------

def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("e.company = %(company)s")

    if filters.get("department"):
        conditions.append("e.department = %(department)s")

    if filters.get("designation"):
        conditions.append("e.designation = %(designation)s")

    if filters.get("employee"):
        conditions.append("e.employee = %(employee)s")

    if conditions:
        return " AND " + " AND ".join(conditions)

    return ""
