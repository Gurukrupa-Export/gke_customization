from frappe.utils import getdate, nowdate, add_days , today
from frappe import _
import frappe
from datetime import timedelta , datetime 


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

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date, fmt_td_or_value

def leave_application_update_monthly_inout_log(doc, method=None):
    """
    Recalculate Monthly In-Out Log when Leave Application is submitted
    """
    try:
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
            fields=["name"],
        )
        
        if not attendance_list:
            return
            
        for att in attendance_list:
            att_doc = frappe.db.get_value("Attendance", att.name, ["attendance_date", "name", "status"], as_dict=True)
            attendance_date = att_doc.attendance_date

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
                return

            mil = frappe.db.get_value("Monthly In-Out Log", mil_name, ["company", "employee"], as_dict=True)

            res = get_attendance_details_by_date(
                mil.company,
                mil.employee,
                attendance_date
            )

            records = res.get("records") or []
            if not records:
                return

            record = records[0]

            frappe.db.set_value("Monthly In-Out Log", mil_name, "status", record.get("status"))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "in_time", record.get("in_time"))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "out_time", record.get("out_time"))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "spent_hrs", fmt_td_or_value(record.get("spent_hrs") or record.get("spent_hours")))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "net_wrk_hrs", fmt_td_or_value(record.get("net_wrk_hrs")))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "late", record.get("late", 0) or record.get("late_entry", 0))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "late_hrs", fmt_td_or_value(record.get("late_hrs")))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "early_hrs", fmt_td_or_value(record.get("early_hrs")))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "ot_hrs", fmt_td_or_value(record.get("ot_hours") or record.get("othrs")))
            frappe.db.set_value("Monthly In-Out Log", mil_name, "p_out_hrs", fmt_td_or_value(record.get("p_out_hrs")))

            frappe.db.commit()
    except Exception as e:
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

    sandwich_dates = get_sandwich_dates(doc)
    # if sandwich_dates:
    #     formatted = ", ".join(d.strftime("%d-%m-%Y") for d in sandwich_dates)

    #     frappe.msgprint(
    #         f"<b>Sandwich Rule Applied</b><br>"
    #         f"Following holiday(s) will be counted as Leave:<br>{formatted}"
    #     )

    public_holidays, weekly_offs = get_holiday_dates(doc.employee)

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

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




def get_sandwich_dates(doc):
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
        List of holiday dates to be treated as Leave.
    """

    if doc.leave_type != "Casual Leave":
        return []

    employee = doc.employee

    public_holidays, weekly_offs = get_holiday_dates(employee)
    holiday_dates = sorted(public_holidays)

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    holidays_in_range = [
        d for d in holiday_dates if from_date <= d <= to_date
    ]

    if not holidays_in_range:
        return []

    sandwich_dates = []
    holiday_blocks = get_continuous_blocks(holidays_in_range)

    for block in holiday_blocks:

        block_start = block[0]
        block_end = block[-1]

        left_day = add_days(block_start, -1)
        right_day = add_days(block_end, 1)

        left_status = get_day_status(employee, left_day, doc)
        right_status = get_day_status(employee, right_day, doc)

        if (
            left_status in ["Casual Leave", "Absent"]
            and right_status in ["Casual Leave", "Absent"]
        ):
            sandwich_dates.extend(block)

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

def get_day_status(employee, date, current_doc):
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
     # 1️⃣ Check current leave application (important for future leave)
    if current_doc:
        if (
            current_doc.employee == employee
            and getdate(current_doc.from_date) <= date <= getdate(current_doc.to_date)
        ):
            return current_doc.leave_type

    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": date, "docstatus": 1},
        ["status", "leave_type"],
        as_dict=True
    )

    if attendance and attendance.status == "Absent":
        return "Absent"
    
    if attendance and attendance.status == "On Leave":
        return attendance.leave_type

    return "Present"

def get_holiday_dates(employee):
    """
    Retrieve holiday dates assigned to an employee.

    Returns:
        tuple:
            (public_holidays_set, weekly_off_set)
    """

    holiday_list = frappe.db.get_value(
        "Employee", employee, "holiday_list"
    )

    if not holiday_list:
        return set(), set()

    holidays = frappe.get_all(
        "Holiday",
        filters={"parent": holiday_list},
        fields=["holiday_date", "weekly_off"]
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
    sandwich_dates = [str(d) for d in sandwich_dates]

    for date in dates:
        
        date = getdate(date)

        attendance = frappe.db.get_value(
            "Attendance",
            {"employee": doc.employee, "attendance_date": date},
            ["name", "docstatus"],
            as_dict=True
        )

        if attendance:
            if attendance.docstatus == 2:
                frappe.delete_doc("Attendance", attendance.name, force=1)
            else:
                continue
        
        if str(date) in sandwich_dates:
            attendance_doc = frappe.new_doc("Attendance")
            attendance_doc.update({
                "employee": doc.employee,
                "attendance_date": date,
                "status": "On Leave",
                "leave_type": "Leave Without Pay",
            })
            attendance_doc.insert(ignore_permissions=True)
            attendance_doc.submit()
            attendance_doc.db_set({"leave_type": "Leave Without Pay", "leave_application": ''})

        else:
            attendance_doc = frappe.new_doc("Attendance")
            attendance_doc.update({
                "employee": doc.employee,
                "attendance_date": date,
                "status": "On Leave",
                "leave_type": doc.leave_type,
                "leave_application": doc.name
            })
            attendance_doc.insert(ignore_permissions=True)
            attendance_doc.submit()

####################################################################################################