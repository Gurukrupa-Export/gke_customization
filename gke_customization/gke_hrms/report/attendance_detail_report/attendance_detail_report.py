# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
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
            "width": 220,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "Employee_name",
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "options": "Designation",
            "width": 150,
        },
        {
            "label": _("Shift"),
            "fieldname": "shift",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 120,
        },
        {
            "label": _("Attendance Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 130,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Late Entry Time"),
            "fieldname": "late_entry_time",
            "fieldtype": "Time",
            "width": 150,
        },
        {
            "label": _("Early Out Time"),
            "fieldname": "early_out_time",
            "fieldtype": "Time",
            "width": 150,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            e.name AS employee,
            e.employee_name AS employee_name,
            e.department AS department,
            e.designation AS designation,
            e.default_shift AS shift,
            e.company AS company,
            a.status AS status,
            a.attendance_date AS attendance_date,
            TIME_FORMAT(ec_in.time, '%%H:%%i:%%s') AS late_entry_time,
            TIME_FORMAT(ec_out.time, '%%H:%%i:%%s') AS early_out_time
        FROM `tabAttendance` a
        INNER JOIN `tabEmployee` e ON e.name = a.employee
        LEFT JOIN `tabEmployee Checkin` ec_in
            ON ec_in.employee = e.name
            AND ec_in.log_type = 'IN'
            AND DATE(ec_in.shift_start) = a.attendance_date
            AND TIME(ec_in.time) > ADDTIME(TIME(ec_in.shift_start), '00:05:59')
        LEFT JOIN `tabEmployee Checkin` ec_out
            ON ec_out.employee = e.name
            AND ec_out.log_type = 'OUT'
            AND DATE(ec_out.shift_start) = a.attendance_date
            AND TIME(ec_out.time) < TIME(ec_out.shift_end)
        WHERE
            e.status = 'Active'
            AND a.docstatus < 2
            {conditions}
        ORDER BY
            a.attendance_date DESC,
            e.name ASC
    """

    return frappe.db.sql(query, filters, as_dict=True)


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("e.company = %(company)s")

    if filters.get("from_date"):
        conditions.append("a.attendance_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("a.attendance_date <= %(to_date)s")

    if filters.get("department"):
        conditions.append("e.department = %(department)s")

    if filters.get("designation"):
        conditions.append("e.designation = %(designation)s")

    if filters.get("shift"):
        conditions.append("e.default_shift = %(shift)s")

    if filters.get("status"):
        conditions.append("a.status = %(status)s")

    if filters.get("employee"):
        conditions.append("e.name = %(employee)s")

    if not conditions:
        return ""

    return "AND " + " AND ".join(conditions)
