import frappe
from typing import Union, Optional, List
from frappe.utils import getdate, get_time, get_datetime, add_days
import json
from datetime import date as dt_date

@frappe.whitelist()
def mark_employee_attendance(
	employee_list: Union[List, str],
    status: str,
    date: Union[str, dt_date],
    leave_type: Optional[str] = None,
    company: Optional[str] = None,
    late_entry: Optional[int] = None,
    early_exit: Optional[int] = None,
    shift: Optional[str] = None,
    mark_half_day: Optional[bool] = False,
    half_day_status: Optional[str] = None,
    half_day_employee_list: Optional[Union[List, str]] = None,
) -> None:
    """
    Path : /api/method/gke_customization.gke_hrms.api.attendance_tool.mark_employee_attendance
    """
    if isinstance(employee_list, str):
        employee_list = json.loads(employee_list)

    date = getdate(date)

    if shift and frappe.db.exists("Shift Type", shift):
        shift_doc = frappe.db.get_values("Shift Type", shift, ["start_time", "end_time", "shift_hours"], as_dict=True)
        start_time = get_time(shift_doc[0].start_time)
        end_time = get_time(shift_doc[0].end_time)
        working_hours = shift_doc[0].shift_hours

        is_night_shift = end_time < start_time

        shift_start_datetime = get_datetime(f"{date} {start_time}")
        shift_end_datetime = get_datetime(f"{date} {end_time}")
        
        if is_night_shift:
            shift_end_datetime = add_days(shift_end_datetime, 1)

        

    for employee in employee_list:
        leave_type = None
        if status == "On Leave" and leave_type:
            leave_type = leave_type

        attendance_dict = frappe._dict({
            "employee": employee,
            "attendance_date": getdate(date),
            "status": status,
            "leave_type": leave_type,
            "late_entry": late_entry,
            "early_exit": early_exit,
            "shift": shift,
            "custom_is_employee_attendance_tool": True,
        })

        if shift:
            attendance_dict.update({
                "in_time": shift_start_datetime,
                "out_time": shift_end_datetime,
            })
        if status in ["Present", "Work From Home", "Half Day"]:
            attendance_dict.update({
                "working_hours": working_hours
            })

        attendance = frappe.new_doc("Attendance")
        attendance.update(attendance_dict)
        attendance.insert()
        attendance.submit()

    if mark_half_day:
        if isinstance(half_day_employee_list, str):
            half_day_employee_list = json.loads(half_day_employee_list)
        Attendance = frappe.qb.DocType("Attendance")
        for employee in half_day_employee_list:
            frappe.qb.update(Attendance).where(
                (Attendance.employee == employee) & (Attendance.attendance_date == date)
            ).set(Attendance.half_day_status, half_day_status).set(Attendance.shift, shift).set(
                Attendance.late_entry, late_entry
            ).set(Attendance.early_exit, early_exit).set(Attendance.modify_half_day_status, 0).run()

