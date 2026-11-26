# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    attendance = frappe.qb.DocType("Attendance")
    checkin = frappe.qb.DocType("Employee Checkin")
    punch_count = Count(checkin.name)

    query = (
        frappe.qb.from_(attendance)
        .left_join(checkin)
        .on(checkin.attendance == attendance.name)
        .select(
            attendance.employee,
            attendance.employee_name,
            attendance.company,
            attendance.shift,
            attendance.department,
            attendance.attendance_date,
            checkin.custom_branch,
            punch_count.as_("punch_count"),
        )
        .where((attendance.in_time.isnotnull()) | (attendance.out_time.isnotnull()))
        .groupby(attendance.employee, attendance.attendance_date)
        .having(punch_count % 2 != 0)
        .orderby(attendance.attendance_date)
    )

    filters = filters or {}
    if filters.get("company"):
        query = query.where(attendance.company == filters.get("company"))

    if filters.get("from_date") and filters.get("to_date"):
        query = query.where(
            attendance.attendance_date.between(
                filters.get("from_date"), filters.get("to_date")
            )
        )

    if filters.get("department"):
        query = query.where(attendance.department == filters.get("department"))

    if filters.get("employee"):
        query = query.where(attendance.employee == filters.get("employee"))

    if filters.get("branch"):
        query = query.where(checkin.custom_branch == filters.get("branch"))

    return query.run(as_dict=True)


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
            "width": 250,
        },
        {"label": _("Punch Date"), "fieldname": "attendance_date", "fieldtype": "Date"},
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Branch"),
            "fieldname": "custom_branch",
            "fieldtype": "Data",
            "width": 200,
        },
        # {
        # 	"label": _("Punch Times"),
        # 	"fieldname": "time",
        # 	"fieldtype": "Data",
        # 	"hidden":1
        # },
        {
            "label": _("Punch Count"),
            "fieldname": "punch_count",
            "fieldtype": "Data",
            "width": 150,
        },
    ]
    return columns
