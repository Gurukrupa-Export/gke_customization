# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import CustomFunction, Max
from pypika.functions import Date
from pypika.terms import LiteralValue


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    employee = frappe.qb.DocType("Employee")
    checkin = frappe.qb.DocType("Employee Checkin")

    checkin_date = Date(checkin.time)
    checkin_time = CustomFunction("TIME", ["datetime_value"])(checkin.time)
    current_date = CustomFunction("CURDATE", [])()

    query = (
        frappe.qb.from_(employee)
        .left_join(checkin)
        .on((employee.employee == checkin.employee) & (checkin_date == current_date))
        .select(
            employee.employee.as_("employee_id"),
            employee.employee_name,
            employee.department,
            employee.company,
            employee.designation,
            LiteralValue("'Absent'").as_("attendance"),
            Max(checkin_date).as_("lastCheckinDate"),
            Max(checkin_time).as_("lastCheckinTime"),
        )
        .where(employee.status == "Active")
        .where(checkin.employee.isnull())
        .groupby(
            employee.employee,
            employee.employee_name,
            employee.department,
            employee.company,
        )
        .orderby(employee.department)
    )

    if filters and filters.get("company"):
        query = query.where(employee.company == filters.get("company"))

    return query.run(as_dict=True)


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
