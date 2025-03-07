import frappe
from frappe.utils import getdate, add_days, nowdate


def check():
    # Fetch all absent or on-leave attendance records
    absent_attendances = frappe.get_all(
        "Attendance",
        filters={"status": ["in", ["Absent", "On Leave"]], "docstatus": 1},
        fields=["name", "employee", "attendance_date"]
    )

    if not absent_attendances:
        return

    # Group attendance records by employee
    employee_attendance_map = {}
    for attendance in absent_attendances:
        employee_attendance_map.setdefault(attendance['employee'], []).append(attendance)

    lop_attendance = []
    holidays_to_insert = []

    for employee, attendances in employee_attendance_map.items():
        holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
        if not holiday_list:
            continue

        holidays = frappe.get_all(
            "Holiday",
            filters={"parent": holiday_list},
            fields=["holiday_date"],
            order_by = "holiday_date asc"
        )

        holiday_dates = {getdate(holiday["holiday_date"]) for holiday in holidays}

        # Sort attendance records by date
        attendances.sort(key=lambda x: getdate(x['attendance_date']))
        attendance_dates = {getdate(attendance['attendance_date']) for attendance in attendances}

        # Check each holiday if it is sandwiched between absents
        for holiday in holiday_dates:
            prev_day = add_days(holiday, -1)
            next_day = add_days(holiday, 1)

            prev_absent_days = set()
            next_absent_days = set()

            # Check previous consecutive absent days
            while prev_day in attendance_dates:
                prev_absent_days.add(prev_day)
                prev_day = add_days(prev_day, -1)

            # Check next consecutive absent days and holiday dates
            while next_day in attendance_dates or next_day in holiday_dates:
                next_absent_days.add(next_day)
                next_day = add_days(next_day, 1)

            # Only mark LOP if absent exists on both sides of the holiday
            if prev_absent_days and next_absent_days:
                all_lop_dates = prev_absent_days | {holiday} | next_absent_days

                # Insert all holidays in the range from prev_absent_days to next_absent_days
                for day in sorted(all_lop_dates):
                    holidays_to_insert.append({"employee": employee, "date": day})
                
                for attendance in attendances:
                    if getdate(attendance['attendance_date']) in all_lop_dates:
                        lop_attendance.append(attendance)

    # Update all identified LOP records
    for att in lop_attendance:
        frappe.db.set_value("Attendance", att["name"], {
            "status": "On Leave",
            "leave_type": "Leave Without Pay"
        })

    # Insert new attendance records for holidays
    for holiday_entry in holidays_to_insert:
        holiday_date = holiday_entry["date"]
        employee = holiday_entry["employee"]

        # Check if attendance already exists
        existing_attendance = frappe.get_all(
            "Attendance",
            filters={"employee": employee, "attendance_date": holiday_date,"docstatus":["!=",2]},
            fields=["name"]
        )

        if not existing_attendance:
            new_attendance = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": holiday_date,
                "status": "On Leave",
                "leave_type": "Leave Without Pay",
                "company": frappe.db.get_value("Employee", employee, "company"),
                "docstatus": 1
            })
            new_attendance.insert(ignore_permissions=True)

    # Commit changes to the database
    frappe.db.commit()
