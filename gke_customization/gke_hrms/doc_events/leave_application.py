from frappe.utils import getdate, nowdate, add_days , today
from frappe import _
import frappe
from datetime import timedelta , datetime 
from gke_customization.gke_hrms.sandwich_rule import (
    get_attendance_request_dates,
    get_day_status_map,
    get_sandwiched_holidays,
    split_holidays,
)


def validate(doc, method):
    """Validation logic to check the sandwich rule and past leave restriction."""
    # check_past_month_restriction(doc)
    # check_sandwich_rule(doc)
    _validate_sandwich_rule(doc)


def check_past_month_restriction(doc):
    """Ensure leave is applied only for the current or future months."""
    current_date = getdate(nowdate())  # Get today's date
    current_year = current_date.year
    current_month = current_date.month

    leave_start_date = getdate(doc.from_date)
    leave_year = leave_start_date.year
    leave_month = leave_start_date.month

    # Check if the leave start date is in a past month
    if (leave_year < current_year) or (leave_year == current_year and leave_month < current_month):
        frappe.throw("You cannot apply for leave in past months. Please select a date in the current or future months.")

def check_sandwich_rule(doc):
    if doc.employee and doc.from_date and doc.to_date:
        holiday_list = frappe.db.get_value('Employee', doc.employee, 'holiday_list')
        # frappe.throw(f"{holiday_list}")
        if holiday_list:
            holiday_list_doc = frappe.get_doc('Holiday List', holiday_list)
            holidays = holiday_list_doc.get('holidays') or []

            from_date = getdate(doc.from_date)
            to_date = getdate(doc.to_date)

            # Separate holiday dates and weekly off dates
            holiday_dates = {
                getdate(holiday.holiday_date)
                for holiday in holidays
            if not holiday.weekly_off
            }
            weekly_off_dates = {
                getdate(holiday.holiday_date)
                for holiday in holidays
                if holiday.weekly_off
            }

            leave_dates = {
                from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)
            }

            # Identify sandwiched holidays (holidays having leave before & after)
            sandwiched_holidays = {
                date for date in holiday_dates
                if (date - timedelta(days=1) in leave_dates and date + timedelta(days=1) in leave_dates)
            }

            # Calculate total leave days (excluding only weekly offs, including sandwiched holidays)
            doc.total_leave_days = len([
                date for date in leave_dates
                if date not in weekly_off_dates and (date not in holiday_dates or date in sandwiched_holidays)
            ])

            # If any holiday is sandwiched, set leave type to LWP
            if sandwiched_holidays:
                frappe.msgprint(
                    _("A holiday is sandwiched between your leave period. Leave type has been automatically set to Leave Without Pay (LWP)."),
                    alert=True
                )
                doc.leave_type = "Leave Without Pay"


def on_submit(doc, method):
    """Create attendance records for the leave period."""
    # create_attendance_records(doc)
    _on_submit(doc, method)

    frappe.db.commit()
    leave_application_update_monthly_inout_log(doc)

def create_attendance_records(doc):
    if doc.employee and doc.from_date and doc.to_date:
        holiday_list = frappe.db.get_value('Employee', doc.employee, 'holiday_list')

        if holiday_list:
            holiday_list_doc = frappe.get_doc('Holiday List', holiday_list)
            holidays = holiday_list_doc.get('holidays') or []

            from_date = getdate(doc.from_date)
            to_date = getdate(doc.to_date)

            holiday_dates = [
                getdate(holiday.holiday_date)
                for holiday in holidays
            ]
            weekly_off_dates = [
                getdate(holiday.holiday_date)
                for holiday in holidays
            ]

            # Adjust `to_date` to exclude holidays/weekly offs
            while to_date in holiday_dates or to_date in weekly_off_dates:
                to_date = add_days(to_date, -1)

            # Start from `from_date` and loop through all dates until `to_date`
            current_date = from_date
            while current_date <= to_date:

                # Skip holidays unless they fall between from_date and to_date (excluding boundaries)
                if current_date in holiday_dates and (current_date == from_date or current_date == to_date):
                    current_date = add_days(current_date, 1)
                    continue

                # Set status as 'On Leave' for all applicable dates
                status = "On Leave"

                # Check if an attendance record already exists for the current date
                attendance = frappe.db.get_value(
                    'Attendance',
                    {'employee': doc.employee, 'attendance_date': current_date},
                    ['name', 'docstatus'],
                    as_dict=True
                )

                if attendance:
                    # If attendance exists but is canceled, recreate it
                    if attendance['docstatus'] == 2:  # Docstatus 2 means "Canceled"
                        frappe.delete_doc('Attendance', attendance['name'], force=1)
                    else:
                        # If attendance exists and is not canceled, skip
                        current_date = add_days(current_date, 1)
                        continue

                # Create a new attendance record
                new_attendance = frappe.get_doc({
                    'doctype': 'Attendance',
                    'employee': doc.employee,
                    'attendance_date': current_date,
                    'status': status,
                    'leave_application': doc.name
                })
                new_attendance.insert(ignore_permissions=True)
                new_attendance.submit()

                current_date = add_days(current_date, 1)


######################### Update Monthly in-out Log after Submit Attendance Req #################################
##### 19 Feb 2026 ####

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date, fmt_td_or_value, to_duration_seconds

def leave_application_update_monthly_inout_log(doc, method=None):
    """
    Recalculate Monthly In-Out Log when Leave Application is submitted
    """
    try:
        # frappe.msgprint(f"Updating Monthly In-Out Log for Leave Application: {doc.name}")
        if not doc.employee or not doc.company:
            return

        # Get attendance of Leave Application
        attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "employee": doc.employee,
                "leave_application": doc.name,
                "docstatus": 1, 
            },
            fields=["name", "attendance_date"],
        )
        
        if not attendance_list:
            # frappe.msgprint(f"No attendance found for Leave Application: {doc.name}")
            return
            
        for att in attendance_list:
            attendance_date = att.attendance_date

            mil_name = frappe.db.get_value(
                "Monthly In-Out Log",
                {
                    "employee": doc.employee,
                    "company": doc.company,
                    "attendance_date": attendance_date,
                    "docstatus": ["in", [0, 1]],
                },
                "name",
            )

            if not mil_name:
                # frappe.msgprint(f"No Monthly In-Out Log found for {attendance_date}")
                return

            mil = frappe.db.get_value("Monthly In-Out Log", mil_name, ["company", "employee"], as_dict=True)

            res = get_attendance_details_by_date(
                mil.company,
                mil.employee,
                attendance_date
            )

            records = res.get("records") or []
            if not records:
                # frappe.msgprint(f"No records found for {attendance_date}")
                return

            record = records[0]
            frappe.db.set_value(
                "Monthly In-Out Log",
                mil_name,
                {
                    "status": record.get("status"),
                    "in_time": record.get("in_time"),
                    "out_time": record.get("out_time"),
                    "spent_hrs": to_duration_seconds(record.get("spent_hrs") or record.get("spent_hours")),
                    "net_wrk_hrs": fmt_td_or_value(record.get("net_wrk_hrs")),
                    "late": record.get("late", 0) or record.get("late_entry", 0),
                    "late_hrs": fmt_td_or_value(record.get("late_hrs")),
                    "early_hrs": fmt_td_or_value(record.get("early_hrs")),
                    "ot_hrs": fmt_td_or_value(record.get("ot_hours") or record.get("othrs")),
                    "p_out_hrs": fmt_td_or_value(record.get("p_out_hrs")),
                },
            )

            frappe.db.commit()
    except Exception as e:
        # frappe.msgprint(f"Error updating Monthly In-Out Log: {e}")
        frappe.log_error(message=f"Error updating Monthly In-Out Log: {e}", title="Monthly In-Out Log Update Error - Leave Application")

###########################################################################################################



################################### New Sandwidch Rule #############################################
#### Date : 20 Feb 2025


def _validate_sandwich_rule(doc, method=''):
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
    # frappe.msgprint(f"Sandwidch dates: {sandwich_dates}")

    if sandwich_dates:
        formatted = ", ".join(d.strftime("%d-%m-%Y") for d in sandwich_dates)

        frappe.msgprint(
            f"<b>Sandwich Rule Applied</b><br>"
            f"Following holiday(s) will be counted as Leave:<br>{formatted}"
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

    holiday_dates = get_holiday_dates(doc.employee)
    public_holidays, weekly_offs = holiday_dates
    sandwich_dates = set(get_sandwich_dates(doc, holiday_dates))

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
        frappe.db.rollback()
        frappe.log_error(f"Error creating attendance records: {e}")
        frappe.throw(f"Error creating attendance records: {e}")



def get_sandwich_dates(doc, holiday_dates=None):
    """
    Core Sandwich Rule Engine.

    Purpose:
        Identify holiday dates that must be converted into Leave
        based on sandwich rules.

    Applies If:
        Leave Type = Casual Leave

    Sandwich Rule:
        A holiday block becomes Leave if:

            (Left Boundary  = Casual Leave OR Half Day OR Absent)
            AND
            (Right Boundary = Casual Leave OR Half Day OR Absent)

        Weekly offs next to a holiday are part of the holiday block and are never
        converted. A boundary that is Present, Sick Leave, Marriage Leave, Outdoor Duty
        or covered by an Attendance Request blocks the sandwich.

    Handles:
        - Single holiday
        - Multiple continuous holidays
        - CL-H-CL
        - CL-H-A
        - A-H-CL
        - CL-H-H-CL
        - CL-H-H-A
        - Multi-day leave ranges

    holiday_dates is an optional (public_holidays, weekly_offs) tuple covering the
    full holiday list of the employee, to avoid fetching it twice.

    Returns:
        List of holiday dates to be treated as Leave.
    """

    if doc.leave_type != "Casual Leave":
        return []

    employee = doc.employee

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    if holiday_dates is None:
        holiday_dates = get_holiday_dates(employee)

    public_holidays, weekly_offs = holiday_dates

    holidays_in_range = {
        d for d in public_holidays if from_date <= d <= to_date
    }

    if not holidays_in_range:
        return []

    non_working_days = public_holidays | weekly_offs
    lookup_from = from_date - timedelta(days=1)
    while lookup_from in non_working_days:
        lookup_from -= timedelta(days=1)
    lookup_to = to_date + timedelta(days=1)
    while lookup_to in non_working_days:
        lookup_to += timedelta(days=1)

    status_map = get_day_status_map([employee], lookup_from, lookup_to)
    attendance_request_dates = get_attendance_request_dates(
        [employee], lookup_from, lookup_to
    ).get(employee, set())

    def get_status(date):
        if from_date <= date <= to_date:
            return doc.leave_type
        return status_map.get((employee, date), "Present")

    return sorted(
        get_sandwiched_holidays(
            public_holidays,
            weekly_offs,
            holidays_in_range,
            get_status,
            attendance_request_dates,
            casual_leave_applied=True,
        )
    )

def get_holiday_dates(employee, from_date=None, to_date=None):
    """
    Retrieve holiday dates assigned to an employee, optionally within a date range.

    Returns:
        tuple:
            (public_holidays_set, weekly_off_set)
    """

    holiday_list = frappe.db.get_value(
        "Employee", employee, "holiday_list"
    )

    if not holiday_list:
        return set(), set()

    filters = {"parent": holiday_list}
    if from_date and to_date:
        filters["holiday_date"] = ["between", [from_date, to_date]]

    holidays = frappe.get_all(
        "Holiday",
        filters=filters,
        fields=["holiday_date", "weekly_off"]
    )

    return split_holidays(holidays)

def _create_attendance_records(doc, dates, sandwich_dates):
    """
    Create Attendance records for given dates.

    Handles:
        - Prevents duplicate attendance
        - Recreates if previous record was cancelled
        - Links attendance to Leave Application
        - Submits attendance automatically
    """
    if not dates:
        return

    sandwich_dates = set(sandwich_dates)
    dates = [getdate(date) for date in dates]

    # One row per date. A live (draft or submitted) row always wins over a cancelled one,
    # so a cancelled row is never deleted and replaced when a live row already exists.
    existing_attendance = {}
    for attendance in frappe.get_all(
        "Attendance",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [min(dates), max(dates)]],
        },
        fields=["name", "docstatus", "attendance_date"],
    ):
        day = getdate(attendance.attendance_date)
        saved = existing_attendance.get(day)
        if saved is None or saved.docstatus == 2:
            existing_attendance[day] = attendance

    for date in dates:

        attendance = existing_attendance.get(date)

        if attendance:
            if attendance.docstatus == 2:
                frappe.delete_doc("Attendance", attendance.name, force=1)
            else:
                continue

        # frappe.msgprint(f"Date {date} ----- {sandwich_dates} <br> is Date in Sandwich Dates: {str(date) in sandwich_dates}")
        is_sandwich_date = date in sandwich_dates

        if is_sandwich_date:
            # frappe.msgprint(f"Creating attendance record for sandwich date as Leave Without Pay: {date}")
            leave_type = "Leave Without Pay"
            leave_application = None
        else:
            leave_type = doc.leave_type
            leave_application = doc.name

        attendance_doc = frappe.new_doc("Attendance")
        attendance_doc.update({
            "employee": doc.employee,
            "attendance_date": date,
            "status": "On Leave",
            "leave_type": leave_type,
            "leave_application": leave_application,
        })
        attendance_doc.insert(ignore_permissions=True)
        attendance_doc.submit()

        if is_sandwich_date:
            attendance_doc.db_set({"leave_type": "Leave Without Pay", "leave_application": ''})

        # frappe.msgprint(f"Created attendance record: {attendance_doc.as_dict()}")
####################################################################################################