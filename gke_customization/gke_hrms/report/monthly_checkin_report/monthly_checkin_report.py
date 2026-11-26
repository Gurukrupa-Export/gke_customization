# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from bisect import bisect_left, bisect_right

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, get_time, getdate

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import (
    fetch_attendance_data_for_employees,
    get_holidays_from_context,
)

# Roles that can see any employee or a whole department
PRIVILEGED_ROLES = {"System Manager", "GK HR"}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def has_full_access():
    return bool(PRIVILEGED_ROLES & set(frappe.get_roles(frappe.session.user)))


def get_department_employees(company=None, department=None, branch=None):
    employee_filters = {"status": "Active"}
    if company:
        employee_filters["company"] = company
    if department:
        employee_filters["department"] = department
    if branch:
        employee_filters["branch"] = branch

    return frappe.get_all(
        "Employee",
        filters=employee_filters,
        pluck="name",
        order_by="employee_name asc",
        ignore_permissions=True,
    )


def validate_employee_against_filters(filters):
    employee = filters.get("employee")
    employee_details = frappe.db.get_value(
        "Employee", employee, ["company", "department", "branch"], as_dict=True
    )
    if not employee_details:
        frappe.throw(_("Employee {0} does not exist").format(employee))

    for fieldname, label in (
        ("company", _("Company")),
        ("department", _("Department")),
        ("branch", _("Branch")),
    ):
        if filters.get(fieldname) and filters.get(fieldname) != employee_details.get(
            fieldname
        ):
            frappe.throw(
                _("Employee {0} does not belong to the selected {1} {2}").format(
                    employee, label, filters.get(fieldname)
                )
            )


def get_report_employee_list(filters):
    """Return the employees the current user may see in the report.

    System Manager and GK HR see the selected employee or the whole department.
    Everyone else sees only themselves and their active direct reports.
    """
    if has_full_access():
        if filters.get("employee"):
            validate_employee_against_filters(filters)
            return [filters.get("employee")]

        if not filters.get("department"):
            frappe.throw(_("Please select a Department or an Employee"))

        return get_department_employees(
            filters.get("company"), filters.get("department"), filters.get("branch")
        )

    own_employee = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        "name",
    )
    if not own_employee:
        frappe.throw(_("No active Employee record is linked to your user"))

    allowed_employees = get_employee_list(own_employee)
    selected_employee = filters.get("employee")
    if not selected_employee:
        return allowed_employees

    if selected_employee not in allowed_employees:
        frappe.throw(_("You can only view your own record and your direct reports"))

    return [selected_employee]


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


def get_employee_list(employee):
    """Return the employee followed by their active direct reports, without duplicates."""
    if not employee:
        return []

    direct_reports = frappe.get_all(
        "Employee",
        filters={"reports_to": employee, "status": "Active"},
        pluck="name",
        ignore_permissions=True,
    )

    return [employee] + [name for name in direct_reports if name != employee]


def get_employee_map(employee_list):
    """Fetch every Employee field the report needs in one query."""
    return {
        row.name: row
        for row in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_list]},
            fields=[
                "name",
                "employee_name",
                "old_punch_id",
                "department",
                "default_shift",
                "holiday_list",
                "company",
            ],
            ignore_permissions=True,
        )
    }


def get_shift_context(employee_list, employee_map, context):
    """Build default shifts, active shift assignments and shift timings from the In Out Log context."""
    default_shift_map = {name: row.default_shift for name, row in employee_map.items()}

    assignment_map = {}
    for employee in employee_list:
        active_assignments = [
            row
            for row in context.assignments.get(employee, [])
            if row.status == "Active"
        ]
        if active_assignments:
            assignment_map[employee] = active_assignments

    return frappe._dict(
        default_shift_map=default_shift_map,
        assignment_map=assignment_map,
        shift_time_map=context.shift_types,
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


def get_holiday_weekoff_map(
    employee_list, employee_map, company, from_date, to_date, context
):
    """Return holidays and week offs per employee, for example
    {"EMP-0001": {"holidays": [...], "weekoffs": [...]}}.

    Holiday list precedence: employee, then default shift, then company default.
    """
    holiday_map = {emp: {"holidays": [], "weekoffs": []} for emp in employee_list}
    company_holiday_list = None

    for emp in employee_list:
        row = employee_map.get(emp)
        holiday_list = row.holiday_list if row and row.holiday_list else None

        if not holiday_list and row and row.default_shift:
            holiday_list = (context.shift_types.get(row.default_shift) or {}).get(
                "holiday_list"
            )

        if not holiday_list and company:
            if company_holiday_list is None:
                company_holiday_list = (
                    frappe.db.get_value("Company", company, "default_holiday_list")
                    or ""
                )
            holiday_list = company_holiday_list

        if not holiday_list:
            continue

        holiday_dates = get_holidays_from_context(
            context, holiday_list, from_date, to_date
        )
        holiday_map[emp] = {
            "holidays": holiday_dates.holidays,
            "weekoffs": holiday_dates.weekly_off,
        }

    return holiday_map


def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not from_date or not to_date:
        frappe.throw(_("Please select From Date and To Date"))

    employee_list = get_report_employee_list(filters)
    if not employee_list:
        return []

    employee_map = get_employee_map(employee_list)
    company = filters.get("company")
    if not company:
        first_employee = employee_map.get(employee_list[0])
        company = first_employee.company if first_employee else None

    date_range = get_date_range(filters)
    attendance_result, context = fetch_attendance_data_for_employees(
        company, employee_list, from_date, to_date, return_context=True
    )
    holiday_map = get_holiday_weekoff_map(
        employee_list,
        employee_map,
        company,
        getdate(from_date),
        getdate(to_date),
        context,
    )

    attendance_details = {}
    for emp in employee_list:
        records = (attendance_result.get(emp) or {}).get("records") or []
        attendance_details[emp] = {
            getdate(record.get("login_date")): record
            for record in records
            if record.get("login_date")
        }

    return process_data(
        attendance_details,
        employee_map,
        date_range,
        holiday_map,
        from_date,
        to_date,
        context,
    )


def get_columns():
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Punch ID"),
            "fieldname": "punch_id",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Date"),
            "fieldname": "login_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Shift"),
            "fieldname": "shift_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Attendance Status"),
            "fieldname": "attendance_status",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("In Time"),
            "fieldname": "in_time",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Out Time"),
            "fieldname": "out_time",
            "fieldtype": "Data",
            "width": 100,
        },
        {"label": _("Late"), "fieldname": "late", "fieldtype": "Data", "width": 100},
        {
            "label": _("Late Hrs"),
            "fieldname": "late_hrs",
            "fieldtype": "Time",
            "width": 100,
        },
        {
            "label": _("Early Hrs"),
            "fieldname": "early_hrs",
            "fieldtype": "Time",
            "width": 100,
        },
        {
            "label": _("OT Hrs"),
            "fieldname": "ot_hours",
            "fieldtype": "Time",
            "width": 100,
        },
    ]
    return columns


def process_data(
    attendance_details,
    employee_map,
    date_range,
    holiday_map,
    from_date,
    to_date,
    context,
):
    report_data = []
    employee_list = list(attendance_details.keys())
    shift_context = get_shift_context(employee_list, employee_map, context)
    attendance_map = get_attendance_map(employee_list, from_date, to_date)
    checkin_time_map = get_checkin_time_map(employee_list, from_date, to_date)

    for emp, emp_dates in attendance_details.items():
        emp_holidays = holiday_map.get(emp, {}).get("holidays", [])
        emp_weekoffs = holiday_map.get(emp, {}).get("weekoffs", [])

        for date in date_range:
            record = emp_dates.get(date, {}) or {}

            attendance_status = record.get("status")

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

            employee_details = employee_map.get(emp) or {}

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
                "out_time": ", ".join(all_out_times) or "",
                "late": record.get("late") or "",
                "late_hrs": record.get("late_hrs"),
                "early_hrs": record.get("early_hrs"),
                "ot_hours": record.get("ot_hours"),
            }

            report_data.append(row)

    return report_data
