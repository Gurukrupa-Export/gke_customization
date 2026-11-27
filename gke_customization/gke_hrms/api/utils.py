from datetime import timedelta

import frappe
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Count, Date, IfNull, Sum
from frappe.utils import flt, getdate

TIME_FORMAT = CustomFunction("TIME_FORMAT", ["time", "format"])
TIMEDIFF = CustomFunction("TIMEDIFF", ["time1", "time2"])
SEC_TO_TIME = CustomFunction("SEC_TO_TIME", ["seconds"])
TIME_TO_SEC = CustomFunction("TIME_TO_SEC", ["time"])
IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])
TIMESTAMP = CustomFunction("TIMESTAMP", ["date", "time"])
TIME = CustomFunction("TIME", ["time"])
ADDDATE = CustomFunction("ADDDATE", ["date", "days"])
ADDTIME = CustomFunction("ADDTIME", ["date", "time"])


def get_personal_out_log_subquery():
    """Return total Personal Out Log hours per employee and date, aliased as "pol"."""
    PersonalOutLog = frappe.qb.DocType("Personal Out Log")
    return (
        frappe.qb.from_(PersonalOutLog)
        .select(
            PersonalOutLog.employee,
            PersonalOutLog.date,
            SEC_TO_TIME(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0)).as_(
                "hrs"
            ),
        )
        .where(PersonalOutLog.is_cancelled == 0)
        .groupby(PersonalOutLog.employee, PersonalOutLog.date)
    ).as_("pol")


def get_ot_log_subquery():
    """Return non-cancelled OT Log rows, aliased as "ot"."""
    OTLog = frappe.qb.DocType("OT Log")
    return (frappe.qb.from_(OTLog).select("*").where(OTLog.is_cancelled == 0)).as_("ot")


def get_shift_type_details(shift):
    return frappe.db.get_value(
        "Shift Type",
        shift,
        [
            "shift_hours",
            "holiday_list",
            "start_time",
            "end_time",
            "early_exit_grace_period",
        ],
        as_dict=1,
    )


def get_checkins_by_attendance(
    employee, from_date_time, to_date_time, shift_start_time, is_night_shift
):
    """Return check-in count per attendance with its login date.

    For night shifts, a check-in before the shift start time belongs to the previous day.
    """
    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")

    if is_night_shift:
        login_date = IF(
            TIME(EmployeeCheckin.time) < shift_start_time,
            Date(EmployeeCheckin.time - timedelta(days=1)),
            Date(EmployeeCheckin.time),
        )
    else:
        login_date = Date(EmployeeCheckin.time)

    return (
        frappe.qb.from_(EmployeeCheckin)
        .select(
            login_date.as_("login_date"),
            EmployeeCheckin.attendance,
            Count(EmployeeCheckin.name).as_("cnt"),
        )
        .where(
            (EmployeeCheckin.time.between(from_date_time, to_date_time))
            & (EmployeeCheckin.employee == employee)
            & (EmployeeCheckin.attendance.isnotnull())
            & (EmployeeCheckin.attendance != "")
        )
        .groupby(EmployeeCheckin.attendance)
    ).run(as_dict=True)


def get_attendance_conditions(from_date, to_date, employee):
    """Return a list of QB conditions instead of raw SQL string."""
    Attendance = frappe.qb.DocType("Attendance")

    from_date = from_date or frappe.form_dict.get("from_date")
    to_date = to_date or frappe.form_dict.get("to_date")
    employee = employee or frappe.form_dict.get("employee")

    conditions = []

    if from_date and to_date:
        conditions.append(Attendance.attendance_date.between(from_date, to_date))
    if employee:
        conditions.append(Attendance.employee == employee)

    return conditions


def get_date_range(start_date, end_date):
    start_date = getdate(start_date)
    end_date = getdate(end_date)

    dates = []
    current_date = start_date

    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


@frappe.whitelist(allow_guest=True)
def employee_details(branch=None, company=None, department=None):
    company = frappe.form_dict.get("company")
    department = frappe.form_dict.get("department")
    branch = frappe.form_dict.get("branch")

    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(employee)
        .select(
            employee.name.as_("employee"),
            employee.employee_name,
            employee.company,
            employee.department,
            employee.default_shift.as_("shift"),
            employee.designation,
            employee.old_punch_id,
            employee.branch,
        )
        .where(employee.status == "Active")
    )

    if company:
        query = query.where(employee.company == company)
    if department:
        query = query.where(employee.department == department)
    if branch:
        query = query.where(employee.branch == branch)

    return query.run(as_dict=True)


def get_totals(data, employee):
    totals = {
        "employee": data[0].get("employee") if data else "Unknown",
        "employee_name": data[0].get("employee_name") if data else "Unknown",
        "company": data[0].get("company") if data else "Unknown",
        "department": data[0].get("department") if data else "Unknown",
        "designation": data[0].get("designation") if data else "Unknown",
        "old_punch_id": data[0].get("old_punch_id") if data else "Unknown",
        "net_wrk_hrs": timedelta(0),
        "spent_hours": timedelta(0),
        "late_hrs": timedelta(0),
        "early_hrs": timedelta(0),
        "p_out_hrs": timedelta(0),
        "ot_hours": timedelta(0),
        "total_pay_hrs": timedelta(0),
        "late_count": 0,
    }

    late_count = 0
    penalty_days = 0
    totals["shift_hours"] = 0.0
    half_day_count = 0
    shift = ""

    for row in data:
        totals["net_wrk_hrs"] += row.get("net_wrk_hrs") or timedelta(0)
        totals["total_pay_hrs"] += row.get("total_pay_hrs") or timedelta(0)
        totals["ot_hours"] += row.get("ot_hours") or timedelta(0)
        totals["early_hrs"] += row.get("early_hrs") or timedelta(0)
        totals["late_hrs"] += row.get("late_hrs") or timedelta(0)
        totals["p_out_hrs"] += row.get("p_out_hrs") or timedelta(0)
        totals["spent_hours"] += row.get("spent_hours") or timedelta(0)
        shift = row.get("shift_name")

        if row.get("late_entry"):
            late_count += 1
        if not totals["shift_hours"] and row.get("shift_hours"):
            totals["shift_hours"] = flt(row.get("shift_hours"))
        if row.get("lh"):
            half_day_count += 1

    totals["late_count"] = late_count
    totals["half_day_count"] = half_day_count

    half_day_shift_hours = frappe.db.get_value(
        "Shift Type", {"name": shift}, "working_hours_threshold_for_half_day"
    )
    totals["half_day_days"] = flt(
        (half_day_count * flt(half_day_shift_hours)) / flt(totals["shift_hours"] or 1),
        2,
    )

    if late_count > 4 and late_count < 10:
        penalty_days = 0.5
    if late_count >= 10 and late_count < 15:
        penalty_days = 1
    if late_count >= 15:
        penalty_days = 1.5

    conversion_factor = 3600 * flt(totals["shift_hours"])
    if conversion_factor <= 0:
        conversion_factor = 1

    employee_shift_info = (
        frappe.db.get_value(
            "Employee",
            employee,
            ["default_shift", "allowed_personal_hours"],
            as_dict=1,
        )
        or {}
    )
    shift_hour_value = frappe.db.get_value(
        "Shift Type",
        {"name": employee_shift_info.get("default_shift")},
        "shift_hours",
    ) or timedelta(0)
    if totals["shift_hours"]:
        penalty_hrs = timedelta(
            hours=flt(totals["shift_hours"]) * penalty_days
        ) or timedelta(0)
    else:
        penalty_hrs = timedelta(
            hours=flt(shift_hour_value) * penalty_days
        ) or timedelta(0)

    for key in [
        "net_wrk_hrs",
        "spent_hours",
        "late_hrs",
        "early_hrs",
        "p_out_hrs",
        "ot_hours",
        "total_pay_hrs",
    ]:
        totals[f"total_days_{key}"] = flt(
            totals[key].total_seconds() / conversion_factor, 2
        )

    allowed_personal_hours = employee_shift_info.get(
        "allowed_personal_hours"
    ) or timedelta(0)
    totals["refund"] = min(
        allowed_personal_hours,
        (totals["early_hrs"] + totals["late_hrs"] + totals["p_out_hrs"]),
    )
    totals["refund_days"] = flt(totals["refund"].total_seconds() / conversion_factor, 2)

    totals["penalty_days"] = penalty_days

    totals["net_pay_hrs"] = (
        totals["net_wrk_hrs"] + totals["ot_hours"] + totals["refund"] - penalty_hrs
    )
    totals["net_pay_days"] = flt(
        totals["net_pay_hrs"].total_seconds() / conversion_factor, 2
    )

    totals["net_pay_hrs_wo_ot"] = totals["net_wrk_hrs"] + totals["refund"] - penalty_hrs
    totals["net_pay_days_wo_ot"] = flt(
        totals["net_pay_hrs_wo_ot"].total_seconds() / conversion_factor, 2
    )

    return totals
