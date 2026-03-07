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
        frappe.msgprint(f"Updating Monthly In-Out Log for Leave Application: {doc.name}")
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
            frappe.msgprint(f"No attendance found for Leave Application: {doc.name}")
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
                frappe.msgprint(f"No Monthly In-Out Log found for {attendance_date}")
                return

            mil = frappe.db.get_value("Monthly In-Out Log", mil_name, ["company", "employee"], as_dict=True)

            res = get_attendance_details_by_date(
                mil.company,
                mil.employee,
                attendance_date
            )

            records = res.get("records") or []
            if not records:
                frappe.msgprint(f"No records found for {attendance_date}")
                return

            record = records[0]
            frappe.msgprint(f"Status : {record.get('status')} <br> Attendance status : {att_doc.status}")

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
        frappe.msgprint(f"Error updating Monthly In-Out Log: {e}")
        frappe.log_error(message=f"Error updating Monthly In-Out Log: {e}", title="Monthly In-Out Log Update Error - Leave Application")

###########################################################################################################

              
