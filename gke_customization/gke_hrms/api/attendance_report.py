from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.query_builder.functions import Concat, Count, Date, IfNull, Sum
from frappe.utils import (
    add_days,
    flt,
    format_time,
    get_time,
    getdate,
)
from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import (
    get_checkins_for_dates,
)

from gke_customization.gke_hrms.api.utils import (
    IF,
    SEC_TO_TIME,
    TIME,
    TIME_FORMAT,
    TIME_TO_SEC,
    TIMEDIFF,
    TIMESTAMP,
    get_date_range,
    get_ot_log_subquery,
    get_personal_out_log_subquery,
    get_shift_type_details,
)

STATUS = {
    "Absent": "A",
    "Present": "P",
    "Half Day": "HD",
    "Paid Leave": "PL",
    "Casual Leave": "CL",
    "Sick Leave": "SL",
    "Leave Without Pay": "LWP",
    "Outdoor Duty": "OD",
    "Work From Home": "WFH",
    "Maternity Leave": "ML",
}


@frappe.whitelist(allow_guest=True)
def attendance(from_date=None, to_date=None, employee=None):
    conditions = get_conditions(from_date, to_date, employee)

    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    ShiftType = frappe.qb.DocType("Shift Type")
    PersonalOutLog = frappe.qb.DocType("Personal Out Log")

    if conditions:
        paid_leave_types = frappe.db.get_list(
            "Leave Type",
            filters={"is_lwp": 0},
            pluck="name",
        )
        worked_seconds = IF(
            (Attendance.status == "On Leave")
            & (Attendance.leave_type.isin(paid_leave_types)),
            ShiftType.shift_hours * 3600,
            IF(
                Attendance.out_time,
                TIME_TO_SEC(TIMEDIFF(Attendance.out_time, Attendance.in_time)),
                Attendance.working_hours * 3600,
            ),
        )

        pol_subquery = get_personal_out_log_subquery()

        ot_subquery = get_ot_log_subquery()

        query = (
            frappe.qb.from_(Attendance)
            .left_join(Employee)
            .on(Attendance.employee == Employee.name)
            .left_join(ShiftType)
            .on(Employee.default_shift == ShiftType.name)
            .left_join(pol_subquery)
            .on(
                (Attendance.attendance_date == pol_subquery.date)
                & (Attendance.employee == pol_subquery.employee)
            )
            .left_join(ot_subquery)
            .on(
                (Attendance.attendance_date == ot_subquery.attendance_date)
                & (Attendance.employee == ot_subquery.employee)
            )
            .select(
                Attendance.attendance_date,
                Concat(
                    TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"),
                    " TO ",
                    TIME_FORMAT(ShiftType.end_time, "%H:%i:%s"),
                ).as_("shift"),
                TIME(Attendance.in_time).as_("in_time"),
                TIME(Attendance.out_time).as_("out_time"),
                TIMEDIFF(Attendance.out_time, Attendance.in_time).as_("spent_hours"),
                Attendance.late_entry,
                IF(
                    Attendance.late_entry,
                    TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time),
                    None,
                ).as_("late_hrs"),
                IF(
                    Attendance.early_exit,
                    TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)),
                    None,
                ).as_("early_hrs"),
                pol_subquery.hrs.as_("p_out_hrs"),
                SEC_TO_TIME(
                    worked_seconds
                    + IF(
                        (Attendance.late_entry == 0)
                        & (TIME(Attendance.in_time) > ShiftType.start_time),
                        TIME_TO_SEC(
                            TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time)
                        ),
                        0,
                    )
                    - IF(
                        TIME(Attendance.in_time) < ShiftType.start_time,
                        TIME_TO_SEC(
                            TIMEDIFF(ShiftType.start_time, TIME(Attendance.in_time))
                        ),
                        0,
                    )
                    - IF(
                        Attendance.out_time
                        > TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time),
                        TIME_TO_SEC(
                            TIMEDIFF(
                                Attendance.out_time,
                                TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time),
                            )
                        ),
                        0,
                    )
                    - IfNull(TIME_TO_SEC(pol_subquery.hrs), 0)
                    + (
                        frappe.qb.from_(PersonalOutLog)
                        .select(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0))
                        .where(
                            (PersonalOutLog.is_cancelled == 0)
                            & (PersonalOutLog.employee == Attendance.employee)
                            & (PersonalOutLog.date == Attendance.attendance_date)
                            & (PersonalOutLog.out_time >= ShiftType.end_time)
                        )
                    )
                ).as_("net_wrk_hrs"),
                ShiftType.shift_hours,
                IF(
                    (
                        ShiftType.working_hours_threshold_for_half_day
                        > Attendance.working_hours
                    )
                    & (Attendance.working_hours > 0),
                    1,
                    0,
                ).as_("lh"),
                ot_subquery.allowed_ot.as_("ot_hours"),
                IfNull(Attendance.leave_type, Attendance.status).as_("status"),
                Attendance.attendance_request,
            )
            .where(Attendance.docstatus == 1)
            .orderby(Attendance.attendance_date, order=frappe.qb.asc)
        )

        for condition in conditions:
            query = query.where(condition)

        data = query.run(as_dict=1)

        if not data:
            return

        data = process_data(data, from_date, to_date, employee)
    return data


def get_conditions(from_date, to_date, employee):
    from_date = frappe.form_dict["from_date"]
    to_date = frappe.form_dict["to_date"]
    employee = frappe.form_dict["employee"]

    Attendance = frappe.qb.DocType("Attendance")

    if not (from_date and to_date):
        frappe.throw(_("From & To Dates are mandatory"))

    conditions = [Attendance.attendance_date.between(from_date, to_date)]
    if employee:
        conditions.append(Attendance.employee == employee)

    return conditions


def process_data(data, from_date, to_date, employee):
    processed = {}
    result = []
    holidays = []
    wo = []
    emp_det = frappe.db.get_value(
        "Employee",
        employee,
        [
            "default_shift",
            "holiday_list",
            "date_of_joining",
            "employee_name",
            "company",
            "department",
            "allowed_personal_hours",
            "designation",
            "old_punch_id",
            "middle_name",
            "gender",
            "date_of_birth",
        ],
        as_dict=1,
    )
    shift = emp_det.get("default_shift")
    shift_det = get_shift_type_details(shift)
    shift_hours = flt(shift_det.get("shift_hours"))
    shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
    grace_period = shift_det.get("early_exit_grace_period")

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    addition_day = add_days(to_date, 1)
    login_date = Date(EmployeeCheckin.time)
    checkins = (
        frappe.qb.from_(EmployeeCheckin)
        .select(
            login_date.as_("login_date"),
            EmployeeCheckin.attendance,
            Count(EmployeeCheckin.name).as_("cnt"),
        )
        .where(
            (EmployeeCheckin.time.between(from_date, addition_day))
            & (EmployeeCheckin.employee == employee)
        )
        .groupby(EmployeeCheckin.attendance)
    ).run(as_dict=True)

    checkins = {row.login_date: row.cnt for row in checkins}
    od = (
        frappe.qb.from_(EmployeeCheckin)
        .select(login_date.as_("login_date"))
        .where(EmployeeCheckin.employee == employee)
        .where(EmployeeCheckin.source == "Outdoor Duty")
        .where(EmployeeCheckin.time.between(from_date, addition_day))
        .groupby(login_date)
        .run(pluck="login_date")
    )
    if shift and not emp_det.get("holiday_list"):
        emp_det["holiday_list"] = shift_det.get("holiday_list")

    if hl_name := emp_det.get("holiday_list"):
        holidays = frappe.get_list(
            "Holiday",
            {"parent": hl_name, "holiday_date": ["between", [from_date, to_date]]},
            ["holiday_date", "weekly_off"],
            ignore_permissions=1,
        )
        wo = [row.holiday_date for row in holidays if row.weekly_off]
        holidays = [row.holiday_date for row in holidays if not row.weekly_off]

    for row in data:
        if grace_period != 0:
            if not (row.early_hrs):
                if row.status == "Absent":
                    row.net_wrk_hrs = timedelta(0)
                elif row.late_hrs or row.p_out_hrs:
                    late = row.late_hrs or timedelta(0)
                    p_out = row.p_out_hrs or timedelta(0)
                    row.net_wrk_hrs = timedelta(hours=shift_hours) - (late + p_out)
                else:
                    row.net_wrk_hrs = timedelta(hours=shift_hours)
        if row.lh:
            row.status = "LH"
        shift_hours_in_sec = row.shift_hours * 3600
        if (
            row.net_wrk_hrs.total_seconds() > shift_hours_in_sec
            or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60
        ):
            row.net_wrk_hrs = timedelta(hours=row.shift_hours)
        row["total_pay_hrs"] = row.net_wrk_hrs + (row.get("ot_hours") or timedelta(0))
        row.status = STATUS.get(row.status) or row.status
        processed[row.attendance_date] = row

    ot_for_wo = frappe.get_all(
        "OT Log",
        {
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "is_cancelled": 0,
        },
        [
            "attendance_date",
            "allowed_ot as ot_hours",
            "first_in as in_time",
            "last_out as out_time",
        ],
    )
    ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
    date_range = get_date_range(from_date, to_date)
    joining_date = getdate(emp_det.get("date_of_joining"))

    weekly_off_shift_starts = {
        date: datetime.combine(date, get_time(shift_det.start_time))
        for date in date_range
        if date not in od and date in wo and date >= joining_date
    }
    weekly_off_checkins = get_checkins_for_dates(
        employee, list(weekly_off_shift_starts.values())
    )

    for date in date_range:
        row = processed.get(date, ot_for_wo.get(date, {}))
        if date in od:
            row["status"] = "OD"
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours
        elif date in weekly_off_shift_starts:
            status = "WO"
            shift_start = weekly_off_shift_starts[date]
            if first_in_last_out := weekly_off_checkins.get(shift_start):
                row["in_time"] = get_time(first_in_last_out[0].get("time"))
                row["out_time"] = get_time(first_in_last_out[-1].get("time"))
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours
        elif (date in holidays) and (date >= joining_date):
            if row:
                clear_worked_hours(row)
            else:
                status = "H"
                row["net_wrk_hrs"] = timedelta(hours=shift_hours)
                row["total_pay_hrs"] = timedelta(hours=shift_hours)
        else:
            status = "XX"
        if count := checkins.get(date):
            if count % 2 != 0:
                row["status"] = "ERR"
                clear_worked_hours(row)
        temp = {
            "login_date": date,
            "shift": shift_name,
            "status": status,
            "employee": employee,
            "employee_name": emp_det.get("employee_name"),
            "company": emp_det.get("company"),
            "department": emp_det.get("department"),
            "designation": emp_det.get("designation"),
            "old_punch_id": emp_det.get("old_punch_id"),
            "middle_name": emp_det.get("middle_name"),
            "gender": emp_det.get("gender"),
            "date_of_birth": emp_det.get("date_of_birth"),
            "date_of_joining": emp_det.get("date_of_joining"),
            "allowed_personal_hours": emp_det.get("allowed_personal_hours"),
            "attendance_date": date,
            "shift_hours": shift_hours,
        }
        if not row.get("spent_hours"):
            row["spent_hours"] = None
        temp.update(row)
        result.append(temp)
    return result


def clear_worked_hours(row):
    row["net_wrk_hrs"] = timedelta(0)
    row["total_pay_hrs"] = timedelta(0)


@frappe.whitelist(allow_guest=True)
def employee_details(company=None, department=None):
    company = frappe.form_dict.get("company")
    department = frappe.form_dict.get("department")

    employee = frappe.qb.DocType("Employee")

    query = frappe.qb.from_(employee).select(
        employee.name.as_("employee"),
        employee.employee_name,
        employee.company,
        employee.department,
        employee.default_shift.as_("shift"),
        employee.designation,
        employee.old_punch_id,
    )

    if company:
        query = query.where(employee.company == company)
    if department:
        query = query.where(employee.department == department)

    return query.run(as_dict=True)
