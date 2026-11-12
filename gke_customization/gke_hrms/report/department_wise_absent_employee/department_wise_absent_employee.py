# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    conditions, values = get_conditions(filters)

    data = frappe.db.sql(
        f"""SELECT
		e.employee as employee_id,e.employee_name as employee_name,
		e.department as department,e.company as company,
		e.designation as designation,'Absent' AS attendance,
		MAX(DATE(ec.time)) AS lastCheckinDate,
		MAX(TIME(ec.time)) AS lastCheckinTime
	FROM `tabEmployee` e
	LEFT JOIN `tabEmployee Checkin` ec
		ON e.employee = ec.employee AND DATE(ec.time) = CURDATE()
		WHERE e.status = 'Active' AND ec.employee IS NULL {conditions} GROUP BY e.employee, e.employee_name, e.department, e.company
	Order by e.department asc""",
        values,
        as_dict=1,
    )

    return data


def get_columns(filters=None):
    columns = [
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "label": _("Attendance"),
            "fieldname": "attendance",
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "label": _("Last Checkin Date"),
            "fieldname": "lastCheckinDate",
            "fieldtype": "Date",
            "width": 0,
        },
        {
            "label": _("Last Checkin Time"),
            "fieldname": "lastCheckinTime",
            "fieldtype": "Data",
            "width": 0,
        },
    ]
    return columns


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("company"):
        conditions += " AND e.company = %(company)s"
        values["company"] = filters.get("company")

    return conditions, values
