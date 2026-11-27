# Copyright (c) 2026, Gurukrupa Export
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case, Order
from frappe.query_builder.functions import CurDate, Date, Max
from pypika.terms import CustomFunction, ExistsCriterion, Field, Interval, ValueWrapper

DayOfWeek = CustomFunction("DAYOFWEEK", ["date"])
Least = CustomFunction("LEAST", ["value1", "value2"])

# MySQL DAYOFWEEK() numbers Sunday as 1
SUNDAY = 1


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))

    columns = get_columns()
    data = get_data(filters)
    return columns, data


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
    attendance = frappe.qb.DocType("Attendance")
    employee = frappe.qb.DocType("Employee")
    leave_application = frappe.qb.DocType("Leave Application")

    past_days_query = (
        frappe.qb.from_(attendance)
        .inner_join(employee)
        .on(employee.employee == attendance.employee)
        .left_join(leave_application)
        .on(
            (leave_application.employee == attendance.employee)
            & (leave_application.status == "Approved")
            & attendance.attendance_date[
                leave_application.from_date : leave_application.to_date
            ]
        )
        .select(
            attendance.attendance_date,
            employee.employee,
            employee.employee_name,
            employee.department,
            employee.company,
            employee.designation,
            attendance.shift,
            get_last_checkin_query(employee).as_("last_checkin"),
            Case()
            .when(leave_application.name.isnotnull(), leave_application.leave_type)
            .else_("Absent")
            .as_("status"),
        )
        .where(
            attendance.attendance_date[
                filters.get("from_date") : Least(
                    filters.get("to_date"), CurDate() - Interval(days=1)
                )
            ]
        )
        .where(DayOfWeek(attendance.attendance_date) != SUNDAY)
        .where(attendance.status.isin(["Absent", "On Leave"]))
        .where(attendance.docstatus == 1)
        .where(employee.status == "Active")
    )

    today_attendance_query = (
        frappe.qb.from_(attendance)
        .select(1)
        .where(attendance.employee == employee.employee)
        .where(attendance.attendance_date == CurDate())
        .where(attendance.docstatus == 1)
    )

    checkin = frappe.qb.DocType("Employee Checkin")
    today_checkin_query = (
        frappe.qb.from_(checkin)
        .select(1)
        .where(checkin.employee == employee.employee)
        .where(checkin.docstatus < 2)
        .where(Date(checkin.time) == CurDate())
    )

    today_query = (
        frappe.qb.from_(employee)
        .left_join(leave_application)
        .on(
            (leave_application.employee == employee.employee)
            & (leave_application.status == "Approved")
            & CurDate()[leave_application.from_date : leave_application.to_date]
        )
        .select(
            CurDate().as_("attendance_date"),
            employee.employee,
            employee.employee_name,
            employee.department,
            employee.company,
            employee.designation,
            ValueWrapper(None).as_("shift"),
            get_last_checkin_query(employee).as_("last_checkin"),
            Case()
            .when(leave_application.name.isnotnull(), "LWP")
            .else_("Absent")
            .as_("status"),
        )
        .where(employee.status == "Active")
        .where(DayOfWeek(CurDate()) != SUNDAY)
        .where(CurDate()[filters.get("from_date") : filters.get("to_date")])
        .where(ExistsCriterion(today_attendance_query).negate())
        .where(ExistsCriterion(today_checkin_query).negate())
    )

    past_days_query = apply_filters(past_days_query, employee, filters)
    today_query = apply_filters(today_query, employee, filters)

    query = (
        past_days_query.union_all(today_query)
        .orderby(Field("attendance_date"), order=Order.desc)
        .orderby(Field("department"))
        .orderby(Field("employee"))
    )
    return query.run(as_dict=True)


def get_last_checkin_query(employee):
    checkin = frappe.qb.DocType("Employee Checkin")
    return (
        frappe.qb.from_(checkin)
        .select(Max(checkin.time))
        .where(checkin.employee == employee.employee)
        .where(checkin.docstatus < 2)
    )


def apply_filters(query, employee, filters):
    for fieldname in ("company", "branch", "department"):
        if filters.get(fieldname):
            query = query.where(employee[fieldname] == filters.get(fieldname))
    return query
