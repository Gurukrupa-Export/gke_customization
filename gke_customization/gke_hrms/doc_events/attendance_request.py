import frappe
from frappe.utils import add_days, date_diff
from datetime import datetime, time

def on_submit(self, method):
    request_days = date_diff(self.to_date, self.from_date) + 1
    for day in range(request_days):
        attendance_date = add_days(self.from_date, day)
        attendance_name = self.get_attendance_record(attendance_date)
        if attendance_name:
            doc = frappe.get_doc("Attendance", attendance_name)
            if isinstance(attendance_date, str):
                attendance_date = datetime.strptime(attendance_date, "%Y-%m-%d").date()  # Convert to date object

            in_time_obj = datetime.combine(attendance_date, datetime.strptime(self.custom_in_time, "%H:%M:%S").time())
            out_time_obj = datetime.combine(attendance_date, datetime.strptime(self.custom_out_time, "%H:%M:%S").time())
        
            doc.db_set({
                        "in_time": in_time_obj,
                        "out_time": out_time_obj,  
                        "attendance_request": self.name,
                        "shift": self.shift})
            
def get_attendance_record(self, attendance_date: None):
    return frappe.db.exists(
        "Attendance",
        {
            "employee": self.employee,
            "attendance_date": attendance_date,
            "docstatus": ("!=", 2),
        },
    )