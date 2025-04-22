

import frappe
from frappe.utils import getdate, add_days, get_first_day
from datetime import date, timedelta
import calendar
from dateutil import relativedelta

@frappe.whitelist()
def check_sadwitch_rule():
    manual = int(frappe.db.get_value("Biometric Settings","Biometric Settings","manual"))
    if manual:
        formatted_from_date = frappe.db.get_value("Biometric Settings","Biometric Settings","from_date")
        formatted_to_date = frappe.db.get_value("Biometric Settings","Biometric Settings","to_date")
        # formatted_from_date = frappe.utils.formatdate(from_date, "dd-MM-yyyy")
        # formatted_to_date = frappe.utils.formatdate(to_date, "dd-MM-yyyy")
    else:
        today = date.today() 
        formatted_to_date = today

        if today.weekday() == 6:
            days_since_last_sunday = today.weekday() + 1
            week_off = timedelta(days=days_since_last_sunday)
        else:
            week_off = timedelta(days=today.weekday() + 1)

        formatted_from_date = today - week_off

    absent_attendances = frappe.get_all(
        "Attendance",
        filters={
            "status": ["in", ["Absent", "On Leave"]],
            "docstatus": 1,
            # "employee": employee_id,
            "attendance_date": ["between", [formatted_from_date, formatted_to_date]]
        },
        fields=["name", "employee", "attendance_date"]
    )

    # Group attendance records by employee
    employee_attendance_map = {}
    for attendance in absent_attendances:
        employee_attendance_map.setdefault(attendance['employee'], []).append(attendance)
    
    holidays_to_insert = [] 

    for employee, attendances in employee_attendance_map.items():
        holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
        if not holiday_list:
            continue

        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list,
                "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
                "weekly_off": 0
            },
            fields=["holiday_date"],
            order_by = "holiday_date asc"
        )

        holiday_dates = {getdate(holiday["holiday_date"]) for holiday in holidays}
        
        # Sort attendance records by date
        attendances.sort(key=lambda x: getdate(x['attendance_date']))
        attendance_dates = {getdate(a['attendance_date']) for a in attendances} 

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
                # if next_day in attendance_dates:
                next_absent_days.add(next_day)
                next_day = add_days(next_day, 1)

            # Only mark LOP if absent exists on both sides of the holiday
            if prev_absent_days and next_absent_days:
                all_lop_dates = prev_absent_days | {holiday} | next_absent_days

                # Insert all holidays in the range from prev_absent_days to next_absent_days
                for day in sorted(all_lop_dates):
                    holidays_to_insert.append({"employee": employee, "date": day})

    # frappe.throw(f"{holidays_to_insert}")            
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
    
    

# prachi
@frappe.whitelist()
def check():
    employee_id = "HR-EMP-00921"

    today = date.today()
    from_date = get_first_day(today)
    to_date = today
    # from_date = getdate('2025-03-01')
    # to_date = getdate('2025-03-31')

    absent_attendances = frappe.get_all(
        "Attendance",
        filters={
            "status": ["in", ["Absent", "On Leave"]],
            "docstatus": 1,
            "employee": employee_id,
            "attendance_date": ["between", [from_date, to_date]]
        },
        fields=["name", "employee", "attendance_date"]
    )

    if not absent_attendances:
        return "No absent or on-leave records found."

    holiday_list = frappe.db.get_value("Employee", employee_id, "holiday_list")
    if not holiday_list:
        return "No holiday list set for employee."

    holidays = frappe.get_all(
        "Holiday",
        filters={"parent": holiday_list},
        fields=["holiday_date", "weekly_off"],
        order_by="holiday_date asc"
    )

    holiday_dates = {getdate(h["holiday_date"]) for h in holidays}
    attendance_dates = {getdate(a["attendance_date"]) for a in absent_attendances}

    holidays_to_insert = []

    for holiday in holiday_dates:
        if not (from_date <= holiday <= to_date):
            continue

        holiday_doc = next((h for h in holidays if getdate(h["holiday_date"]) == holiday), None)
        is_week_off = holiday_doc.get("weekly_off", 0) if holiday_doc else 0

        if is_week_off:
            continue  

        prev_day = add_days(holiday, -1)
        next_day = add_days(holiday, 1)

       
        if prev_day in attendance_dates and next_day in attendance_dates:
            holidays_to_insert.append({"employee": employee_id, "date": holiday})

    for entry in holidays_to_insert:
        att_date = entry["date"]
        existing = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee_id,
                "attendance_date": att_date,
                "docstatus": ["!=", 2]
            },
            fields=["name"]
        )

        if not existing:
            new_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee_id,
                "attendance_date": att_date,
                "status": "On Leave",
                "leave_type": "Leave Without Pay",
                "company": frappe.db.get_value("Employee", employee_id, "company"),
                "docstatus": 1
            })
            new_doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return f"LOP holiday marking done for {employee_id} from {from_date} to {to_date}."

