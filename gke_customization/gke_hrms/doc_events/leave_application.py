import frappe
from frappe import _
from frappe.utils import add_days, getdate

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import (
    fmt_td_or_value,
    get_attendance_details_by_date,
)


def validate(doc, method):
    """Validation logic to check the sandwich rule."""
    _validate_sandwich_rule(doc)


def on_submit(doc, method):
    """Create attendance records for the leave period."""
    _on_submit(doc, method)
    leave_application_update_monthly_inout_log(doc)


def leave_application_update_monthly_inout_log(doc, method=None):
    """
    Recalculate Monthly In-Out Log when Leave Application is submitted
    """
    try:
        if not doc.employee or not doc.company:
            return

        attendance_dates = frappe.get_all(
            "Attendance",
            filters={
                "employee": doc.employee,
                "leave_application": doc.name,
                "docstatus": 1,
            },
            pluck="attendance_date",
        )

        if not attendance_dates:
            return

        mil_by_date = {}
        for row in frappe.get_all(
            "Monthly In-Out Log",
            filters={
                "employee": doc.employee,
                "company": doc.company,
                "attendance_date": ["in", attendance_dates],
                "docstatus": ["in", [0, 1]],
            },
            fields=["name", "attendance_date"],
        ):
            mil_by_date.setdefault(row.attendance_date, row.name)

        for attendance_date in attendance_dates:
            mil_name = mil_by_date.get(attendance_date)
            if not mil_name:
                continue

            res = get_attendance_details_by_date(
                doc.company, doc.employee, attendance_date
            )

            records = res.get("records") or []
            if not records:
                continue

            record = records[0]

            frappe.db.set_value(
                "Monthly In-Out Log",
                mil_name,
                {
                    "status": record.get("status"),
                    "in_time": record.get("in_time"),
                    "out_time": record.get("out_time"),
                    "spent_hrs": fmt_td_or_value(
                        record.get("spent_hrs") or record.get("spent_hours")
                    ),
                    "net_wrk_hrs": fmt_td_or_value(record.get("net_wrk_hrs")),
                    "late": record.get("late", 0) or record.get("late_entry", 0),
                    "late_hrs": fmt_td_or_value(record.get("late_hrs")),
                    "early_hrs": fmt_td_or_value(record.get("early_hrs")),
                    "ot_hrs": fmt_td_or_value(
                        record.get("ot_hours") or record.get("othrs")
                    ),
                    "p_out_hrs": fmt_td_or_value(record.get("p_out_hrs")),
                },
            )
    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Monthly In-Out Log Update Error - Leave Application",
        )


def _validate_sandwich_rule(doc, method=""):
    """
    Purpose:
        Detect sandwich holiday dates before submission
        and inform the user which holidays will be counted as Leave.

    Logic:
        - Applies sandwich detection only for eligible leave types.
        - Identifies holiday blocks within leave range.
        - If sandwich rule applies, displays affected holiday dates.
    """

    if not doc.employee or not doc.from_date or not doc.to_date:
        return

    sandwich_dates = get_sandwich_dates(doc)

    if sandwich_dates:
        formatted = ", ".join(d.strftime("%d-%m-%Y") for d in sorted(sandwich_dates))

        frappe.msgprint(
            _(
                "<b>Sandwich Rule Applied</b><br>Following holiday(s) will be counted as Leave:<br>{0}"
            ).format(formatted)
        )


def _on_submit(doc, method):
    """
    Purpose:
        Create Attendance records for:
            - Normal leave dates
            - Sandwich holiday dates (if applicable)

    Logic:
        - Fetch sandwich holiday dates
        - Determine final leave dates
        - Create Attendance entries accordingly

    Important:
        Attendance creation reflects final sandwich decision.
        Ensures payroll and leave ledger consistency.
    """

    if not doc.employee:
        return

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    public_holidays, weekly_offs = get_holiday_dates(doc.employee, from_date, to_date)
    sandwich_dates = get_sandwich_dates(doc, public_holidays)

    final_leave_dates = []

    current = from_date

    while current <= to_date:
        if current in public_holidays:
            if current in sandwich_dates:
                final_leave_dates.append(current)
        elif current in weekly_offs:
            pass
        else:
            final_leave_dates.append(current)

        current = add_days(current, 1)

    try:
        _create_attendance_records(doc, final_leave_dates, sandwich_dates)
    except Exception as e:
        frappe.log_error(
            title="Leave Application attendance error", message=frappe.get_traceback()
        )
        frappe.throw(_("Error creating attendance records: {0}").format(e))


def get_sandwich_dates(doc, public_holidays=None):
    """
    Core Sandwich Rule Engine.

    Purpose:
        Identify holiday dates that must be converted into Leave
        based on sandwich rules.

    Applies If:
        Leave Type = Casual Leave

    Sandwich Rule:
        A holiday block becomes Leave if:

            (Left Boundary  = Casual Leave OR Absent)
            AND
            (Right Boundary = Casual Leave OR Absent)

    Handles:
        - Single holiday
        - Multiple continuous holidays
        - CL-H-CL
        - CL-H-A
        - A-H-CL
        - CL-H-H-CL
        - CL-H-H-A
        - Multi-day leave ranges

    Returns:
        Set of holiday dates to be treated as Leave.
    """

    if doc.leave_type != "Casual Leave":
        return set()

    employee = doc.employee
    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    if public_holidays is None:
        public_holidays, _weekly_offs = get_holiday_dates(employee, from_date, to_date)
    holiday_dates = sorted(public_holidays)

    holidays_in_range = [d for d in holiday_dates if from_date <= d <= to_date]

    if not holidays_in_range:
        return set()

    sandwich_dates = set()
    holiday_blocks = get_continuous_blocks(holidays_in_range)

    boundary_days = set()
    for block in holiday_blocks:
        boundary_days.add(add_days(block[0], -1))
        boundary_days.add(add_days(block[-1], 1))

    boundary_days = {d for d in boundary_days if not (from_date <= d <= to_date)}
    boundary_attendance = get_boundary_attendance(employee, boundary_days)

    for block in holiday_blocks:
        left_day = add_days(block[0], -1)
        right_day = add_days(block[-1], 1)

        left_status = get_day_status(employee, left_day, doc, boundary_attendance)
        right_status = get_day_status(employee, right_day, doc, boundary_attendance)

        if left_status in ["Casual Leave", "Absent"] and right_status in [
            "Casual Leave",
            "Absent",
        ]:
            sandwich_dates.update(block)

    return sandwich_dates


def get_continuous_blocks(dates):
    """
    Groups consecutive holiday dates into continuous blocks.

    Purpose:
        Ensure sandwich logic is applied to entire holiday ranges
        instead of evaluating holidays individually.

    Example 1:
        Input: [11 Jan, 12 Jan, 14 Jan]
        Output:[[11 Jan, 12 Jan], [14 Jan]]

    Example 2 (Single Holiday Only):
        Input: [15 Jan]
        Output: [[15 Jan]]

    Example 3 (Three Continuous Holidays):
        Input: [10 Jan, 11 Jan, 12 Jan]
        Output: [[10 Jan, 11 Jan, 12 Jan]]

    Example 4 (Two Separate Blocks):
        Input: [5 Jan, 6 Jan, 8 Jan, 9 Jan, 12 Jan]
        Output: [[5 Jan, 6 Jan], [8 Jan, 9 Jan], [12 Jan]]

    Returns:
        List of holiday blocks (each block is a list of dates).
    """

    if not dates:
        return []

    blocks = []
    current_block = [dates[0]]

    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current_block.append(dates[i])
        else:
            blocks.append(current_block)
            current_block = [dates[i]]

    blocks.append(current_block)
    return blocks


def get_boundary_attendance(employee, dates):
    """
    Fetch submitted attendance of an employee for the given dates in one query.

    Returns:
        dict of attendance_date -> {status, leave_type}
    """
    if not dates:
        return {}

    attendance_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["in", list(dates)],
            "docstatus": 1,
        },
        fields=["attendance_date", "status", "leave_type"],
    )
    return {row.attendance_date: row for row in attendance_records}


def get_day_status(employee, date, current_doc, boundary_attendance):
    """
    Determine the status of a specific date for an employee.

    Checks:
        1. Attendance record (Absent, On Leave)
        2. Defaults to Present

    Returns:
        - Leave Type name (e.g., 'Casual Leave')
        - 'Absent'
        - 'Present'
    """
    # The current leave application takes priority, since its attendance is not created yet.
    if current_doc:
        if current_doc.employee == employee and getdate(
            current_doc.from_date
        ) <= date <= getdate(current_doc.to_date):
            return current_doc.leave_type

    attendance = boundary_attendance.get(date)

    if attendance and attendance.status == "Absent":
        return "Absent"

    if attendance and attendance.status == "On Leave":
        return attendance.leave_type

    return "Present"


def get_holiday_dates(employee, from_date=None, to_date=None):
    """
    Retrieve holiday dates assigned to an employee, optionally limited to a date range.

    Returns:
        tuple:
            (public_holidays_set, weekly_off_set)
    """

    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")

    if not holiday_list:
        return set(), set()

    holiday_filters = {"parent": holiday_list}
    if from_date and to_date:
        holiday_filters["holiday_date"] = ["between", [from_date, to_date]]

    holidays = frappe.get_all(
        "Holiday",
        filters=holiday_filters,
        fields=["holiday_date", "weekly_off"],
    )

    public_holidays = set()
    weekly_offs = set()

    for h in holidays:
        date = getdate(h.holiday_date)
        if h.weekly_off:
            weekly_offs.add(date)
        else:
            public_holidays.add(date)

    return public_holidays, weekly_offs


def _create_attendance_records(doc, dates, sandwich_dates):
    """
    Create Attendance records for given dates.

    Handles:
        - Prevents duplicate attendance
        - Recreates if previous record was cancelled
        - Links attendance to Leave Application
        - Submits attendance automatically
    """
    dates = [getdate(date) for date in dates]
    if not dates:
        return

    existing_attendance = {}
    for row in frappe.get_all(
        "Attendance",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [min(dates), max(dates)]],
        },
        fields=["name", "docstatus", "attendance_date"],
    ):
        previous = existing_attendance.get(row.attendance_date)
        if not previous or previous.docstatus == 2:
            existing_attendance[row.attendance_date] = row

    for date in dates:
        attendance = existing_attendance.get(date)

        if attendance:
            if attendance.docstatus == 2:
                frappe.delete_doc("Attendance", attendance.name, force=1)
            else:
                continue

        if date in sandwich_dates:
            attendance_doc = frappe.new_doc("Attendance")
            attendance_doc.update(
                {
                    "employee": doc.employee,
                    "attendance_date": date,
                    "status": "On Leave",
                    "leave_type": "Leave Without Pay",
                }
            )
            attendance_doc.insert(ignore_permissions=True)
            attendance_doc.submit()
            attendance_doc.db_set("leave_application", "")

        else:
            attendance_doc = frappe.new_doc("Attendance")
            attendance_doc.update(
                {
                    "employee": doc.employee,
                    "attendance_date": date,
                    "status": "On Leave",
                    "leave_type": doc.leave_type,
                    "leave_application": doc.name,
                }
            )
            attendance_doc.insert(ignore_permissions=True)
            attendance_doc.submit()
