# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import CustomFunction, Date, Max
from frappe.utils import get_datetime
from pypika.terms import ValueWrapper


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    employee = frappe.qb.DocType("Employee")
    checkin = frappe.qb.DocType("Employee Checkin")
    current_date = CustomFunction("CURDATE", [])()

    query = (
        frappe.qb.from_(employee)
        .left_join(checkin)
        .on(
            (employee.employee == checkin.employee)
            & (Date(checkin.time) == current_date)
        )
        .select(
            employee.employee.as_("employee_id"),
            employee.employee_name,
            employee.department,
            employee.company,
            employee.designation,
            ValueWrapper("Absent").as_("attendance"),
        )
        .where(employee.status == "Active")
        .where(checkin.employee.isnull())
        .orderby(employee.department)
        .orderby(employee.employee)
    )

    if filters and filters.get("company"):
        query = query.where(employee.company == filters.get("company"))

    data = query.run(as_dict=True)
    set_last_checkin_before_today(data)
    return data


def set_last_checkin_before_today(data):
    if not data:
        return

    checkin = frappe.qb.DocType("Employee Checkin")
    employee_ids = [row.employee_id for row in data]
    last_checkins = (
        frappe.qb.from_(checkin)
        .select(checkin.employee, Max(checkin.time).as_("last_time"))
        .where(checkin.employee.isin(employee_ids))
        .where(checkin.time < CustomFunction("CURDATE", [])())
        .groupby(checkin.employee)
    ).run(as_dict=True)

    last_checkin_by_employee = {
        row.employee: get_datetime(row.last_time) for row in last_checkins
    }
    for row in data:
        last_time = last_checkin_by_employee.get(row.employee_id)
        row.lastCheckinDate = last_time.date() if last_time else None
        row.lastCheckinTime = last_time.strftime("%H:%M:%S") if last_time else None


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
