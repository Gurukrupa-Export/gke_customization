

import frappe
from frappe.utils import getdate, add_days, get_first_day, today
from datetime import date, timedelta
import calendar
from dateutil import relativedelta

# @frappe.whitelist()
# def check_sadwitch_rule():
#     manual = int(frappe.db.get_value("Biometric Settings","Biometric Settings","manual"))
#     if manual:
#         formatted_from_date = frappe.db.get_value("Biometric Settings","Biometric Settings","from_date")
#         formatted_to_date = frappe.db.get_value("Biometric Settings","Biometric Settings","to_date")
#         # formatted_from_date = frappe.utils.formatdate(from_date, "dd-MM-yyyy")
#         # formatted_to_date = frappe.utils.formatdate(to_date, "dd-MM-yyyy")
#     else:
#         today = date.today() 
#         formatted_to_date = today

#         if today.weekday() == 6:
#             days_since_last_sunday = today.weekday() + 1
#             week_off = timedelta(days=days_since_last_sunday)
#         else:
#             week_off = timedelta(days=today.weekday() + 1)

#         formatted_from_date = today - week_off

#     absent_attendances = frappe.get_all(
#         "Attendance",
#         filters={
#             "status": ["in", ["Absent", "On Leave"]],
#             "docstatus": 1,
#             # "employee": employee_id,
#             "attendance_date": ["between", [formatted_from_date, formatted_to_date]]
#         },
#         fields=["name", "employee", "attendance_date"]
#     )
#     # Group attendance records by employee
#     employee_attendance_map = {}
#     for attendance in absent_attendances:
#         employee_attendance_map.setdefault(attendance['employee'], []).append(attendance)
    
#     holidays_to_insert = [] 

#     for employee, attendances in employee_attendance_map.items():
#         holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
#         if not holiday_list:
#             continue

#         holidays = frappe.get_all(
#             "Holiday",
#             filters={
#                 "parent": holiday_list,
#                 "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
#                 "weekly_off": 0
#             },
#             fields=["holiday_date"],
#             order_by = "holiday_date asc"
#         )

#         weekoff_holidays = frappe.get_all(
#             "Holiday",
#             filters={
#                 "parent": holiday_list,
#                 "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
#                 "weekly_off": 1
#             },
#             fields=["holiday_date"],
#             order_by = "holiday_date asc"
#         )

#         holiday_dates = {getdate(holiday["holiday_date"]) for holiday in holidays}
#         weekoff_dates = {getdate(holiday["holiday_date"]) for holiday in weekoff_holidays}
#         # sandwich_dates = attendance_dates | holiday_dates | weekoff_dates

#         # Sort attendance records by date
#         attendances.sort(key=lambda x: getdate(x['attendance_date']))
#         attendance_dates = {getdate(a['attendance_date']) for a in attendances} 

#         # Check each holiday if it is sandwiched between absents
#         for holiday in holiday_dates:
#             prev_day = add_days(holiday, -1)
#             next_day = add_days(holiday, 1)

#             prev_absent_days = set()
#             next_absent_days = set()

#             # Check previous consecutive absent days / holidays / weekoffs
#             while prev_day in attendance_dates or prev_day in holiday_dates or prev_day in weekoff_dates:
#                 prev_absent_days.add(prev_day)
#                 prev_day = add_days(prev_day, -1)

#             # Check next consecutive absent days / holidays / weekoffs
#             while next_day in attendance_dates or next_day in holiday_dates or next_day in weekoff_dates:
#                 next_absent_days.add(next_day)
#                 next_day = add_days(next_day, 1)
            
#             # Only mark LOP if absent exists on both sides of the holiday
#             if prev_absent_days and next_absent_days:
#                 all_lop_dates = prev_absent_days | {holiday} | next_absent_days
                
#                 # Insert all holidays in the range from prev_absent_days to next_absent_days
#                 # Insert only holidays (not weekoffs) in the LOP list
#                 for day in sorted(all_lop_dates):
#                     if day not in weekoff_dates:   # 🚫 exclude weekoffs
#                         holidays_to_insert.append({"employee": employee, "date": day})        

#     # Insert new attendance records for holidays
#     for holiday_entry in holidays_to_insert:
#         holiday_date = holiday_entry["date"]
#         employee = holiday_entry["employee"]

#         # Check if attendance already exists
#         existing_attendance = frappe.get_all(
#             "Attendance",
#             filters={"employee": employee, "attendance_date": holiday_date,"docstatus":["!=",2]},
#             fields=["name"]
#         )
#         if not existing_attendance:
#             new_attendance = frappe.get_doc({
#                 "doctype": "Attendance",
#                 "employee": employee,
#                 "attendance_date": holiday_date,
#                 "status": "On Leave",
#                 "leave_type": "Leave Without Pay",
#                 "company": frappe.db.get_value("Employee", employee, "company"),
#                 "docstatus": 1
#             })
#             new_attendance.insert(ignore_permissions=True)
            
#     # Commit changes to the database
#     frappe.db.commit()

# 21-01-2026 by Aditya
@frappe.whitelist()
def check_sadwitch_rule():

    manual = int(frappe.db.get_value("Biometric Settings", "Biometric Settings", "manual"))

    # --------------------------------------------------
    # Date range calculation
    # --------------------------------------------------
    if manual:
        formatted_from_date = frappe.db.get_value("Biometric Settings", "Biometric Settings", "from_date")
        formatted_to_date = frappe.db.get_value("Biometric Settings", "Biometric Settings", "to_date")
    else:
        today = date.today()
        # today = getdate('2025-12-28')
        formatted_to_date = today

        if today.weekday() == 6:  # Sunday
            days_since_last_sunday = today.weekday() + 1
            week_off = timedelta(days=days_since_last_sunday)
        else:
            week_off = timedelta(days=today.weekday() + 1)

        formatted_from_date = today - week_off

    # --------------------------------------------------
    # Fetch Absent + On Leave attendances
    # --------------------------------------------------
    absent_attendances = frappe.get_all(
        "Attendance",
        filters={
            "status": ["in", ["Absent", "On Leave"]],
            "docstatus": 1,
            "attendance_date": ["between", [formatted_from_date, formatted_to_date]]
        },
        fields=["name", "employee", "attendance_date"]
    )

    # Group by employee
    employee_attendance_map = {}
    for attendance in absent_attendances:
        employee_attendance_map.setdefault(
            attendance["employee"], []
        ).append(attendance)

    holidays_to_insert = []

    # --------------------------------------------------
    # Employee-wise sandwich evaluation
    # --------------------------------------------------
    for employee, attendances in employee_attendance_map.items():

        employee_data = frappe.db.get_value("Employee", employee, ["holiday_list", "status"], as_dict=True)
        
        if not employee_data:
            continue

        if not employee_data.holiday_list or employee_data.status != "Active":
            continue

        # Paid Holidays
        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": employee_data.holiday_list,
                "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
                "weekly_off": 0
            },
            fields=["holiday_date"],
            order_by="holiday_date asc"
        )

        # Weekoffs
        weekoff_holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": employee_data.holiday_list,
                "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
                "weekly_off": 1
            },
            fields=["holiday_date"],
            order_by="holiday_date asc"
        )

        holiday_dates = {
            getdate(h["holiday_date"]) for h in holidays
        }
        weekoff_dates = {
            getdate(h["holiday_date"]) for h in weekoff_holidays
        }

        attendance_dates = {
            getdate(a["attendance_date"]) for a in attendances
        }

        # --------------------------------------------------
        # Sandwich logic per holiday
        # --------------------------------------------------
        for holiday in holiday_dates:

            prev_day = add_days(holiday, -1)
            next_day = add_days(holiday, 1)

            prev_chain_days = set()
            next_chain_days = set()

            prev_real_absent = set()
            next_real_absent = set()

            # ---------- Previous side ----------
            while (
                prev_day in attendance_dates
                or prev_day in holiday_dates
                or prev_day in weekoff_dates
            ):
                prev_chain_days.add(prev_day)

                if prev_day in attendance_dates:
                    prev_real_absent.add(prev_day)

                prev_day = add_days(prev_day, -1)

            # ---------- Next side ----------
            while (
                next_day in attendance_dates
                or next_day in holiday_dates
                or next_day in weekoff_dates
            ):
                next_chain_days.add(next_day)

                if next_day in attendance_dates:
                    next_real_absent.add(next_day)

                next_day = add_days(next_day, 1)

            # --------------------------------------------------
            # STRICT sandwich condition
            # --------------------------------------------------
            if prev_real_absent and next_real_absent:

                all_lop_dates = (
                    prev_chain_days | {holiday} | next_chain_days
                )

                for day in sorted(all_lop_dates):
                    if day not in weekoff_dates:
                        holidays_to_insert.append({
                            "employee": employee,
                            "date": day
                        })

    # --------------------------------------------------
    # Insert Attendance (LWP)
    # --------------------------------------------------
    for entry in holidays_to_insert:

        employee = entry["employee"]
        holiday_date = entry["date"]

        existing = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee,
                "attendance_date": holiday_date,
                "docstatus": ["!=", 2]
            },
            fields=["name"]
        )

        if not existing:
            frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": holiday_date,
                "status": "On Leave",
                "leave_type": "Leave Without Pay",
                "company": frappe.db.get_value(
                    "Employee", employee, "company"
                ),
                "docstatus": 1
            }).insert(ignore_permissions=True)

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

@frappe.whitelist()
def get_employee_shift(employee, for_date=None):
    if not for_date:
        for_date = today()

    for_date = getdate(for_date)

    # Shift Assignment takes priority
    shift = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "start_date": ("<=", for_date),
            "end_date": ("is", "not set"),
            "status": "Active"
        },
        "shift_type"
    )

    if not shift:
        # Try with end_date is set
        shift = frappe.db.get_value(
            "Shift Assignment",
            {
                "employee": employee,
                "docstatus": 1,
                "start_date": ("<=", for_date),
                "end_date": ("is", "set"),
                "status": "Active"
            },
            "shift_type"
        )

    if shift:
        return shift

    # Fallback to default shift
    return frappe.db.get_value(
        "Employee",
        employee,
        "default_shift"
    )