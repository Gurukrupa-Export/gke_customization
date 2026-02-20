import frappe
from frappe import _
from frappe.utils import get_link_to_form
from datetime import datetime, time, timedelta 
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str, getdate, get_time,add_days, date_diff, getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date, fmt_td_or_value

from datetime import datetime

def validate(self, method):
    if not (self.custom_in_time and self.custom_out_time):
        # Parse time strings if necessary
        in_time = (
            datetime.strptime(self.custom_in_time, "%H:%M:%S").time()
            if isinstance(self.custom_in_time, str)
            else self.custom_in_time
        )
        out_time = (
            datetime.strptime(self.custom_out_time, "%H:%M:%S").time()
            if isinstance(self.custom_out_time, str)
            else self.custom_out_time
        )

        if out_time < in_time:
            frappe.throw(
                _("Out Time ({0}) cannot be earlier than In Time ({1})").format(
                    out_time.strftime("%H:%M:%S"), in_time.strftime("%H:%M:%S")
                )
            )

    request_days = date_diff(self.to_date, self.from_date) + 1
    
    for day in range(request_days):
        checkin_date = getdate(add_days(self.from_date, day))

        if self.workflow_state == 'Create Checkin':
            if not self.should_mark_attendance(checkin_date):
                continue

            if self.reason == 'On Duty':
                status = 'Outdoor Duty'
            else:
                status = self.reason

            if self.custom_in_time:
                formatted_time = self.custom_in_time            
                in_datetime_combined = f"{checkin_date} {formatted_time}" # Format as "DD-MM-YYYY HH:MM:SS"

                checkin_doc = frappe.db.sql(f""" SELECT name FROM `tabEmployee Checkin`
                        WHERE employee = '{self.employee}' 
                        AND log_type = 'IN' 
                        AND shift = '{self.shift}'
                        AND DATE(time) = '{checkin_date}';
                            
                """,as_dict=1)
                
                if checkin_doc:
                    checkin_name = checkin_doc[0].get("name")
                    frappe.throw(
                        _("Employee Checkin exists for {0} {1})")
                        .format(self.employee, get_link_to_form("Employee Checkin", checkin_name)
                        )
                    )
                    #   continue
                    # update_checkin = frappe.get_doc("Employee Checkin", checkin_name)

                in_doc = frappe.new_doc("Employee Checkin")
                in_doc.employee = self.employee
                in_doc.skip_auto_attendance = 0
                in_doc.source = status
                in_doc.log_type = 'IN'
                in_doc.time = in_datetime_combined  
                in_doc.custom_attendance_request = self.name  
                in_doc.save()
            
            if self.custom_out_time:
                formatted_time = self.custom_out_time 
                out_datetime_combined = f"{checkin_date} {formatted_time}" # Format as "DD-MM-YYYY HH:MM:SS"
                
                # checkin_doc = frappe.db.sql(f""" SELECT name FROM `tabEmployee Checkin`
                #         WHERE employee = '{self.employee}' 
                #         AND log_type = 'OUT' 
                #         AND shift = '{self.shift}'
                #         AND DATE(time) = '{checkin_date}';
                            
                # """,as_dict=1)                

                # if checkin_doc:
                #     continue
                    # checkin_name = checkin_doc[0].get("name")
                    # update_checkin = frappe.get_doc("Employee Checkin", checkin_name)

                out_doc = frappe.new_doc("Employee Checkin")
                out_doc.employee = self.employee
                out_doc.skip_auto_attendance = 0
                out_doc.log_type = 'OUT'
                out_doc.source = status
                out_doc.time = out_datetime_combined  
                out_doc.custom_attendance_request = self.name  
                out_doc.save()
        
            frappe.msgprint(_("Employee Checkin created"))
         
def on_submit(self, method):
    request_days = date_diff(self.to_date, self.from_date) + 1
    attendance_results = []

    for day in range(request_days):
        attendance_date = add_days(self.from_date, day)
        attendance_name = get_attendance_record(self, attendance_date)

        if attendance_name:
            doc = frappe.get_doc("Attendance", attendance_name)
            filters = {
                "skip_auto_attendance": 0,
                "attendance": ("is", "not set"),
                "custom_attendance_request": self.name,
                "shift": self.shift,
                "employee": self.employee
            }

            logs = frappe.db.get_list(
                "Employee Checkin", fields=["*"], filters=filters, order_by="time"
            )
            
            # Filter logs for the current `attendance_date`
            log_entries = [log for log in logs if log["time"].date() == attendance_date]

            if log_entries:
                attendance_data = get_attendance(self, log_entries)
                attendance_data["attendance_date"] = str(attendance_date)
    #             attendance_results.append(attendance_data)

                doc.db_set({
                    "status": attendance_data["status"],
                    "working_hours": attendance_data["working_hours"],
                    "in_time": attendance_data["in_time"],
                    "out_time": attendance_data["out_time"],  
                    "attendance_request": self.name,
                    "shift": self.shift,
                    "early_exit": attendance_data["early_exit"],
                    "late_entry": attendance_data["late_entry"]
                })

                for log in log_entries:
                    frappe.db.set_value("Employee Checkin", log.name, "attendance", doc.name)     

    frappe.db.commit()
    # Update Monthly in-out Log after attendance is processed
    att_req_update_monthly_inout_log(self)


def get_attendance(self, logs):
    """Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time for a single date."""

    shift_doc = frappe.get_doc("Shift Type", self.shift)

    late_entry = early_exit = False
    total_working_hours, in_time, out_time = calculate_working_hours(
        logs, shift_doc.determine_check_in_and_check_out, shift_doc.working_hours_calculation_based_on
    )

    shift_start = logs[0]["shift_start"]
    shift_end = logs[0]["shift_end"]

    if (
        cint(shift_doc.enable_late_entry_marking)
        and in_time
        and in_time > shift_start + timedelta(minutes=cint(shift_doc.late_entry_grace_period))
    ):
        late_entry = True

    if (
        cint(shift_doc.enable_early_exit_marking)
        and out_time
        and out_time < shift_end - timedelta(minutes=cint(shift_doc.early_exit_grace_period))
    ):
        early_exit = True

    # Determine attendance status based on source (reason)
    source = logs[0].get("source", "")

    if source == "Work From Home":
        status = "Work From Home"
    elif source in ("Outdoor Duty","Manual Punch"):
        status = "Present"
    # frappe.throw(f"{status}")

    return {
        "status": status,
        "working_hours": total_working_hours,
        "late_entry": late_entry,
        "early_exit": early_exit,
        "in_time": in_time,
        "out_time": out_time
    }

def get_attendance_record(self, attendance_date: str) -> str | None:
    frappe.msgprint(_("Attendance Checking.."))
    attedance =  frappe.db.exists(
        "Attendance",
        {
            "employee": self.employee,
            "attendance_date": attendance_date,
            "docstatus": ("!=", 2),
        },
    )
    return attedance


######################### Update Monthly in-out Log after Submit Attendance Req #################################
##### 19 Feb 2026 ####


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