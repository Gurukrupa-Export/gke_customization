# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Max
from frappe.utils import add_days, get_datetime, getdate
from pypika.terms import ValueWrapper


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    employee = frappe.qb.DocType("Employee")
    checkin = frappe.qb.DocType("Employee Checkin")
    today = getdate()

    query = (
        frappe.qb.from_(employee)
        .left_join(checkin)
        .on(
            (employee.employee == checkin.employee)
            & (checkin.time >= today)
            & (checkin.time < add_days(today, 1))
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
    set_last_checkin_before_today(data, today)
    return data


def set_last_checkin_before_today(data, today):
    if not data:
        return

    checkin = frappe.qb.DocType("Employee Checkin")
    employee_ids = [row.employee_id for row in data]
    last_checkins = (
        frappe.qb.from_(checkin)
        .select(checkin.employee, Max(checkin.time).as_("last_time"))
        .where(checkin.employee.isin(employee_ids))
        .where(checkin.time < today)
        .groupby(checkin.employee)
    ).run(as_dict=True)

    last_checkin_by_employee = {
        row.employee: get_datetime(row.last_time) for row in last_checkins
    }
    for row in data:
        last_time = last_checkin_by_employee.get(row.employee_id)
        row.last_checkin_date = last_time.date() if last_time else None
        row.last_checkin_time = last_time.strftime("%H:%M:%S") if last_time else None


def get_columns(filters=None):
    columns = [
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Link",
            "options": "Employee",
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
            "fieldtype": "Link",
            "options": "Department",
            "width": 150,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 0,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
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
            "fieldname": "last_checkin_date",
            "fieldtype": "Date",
            "width": 0,
        },
        {
            "label": _("Last Checkin Time"),
            "fieldname": "last_checkin_time",
            "fieldtype": "Time",
            "width": 0,
        },
    ]
    return columns
