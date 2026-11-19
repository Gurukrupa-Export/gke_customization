import json
import math
from collections import defaultdict
from datetime import timedelta

import frappe
import openpyxl
from frappe.utils import (
    add_days,
    flt,
    get_datetime,
    get_first_day,
    get_last_day,
    getdate,
)
from frappe.utils.file_manager import get_file_path


def set_shift_details(employee, from_date):
    if not from_date:
        return

    matched_shift = None

    # Case 1: Get Shift Assignment
    shift_assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "status": "Active",
        },
        fields=["shift_type", "start_date", "end_date"],
        order_by="start_date desc",
    )

    for shift in shift_assignments:
        # If end_date exists
        if shift.end_date:
            if shift.start_date <= from_date <= shift.end_date:
                matched_shift = shift
                break

        # Open shift assignment
        else:
            if from_date >= shift.start_date:
                matched_shift = shift
                break

    # Apply matched shift
    if matched_shift:
        return apply_shift_time(matched_shift.shift_type)

    # Case 2: fallback to Employee default_shift
    default_shift = frappe.db.get_value("Employee", employee, "default_shift")

    if default_shift:
        return apply_shift_time(default_shift)
    frappe.throw(
        f"No Shift Assignment or Default Shift {default_shift} found {employee} "
    )


@frappe.whitelist()
def check_employee_active_validation_based_on_doj(employees):
    # JS se aane wali JSON string ko list me convert karo
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)

    if not employees:
        return True

    for row in employees:
        # Row can be a dict like {"employee": "EMP-0001"}
        if isinstance(row, dict):
            emp = row.get("employee")

        # or a plain employee ID string like "EMP-0001"
        else:
            emp = row

        if not emp:
            continue

        employee_details = frappe.db.get_value(
            "Employee", emp, ["employee_name", "relieving_date", "status"], as_dict=True
        )

        if not employee_details:
            continue

        if employee_details.relieving_date and employee_details.status == "Active":
            frappe.throw(
                f"""
                Employee <b>{employee_details.employee_name}</b> ({emp})
                has a Relieving Date
                <b>{frappe.format(employee_details.relieving_date)}</b>
                but the employee status is still <b>Active</b>.
                Please mark the employee as <b>Inactive</b> before proceeding.
                """
            )

    return True


def apply_shift_time(shift_type):
    shift = frappe.db.get_value(
        "Shift Type", shift_type, ["start_time", "end_time"], as_dict=True
    )

    if shift:
        start_time = shift.start_time
        end_time = shift.end_time

        total_hours = end_time - start_time

        return {
            "shift": shift_type,
            "in_time": start_time,
            "out_time": end_time,
            "total_hours": total_hours.total_seconds() / 3600,
        }


@frappe.whitelist()
def process_salary_adjustment(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)
    doc.check_permission("read")

    # Attachment field se file path lo
    file_path = doc.records

    if not file_path:
        frappe.throw("Please attach an Excel file")

    file_full_path = get_file_path(file_path)

    if not file_full_path:
        frappe.throw("File not found in request")

    wb = openpyxl.load_workbook(file_full_path)
    sheet = wb.active

    data = []
    headers = [cell.value for cell in sheet[1]]

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_dict = dict(zip(headers, row))
        data.append(row_dict)

    review_data = []

    for row in data:
        employee = row.get("employee")
        actual_salary = flt(row.get("actual_salary"))
        monthly_salary = flt(row.get("monthly_salary"))
        calendar_days = flt(row.get("calendar_days"))

        shift_hours = set_shift_details(employee, doc.from_date)

        shift_hours = float(shift_hours.get("total_hours", 0))

        # Actual salary = 26000 ,, month salay = 18000 ,, calander_days = 26 ,, shift = 10 hr ,, days = 18, day/wage = 1000

        per_day_wage = actual_salary / calendar_days if calendar_days else 0

        adjusted_days = monthly_salary / per_day_wage if per_day_wage else 0

        full_days = int(adjusted_days)

        # fractional_day = 18.00 - 18 = 0.00
        fractional_day = adjusted_days - full_days

        # fractional_hours = 0.00 * 10 = 0.00
        fractional_hours = fractional_day * shift_hours

        if monthly_salary < actual_salary:
            action = "Checkin Adjustment"
            keep_days = round(adjusted_days)

            remove_days = calendar_days - keep_days
        else:
            action = "Incentive"
            keep_days = calendar_days
            remove_days = 0

        incentive = 0
        if monthly_salary > actual_salary:
            incentive = monthly_salary - actual_salary

        review_data.append(
            {
                "employee": employee,  # employee
                "employee_name": " ".join(
                    filter(
                        None,
                        frappe.get_value(
                            "Employee",
                            employee,
                            ["first_name", "middle_name", "last_name"],
                        )
                        or [],
                    )
                ),
                "per_day_wage": per_day_wage,
                "adjusted_days": adjusted_days,
                "full_days": round(float(adjusted_days or 0), 2),  # payable_days
                "calendar_days": calendar_days,  # calender_days
                "fractional_hours": round(float(fractional_hours or 0), 2),
                "remove_days": remove_days,  # difference_days
                "shift_hours": shift_hours,  # shift_hours
                "action": action,
                "monthly_salary": monthly_salary,
                "actual_salary": actual_salary,
                "incentive": incentive,
            }
        )

    frappe.response["message"] = review_data


@frappe.whitelist()
def proceed_check_in_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)
    doc.check_permission("read")

    try:
        from_date = doc.from_date
        to_date = doc.to_date

        emp_dates_map = json.loads(doc.date or "{}")

        holiday_list_cache = {}
        holiday_dates_cache = {}

        for row in doc.adjustment_details:
            if row.processed != 1:
                frappe.throw(
                    "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                )

            monthly_salary = float(row.monthly_salary or 0)
            actual_salary = float(row.actual_salary or 0)
            fractional_hours = float(row.fractional_hours or 0)

            action = row.action
            employee = row.employee

            shift_hours = set_shift_details(employee, doc.from_date)

            per_day_wage = (
                actual_salary / float(row.calendar_days)
                if row.calendar_days and float(row.calendar_days) > 0
                else 0
            )

            adjusted_days = monthly_salary / per_day_wage if per_day_wage else 0

            fractional_date = None

            if monthly_salary < actual_salary and action == "Checkin Adjustment":
                keep_days = round(adjusted_days)

                # 🔹 Employee Shift

                from_dt = get_datetime(from_date)
                to_dt = get_datetime(to_date).replace(hour=23, minute=59, second=59)

                # 🔹 Checkins
                employee_check_in = frappe.db.get_all(
                    "Employee Checkin",
                    filters={
                        "employee": employee,
                        "time": ["between", [from_dt, to_dt]],
                    },
                    fields=["name", "employee", "time", "log_type", "attendance"],
                )

                employee_check_in = sorted(employee_check_in, key=lambda x: x["time"])

                # holidays dates

                if employee not in holiday_list_cache:
                    holiday_list_cache[employee] = frappe.db.get_value(
                        "Employee", employee, "holiday_list"
                    )
                holiday_list = holiday_list_cache[employee]

                holiday_dates = []

                if holiday_list:
                    if holiday_list not in holiday_dates_cache:
                        holiday_dates_cache[holiday_list] = frappe.get_all(
                            "Holiday",
                            filters={
                                "parent": holiday_list,
                                "holiday_date": ["between", [from_date, to_date]],
                            },
                            pluck="holiday_date",
                        )
                    holiday_dates = holiday_dates_cache[holiday_list]

                holiday_dates = set([getdate(x) for x in holiday_dates])

                employee_check_in = [
                    row
                    for row in employee_check_in
                    if getdate(row.time) not in holiday_dates
                ]

                date_map = defaultdict(list)

                for log in employee_check_in:
                    date = getdate(log["time"])
                    date_map[date].append(log)

                sorted_dates = sorted(date_map.keys())

                keep_dates = None
                remove_dates = None
                if keep_days == round(adjusted_days):
                    keep_dates = sorted_dates[: keep_days + 1]
                    remove_dates = sorted_dates[keep_days + 1 :]
                else:
                    keep_dates = sorted_dates[:keep_days]
                    remove_dates = sorted_dates[keep_days:]

                correct_date, d = get_even_odd_cases_from_check_in_out(
                    employee, date_map, keep_dates
                )

                if correct_date:
                    shift_out_time = shift_hours.get("out_time", "00:00:00")

                    shift_end = get_datetime(
                        f"{add_days(max(d.keys()), -1)} {shift_out_time}"
                    )

                    frappe.db.set_value(
                        "Employee Checkin",
                        d[max(d.keys())],
                        {"time": shift_end, "skip_auto_attendance": 0},
                        update_modified=True,
                    )

                correct_date, d = get_even_odd_cases_from_check_in_out(
                    employee, date_map, remove_dates
                )
                remove_dates = sorted(set(remove_dates).union(correct_date))

                for date in remove_dates:
                    if not date_map[date] and date in holiday_dates:
                        frappe.db.set_value(
                            "Employee Checkin", d.get(date), "skip_auto_attendance", 1
                        )

                    for log in date_map[date]:
                        frappe.db.set_value(
                            "Employee Checkin", log["name"], "skip_auto_attendance", 1
                        )
                if fractional_hours > 0 and keep_dates:
                    fractional_date = keep_dates[-1]

                    logs = frappe.db.get_all(
                        "Employee Checkin",
                        filters={
                            "employee": employee,
                            "time": [
                                "between",
                                [fractional_date, str(fractional_date) + " 23:59:59"],
                            ],
                        },
                        fields=["name", "log_type", "time"],
                        order_by="time asc",
                    )

                    in_log = None
                    out_log = None

                    for log in logs:
                        if log.log_type == "IN":
                            in_log = log

                        elif log.log_type == "OUT":
                            out_log = log

                    # update OUT time
                    if in_log and out_log:
                        new_out_time = (
                            get_datetime(in_log.time)
                            + timedelta(hours=fractional_hours)
                        ).replace(second=0, microsecond=0)

                        frappe.db.set_value(
                            "Employee Checkin",
                            out_log.name,
                            {"time": new_out_time, "skip_auto_attendance": 0},
                        )

            elif action == "Incentive":
                employee_details = frappe.db.get_value(
                    "Employee", employee, ["company", "relieving_date"], as_dict=True
                )

                payroll_date = doc.to_date

                # payroll date should not exceed relieving date
                if employee_details.relieving_date and getdate(payroll_date) > getdate(
                    employee_details.relieving_date
                ):
                    payroll_date = employee_details.relieving_date
                    doc.payroll_date = employee_details.relieving_date

                additional_salary = frappe.get_doc(
                    {
                        "doctype": "Additional Salary",
                        "employee": employee,
                        "payroll_date": payroll_date,
                        "salary_component": "Product Incentive",
                        "company": employee_details.company,
                        "currency": "INR",
                        "amount": monthly_salary - actual_salary,
                        "overwrite_salary_structure_amount": 0,
                    }
                )

                additional_salary.insert(ignore_permissions=True)
                additional_salary.submit()

            elif monthly_salary == 0:
                checkins = frappe.get_all(
                    "Employee Checkin",
                    filters={
                        "employee": employee,
                        "time": [
                            "between",
                            [f"{from_date} 00:00:00", f"{to_date} 23:59:59"],
                        ],
                    },
                    fields=["name"],
                )

                for row in checkins:
                    frappe.db.set_value(
                        "Employee Checkin", row.name, "skip_auto_attendance", 1
                    )

            checkins = frappe.db.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "time": [
                        "between",
                        [f"{from_date} 00:00:00", f"{to_date} 23:59:59"],
                    ],
                },
                fields=["time", "log_type", "name"],
            )

            # adjust check ins if check in time is after the actul shift time and check out before shift time
            shift_in_time = shift_hours.get("in_time", "00:00:00")
            shift_out_time = shift_hours.get("out_time", "00:00:00")

            # Example 1 (Normal)
            # IN  : 15-07-2026 08:45
            # OUT : 15-07-2026 17:55

            # => Shift adjustment hoga.

            # Example 2 (Tumhara Case)
            # IN  : 14-07-2026 08:35
            # OUT : 15-07-2026 04:00

            # previous_in.date = 14
            # out.date = 15

            # 14 != 15

            # => continue
            # => OUT 04:00 hi rahega.

            previous_in = None

            for row in checkins:
                checkin_datetime = get_datetime(row.time)

                if row.log_type == "IN":
                    previous_in = checkin_datetime

                    shift_start = get_datetime(
                        f"{checkin_datetime.date()} {shift_in_time}"
                    )

                    if checkin_datetime > shift_start:
                        frappe.db.set_value(
                            "Employee Checkin",
                            row.name,
                            "time",
                            shift_start,
                            update_modified=True,
                        )

                elif row.log_type == "OUT":
                    if not previous_in:
                        continue

                    # create shift end based on IN date
                    shift_end = get_datetime(f"{previous_in.date()} {shift_out_time}")

                    # overnight shift handling
                    if shift_end < previous_in:
                        shift_end += timedelta(days=1)

                    # if OUT is next day but before shift end, don't modify
                    if checkin_datetime.date() != previous_in.date():
                        if checkin_datetime <= shift_end:
                            continue

                    # normal OUT adjustment
                    if checkin_datetime < shift_end:
                        frappe.db.set_value(
                            "Employee Checkin",
                            row.name,
                            "time",
                            shift_end,
                            update_modified=True,
                        )

            dates = {}
            for d in checkins:
                dt = getdate(d.time)
                dates.setdefault(dt, set()).add(d.log_type)

                # count where both IN & OUT present
            valid_days = sum(1 for v in dates.values() if "IN" in v and "OUT" in v)

            payable_days = math.floor(float(row.payable_days or 0))

            if payable_days > valid_days:
                missing_days = payable_days - valid_days

                shift_type = frappe.db.get_value(
                    "Shift Assignment",
                    {"employee": employee, "docstatus": 1, "status": "Active"},
                    "shift_type",
                )

                if not shift_type:
                    shift_type = frappe.db.get_value(
                        "Employee", employee, "default_shift"
                    )

                shift = frappe.db.get_value(
                    "Shift Type", shift_type, ["start_time", "end_time"], as_dict=1
                )

                if not shift:
                    frappe.throw("Shift Type not found")

                start_time = shift.start_time
                end_time = shift.end_time

                absent_dates = emp_dates_map.get(employee, [])

                absent_dates = [getdate(d) for d in absent_dates]

                # Sort dates (important)
                absent_dates = sorted(absent_dates)

                # Create missing attendance
                count = 0
                existing_log_types = get_log_types_grouped_by_date(
                    employee, absent_dates
                )
                for new_date in absent_dates:
                    if count >= missing_days:
                        # to change the last check in out if fraction paybale found
                        if fractional_hours > 0 and fractional_date:
                            logs = frappe.db.get_all(
                                "Employee Checkin",
                                filters={
                                    "employee": employee,
                                    "time": [
                                        "between",
                                        [
                                            fractional_date,
                                            str(fractional_date) + " 23:59:59",
                                        ],
                                    ],
                                },
                                fields=["name", "log_type", "time"],
                                order_by="time asc",
                            )

                            in_log = None
                            out_log = None

                            for log in logs:
                                if log.log_type == "IN":
                                    in_log = log

                                elif log.log_type == "OUT":
                                    out_log = log

                            # update OUT time
                            if in_log and out_log:
                                new_out_time_for_paybale_case = (
                                    get_datetime(in_log.time)
                                    + timedelta(hours=fractional_hours)
                                ).replace(second=0, microsecond=0)

                                frappe.db.set_value(
                                    "Employee Checkin",
                                    out_log.name,
                                    {
                                        "time": new_out_time_for_paybale_case,
                                        "skip_auto_attendance": 0,
                                    },
                                )

                        break

                    log_types = existing_log_types[new_date]

                    #  Skip if already complete
                    if "IN" in log_types and "OUT" in log_types:
                        continue

                    shift_start = get_datetime(f"{new_date} {start_time}").replace(
                        second=0, microsecond=0
                    )
                    shift_end = get_datetime(f"{new_date} {end_time}").replace(
                        second=0, microsecond=0
                    )

                    created = False

                    # IN
                    if "IN" not in log_types:
                        frappe.get_doc(
                            {
                                "doctype": "Employee Checkin",
                                "employee": employee,
                                "time": shift_start,
                                "log_type": "IN",
                                "skip_auto_attendance": 0,
                            }
                        ).insert(ignore_permissions=True)
                        log_types.add("IN")
                        created = True

                    # OUT
                    if "OUT" not in log_types:
                        frappe.get_doc(
                            {
                                "doctype": "Employee Checkin",
                                "employee": employee,
                                "time": shift_end,
                                "log_type": "OUT",
                                "skip_auto_attendance": 0,
                            }
                        ).insert(ignore_permissions=True)
                        log_types.add("OUT")
                        created = True

                    #  count tabhi badhao jab actual creation hua
                    if created:
                        count += 1

                # commit
                frappe.db.commit()
        doc.db_set("workflow_state", "Completed")

    except Exception:
        error = frappe.get_traceback()
        # Error log create
        log = frappe.log_error(
            title=f"Attendance Adjustment Failed: {doc.name}", message=error
        )

        # Update document
        doc.db_set("workflow_state", "Failed")
        doc.db_set(
            "error_details",
            f"""
                Process failed.

                Check Error Log: {log.name}

                {str(error)}
                """,
        )

        frappe.db.commit()


@frappe.whitelist()
def proceed_attendance_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)

    try:
        from_date = doc.from_date
        to_date = doc.to_date
        emp_dates_map = {}

        for row in doc.adjustment_details:
            if row.processed != 1:
                frappe.throw(
                    "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                )

            if not row.processed:
                continue

            employee = row.employee

            if row.monthly_salary == 0:
                attendance_list = frappe.db.get_all(
                    "Attendance",
                    filters={
                        "employee": employee,
                        "attendance_date": ["between", [from_date, to_date]],
                        "docstatus": 1,
                        "status": "Present",
                    },
                    fields=["name", "attendance_date"],
                )

                for attendance in attendance_list:
                    frappe.db.set_value(
                        "Attendance",
                        attendance.name,
                        "docstatus",
                        2,
                    )

            #  Attendance fetch karo
            attendance_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,  # only submitted
                },
                fields=["name", "attendance_date"],
            )

            attendance_absent_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,
                    "status": "Absent",
                },
                fields=["attendance_date"],
            )

            # extract only dates
            dates = [str(d["attendance_date"]) for d in attendance_absent_list]

            # assign per employee
            emp_dates_map[employee] = dates

            # Cancel attendance
            for att in attendance_list:
                try:
                    # Cancel attendance
                    frappe.db.set_value(
                        "Attendance",
                        att["name"],
                        {
                            "docstatus": 2,  # Cancel
                            "modified": frappe.utils.now(),
                            "modified_by": frappe.session.user,
                        },
                    )

                    # Remove attendance link from checkins
                    frappe.db.set_value(
                        "Employee Checkin",
                        {"attendance": att["name"]},
                        "attendance",
                        "",
                        update_modified=False,
                    )
                except Exception:
                    frappe.log_error(f"Error updating attendance: {att['name']}")

        frappe.db.set_value(
            "Attendance Adjustment Tool",
            doc.name,
            {
                "date": json.dumps(emp_dates_map),
                "workflow_state": "Update Attendance Completed",
                "update_attendance": 1,
            },
        )

    except Exception:
        error = frappe.get_traceback()

        log = frappe.log_error(
            title=f"Attendance Adjustment Failed: {doc.name}", message=error
        )

        # Update document
        doc.db_set("workflow_state", "Failed")
        doc.db_set(
            "error_details",
            f"""
            Process failed.

            Check Error Log: {log.name}

            {str(error)}
            """,
        )

        frappe.db.commit()


@frappe.whitelist()
def update_proceed_check_in_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)
    doc.check_permission("read")

    try:
        from_date = doc.from_date
        to_date = doc.to_date

        for row in doc.adjustment_details:
            if not row.processed:
                frappe.throw(
                    "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                )

            employee = row.employee

            employee_check_in = frappe.db.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "time": [
                        "between",
                        [f"{from_date} 00:00:00", f"{to_date} 23:59:59"],
                    ],
                },
                fields=["name"],
            )

            for checkin in employee_check_in:
                frappe.delete_doc(
                    "Employee Checkin", checkin.name, ignore_permissions=True
                )

            monthly_salary = float(row.monthly_salary or 0)
            actual_salary = float(row.actual_salary or 0)
            fractional_hours = float(row.fractional_hours or 0)
            calendar_days = float(row.calendar_days)

            shift_hours = set_shift_details(employee, from_date)

            shift_in_time = shift_hours.get("in_time", "00:00:00")
            shift_out_time = shift_hours.get("out_time", "00:00:00")

            per_day_wage = (
                actual_salary / float(row.calendar_days)
                if row.calendar_days and float(row.calendar_days) > 0
                else 0
            )

            adjusted_days = monthly_salary / per_day_wage if per_day_wage else 0

            # Start from first day of month
            month_start = get_first_day(from_date)
            month_end = get_last_day(from_date)

            # Get Employee Holiday List
            holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")

            holiday_dates = set()

            if holiday_list:
                holiday_dates = set(
                    getdate(d)
                    for d in frappe.get_all(
                        "Holiday",
                        filters={
                            "parent": holiday_list,
                            "holiday_date": ["between", [month_start, month_end]],
                        },
                        pluck="holiday_date",
                    )
                )

            keep_days = round(adjusted_days)

            # working_dates must exist before use even if keep_days <= calendar_days
            from_date_obj = getdate(doc.from_date)
            to_date_obj = getdate(doc.to_date)

            working_dates = []
            current_date = from_date_obj

            while current_date <= to_date_obj:
                if current_date not in holiday_dates:
                    working_dates.append(current_date)
                current_date = add_days(current_date, 1)

            if keep_days > calendar_days:
                employee_details = frappe.db.get_value(
                    "Employee", employee, ["company", "relieving_date"], as_dict=True
                )

                payroll_date = doc.to_date

                # payroll date should not exceed relieving date
                if employee_details.relieving_date and getdate(payroll_date) > getdate(
                    employee_details.relieving_date
                ):
                    payroll_date = employee_details.relieving_date
                doc.payroll_date = payroll_date

                check_already_exist = frappe.get_all(
                    "Additional Salary",
                    filters={
                        "employee": employee,
                        "payroll_date": payroll_date,
                        "salary_component": "Product Incentive",
                        "docstatus": 1,
                    },
                    fields=["name"],
                )

                for record in check_already_exist:
                    # 1. Update the status and docstatus directly in the database
                    frappe.db.set_value(
                        "Additional Salary",
                        record.name,
                        {
                            "docstatus": 2,  # 2 represents Cancelled status in Frappe
                        },
                        update_modified=True,
                    )

                    # Optional: Clear local cache for this document
                    frappe.clear_document_cache("Additional Salary", record.name)

                additional_salary = frappe.get_doc(
                    {
                        "doctype": "Additional Salary",
                        "employee": employee,
                        "payroll_date": payroll_date,
                        "salary_component": "Product Incentive",
                        "company": employee_details.company,
                        "currency": "INR",
                        "amount": monthly_salary - actual_salary,
                        "overwrite_salary_structure_amount": 0,
                    }
                )

                additional_salary.insert(ignore_permissions=True)
                additional_salary.submit()

                keep_days = len(working_dates)

            # If full day then add extra day
            if keep_days == math.floor(adjusted_days) and keep_days != 0:
                keep_days += 1

            created_days = 0

            # Both branches walk the same working_dates list and create
            # matching IN/OUT checkins. The only behavioural difference is
            # whether the last day's OUT time gets trimmed to fractional_hours:
            # that trim is skipped for "Incentive" rows.
            apply_fractional_trim = row.action != "Incentive"
            existing_checkin_times = get_checkin_times(
                employee, working_dates[:keep_days]
            )
            for current_date in working_dates[:keep_days]:
                # Skip holidays (defensive; working_dates already excludes them)
                if getdate(current_date) in holiday_dates:
                    continue

                if created_days >= keep_days:
                    break

                shift_start = get_datetime(f"{current_date} {shift_in_time}")
                shift_end = get_datetime(f"{current_date} {shift_out_time}")

                if (
                    apply_fractional_trim
                    and fractional_hours > 0
                    and created_days == keep_days - 1
                ):
                    shift_end = (
                        shift_start + timedelta(hours=fractional_hours)
                    ).replace(second=0, microsecond=0)

                # Check IN already exists
                if shift_start not in existing_checkin_times:
                    frappe.get_doc(
                        {
                            "doctype": "Employee Checkin",
                            "employee": employee,
                            "time": shift_start,
                            "log_type": "IN",
                            "skip_auto_attendance": 0,
                        }
                    ).insert(ignore_permissions=True)
                    existing_checkin_times.add(shift_start)

                # Check OUT already exists
                if shift_end not in existing_checkin_times:
                    frappe.get_doc(
                        {
                            "doctype": "Employee Checkin",
                            "employee": employee,
                            "time": shift_end,
                            "log_type": "OUT",
                            "skip_auto_attendance": 0,
                        }
                    ).insert(ignore_permissions=True)
                    existing_checkin_times.add(shift_end)

                created_days += 1

            frappe.db.commit()

        # All rows processed successfully
        doc.db_set("workflow_state", "Completed")

    except Exception:
        error = frappe.get_traceback()

        log = frappe.log_error(
            title=f"Attendance Adjustment Failed: {doc.name}", message=error
        )

        doc.db_set("workflow_state", "Failed")

        doc.db_set(
            "error_details",
            f"""
            Process failed.

            Check Error Log: {log.name}

            {str(error)}
            """,
        )

        frappe.db.commit()


@frappe.whitelist()
def update_proceed_attendance_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)
    try:
        from_date = doc.from_date
        to_date = doc.to_date
        for row in doc.adjustment_details:
            if not row.processed:
                frappe.throw(
                    "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                )
            employee = row.employee

            # Fetch all submitted attendance
            attendance_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,
                },
                fields=["name"],
            )
            for att in attendance_list:
                frappe.db.set_value(
                    "Attendance",
                    att.name,
                    {
                        "docstatus": 2,
                        "modified": frappe.utils.now(),
                        "modified_by": frappe.session.user,
                    },
                )

        frappe.db.commit()

        doc.db_set("workflow_state", "Update Attendance Completed")

        doc.db_set("update_attendance", 1)
    except Exception:
        error = frappe.get_traceback()

        log = frappe.log_error(
            title=f"Attendance Adjustment Failed: {doc.name}", message=error
        )

        doc.db_set("workflow_state", "Failed")

        doc.db_set(
            "error_details",
            f"""
            Process failed.

            Check Error Log: {log.name}

            {str(error)}
            """,
        )

        frappe.db.commit()


@frappe.whitelist()
def enqueue_modify_checkin(docname):
    job = frappe.enqueue(
        method="gke_customization.gke_hrms.api.generate_attendence_adjusment.update_proceed_check_in_modify",
        queue="long",
        timeout=10000,
        job_name=f"Modify Checkin {docname}",
        now=False,
        docname=docname,
    )

    frappe.msgprint(f"Job Enqueued: {job.id}")
    return job.id


@frappe.whitelist()
def enqueue_modify_attendance(docname):
    job = frappe.enqueue(
        method="gke_customization.gke_hrms.api.generate_attendence_adjusment.update_proceed_attendance_modify",
        queue="long",
        timeout=10000,
        job_name=f"Modify Attendance {docname}",
        now=False,
        docname=docname,
    )

    frappe.msgprint(f"Job Enqueued: {job.id}")
    return job.id


def get_even_odd_cases_from_check_in_out(employee, date_map, dates):
    off_dates = set()

    for date in dates:
        logs = date_map.get(date, [])

        in_count = 0
        out_count = 0

        for log in logs:
            if log["log_type"] == "IN":
                in_count += 1
            elif log["log_type"] == "OUT":
                out_count += 1

        # A date without both an IN and an OUT punch is treated as off
        if in_count == 0 or out_count == 0:
            off_dates.add(date)

    correct_date = set()
    d = {}

    if not off_dates:
        return correct_date, d

    checkins_by_date = get_checkins_grouped_by_date(employee, off_dates)

    for dt in off_dates:
        dt = getdate(dt)
        day_checkins = checkins_by_date.get(dt, [])
        if not day_checkins or day_checkins[0].log_type != "IN":
            continue

        next_day = add_days(dt, 1)

        for row in checkins_by_date.get(next_day, []):
            if not row.shift_actual_start or getdate(row.shift_actual_start) != dt:
                continue

            if not row.shift:
                continue

            shift_doc = frappe.get_cached_doc("Shift Type", row.shift)

            begin_before = shift_doc.begin_check_in_before_shift_start_time or 0
            allow_after = shift_doc.allow_check_out_after_shift_end_time or 0

            checkin_time = get_datetime(row.time)
            shift_start = get_datetime(row.shift_actual_start)
            shift_end = get_datetime(row.shift_actual_end)

            allowed_checkin_start = shift_start - timedelta(minutes=begin_before)
            allowed_checkout_end = shift_end + timedelta(minutes=allow_after)

            if allowed_checkin_start <= checkin_time <= allowed_checkout_end:
                correct_date.add(next_day)
                d[next_day] = row.name

    return correct_date, d


def get_checkins_grouped_by_date(employee, dates):
    """Fetch the employee's checkins from the first date to the day after the last date, grouped by date."""
    dates = [getdate(dt) for dt in dates]
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": [
                "between",
                [f"{min(dates)} 00:00:00", f"{add_days(max(dates), 1)} 23:59:59"],
            ],
        },
        fields=[
            "name",
            "employee",
            "time",
            "log_type",
            "attendance",
            "shift",
            "shift_actual_start",
            "shift_actual_end",
        ],
        order_by="time",
    )

    checkins_by_date = defaultdict(list)
    for row in checkins:
        checkins_by_date[getdate(row.time)].append(row)

    return checkins_by_date


def get_log_types_grouped_by_date(employee, dates):
    """Return a dict of date to the set of checkin log types the employee has on that date."""
    log_types_by_date = defaultdict(set)
    if not dates:
        return log_types_by_date

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": [
                "between",
                [f"{min(dates)} 00:00:00", f"{max(dates)} 23:59:59"],
            ],
        },
        fields=["time", "log_type"],
    )
    for row in checkins:
        log_types_by_date[getdate(row.time)].add(row.log_type)

    return log_types_by_date


def get_checkin_times(employee, dates):
    """Return the set of checkin times the employee has between the first and last date."""
    if not dates:
        return set()

    dates = [getdate(dt) for dt in dates]
    checkin_times = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": [
                "between",
                [f"{min(dates)} 00:00:00", f"{max(dates)} 23:59:59"],
            ],
        },
        pluck="time",
    )
    return {get_datetime(time) for time in checkin_times}
