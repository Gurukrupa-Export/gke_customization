from frappe.utils import getdate, nowdate, add_days , today
from frappe import _
import frappe
from datetime import timedelta , datetime 


def validate(doc, method):
    """Validation logic to check the sandwich rule and past leave restriction."""
    # check_past_month_restriction(doc)
    check_sandwich_rule(doc)


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
    create_attendance_records(doc)

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





              
