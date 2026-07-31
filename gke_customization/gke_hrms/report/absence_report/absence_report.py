# Copyright (c) 2026, Gurukrupa Export
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
            "width": 130,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 280,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 160,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 160,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Shift"),
            "fieldname": "shift",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 150,
        },
        {
            "label": _("Last Check-in"),
            "fieldname": "last_checkin",
            "fieldtype": "Datetime",
            "width": 210,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT 
            a.attendance_date,
            e.employee,
            e.employee_name,
            e.department,
            e.company,
            e.designation,
            a.shift,

            (
                SELECT MAX(ec.time)
                FROM `tabEmployee Checkin` ec
                WHERE ec.employee = e.employee
                AND ec.docstatus < 2
            ) AS last_checkin,

            CASE 
            WHEN la.name IS NOT NULL THEN la.leave_type
            ELSE 'Absent'
            END AS status


        FROM `tabAttendance` a
        INNER JOIN `tabEmployee` e ON e.employee = a.employee
        LEFT JOIN `tabLeave Application` la
            ON la.employee = a.employee
            AND la.status = 'Approved'
            AND a.attendance_date BETWEEN la.from_date AND la.to_date

        WHERE
            a.attendance_date BETWEEN %(from_date)s
                AND LEAST(%(to_date)s, DATE_SUB(CURDATE(), INTERVAL 1 DAY))
            AND DAYOFWEEK(a.attendance_date) != 1
            AND a.status IN ('Absent', 'On Leave')
            AND a.docstatus = 1
            AND e.status = 'Active'
            {conditions}

        UNION ALL

        SELECT 
            CURDATE() AS attendance_date,
            e.employee,
            e.employee_name,
            e.department,
            e.company,
            e.designation,
            NULL AS shift,

            (
                SELECT MAX(ec.time)
                FROM `tabEmployee Checkin` ec
                WHERE ec.employee = e.employee
                AND ec.docstatus < 2
            ) AS last_checkin,

            CASE 
                WHEN la.name IS NOT NULL THEN 'LWP'
                ELSE 'Absent'
            END AS status

        FROM `tabEmployee` e
        LEFT JOIN `tabLeave Application` la
            ON la.employee = e.employee
            AND la.status = 'Approved'
            AND CURDATE() BETWEEN la.from_date AND la.to_date

        WHERE
            e.status = 'Active'
            AND DAYOFWEEK(CURDATE()) != 1
            AND CURDATE() BETWEEN %(from_date)s AND %(to_date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabAttendance` a
                WHERE a.employee = e.employee
                AND a.attendance_date = CURDATE()
                AND a.docstatus = 1
            )
            AND NOT EXISTS (
                SELECT 1
                FROM `tabEmployee Checkin` ec
                WHERE ec.employee = e.employee
                AND ec.docstatus < 2
            AND DATE(ec.time) = CURDATE()
            )
            {conditions}

        ORDER BY
            attendance_date DESC,
            department ASC
    """

    return frappe.db.sql(query, filters, as_dict=True)


# -------------------------------------------------------
# Conditions
# -------------------------------------------------------

def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("e.company = %(company)s")

    if filters.get("branch"):
        conditions.append("e.branch = %(branch)s")

    if filters.get("department"):
        conditions.append("e.department = %(department)s")

    if conditions:
        return " AND " + " AND ".join(conditions)

    return ""
