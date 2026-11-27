import json
import math
from collections import defaultdict
from datetime import timedelta

import frappe
import openpyxl
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from frappe import _
from frappe.utils import add_days, flt, get_datetime, getdate
from frappe.utils.file_manager import get_file_path


def set_shift_details(employee, from_date):
    if not from_date:
        return

    matched_shift = None

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
        if shift.end_date:
            if shift.start_date <= from_date <= shift.end_date:
                matched_shift = shift
                break

        # Open ended shift assignment
        else:
            if from_date >= shift.start_date:
                matched_shift = shift
                break

    if matched_shift:
        return apply_shift_time(matched_shift.shift_type)

    default_shift = frappe.db.get_value("Employee", employee, "default_shift")

    if default_shift:
        return apply_shift_time(default_shift)
    frappe.throw(
        _("No Shift Assignment or Default Shift {0} found {1}").format(
            default_shift, employee
        )
    )


@frappe.whitelist()
def check_employee_active_validation_based_on_doj(employees):
    # Employees arrive from JS as a JSON string
    if isinstance(employees, str):
        employees = frappe.parse_json(employees)

    if not employees:
        return True

    employee_ids = []
    for row in employees:
        # A row is either {"employee": "EMP-0001"} or "EMP-0001"
        if isinstance(row, dict):
            emp = row.get("employee")
        else:
            emp = row

        if emp:
            employee_ids.append(emp)

    if not employee_ids:
        return True

    employee_details_map = {
        employee.name: employee
        for employee in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_ids]},
            fields=["name", "employee_name", "relieving_date", "status"],
        )
    }

    for emp in employee_ids:
        employee_details = employee_details_map.get(emp)

        if not employee_details:
            continue

        if employee_details.relieving_date and employee_details.status == "Active":
            frappe.throw(
                _(
                    """
                Employee <b>{0}</b> ({1})
                has a Relieving Date
                <b>{2}</b>
                but the employee status is still <b>Active</b>.
                Please mark the employee as <b>Inactive</b> before proceeding.
                """
                ).format(
                    employee_details.employee_name,
                    emp,
                    frappe.format(employee_details.relieving_date),
                )
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


@frappe.whitelist(allow_guest=True)
def process_salary_adjustment(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)

    file_path = doc.records

    if not file_path:
        frappe.throw(_("Please attach an Excel file"))

    file_full_path = get_file_path(file_path)

    if not file_full_path:
        frappe.throw(_("File not found in request"))

    wb = openpyxl.load_workbook(file_full_path)
    sheet = wb.active

    data = []
    headers = [cell.value for cell in sheet[1]]

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_dict = dict(zip(headers, row))
        data.append(row_dict)

    employee_ids = list({row.get("employee") for row in data if row.get("employee")})
    employee_name_map = {}
    if employee_ids:
        for employee in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_ids]},
            fields=["name", "first_name", "middle_name", "last_name"],
        ):
            employee_name_map[employee.name] = " ".join(
                filter(
                    None,
                    [employee.first_name, employee.middle_name, employee.last_name],
                )
            )

    shift_details_cache = {}
    review_data = []

    for row in data:
        employee = row.get("employee")
        actual_salary = flt(row.get("actual_salary"))
        monthly_salary = flt(row.get("monthly_salary"))
        calendar_days = flt(row.get("calendar_days"))

        if employee not in shift_details_cache:
            shift_details_cache[employee] = set_shift_details(employee, doc.from_date)

        shift_hours = float(shift_details_cache[employee].get("total_hours", 0))

        # Example: actual 26000, monthly 18000, 26 calendar days, 10 hour shift
        # gives per day wage 1000, adjusted days 18.00, fractional hours 0.00
        per_day_wage = actual_salary / calendar_days if calendar_days else 0
        adjusted_days = monthly_salary / per_day_wage if per_day_wage else 0
        full_days = int(adjusted_days)
        fractional_day = adjusted_days - full_days
        fractional_hours = fractional_day * shift_hours

        if monthly_salary < actual_salary:
            action = "Checkin Adjustment"
            keep_days = round(adjusted_days)
            remove_days = calendar_days - keep_days
        else:
            action = "Incentive"
            remove_days = 0

        incentive = (
            monthly_salary - actual_salary if monthly_salary > actual_salary else 0
        )

        review_data.append(
            {
                "employee": employee,
                "employee_name": employee_name_map.get(employee, ""),
                "per_day_wage": per_day_wage,
                "adjusted_days": adjusted_days,
                "full_days": round(float(adjusted_days or 0), 2),
                "calendar_days": calendar_days,
                "fractional_hours": round(float(fractional_hours or 0), 2),
                "remove_days": remove_days,
                "shift_hours": shift_hours,
                "action": action,
                "monthly_salary": monthly_salary,
                "actual_salary": actual_salary,
                "incentive": incentive,
            }
        )

    frappe.response["message"] = review_data


@frappe.whitelist(allow_guest=True)
def proceed_check_in_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)

    try:
        from_date = doc.from_date
        to_date = doc.to_date

        emp_dates_map = json.loads(doc.date or "{}")

        employee_ids = list(
            {row.employee for row in doc.adjustment_details if row.employee}
        )
        holiday_list_map = {}
        holiday_dates_map = defaultdict(set)
        if employee_ids:
            holiday_list_map = {
                employee.name: employee.holiday_list
                for employee in frappe.get_all(
                    "Employee",
                    filters={"name": ["in", employee_ids]},
                    fields=["name", "holiday_list"],
                )
            }

            holiday_lists = list(
                {
                    holiday_list
                    for holiday_list in holiday_list_map.values()
                    if holiday_list
                }
            )
            if holiday_lists:
                for holiday in frappe.get_all(
                    "Holiday",
                    filters={
                        "parent": ["in", holiday_lists],
                        "holiday_date": ["between", [from_date, to_date]],
                    },
                    fields=["parent", "holiday_date"],
                ):
                    holiday_dates_map[holiday.parent].add(getdate(holiday.holiday_date))

        for row in doc.adjustment_details:
            if row.processed != 1:
                frappe.throw(
                    _(
                        "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                    )
                )

            if not row.processed:
                continue

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

                from_dt = get_datetime(from_date)
                to_dt = get_datetime(to_date).replace(hour=23, minute=59, second=59)

                employee_check_in = frappe.db.get_all(
                    "Employee Checkin",
                    filters={
                        "employee": employee,
                        "time": ["between", [from_dt, to_dt]],
                    },
                    fields=["name", "employee", "time", "log_type", "attendance"],
                )

                employee_check_in = sorted(employee_check_in, key=lambda x: x["time"])

                holiday_list = holiday_list_map.get(employee)
                holiday_dates = (
                    set(holiday_dates_map.get(holiday_list, set()))
                    if holiday_list
                    else set()
                )

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

                keep_dates = sorted_dates[: keep_days + 1]
                remove_dates = sorted_dates[keep_days + 1 :]

                correct_date, d = get_even_odd_cases_from_check_in_out(
                    holiday_dates, employee, date_map, keep_dates
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

                # Covers the odd case where the OUT punch falls on a holiday
                correct_date, d = get_even_odd_cases_from_check_in_out(
                    holiday_dates, employee, date_map, remove_dates
                )
                remove_dates = sorted(set(remove_dates).union(correct_date))

                checkins_to_skip = []
                for date in remove_dates:
                    if not date_map[date] and date in holiday_dates and d.get(date):
                        checkins_to_skip.append(d.get(date))

                    for log in date_map[date]:
                        checkins_to_skip.append(log["name"])

                if checkins_to_skip:
                    frappe.db.set_value(
                        "Employee Checkin",
                        {"name": ["in", checkins_to_skip]},
                        "skip_auto_attendance",
                        1,
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

                # Payroll date should not exceed the relieving date
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
                checkin_names = frappe.get_all(
                    "Employee Checkin",
                    filters={
                        "employee": employee,
                        "time": [
                            "between",
                            [f"{from_date} 00:00:00", f"{to_date} 23:59:59"],
                        ],
                    },
                    pluck="name",
                )

                if checkin_names:
                    frappe.db.set_value(
                        "Employee Checkin",
                        {"name": ["in", checkin_names]},
                        "skip_auto_attendance",
                        1,
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

            # Move a late IN back to shift start and an early OUT forward to shift end.
            # An OUT on the next day that is still before the shift end is left as it is.
            shift_in_time = shift_hours.get("in_time", "00:00:00")
            shift_out_time = shift_hours.get("out_time", "00:00:00")

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

                    shift_end = get_datetime(f"{previous_in.date()} {shift_out_time}")

                    # Overnight shift
                    if shift_end < previous_in:
                        shift_end += timedelta(days=1)

                    if checkin_datetime.date() != previous_in.date():
                        if checkin_datetime <= shift_end:
                            continue

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

            # Days that have both an IN and an OUT
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
                    frappe.throw(_("Shift Type not found"))

                start_time = shift.start_time
                end_time = shift.end_time

                absent_dates = sorted(
                    getdate(d) for d in emp_dates_map.get(employee, [])
                )

                log_types_by_date = defaultdict(list)
                if absent_dates:
                    for log in frappe.db.get_all(
                        "Employee Checkin",
                        filters={
                            "employee": employee,
                            "time": [
                                "between",
                                [
                                    f"{absent_dates[0]} 00:00:00",
                                    f"{absent_dates[-1]} 23:59:59",
                                ],
                            ],
                        },
                        fields=["log_type", "time"],
                    ):
                        log_types_by_date[getdate(log.time)].append(log.log_type)

                count = 0
                for new_date in absent_dates:
                    if count >= missing_days:
                        # Apply the fractional payable hours to the last OUT
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

                            if in_log and out_log:
                                new_out_time_for_payable_case = get_datetime(
                                    in_log.time
                                ) + timedelta(hours=fractional_hours).replace(
                                    second=0, microsecond=0
                                )

                                frappe.db.set_value(
                                    "Employee Checkin",
                                    out_log.name,
                                    {
                                        "time": new_out_time_for_payable_case,
                                        "skip_auto_attendance": 0,
                                    },
                                )

                        break

                    log_types = log_types_by_date[new_date]

                    if "IN" in log_types and "OUT" in log_types:
                        continue

                    shift_start = get_datetime(f"{new_date} {start_time}").replace(
                        second=0, microsecond=0
                    )
                    shift_end = get_datetime(f"{new_date} {end_time}").replace(
                        second=0, microsecond=0
                    )

                    created = False

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
                        created = True

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
                        created = True

                    # Count a day only when a checkin was actually created
                    if created:
                        count += 1

                frappe.db.commit()

        doc.db_set("workflow_state", "Completed")

    except Exception:
        set_failed_status(doc)
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
                    _(
                        "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                    )
                )

            if not row.processed:
                continue

            employee = row.employee

            if row.monthly_salary == 0:
                present_attendance_names = frappe.db.get_all(
                    "Attendance",
                    filters={
                        "employee": employee,
                        "attendance_date": ["between", [from_date, to_date]],
                        "docstatus": 1,
                        "status": "Present",
                    },
                    pluck="name",
                )

                if present_attendance_names:
                    frappe.db.set_value(
                        "Attendance",
                        {"name": ["in", present_attendance_names]},
                        "docstatus",
                        2,
                    )

            attendance_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,
                },
                fields=["name", "attendance_date", "status"],
            )

            emp_dates_map[employee] = [
                str(attendance.attendance_date)
                for attendance in attendance_list
                if attendance.status == "Absent"
            ]

            for attendance in attendance_list:
                try:
                    frappe.db.set_value(
                        "Attendance",
                        attendance.name,
                        {
                            "docstatus": 2,
                            "modified": frappe.utils.now(),
                            "modified_by": frappe.session.user,
                        },
                    )

                    frappe.db.set_value(
                        "Employee Checkin",
                        {"attendance": attendance.name},
                        "attendance",
                        "",
                        update_modified=False,
                    )
                except Exception:
                    frappe.log_error(f"Error updating attendance: {attendance.name}")

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
        set_failed_status(doc)
        frappe.db.commit()


def create_employee_checkin(employee, time, log_type):
    """Create an Employee Checkin unless one already exists for the same employee and time.

    A duplicate created in between (race condition or double click) raises a
    'same timestamp' validation error, which is ignored.
    """
    if frappe.db.exists("Employee Checkin", {"employee": employee, "time": time}):
        return

    try:
        frappe.get_doc(
            {
                "doctype": "Employee Checkin",
                "employee": employee,
                "time": time,
                "log_type": log_type,
                "skip_auto_attendance": 0,
            }
        ).insert(ignore_permissions=True)

    except frappe.ValidationError as e:
        if "same timestamp" in str(e):
            return
        raise


def set_failed_status(doc):
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


@frappe.whitelist()
def update_proceed_check_in_modify(docname):
    doc = frappe.get_doc("Attendance Adjustment Tool", docname)

    try:
        from_date = getdate(doc.from_date)
        to_date = getdate(doc.to_date)

        employees = [row.employee for row in doc.adjustment_details]
        employee_details_map = {}
        if employees:
            employee_details_map = {
                employee_details.name: employee_details
                for employee_details in frappe.get_all(
                    "Employee",
                    filters={"name": ["in", employees]},
                    fields=["name", "date_of_joining", "company", "relieving_date"],
                )
            }

        for row in doc.adjustment_details:
            if not row.processed:
                frappe.throw(
                    _(
                        "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                    )
                )

            employee = row.employee

            # Start from the joining date when the employee joined inside the period
            employee_details = employee_details_map.get(employee) or frappe._dict()
            joining_date = employee_details.date_of_joining

            row_from_date = from_date

            if joining_date and getdate(joining_date) > row_from_date:
                row_from_date = getdate(joining_date)

            from_date_obj = row_from_date
            to_date_obj = to_date

            if from_date_obj > to_date_obj:
                continue

            personal_out_log = frappe.db.get_all(
                "Personal Out Log",
                filters={
                    "date": ["between", [from_date_obj, to_date_obj]],
                    "employee": employee,
                },
                pluck="name",
            )

            ot_log = frappe.db.get_all(
                "OT Log",
                filters={
                    "attendance_date": ["between", [from_date_obj, to_date_obj]],
                    "employee": employee,
                },
                pluck="name",
            )

            manual_punch_entry = frappe.db.get_all(
                "Manual Punch Entry",
                filters={
                    "date": ["between", [from_date_obj, to_date_obj]],
                    "employee": employee,
                },
                pluck="name",
            )

            for pol_name in personal_out_log:
                frappe.delete_doc("Personal Out Log", pol_name, ignore_permissions=True)

            for ot_name in ot_log:
                frappe.delete_doc("OT Log", ot_name, ignore_permissions=True)

            if manual_punch_entry:
                linked_details = frappe.get_all(
                    "Manual Punch Details",
                    filters={
                        "parent": ["in", manual_punch_entry],
                        "parenttype": "Manual Punch Entry",
                        "employee_checkin": ["is", "set"],
                    },
                    pluck="name",
                )

                if linked_details:
                    frappe.db.set_value(
                        "Manual Punch Details",
                        {"name": ["in", linked_details]},
                        "employee_checkin",
                        None,
                        update_modified=False,
                    )

            for mpe_name in manual_punch_entry:
                frappe.delete_doc(
                    "Manual Punch Entry", mpe_name, ignore_permissions=True
                )

            holiday_list = get_holiday_list_for_employee(
                employee, raise_exception=False
            )

            holiday_dates = set()
            sandwich_dates = set()

            if holiday_list:
                holidays = frappe.get_all(
                    "Holiday",
                    filters={
                        "parent": holiday_list,
                        "holiday_date": ["between", [from_date_obj, to_date_obj]],
                    },
                    fields=["holiday_date", "weekly_off"],
                )

                for holiday in holidays:
                    if holiday.weekly_off:
                        holiday_dates.add(getdate(holiday.holiday_date))
                    else:
                        sandwich_dates.add(getdate(holiday.holiday_date))

            employee_check_in = frappe.db.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "time": [
                        "between",
                        [f"{from_date_obj} 00:00:00", f"{to_date_obj} 23:59:59"],
                    ],
                },
                pluck="name",
            )

            for checkin_name in employee_check_in:
                frappe.delete_doc(
                    "Employee Checkin", checkin_name, ignore_permissions=True
                )

            monthly_salary = float(row.monthly_salary or 0)
            actual_salary = float(row.actual_salary or 0)
            fractional_hours = float(row.fractional_hours or 0)
            calendar_days = float(row.calendar_days or 0)

            shift_hours = set_shift_details(employee, from_date_obj)

            shift_in_time = shift_hours.get("in_time", "00:00:00")
            shift_out_time = shift_hours.get("out_time", "00:00:00")

            per_day_wage = actual_salary / calendar_days if calendar_days > 0 else 0

            adjusted_days = monthly_salary / per_day_wage if per_day_wage else 0

            keep_days = round(adjusted_days)

            # Eligible working dates exclude weekly offs
            working_dates = []
            current_date = from_date_obj

            while current_date <= to_date_obj:
                if current_date not in holiday_dates:
                    working_dates.append(current_date)
                current_date = add_days(current_date, 1)

            if keep_days > calendar_days:
                payroll_date = doc.to_date

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
                    pluck="name",
                )

                if check_already_exist:
                    frappe.db.set_value(
                        "Additional Salary",
                        {"name": ["in", check_already_exist]},
                        {"docstatus": 2},
                        update_modified=True,
                    )

                    for additional_salary_name in check_already_exist:
                        frappe.clear_document_cache(
                            "Additional Salary", additional_salary_name
                        )

                additional_salary = frappe.get_doc(
                    {
                        "doctype": "Additional Salary",
                        "employee": employee,
                        "payroll_date": payroll_date,
                        "salary_component": "Product Incentive",
                        "company": employee_details.company,
                        "currency": "INR",
                        "amount": (
                            (flt(row.payable_days) - len(working_dates))
                            * flt(per_day_wage)
                            if joining_date
                            and from_date < getdate(joining_date) <= to_date
                            else monthly_salary - actual_salary
                        ),
                        "overwrite_salary_structure_amount": 0,
                    }
                )

                additional_salary.insert(ignore_permissions=True)
                additional_salary.submit()

                keep_days = len(working_dates)

            # Existing full-day adjustment
            if keep_days == math.floor(adjusted_days) and keep_days != 0:
                keep_days += 1

            created_days = 0
            apply_fractional_trim = row.action != "Incentive"

            for current_date in working_dates[:keep_days]:
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

                create_employee_checkin(employee, shift_start, "IN")
                create_employee_checkin(employee, shift_end, "OUT")

                created_days += 1

            # Sandwich holidays without IN and OUT on both sides become LWP attendance
            holiday_list_dates = sorted(sandwich_dates)

            checkin_rows = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "time": [
                        "between",
                        [
                            f"{add_days(from_date_obj, -1)} 00:00:00",
                            f"{add_days(to_date_obj, 1)} 23:59:59",
                        ],
                    ],
                },
                fields=["time", "log_type"],
            )

            checkin_map = {}

            for checkin_row in checkin_rows:
                checkin_map.setdefault(getdate(checkin_row.time), set()).add(
                    checkin_row.log_type
                )

            def has_in_out(date):
                return {"IN", "OUT"} <= checkin_map.get(date, set())

            holiday_status = {}
            for holiday_date in holiday_list_dates:
                both = has_in_out(add_days(holiday_date, -1)) and has_in_out(
                    add_days(holiday_date, 1)
                )
                holiday_status[str(holiday_date)] = 1 if both else 0

            for date, flag in holiday_status.items():
                if flag != 0:
                    continue

                attendance = frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": employee,
                        "attendance_date": date,
                        "status": "On Leave",
                        "leave_type": "Leave Without Pay",
                    }
                )

                attendance.insert(ignore_permissions=True)
                attendance.submit()

            # Background job: persist each employee's changes as they finish
            frappe.db.commit()

        doc.db_set("workflow_state", "Completed")

    except Exception:
        set_failed_status(doc)

        # Background job: persist the Failed status
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
                    _(
                        "Please check the 'Proceed' checkbox in Adjustment Details before continuing."
                    )
                )

            employee = row.employee

            attendance_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": ["between", [from_date, to_date]],
                    "docstatus": 1,
                },
                pluck="name",
            )

            if attendance_list:
                frappe.db.set_value(
                    "Attendance",
                    {"name": ["in", attendance_list]},
                    {
                        "docstatus": 2,
                        "modified": frappe.utils.now(),
                        "modified_by": frappe.session.user,
                    },
                )

        # Background job: persist the cancelled attendance
        frappe.db.commit()

        doc.db_set(
            {"workflow_state": "Update Attendance Completed", "update_attendance": 1}
        )

    except Exception:
        set_failed_status(doc)

        # Background job: persist the Failed status
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

    frappe.msgprint(_("Job Enqueued: {0}").format(job.id))
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

    frappe.msgprint(_("Job Enqueued: {0}").format(job.id))
    return job.id


def get_even_odd_cases_from_check_in_out(holiday_dates, employee, date_map, dates):
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

        # Dates without a proper IN and OUT pair are treated as off dates
        if in_count == 0 or out_count == 0:
            off_dates.add(date)

    correct_date = set()
    d = {}

    if not off_dates:
        return correct_date, d

    first_off_date = min(getdate(dt) for dt in off_dates)
    last_off_date = max(getdate(dt) for dt in off_dates)

    employee_checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": [
                "between",
                [
                    f"{first_off_date} 00:00:00",
                    f"{add_days(last_off_date, 1)} 23:59:59",
                ],
            ],
        },
        fields=[
            "name",
            "employee",
            "time",
            "shift",
            "log_type",
            "attendance",
            "shift_actual_start",
            "shift_actual_end",
        ],
        order_by="time",
    )

    checkins_by_date = defaultdict(list)
    for checkin in employee_checkins:
        checkins_by_date[getdate(checkin.time)].append(checkin)

    for dt in off_dates:
        check_actual_time = checkins_by_date.get(getdate(dt), [])

        if check_actual_time and check_actual_time[0].log_type == "IN":
            next_day = add_days(dt, 1)

            next_day_checkins = checkins_by_date.get(getdate(next_day), [])

            for row in next_day_checkins:
                if row.shift_actual_start and getdate(row.shift_actual_start) == dt:
                    if row.shift:
                        shift_doc = frappe.get_cached_doc(
                            "Shift Type",
                            row.shift,
                        )

                        begin_before = (
                            shift_doc.begin_check_in_before_shift_start_time or 0
                        )
                        allow_after = (
                            shift_doc.allow_check_out_after_shift_end_time or 0
                        )

                        checkin_time = get_datetime(row.time)
                        shift_start = get_datetime(row.shift_actual_start)
                        shift_end = get_datetime(row.shift_actual_end)

                        allowed_checkin_start = shift_start - timedelta(
                            minutes=begin_before
                        )

                        allowed_checkout_end = shift_end + timedelta(
                            minutes=allow_after
                        )

                        if (
                            allowed_checkin_start
                            <= checkin_time
                            <= allowed_checkout_end
                        ):
                            correct_date.add(next_day)
                            d[next_day] = row.name

    return correct_date, d
