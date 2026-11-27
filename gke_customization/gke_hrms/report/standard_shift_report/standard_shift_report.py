# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder.functions import CustomFunction, IfNull
from frappe.utils import add_days, getdate
from pypika.functions import Date
from pypika.terms import LiteralValue


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    validate_filters(filters)

    time_format = CustomFunction("TIME_FORMAT", ["time_value", "format"])
    sec_to_time = CustomFunction("SEC_TO_TIME", ["seconds"])
    add_time = CustomFunction("ADDTIME", ["time_value", "time_to_add"])
    time_diff = CustomFunction("TIMEDIFF", ["end_time", "start_time"])
    timestamp_diff = CustomFunction("TIMESTAMPDIFF", ["unit", "start", "end"])
    date_add = CustomFunction("DATE_ADD", ["date_value", "interval_value"])
    if_function = CustomFunction("IF", ["condition", "value_if_true", "value_if_false"])
    floor = CustomFunction("FLOOR", ["number"])
    random_number = CustomFunction("RAND", [])

    time_pattern = "%H:%i"
    attendance = frappe.qb.DocType("Attendance")

    adj_out_time = if_function(
        timestamp_diff(LiteralValue("HOUR"), attendance.in_time, attendance.out_time)
        >= 9,
        date_add(attendance.in_time, LiteralValue("INTERVAL 9 HOUR")),
        attendance.out_time,
    )

    attendance_query = (
        frappe.qb.from_(attendance)
        .select(
            attendance.attendance_date.as_("attendance_date"),
            attendance.late_entry.as_("late_entry"),
            time_format(attendance.in_time, time_pattern).as_("in_time"),
            time_format(sec_to_time(attendance.working_hours * 3600), time_pattern).as_(
                "spent_hours"
            ),
            IfNull(attendance.leave_type, attendance.status).as_("status"),
            time_format(adj_out_time, time_pattern).as_("adj_out"),
            time_format(time_diff(adj_out_time, attendance.in_time), time_pattern).as_(
                "adj_spent_hour"
            ),
            floor(random_number() * 10).as_("rand_int"),
        )
        .where(attendance.docstatus == 1)
        .where(
            attendance.attendance_date[
                filters.get("from_date") : filters.get("to_date")
            ]
        )
    )
    if filters.get("employee"):
        attendance_query = attendance_query.where(
            attendance.employee == filters.get("employee")
        )

    subquery = attendance_query.as_("subquery")
    adj_out_with_random = add_time(
        subquery.adj_out, sec_to_time(subquery.rand_int * 60)
    )

    data = (
        frappe.qb.from_(subquery)
        .select(
            subquery.attendance_date,
            subquery.in_time,
            subquery.spent_hours,
            subquery.status,
            subquery.adj_out,
            subquery.adj_spent_hour,
            subquery.rand_int,
            subquery.late_entry,
            time_format(adj_out_with_random, time_pattern).as_("adj_out_2"),
            time_diff(
                time_format(adj_out_with_random, time_pattern), subquery.in_time
            ).as_("total_adj"),
        )
        .orderby(subquery.attendance_date)
        .run(as_dict=True)
    )

    if not data:
        return []

    data = process_data(data, filters)
    totals = get_totals(data)
    data += totals

    return data


def process_data(data, filters):
    employee = filters.get("employee")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    processed = {}
    result = []
    holidays = []
    weekly_offs = []
    emp_det = frappe.db.get_value(
        "Employee",
        employee,
        ["default_shift", "holiday_list", "date_of_joining"],
        as_dict=1,
    )
    shift = emp_det.get("default_shift")
    date_of_joining = getdate(emp_det.get("date_of_joining"))

    checkin = frappe.qb.DocType("Employee Checkin")
    login_date = Date(checkin.time)
    od_dates = (
        frappe.qb.from_(checkin)
        .select(login_date.as_("login_date"))
        .where(checkin.employee == employee)
        .where(checkin.source == "Outdoor Duty")
        .where(checkin.time[from_date : add_days(to_date, 1)])
        .groupby(login_date)
        .run(pluck="login_date")
    )
    od_dates = set(od_dates)

    if shift and not emp_det.get("holiday_list"):
        emp_det["holiday_list"] = frappe.db.get_value(
            "Shift Type", shift, "holiday_list"
        )

    if holiday_list := emp_det.get("holiday_list"):
        holiday_rows = frappe.get_all(
            "Holiday",
            {"parent": holiday_list, "holiday_date": ["between", [from_date, to_date]]},
            ["holiday_date", "weekly_off"],
        )
        weekly_offs = {row.holiday_date for row in holiday_rows if row.weekly_off}
        holidays = {row.holiday_date for row in holiday_rows if not row.weekly_off}

    for row in data:
        if row.status == "Present":
            row.status = "P"
        elif row.status == "Absent":
            row.status = "A"

        processed[row.attendance_date] = row

    ot_for_wo = frappe.get_all(
        "OT Log",
        {
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "is_cancelled": 0,
        },
        [
            "attendance_date",
            "allowed_ot as ot_hours",
            "first_in as in_time",
            "last_out as out_time",
        ],
    )
    ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
    date_range = get_date_range(from_date, to_date)

    for date in date_range:
        row = processed.get(date, ot_for_wo.get(date, {}))

        if date in od_dates:
            status = "OD"
        elif date in weekly_offs and date >= date_of_joining:
            status = "WO"
        elif date in holidays and date >= date_of_joining:
            status = "H"
        else:
            status = "XX"

        day_row = {"attendance_date": date, "status": status}
        day_row.update(row)
        if status == "OD":
            day_row["status"] = "OD"
        result.append(day_row)

    return result


def get_totals(data):
    totals = {
        "adj_out_2": "Total Hours",
        "total_adj": timedelta(0),
    }

    for row in data:
        total_adj = row.get("total_adj") or "00:00"
        totals["total_adj"] += str_to_timedelta(total_adj)

    total_hours = totals["total_adj"].total_seconds() / 3600
    hours_per_day = 9
    net_days = total_hours / hours_per_day

    total_adj_days = {"adj_out_2": "Net Days", "total_adj": round(net_days, 2)}

    return totals, total_adj_days


def get_columns(filters=None):
    columns = [
        {
            "label": _("Attendance Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Late Entry"),
            "fieldname": "late_entry",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("In Time"),
            "fieldname": "in_time",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Out Time"),
            "fieldname": "adj_out_2",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Total Spent Hours"),
            "fieldname": "total_adj",
            "fieldtype": "Data",
            "width": 250,
        },
    ]
    return columns


def validate_filters(filters):
    if not (filters.get("from_date") and filters.get("to_date")):
        frappe.throw(_("From & To Dates are mandatory"))

    if not filters.get("employee"):
        frappe.throw(_("Employee is mandatory"))


def get_date_range(start_date, end_date):
    current_date = getdate(start_date)
    end_date = getdate(end_date)

    dates = []
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


def str_to_timedelta(time_value):
    """Convert an "HH:MM" or "HH:MM:SS" value to a timedelta, ignoring seconds."""
    hours, minutes = str(time_value).split(":")[:2]
    return timedelta(hours=int(hours), minutes=int(minutes))
