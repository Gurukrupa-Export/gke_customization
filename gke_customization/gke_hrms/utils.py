from datetime import date, timedelta

import frappe
from frappe.utils import add_days, get_first_day, getdate, today

from gke_customization.gke_hrms.report.pf_challan_report.pf_challan_report import (
    get_account_total_summary,
)

SANDWICH_RULE_LOOKBACK_DAYS = 15


def _log_exc(title):
    """Log the exception being handled to the Error Log with the given title."""
    frappe.log_error(title=title[:140], message=frappe.get_traceback())


@frappe.whitelist()
def get_account_total_summary_for_print(company, from_date, to_date):
    filters = {"company": company, "from_date": from_date, "to_date": to_date}
    return get_account_total_summary(filters)


# 21-01-2026 by Aditya
@frappe.whitelist()
def check_sadwitch_rule():
    manual, formatted_from_date, formatted_to_date = frappe.db.get_value(
        "Biometric Settings", "Biometric Settings", ["manual", "from_date", "to_date"]
    )

    manual = int(manual)

    # --------------------------------------------------
    # Date range calculation
    # --------------------------------------------------
    if not manual:
        today = date.today()
        formatted_to_date = today
        formatted_from_date = today - timedelta(days=SANDWICH_RULE_LOOKBACK_DAYS)

    # --------------------------------------------------
    # Fetch Absent + On Leave attendances
    # --------------------------------------------------
    absent_attendances = frappe.get_all(
        "Attendance",
        filters={
            "status": ["in", ["Absent", "On Leave"]],
            "docstatus": 1,
            "attendance_date": ["between", [formatted_from_date, formatted_to_date]],
        },
        fields=["name", "employee", "attendance_date"],
    )

    # Group by employee
    employee_attendance_map = {}
    for attendance in absent_attendances:
        employee_attendance_map.setdefault(attendance["employee"], []).append(
            attendance
        )

    holidays_to_insert = []

    # --------------------------------------------------
    # Employee-wise sandwich evaluation
    # --------------------------------------------------
    employee_data_map = {
        emp.name: emp
        for emp in frappe.get_all(
            "Employee",
            filters={"name": ["in", list(employee_attendance_map.keys())]},
            fields=["name", "holiday_list", "status"],
        )
    }

    # Holidays per list are shared across employees, fetch each list once
    holiday_cache = {}
    holiday_lists = {
        emp.holiday_list
        for emp in employee_data_map.values()
        if emp.holiday_list and emp.status == "Active"
    }
    if holiday_lists:
        all_holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": ["in", list(holiday_lists)],
                "holiday_date": ["between", [formatted_from_date, formatted_to_date]],
            },
            fields=["parent", "holiday_date", "weekly_off"],
            order_by="holiday_date asc",
        )
        for h in all_holidays:
            entry = holiday_cache.setdefault(
                h.parent, {"holidays": set(), "weekoffs": set()}
            )
            if h.weekly_off:
                entry["weekoffs"].add(getdate(h.holiday_date))
            else:
                entry["holidays"].add(getdate(h.holiday_date))

    for employee, attendances in employee_attendance_map.items():
        employee_data = employee_data_map.get(employee)

        if not employee_data:
            continue

        if not employee_data.holiday_list or employee_data.status != "Active":
            continue

        list_entry = holiday_cache.get(employee_data.holiday_list, {})

        holiday_dates = set(list_entry.get("holidays") or ())
        weekoff_dates = set(list_entry.get("weekoffs") or ())

        attendance_dates = {getdate(a["attendance_date"]) for a in attendances}

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
                all_lop_dates = prev_chain_days | {holiday} | next_chain_days

                for day in sorted(all_lop_dates):
                    if day not in weekoff_dates:
                        holidays_to_insert.append({"employee": employee, "date": day})

    # --------------------------------------------------
    # Insert Attendance (LWP)
    # --------------------------------------------------
    if not holidays_to_insert:
        return

    candidate_employees = list({entry["employee"] for entry in holidays_to_insert})
    candidate_dates = [entry["date"] for entry in holidays_to_insert]

    existing_attendance = {
        (row.employee, getdate(row.attendance_date))
        for row in frappe.get_all(
            "Attendance",
            filters={
                "employee": ["in", candidate_employees],
                "attendance_date": [
                    "between",
                    [min(candidate_dates), max(candidate_dates)],
                ],
                "docstatus": ["!=", 2],
            },
            fields=["employee", "attendance_date"],
        )
    }

    employee_company_map = dict(
        frappe.get_all(
            "Employee",
            filters={"name": ["in", candidate_employees]},
            fields=["name", "company"],
            as_list=True,
        )
    )

    for entry in holidays_to_insert:
        employee = entry["employee"]
        holiday_date = entry["date"]

        if (employee, holiday_date) in existing_attendance:
            continue

        frappe.db.savepoint("sandwich_rule_attendance")
        try:
            frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": holiday_date,
                    "status": "On Leave",
                    "leave_type": "Leave Without Pay",
                    "company": employee_company_map.get(employee),
                    "docstatus": 1,
                }
            ).insert()
        except Exception:
            frappe.db.rollback(save_point="sandwich_rule_attendance")
            _log_exc(
                "Sandwich Rule: Attendance failed for {0} on {1}".format(
                    employee, holiday_date
                )
            )
            continue

        frappe.db.release_savepoint("sandwich_rule_attendance")
        existing_attendance.add((employee, holiday_date))

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
            "attendance_date": ["between", [from_date, to_date]],
        },
        fields=["name", "employee", "attendance_date"],
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
        order_by="holiday_date asc",
    )

    holiday_dates = {getdate(h["holiday_date"]) for h in holidays}
    attendance_dates = {getdate(a["attendance_date"]) for a in absent_attendances}

    holidays_to_insert = []

    for holiday in holiday_dates:
        if not (from_date <= holiday <= to_date):
            continue

        holiday_doc = next(
            (h for h in holidays if getdate(h["holiday_date"]) == holiday), None
        )
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
                "docstatus": ["!=", 2],
            },
            fields=["name"],
        )

        if not existing:
            new_doc = frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": employee_id,
                    "attendance_date": att_date,
                    "status": "On Leave",
                    "leave_type": "Leave Without Pay",
                    "company": frappe.db.get_value("Employee", employee_id, "company"),
                    "docstatus": 1,
                }
            )
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
            "status": "Active",
        },
        "shift_type",
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
                "status": "Active",
            },
            "shift_type",
        )

    if shift:
        return shift

    # Fallback to default shift
    return frappe.db.get_value("Employee", employee, "default_shift")


def get_employees_by_shift(shift_type: str, date: date | None = None) -> list[str]:
    """
    Returns a list of Employees assigned to a given Shift Type.

    Logic Rules:
    1. Check Shift Assignment:
       - Must match: shift_type
       - start_date <= today
       - end_date is null OR end_date >= today
       - status == "Active"
       - docstatus == 1 (Submitted)
    2. Fallback to Employee:
       - Only if no active Shift Assignment exists for the employee today.
       - Must match: Employee.default_shift == shift_type
       - Employee.status == "Active"
    """
    if not shift_type:
        return []

    current_date = date or today()

    # 1. Find all active shift assignments for today
    # We include 'creation' and 'start_date' to handle deduplication later
    active_assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "status": "Active",
            "start_date": ["<=", current_date],
            "docstatus": 1,
        },
        or_filters=[["end_date", ">=", current_date], ["end_date", "is", "not set"]],
        fields=["employee", "shift_type", "start_date", "creation"],
        order_by="start_date desc, creation desc",
    )

    # Map to identify the PRIMARY active assignment for each employee
    # Since it's sorted by start_date desc, creation desc, the first one seen per employee is the latest.
    primary_assigned_shift_map = {}
    for d in active_assignments:
        if d.employee not in primary_assigned_shift_map:
            primary_assigned_shift_map[d.employee] = d.shift_type

    # Employees whose primary assignment matches the requested shift_type
    employees_matching_assignment = [
        emp
        for emp, s_type in primary_assigned_shift_map.items()
        if s_type == shift_type
    ]

    # 2. Fallback: Find employees with matching default_shift who have NO active assignment today
    employees_with_any_assignment = list(primary_assigned_shift_map.keys())

    fallback_employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "default_shift": shift_type,
            "name": ["not in", employees_with_any_assignment]
            if employees_with_any_assignment
            else ["!=", ""],
        },
        pluck="name",
    )

    # Final check: Ensure employees matching via assignment are also Active
    # (Though assignments usually imply active status, this is safer)
    active_matching_assignment = []
    if employees_matching_assignment:
        active_matching_assignment = frappe.get_all(
            "Employee",
            filters={"status": "Active", "name": ["in", employees_matching_assignment]},
            pluck="name",
        )

    # Combine results and remove duplicates
    result = list(set(active_matching_assignment + fallback_employees))

    return result
