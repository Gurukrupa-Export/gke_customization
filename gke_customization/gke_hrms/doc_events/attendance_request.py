import frappe
from frappe import _
from frappe.utils import get_link_to_form
from datetime import datetime, time, timedelta 
from frappe.utils import (
    today, get_time, add_to_date, get_datetime, time_diff_in_seconds, 
    cint, getdate,add_days, date_diff, getdate)
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from datetime import datetime


def validate(self, method):
    validate_attendance_request(self, method)

    shift_doc = frappe.get_doc("Shift Type", self.shift)
    shift_start = shift_doc.start_time
    shift_end = shift_doc.end_time
    is_night_shift = shift_end <= shift_start # Night shift detection

    # ----------------------------
    # Validate In / Out Time Order
    # ----------------------------
    if self.custom_in_time and self.custom_out_time:

        in_time = get_time(self.custom_in_time)
        out_time = get_time(self.custom_out_time)

        if not is_night_shift and out_time <= in_time:
            frappe.throw(_(f"Out Time ({out_time}) cannot be earlier than or equal to In Time ({in_time})"))

    # ----------------------------
    # Process Checkin Creation
    # ----------------------------
    if self.workflow_state != "Create Checkin":
        return

    request_days = date_diff(self.to_date, self.from_date) + 1
    status = "Outdoor Duty" if self.reason == "On Duty" else self.reason

    for day in range(request_days):
        checkin_date = getdate(add_days(self.from_date, day))

        if not self.should_mark_attendance(checkin_date):
            continue

        # Create IN and OUT logs
        create_employee_checkin(self, checkin_date, "IN", self.custom_in_time, status)

        if is_night_shift:
            checkin_date = add_days(checkin_date, 1)

        create_employee_checkin(self, checkin_date, "OUT", self.custom_out_time, status)

    frappe.msgprint(_("Employee Checkin(s) created successfully"))


def create_employee_checkin(doc, checkin_date, log_type, time_value, status):
    if not time_value:
        return

    # Combine date & time safely
    combined_datetime = get_datetime(f"{checkin_date} {time_value}")

    # Check duplicate using frappe.db.exists (safe)
    exists = frappe.db.exists(
        "Employee Checkin",
        {
            "employee": doc.employee,
            "log_type": log_type,
            "shift": doc.shift,
            "time": combined_datetime,
        },
    )

    if exists:
        frappe.throw(
            _("Employee Checkin already exists for {0} ({1})")
            .format(
                doc.employee,
                frappe.utils.get_link_to_form("Employee Checkin", exists),
            )
        )

    # Create new checkin
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = doc.employee
    checkin.shift = doc.shift
    checkin.log_type = log_type
    checkin.source = status
    checkin.time = combined_datetime
    checkin.skip_auto_attendance = 0
    checkin.custom_attendance_request = doc.name
    checkin.insert(ignore_permissions=True)



def on_submit(self, method):
    request_days = date_diff(self.to_date, self.from_date) + 1
    # frappe.throw(f"Request Days : {request_days}")

    for day in range(request_days):
        attendance_date = add_days(self.from_date, day)
        attendance_name = get_attendance_record(self, attendance_date)

        if not attendance_name:
            continue

        attendance_doc = frappe.get_doc("Attendance", attendance_name)
        frappe.msgprint(f"Attendance Doc: {attendance_doc.name}")

        # Get proper shift window (handles OT + night shift)
        shift_start, shift_end = get_shift_window(self, attendance_date)

        logs = frappe.db.get_all(
            "Employee Checkin",
            fields=["name", "time", "log_type", "source"],
            filters={
                "employee": self.employee,
                # "shift": self.shift,
                "skip_auto_attendance": 0,
                "custom_attendance_request": self.name,
                # "time": ["between", [shift_start, shift_end]],
            },
            order_by="time asc"
        )

        if not logs:
            frappe.msgprint(f"No logs found for {attendance_date}")
            continue

        attendance_data = get_attendance(self, logs, attendance_date)
        frappe.msgprint(f"Attndance Data : {attendance_data}")

        attendance_doc.db_set({
            "status": attendance_data["status"],
            "working_hours": attendance_data["working_hours"],
            "in_time": attendance_data["in_time"],
            "out_time": attendance_data["out_time"],
            "attendance_request": self.name,
            "shift": self.shift,
            "early_exit": attendance_data["early_exit"],
            "late_entry": attendance_data["late_entry"]
        })

        attendance_doc.reload()
        frappe.msgprint(f"Updated Attendance: {attendance_doc.as_dict()}")

        # Link all logs to this attendance
        for log in logs:
            frappe.db.set_value("Employee Checkin", log["name"], "attendance", attendance_doc.name)

    frappe.db.commit()
    att_req_update_monthly_inout_log(self)


# def get_attendance(self, logs):
#     """Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time for a single date."""

#     shift_doc = frappe.get_doc("Shift Type", self.shift)

#     late_entry = early_exit = False
#     total_working_hours, in_time, out_time = calculate_working_hours(
#         logs, shift_doc.determine_check_in_and_check_out, shift_doc.working_hours_calculation_based_on
#     )

#     shift_start = logs[0]["shift_start"]
#     shift_end = logs[0]["shift_end"]

#     if (
#         cint(shift_doc.enable_late_entry_marking)
#         and in_time
#         and in_time > shift_start + timedelta(minutes=cint(shift_doc.late_entry_grace_period))
#     ):
#         late_entry = True

#     if (
#         cint(shift_doc.enable_early_exit_marking)
#         and out_time
#         and out_time < shift_end - timedelta(minutes=cint(shift_doc.early_exit_grace_period))
#     ):
#         early_exit = True

#     # Determine attendance status based on source (reason)
#     source = logs[0].get("source", "")

#     if source == "Work From Home":
#         status = "Work From Home"
#     elif source in ("Outdoor Duty","Manual Punch"):
#         status = "Present"
#     # frappe.throw(f"{status}")

#     return {
#         "status": status,
#         "working_hours": total_working_hours,
#         "late_entry": late_entry,
#         "early_exit": early_exit,
#         "in_time": in_time,
#         "out_time": out_time
#     }

def get_attendance_record(self, attendance_date: str) -> str | None:
    attedance =  frappe.db.exists(
        "Attendance",
        {
            "employee": self.employee,
            "attendance_date": attendance_date,
            "docstatus": ("!=", 2),
        },
    )
    frappe.msgprint(f"Attendance Record: {attedance or 'Not Found'}")
    return attedance


def get_attendance(self, logs, attendance_date):
    """
    Calculate attendance based on:
    - First IN
    - Last OUT
    - Shift Type settings
    - Late entry / Early exit rules
    """

    shift_doc = frappe.get_doc("Shift Type", self.shift)

    total_working_hours, first_in_time, last_out_time = calculate_working_hours(
        logs, shift_doc.determine_check_in_and_check_out, shift_doc.working_hours_calculation_based_on
    )

    # --------------------------------------------------
    # Late Entry & Early Exit (Using Your Exact Logic)
    # --------------------------------------------------

    shift_start = get_datetime(f"{attendance_date} {shift_doc.start_time}")
    shift_end = get_datetime(f"{attendance_date} {shift_doc.end_time}")

    # Handle night shift
    if shift_end <= shift_start:
        shift_end = add_days(shift_end, 1)

    late_entry = False
    early_exit = False

    if (
        cint(shift_doc.enable_late_entry_marking)
        and first_in_time
        and first_in_time > shift_start + timedelta(
            minutes=cint(shift_doc.late_entry_grace_period)
        )
    ):
        late_entry = True

    if (
        cint(shift_doc.enable_early_exit_marking)
        and last_out_time
        and last_out_time < shift_end - timedelta(
            minutes=cint(shift_doc.early_exit_grace_period)
        )
    ):
        early_exit = True

    # --------------------------------------------------
    # Determine Status
    # --------------------------------------------------

    source = logs[0].get("source", "")

    if source == "Work From Home":
        status = "Work From Home"
    else:
        status = "Present"

    return {
        "status": status,
        "working_hours": total_working_hours,
        "late_entry": late_entry,
        "early_exit": early_exit,
        "in_time": first_in_time,
        "out_time": last_out_time
    }


def get_shift_window(self, attendance_date):
    shift_doc = frappe.get_doc("Shift Type", self.shift)

    shift_start = get_datetime(f"{attendance_date} {shift_doc.start_time}")
    shift_end = get_datetime(f"{attendance_date} {shift_doc.end_time}")

    # Handle night shift
    if shift_end <= shift_start:
        shift_end = add_days(shift_end, 1)

    # Apply official shift settings
    shift_start -= timedelta(
        minutes=shift_doc.begin_check_in_before_shift_start_time or 0
    )

    shift_end += timedelta(
        minutes=shift_doc.allow_check_out_after_shift_end_time or 0
    )

    return shift_start, shift_end


######## Edited by Aditya at 27/01/2026 #################


def validate_attendance_request(doc, method):
    if not doc.employee:
        return

    employee = frappe.get_doc("Employee", doc.employee)

    shift_type = doc.shift or employee.default_shift
    if not shift_type:
        return

    shift = frappe.get_doc("Shift Type", shift_type)

    if not shift.start_time or not shift.end_time:
        return

    base_date = today()

    shift_start = get_time(shift.start_time)
    shift_end = get_time(shift.end_time)

    is_night_shift = shift_start > shift_end

    shift_start_dt = get_datetime(f"{base_date} {shift_start}")
    shift_end_dt = get_datetime(f"{base_date} {shift_end}")

    in_time = get_time(doc.custom_in_time) if doc.custom_in_time else None
    out_time = get_time(doc.custom_out_time) if doc.custom_out_time else None

    # Early check-in window (minutes before shift start)
    early_entry_minutes = shift.begin_check_in_before_shift_start_time or 0
    

    allowed_in_start_dt = add_to_date(
        shift_start_dt,
        minutes=-early_entry_minutes,
        as_datetime=True
    )

    allowed_in_end_dt = shift_end_dt  if not is_night_shift else shift_end_dt + timedelta(days=1)  # strictly shift end

    # Grace period for checkout (30 mins after shift end)
    out_grace_minutes = 30
    
    allowed_out_start_dt = shift_start_dt 
    # allowed_out_end_dt = add_to_date(
    #     shift_end_dt,
    #     minutes=out_grace_minutes,
    #     as_datetime=True
    # )
    allowed_out_end_dt = shift_end_dt if not is_night_shift else shift_end_dt + timedelta(days=1) 


    # --------------------
    # IN TIME VALIDATION
    # --------------------
    if in_time:
        in_time_dt = get_datetime(f"{base_date} {in_time}")

        # frappe.throw(f"In Time DT: {in_time_dt} , Allowed In Start DT: {allowed_in_start_dt} , Allowed In End DT: {allowed_in_end_dt} <br><br> in_time_dt < allowed_in_start_dt : {in_time_dt < allowed_in_start_dt} <br> in_time_dt > allowed_in_end_dt : {in_time_dt > allowed_in_end_dt}")
        if in_time_dt < allowed_in_start_dt or in_time_dt > allowed_in_end_dt:
            frappe.throw(
                f"Check-in time must be between "
                f"{allowed_in_start_dt.time()} and {allowed_in_end_dt.time()}."
            )

    # --------------------
    # OUT TIME VALIDATION
    # --------------------
    if out_time:
        out_time_dt = get_datetime(f"{base_date} {out_time}") if not is_night_shift else get_datetime(f"{base_date} {out_time}") + timedelta(days=1)

        # frappe.throw(f"Out Time DT: {out_time_dt} , Allowed Out Start DT: {allowed_out_start_dt} , Allowed Out End DT: {allowed_out_end_dt} <br><br> out_time_dt < allowed_out_start_dt : {out_time_dt < allowed_out_start_dt} <br> out_time_dt > allowed_out_end_dt : {out_time_dt > allowed_out_end_dt}")
        if out_time_dt < allowed_out_start_dt or out_time_dt > allowed_out_end_dt:
            frappe.throw(
                f"Check-out time must be between "
                f"{allowed_out_start_dt.time()} and {allowed_out_end_dt.time()}."
            )

    # --------------------
    # IN < OUT VALIDATION
    # --------------------
    if in_time and out_time:
        in_time_dt = get_datetime(f"{base_date} {in_time}")
        out_time_dt = get_datetime(f"{base_date} {out_time}") if not is_night_shift else get_datetime(f"{base_date} {out_time}") + timedelta(days=1)

        if time_diff_in_seconds(out_time_dt, in_time_dt) <= 0:
            frappe.throw("Check-out time must be after check-in time.")

###### End of Edited by Aditya at 27/01/2026 #################

######################### Update Monthly in-out Log after Submit Attendance Req #################################
##### 19 Feb 2026 ####

from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date, fmt_td_or_value

def att_req_update_monthly_inout_log(doc, method=None):
    """
    Recalculate Monthly In-Out Log when Attendance Request is submitted
    """
    try:
        if not doc.employee or not doc.company:
            return

        # Get attendance of Attendance Request
        attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "employee": doc.employee,
                "attendance_request": doc.name,
                "docstatus": 1, 
            },
            fields=["name"],
        )
        
        if not attendance_list:
            return
            
        for att in attendance_list:
            att_doc = frappe.db.get_value("Attendance", att.name, ["attendance_date", "name"], as_dict=True)
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
        frappe.log_error(message=f"Error updating Monthly In-Out Log: {e}", title="Monthly In-Out Log Update Error - Att Req")

##############################################################################################