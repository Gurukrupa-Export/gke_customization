import frappe
from frappe.utils import add_days, date_diff

def on_submit(self, method):
    request_days = date_diff(self.to_date, self.from_date) + 1
    for day in range(request_days):
        attendance_date = add_days(self.from_date, day)
        attendance_name = self.get_attendance_record(attendance_date)
        if attendance_name:
            doc = frappe.get_doc("Attendance", attendance_name)
            doc.db_set({'in_time': self.custom_in_time, 'out_time': self.custom_out_time,  "attendance_request": self.name})
            
def get_attendance_record(self, attendance_date: None):
    return frappe.db.exists(
        "Attendance",
        {
            "employee": self.employee,
            "attendance_date": attendance_date,
            "docstatus": ("!=", 2),
        },
    )