# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


# is_prepared_report = False
def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    conditions, values = get_conditions(filters)

    data = frappe.db.sql(
        f"""
			SELECT
				at.employee, at.employee_name,
				at.company, at.shift,
				at.department, at.attendance_date,
				te.branch,
				COUNT(tec.name) AS punch_count
			FROM
				`tabAttendance` AS at
			LEFT JOIN
				`tabEmployee Checkin` AS tec ON tec.attendance = at.name
			LEFT JOIN
				`tabEmployee` AS te on te.name = at.employee and at.company = te.company
			WHERE (at.in_time IS NOT NULL OR at.out_time IS NOT NULL) AND at.out_time IS NULL {conditions}
			GROUP BY
				at.employee, at.attendance_date
			HAVING
				punch_count > 0
			ORDER BY
				at.attendance_date ASC;
			""",
        values,
        as_dict=1,
    )

    return data


def get_columns(filters=None):
    columns = [
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": _("Punch Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Punch Count"),
            "fieldname": "punch_count",
            "fieldtype": "Data",
            "width": 80,
        },
    ]
    return columns


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("company"):
        conditions += " AND at.company = %(company)s"
        values["company"] = filters.get("company")

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND at.attendance_date BETWEEN %(from_date)s AND %(to_date)s"
        values["from_date"] = filters.get("from_date")
        values["to_date"] = filters.get("to_date")

    if filters.get("department"):
        conditions += " AND at.department = %(department)s"
        values["department"] = filters.get("department")

    if filters.get("employee"):
        conditions += " AND at.employee = %(employee)s"
        values["employee"] = filters.get("employee")

    if filters.get("branch"):
        conditions += " AND te.branch = %(branch)s"
        values["branch"] = filters.get("branch")

    return conditions, values
