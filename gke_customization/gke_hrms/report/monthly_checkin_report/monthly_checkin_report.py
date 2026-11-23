# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from bisect import bisect_left, bisect_right

import frappe
from frappe.utils import add_days, add_to_date, get_datetime, get_time, getdate

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import (
    fetch_attendance_data,
)


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_date_range(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not from_date or not to_date:
        return []

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    date_list = []
    current_date = from_date

    while current_date <= to_date:
        date_list.append(current_date)
        current_date = add_days(current_date, 1)

    return date_list


def get_employee_list(employee, department=None):
    """
    Return a list of Employee IDs that report to the given employee, including the employee itself.

    This function fetches all employees whose `reports_to` field matches the provided employee ID.
    It then returns a list containing their employee IDs (`name`) along with the given employee.
    """
    if not employee:
        return []

    filters = {"reports_to": employee, "status": "Active"}
    if department:
        filters["department"] = department
    employees = frappe.get_all("Employee", filters=filters, fields=["name"])
    # frappe.throw(str(employees))

    employee_ids = [emp["name"] for emp in employees]
    employee_ids.append(employee)

    return employee_ids


def get_shift_context(employee_list):
    """Fetch default shifts, shift assignments and shift timings for all employees at once."""
    default_shift_map = {
        row.name: row.default_shift
        for row in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_list]},
            fields=["name", "default_shift"],
            ignore_permissions=1,
        )
    }

    assignment_map = {}
    assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": ["in", employee_list],
            "status": "Active",
            "docstatus": 1,
        },
        fields=["employee", "start_date", "shift_type"],
        order_by="start_date desc",
        ignore_permissions=1,
    )
    for row in assignments:
        assignment_map.setdefault(row.employee, []).append(row)

    shift_names = set(default_shift_map.values()) | {
        row.shift_type for row in assignments
    }
    shift_names.discard(None)

    shift_time_map = {}
    if shift_names:
        shift_time_map = {
            row.name: row
            for row in frappe.get_all(
                "Shift Type",
                filters={"name": ["in", list(shift_names)]},
                fields=["name", "start_time", "end_time"],
                ignore_permissions=1,
            )
        }

    return frappe._dict(
        default_shift_map=default_shift_map,
        assignment_map=assignment_map,
        shift_time_map=shift_time_map,
    )


def get_employee_shift(employee, date, shift_context):
    shift_type = None
    for assignment in shift_context.assignment_map.get(employee, []):
        if getdate(assignment.start_date) <= getdate(date):
            shift_type = assignment.shift_type
            break

    if not shift_type:
        shift_type = shift_context.default_shift_map.get(employee)

    shift = shift_context.shift_time_map.get(shift_type)
    if not shift:
        return None, None, shift_type or None

    return shift.start_time, shift.end_time, shift_type


def get_attendance_map(employee_list, from_date, to_date):
    attendance_rows = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employee_list],
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": 1,
        },
        fields=[
            "employee",
            "attendance_date",
            "in_time",
            "out_time",
            "custom_is_employee_attendance_tool",
        ],
        ignore_permissions=1,
    )

    attendance_map = {}
    for row in attendance_rows:
        attendance_map.setdefault((row.employee, getdate(row.attendance_date)), row)
    return attendance_map


def get_checkin_time_map(employee_list, from_date, to_date):
    """Return sorted checkin times per employee, wide enough to cover every daily window."""
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_list],
            "time": [
                "between",
                [add_days(getdate(from_date), -2), add_days(getdate(to_date), 3)],
            ],
        },
        fields=["employee", "time"],
        order_by="time asc",
        ignore_permissions=1,
    )

    checkin_time_map = {}
    for row in checkins:
        checkin_time_map.setdefault(row.employee, []).append(row.time)
    return checkin_time_map


def get_employee_checkins(
    employee_checkin_times, date, start_time, end_time, attendance_data
):
    if (
        attendance_data
        and attendance_data.get("in_time")
        and attendance_data.get("out_time")
    ):
        start_dt = get_datetime(attendance_data.in_time)
        end_dt = get_datetime(attendance_data.out_time)
    # fallback if shift not found
    elif not start_time or not end_time:
        start_dt = get_datetime(str(date) + " 00:00:00")
        end_dt = add_to_date(start_dt, days=1)
    else:
        start_dt = get_datetime(f"{date} {start_time}")
        end_dt = get_datetime(f"{date} {end_time}")

        # night shift handling
        if get_time(end_time) < get_time(start_time):
            end_dt = add_to_date(end_dt, days=1)

        # add buffer (important)
        start_dt = add_to_date(start_dt, minutes=-90)  # -1.5 hrs buffer
        end_dt = add_to_date(end_dt, minutes=90)  # +1.5 hrs buffer

    first_index = bisect_left(employee_checkin_times, start_dt)
    last_index = bisect_right(employee_checkin_times, end_dt)
    checkin_times = employee_checkin_times[first_index:last_index]

    in_times = [time.strftime("%H:%M:%S") for time in checkin_times[0::2]]
    out_times = [time.strftime("%H:%M:%S") for time in checkin_times[1::2]]

    error_status = ""
    if len(checkin_times) % 2 != 0:
        error_status = "ERR"

    if (
        (not in_times or not out_times)
        and attendance_data
        and attendance_data.get("custom_is_employee_attendance_tool")
        and attendance_data.get("in_time")
        and attendance_data.get("out_time")
    ):
        in_times.append(attendance_data.in_time.strftime("%H:%M:%S"))
        out_times.append(attendance_data.out_time.strftime("%H:%M:%S"))

    return in_times, out_times, error_status


def get_holiday_weekoff_map(employee_list, company, from_date, to_date):
    """
    Returns:
    {
            "EMP-0001": {"holidays": [...], "weekoffs": [...]},
            "EMP-0002": {"holidays": [...], "weekoffs": [...]}
    }
    """

    if not employee_list:
        return {}

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # 1) Fetch employee holiday_list + default_shift
    employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", employee_list]},
        fields=["name", "holiday_list", "default_shift"],
        ignore_permissions=1,
    )

    emp_map = {e.name: e for e in employees}

    # 2) Fetch shift holiday_list
    shift_types = list({e.default_shift for e in employees if e.default_shift})

    shift_map = {}
    if shift_types:
        shifts = frappe.get_all(
            "Shift Type",
            filters={"name": ["in", shift_types]},
            fields=["name", "holiday_list"],
            ignore_permissions=1,
        )
        shift_map = {s.name: s.holiday_list for s in shifts}

    # 3) Company fallback holiday list
    company_holiday_list = None
    if company:
        company_holiday_list = frappe.db.get_value(
            "Company", company, "default_holiday_list"
        )

    # 4) Resolve holiday list per employee
    emp_holiday_list = {}
    for emp in employee_list:
        row = emp_map.get(emp)

        hl = row.holiday_list if row and row.holiday_list else None

        if not hl and row and row.default_shift:
            hl = shift_map.get(row.default_shift)

        if not hl:
            hl = company_holiday_list

        emp_holiday_list[emp] = hl

    # 5) Unique holiday lists
    holiday_lists = list({hl for hl in emp_holiday_list.values() if hl})

    holiday_map = {emp: {"holidays": [], "weekoffs": []} for emp in employee_list}

    if not holiday_lists:
        return holiday_map

    # 6) Fetch all holidays in one query
    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": ["in", holiday_lists],
            "holiday_date": ["between", [from_date, to_date]],
        },
        fields=["parent", "holiday_date", "weekly_off"],
        order_by="holiday_date asc",
        ignore_permissions=1,
    )

    # 7) Group by holiday list
    holiday_list_map = {}

    for row in holidays:
        if row.parent not in holiday_list_map:
            holiday_list_map[row.parent] = {"holidays": [], "weekoffs": []}

        if row.weekly_off:
            holiday_list_map[row.parent]["weekoffs"].append(row.holiday_date)
        else:
            holiday_list_map[row.parent]["holidays"].append(row.holiday_date)

    # 8) Assign holiday/weekoff per employee
    for emp, hl in emp_holiday_list.items():
        if hl and hl in holiday_list_map:
            holiday_map[emp] = holiday_list_map[hl]

    return holiday_map


def get_data(filters):
    employee = filters.get("employee")
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    department = filters.get("department")

    if not employee or not from_date or not to_date:
        frappe.throw("Please select Employee, From Date and To Date")
        return []

    date_range = get_date_range(filters)
    employee_list = get_employee_list(employee, department)
    holiday_map = get_holiday_weekoff_map(employee_list, company, from_date, to_date)

    attendance_details = {}

    for emp in employee_list:
        result = (
            fetch_attendance_data(
                {
                    "company": company,
                    "employee": emp,
                    "from_date": from_date,
                    "to_date": to_date,
                }
            )
            or {}
        )
        attendance_details[emp] = {
            getdate(record.get("login_date")): record
            for record in result.get("records") or []
            if record.get("login_date")
        }

    final_data = process_data(
        attendance_details, date_range, holiday_map, from_date, to_date
    )

    return final_data


def get_columns():
    columns = [
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Employee Name",
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "Punch ID",
            "fieldname": "punch_id",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 150,
        },
        {"label": "Date", "fieldname": "login_date", "fieldtype": "Date", "width": 120},
        {
            "label": "Shift",
            "fieldname": "shift_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Attendance Status",
            "fieldname": "attendance_status",
            "fieldtype": "Data",
            "width": 150,
        },
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Data", "width": 100},
        {
            "label": "Out Time",
            "fieldname": "out_time",
            "fieldtype": "Data",
            "width": 100,
        },
        {"label": "Late", "fieldname": "late", "fieldtype": "Data", "width": 100},
        {
            "label": "Late Hrs",
            "fieldname": "late_hrs",
            "fieldtype": "Time",
            "width": 100,
        },
        {
            "label": "Early Hrs",
            "fieldname": "early_hrs",
            "fieldtype": "Time",
            "width": 100,
        },
        {"label": "OT Hrs", "fieldname": "ot_hours", "fieldtype": "Time", "width": 100},
    ]
    return columns


def process_data(attendance_details, date_range, holiday_map, from_date, to_date):
    report_data = []
    employee_list = list(attendance_details.keys())
    shift_context = get_shift_context(employee_list)
    attendance_map = get_attendance_map(employee_list, from_date, to_date)
    checkin_time_map = get_checkin_time_map(employee_list, from_date, to_date)

    employee_details_map = {
        emp.name: emp
        for emp in frappe.get_all(
            "Employee",
            filters={"name": ["in", list(attendance_details.keys())]},
            fields=[
                "name",
                "employee_name",
                "old_punch_id",
                "department",
                "default_shift",
            ],
        )
    }

    for emp, emp_dates in attendance_details.items():
        emp_holidays = holiday_map.get(emp, {}).get("holidays", [])
        emp_weekoffs = holiday_map.get(emp, {}).get("weekoffs", [])

        for date in date_range:
            record = emp_dates.get(date, {}) or {}

            attendance_status = record.get("status")
            # frappe.msgprint(f"Attendance status for {emp} on {date}: {attendance_status}")

            if not attendance_status:
                if date in emp_holidays:
                    attendance_status = "H"
                elif date in emp_weekoffs:
                    attendance_status = "WO"
                else:
                    attendance_status = "XX"

            start_time, end_time, assigned_shift_type = get_employee_shift(
                emp, date, shift_context
            )

            if attendance_status not in [
                "Absent",
                "On Leave",
            ]:
                all_in_times, all_out_times, error_status = get_employee_checkins(
                    checkin_time_map.get(emp, []),
                    date,
                    start_time,
                    end_time,
                    attendance_map.get((emp, date)),
                )
                attendance_status = error_status if error_status else attendance_status
            else:
                all_in_times, all_out_times = [], []

            employee_details = employee_details_map.get(emp) or {}

            row = {
                "employee": record.get("employee") or emp,
                "employee_name": record.get("employee_name")
                or employee_details.get("employee_name"),
                "punch_id": record.get("punch_id")
                or employee_details.get("old_punch_id"),
                "department": record.get("department")
                or employee_details.get("department"),
                "login_date": record.get("login_date") or date,
                "shift_type": (
                    attendance_map.get((emp, date)) and record.get("shift_type")
                )
                or assigned_shift_type
                or "",
                "attendance_status": attendance_status,
                "in_time": ", ".join(all_in_times) or "",
                # "in_time": record.get("in_time") or "",
                "out_time": ", ".join(all_out_times) or "",
                # "out_time": record.get("out_time") or "",
                "late": record.get("late") or "",
                "late_hrs": record.get("late_hrs"),
                "early_hrs": record.get("early_hrs"),
                "ot_hours": record.get("ot_hours"),
            }

            report_data.append(row)

    return report_data
