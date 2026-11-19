from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.query_builder import CustomFunction, Interval
from frappe.query_builder.functions import Concat, Count, Date, IfNull, Max, Min, Sum
from frappe.utils import add_days, flt, format_time, get_datetime, get_time, getdate
from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import (
    get_checkins,  # type: ignore
)

STATUS = {
    "Absent": "A",
    "Present": "P",
    "Half Day": "HD",
    "Privilege Leave": "PL",
    "Casual Leave": "CL",
    "Sick Leave": "SL",
    "Leave Without Pay": "LWP",
    "Outdoor Duty": "OD",
    "Work From Home": "WFH",
    "Maternity Leave": "ML",
}


@frappe.whitelist(allow_guest=True)
def attendance(from_date=None, to_date=None, employee=None):
    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    ShiftType = frappe.qb.DocType("Shift Type")
    PersonalOutLog = frappe.qb.DocType("Personal Out Log")
    OTLog = frappe.qb.DocType("OT Log")

    conditions = get_conditions(from_date, to_date, employee)

    TIME_FORMAT = CustomFunction("TIME_FORMAT", ["time", "format"])
    TIMEDIFF = CustomFunction("TIMEDIFF", ["time1", "time2"])
    SEC_TO_TIME = CustomFunction("SEC_TO_TIME", ["seconds"])
    TIME_TO_SEC = CustomFunction("TIME_TO_SEC", ["time"])
    IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])
    TIMESTAMP = CustomFunction("TIMESTAMP", ["date", "time"])
    TIME = CustomFunction("TIME", ["time"])
    ADDDATE = CustomFunction("ADDDATE", ["date", "days"])

    # Personal Out Log subquery
    pol_subquery = (
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

    # OT Log subquery
    ot_subquery = (
        frappe.qb.from_(OTLog).select("*").where(OTLog.is_cancelled == 0)
    ).as_("ot")

    # SHIFT WINDOW -- New Added
    shift_start = TIMESTAMP(Attendance.attendance_date, ShiftType.start_time)

    shift_end = IF(
        ShiftType.start_time < ShiftType.end_time,
        TIMESTAMP(Attendance.attendance_date, ShiftType.end_time),
        TIMESTAMP(ADDDATE(Attendance.attendance_date, 1), ShiftType.end_time),
    )

    effective_in = IF(Attendance.in_time < shift_start, shift_start, Attendance.in_time)

    effective_out = IF(Attendance.out_time > shift_end, shift_end, Attendance.out_time)

    # Main Query
    query = (
        frappe.qb.from_(Attendance)
        .left_join(Employee)
        .on(Attendance.employee == Employee.name)
        .left_join(ShiftType)
        .on(Attendance.shift == ShiftType.name)
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
            (Attendance.shift).as_("shift_name"),
            Concat(
                TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"),
                " TO ",
                TIME_FORMAT(ShiftType.end_time, "%H:%i:%s"),
            ).as_("shift"),
            TIME(Attendance.in_time).as_("in_time"),
            TIME(Attendance.out_time).as_("out_time"),
            SEC_TO_TIME(
                IF(
                    Attendance.out_time.isnull(),
                    0,
                    TIME_TO_SEC(
                        TIMEDIFF(
                            IF(
                                Attendance.out_time < Attendance.in_time,
                                TIMESTAMP(
                                    ADDDATE(Date(Attendance.in_time), 1),
                                    TIME(Attendance.out_time),
                                ),
                                Attendance.out_time,
                            ),
                            Attendance.in_time,
                        )
                    ),
                )
            ).as_("spent_hours"),
            Attendance.late_entry,
            IF(
                Attendance.late_entry,
                TIMEDIFF(
                    Attendance.in_time,
                    TIMESTAMP(Attendance.attendance_date, ShiftType.start_time),
                ),
                None,
            ).as_("late_hrs"),
            IF(
                Attendance.early_exit,
                TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)),
                None,
            ).as_("early_hrs"),
            pol_subquery.hrs.as_("p_out_hrs"),
            SEC_TO_TIME(
                IfNull(
                    TIME_TO_SEC(TIMEDIFF(effective_out, effective_in))
                    - IfNull(TIME_TO_SEC(pol_subquery.hrs), 0),
                    0,
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
        .where((Attendance.docstatus == 1))
        .orderby(Attendance.attendance_date, order=frappe.qb.asc)
    )

    for condition in conditions:
        query = query.where(condition)

    data = query.run(as_dict=1)

    if not data:
        data = []

    data = process_data(data, from_date, to_date, employee)

    return data


def get_conditions(from_date, to_date, employee):
    """Return a list of QB conditions instead of raw SQL string."""
    Attendance = frappe.qb.DocType("Attendance")

    # fallback to frappe.form_dict if not passed explicitly
    from_date = from_date or frappe.form_dict.get("from_date")
    to_date = to_date or frappe.form_dict.get("to_date")
    employee = employee or frappe.form_dict.get("employee")

    conditions = []

    if from_date and to_date:
        conditions.append(Attendance.attendance_date.between(from_date, to_date))
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
            "branch",
        ],
        as_dict=1,
    )

    shift = ""
    for sh in data:
        shift = sh.shift_name
    if not shift:
        shift = emp_det.get("default_shift")

    shift_det = frappe.db.get_value(
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
    if not shift_det:
        frappe.throw(_("No Shift found for Employee {0}").format(employee))
    shift_hours = flt(shift_det.get("shift_hours"))
    grace_period = shift_det.get("early_exit_grace_period")

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    addition_day = add_days(to_date, 1)

    from_date_time = get_datetime(from_date)
    to_date_time = get_datetime(f"{addition_day} 23:59:59")

    shift_start_time = get_time(shift_det.get("start_time"))
    is_night_shift = shift_start_time > get_time(shift_det.get("end_time"))

    all_checkins = frappe.get_all(
        "Employee Checkin",
        {"employee": employee, "time": ["between", [from_date_time, to_date_time]]},
        ["time", "log_type"],
        order_by="time asc",
    )
    # Night-shift punches before the shift start belong to the previous day's shift
    checkin_time_map = {}
    for row in all_checkins:
        login_date = getdate(row.time)
        if is_night_shift and get_time(row.time) < shift_start_time:
            login_date = add_days(login_date, -1)
        checkin_time_map.setdefault(login_date, []).append(row)

    TIME = CustomFunction("TIME", ["time"])
    IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])

    if is_night_shift:
        login_date_expr = IF(
            TIME(EmployeeCheckin.time) < shift_det.get("start_time"),
            Date(EmployeeCheckin.time - Interval(days=1)),
            Date(EmployeeCheckin.time),
        )
    else:
        login_date_expr = Date(EmployeeCheckin.time)

    checkins = (
        frappe.qb.from_(EmployeeCheckin)
        .select(
            login_date_expr.as_("login_date"),
            EmployeeCheckin.attendance,
            Count(EmployeeCheckin.name).as_("cnt"),
            Min(EmployeeCheckin.time).as_("first_in"),
            Max(EmployeeCheckin.time).as_("last_out"),
        )
        .where(
            (EmployeeCheckin.time.between(from_date_time, to_date_time))
            & (EmployeeCheckin.employee == employee)
            & (EmployeeCheckin.attendance.isnotnull())
            & (EmployeeCheckin.attendance != "")
        )
        .groupby(EmployeeCheckin.attendance)
    ).run(as_dict=True)

    # convert to dict keyed by date
    checkins = {row.login_date: row for row in checkins}

    od = frappe.db.sql(
        """
			SELECT DATE(time) as login_date
			FROM `tabEmployee Checkin`
			WHERE employee = %(employee)s
				AND source = 'Outdoor Duty'
				AND time BETWEEN %(from_date)s AND %(to_date)s
			GROUP BY DATE(time)
		""",
        {"employee": employee, "from_date": from_date, "to_date": add_days(to_date, 1)},
        pluck="login_date",
    )
    if shift and not emp_det.get("holiday_list"):
        emp_det["holiday_list"] = shift_det.get("holiday_list")

    if hl_name := emp_det.get("holiday_list"):
        holidays = frappe.db.sql(
            """
				SELECT holiday_date, weekly_off
				FROM `tabHoliday`
				WHERE parent = %(hl_name)s
					AND holiday_date BETWEEN %(from_date)s AND %(to_date)s
			""",
            {"hl_name": hl_name, "from_date": from_date, "to_date": to_date},
            as_dict=1,
        )
        wo = [row.holiday_date for row in holidays if row.weekly_off]
        holidays = [row.holiday_date for row in holidays if not row.weekly_off]

    date_of_joining = (
        getdate(emp_det.get("date_of_joining"))
        if emp_det.get("date_of_joining")
        else None
    )

    leave_type_flags = {
        lt.name: lt
        for lt in frappe.get_all(
            "Leave Type",
            filters={"name": ["in", [s for s in {row.status for row in data} if s]]},
            fields=["name", "is_earned_leave", "max_continuous_days_allowed", "is_lwp"],
        )
    }
    default_shift_name = emp_det.get("default_shift")
    default_shift_det = (
        frappe.db.get_value(
            "Shift Type",
            default_shift_name,
            ["shift_hours", "start_time", "end_time"],
            as_dict=1,
        )
        if default_shift_name
        else None
    )

    shift_det_by_date = {}
    for row in data:
        # for security grace period 45 min
        if flt(grace_period):
            if not (row.early_hrs):
                if row.status == "Absent":
                    row.net_wrk_hrs = timedelta(0)
                    row.total_pay_hrs = timedelta(0)
                elif row.status == "Leave Without Pay":
                    # FIXED: Force LWP to 0 hours
                    row.net_wrk_hrs = timedelta(0)
                    row.total_pay_hrs = timedelta(0)
                elif row.late_hrs or row.p_out_hrs:
                    late = row.late_hrs or timedelta(0)
                    p_out = row.p_out_hrs or timedelta(0)
                    total = late + p_out

                    row.net_wrk_hrs = timedelta(hours=shift_hours) - total
                    row.total_pay_hrs = timedelta(0)
                else:
                    row.net_wrk_hrs = timedelta(hours=shift_hours)
                    row.total_pay_hrs = row.net_wrk_hrs + (row.ot_hours or timedelta(0))

        if row.lh:
            row.status = "LH"
        shift_hours_in_sec = ""
        if row.shift_hours:
            shift_hours_in_sec = row.shift_hours * 3600
            if (
                row.net_wrk_hrs.total_seconds() > shift_hours_in_sec
                or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60
            ):
                row.net_wrk_hrs = timedelta(hours=row.shift_hours)
        else:
            row_shift_det = default_shift_det or shift_det
            shift_det_by_date[row.attendance_date] = row_shift_det
            row_shift_hours = flt(row_shift_det.get("shift_hours"))
            row.shift = f"{format_time(row_shift_det.get('start_time'))} To {format_time(row_shift_det.get('end_time'))}"

            lt = leave_type_flags.get(row.status)
            leave_status = lt.name if lt and lt.is_earned_leave else None
            e_leave_status = (
                lt.name if lt and flt(lt.max_continuous_days_allowed) > 0 else None
            )

            # FIXED: Check if LWP specifically
            is_lwp = lt.name if lt and lt.is_lwp else None

            if is_lwp:
                # Force LWP to 0 hours
                row.status = STATUS.get(row.status) or row.status
                row.net_wrk_hrs = timedelta(0)
            elif leave_status or e_leave_status:
                row.status = leave_status or e_leave_status
                row.net_wrk_hrs = timedelta(hours=row_shift_hours)
            else:
                row.net_wrk_hrs = timedelta(0)

        row["total_pay_hrs"] = row.net_wrk_hrs + (row.get("ot_hours") or timedelta(0))
        row.status = STATUS.get(row.status) or row.status
        processed[row.attendance_date] = row

    ot_logs = frappe.get_all(
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
            "allow",
        ],
    )
    ot_for_wo = {}
    ot_details_map = {}
    for ot_log in ot_logs:
        allow = ot_log.pop("allow")
        ot_for_wo[ot_log.attendance_date] = ot_log
        if allow == 1:
            ot_details_map[ot_log.attendance_date] = {
                "hrs": ot_log.ot_hours,
                "allow": allow,
            }
    date_range = get_date_range(from_date, to_date)

    # Check-ins already linked to an Attendance, used to hide previous-shift punches on WO days
    linked_checkin_ids = set()
    if wo:
        linked_checkin_ids = set(
            frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "time": ["between", [add_days(from_date_time, -1), to_date_time]],
                    "attendance": ["is", "set"],
                },
                pluck="name",
            )
        )

    for date in date_range:
        row = processed.get(date, ot_for_wo.get(date, {}))

        day_shift_det = shift_det_by_date.get(date, shift_det)
        day_shift_hours = flt(day_shift_det.get("shift_hours"))

        times = checkin_time_map.get(date, [])
        in_times = []
        out_times = []

        for idx, checkin in enumerate(times):
            punch_time = get_time(checkin.time).strftime("%H:%M:%S")
            if checkin.log_type == "IN" or (not checkin.log_type and idx % 2 == 0):
                in_times.append(punch_time)
            else:
                out_times.append(punch_time)

        tin_time_str = ", ".join(in_times) if in_times else None
        out_time_str = ", ".join(out_times) if out_times else None

        # Attendance not available, but check-in exists
        if not row and date in checkins:
            ci = checkins[date]
            is_error = ci.cnt % 2 != 0  # odd punches → missing OUT

            # If odd punch count, OUT is not valid
            if is_error:
                out_time = None
            else:
                out_time = get_time(ci.last_out) if ci.last_out else None

            row = frappe._dict(
                {
                    "attendance_date": date,
                    "in_time": tin_time_str,
                    "out_time": out_time_str,
                    "spent_hours": None
                    if not out_time
                    else (ci.last_out - ci.first_in),
                    "net_wrk_hrs": timedelta(0),
                    "total_pay_hrs": timedelta(0),
                    "status": "ERR",
                }
            )

        # No attendance and no check-in, fall back to OT Log
        if not row:
            row = ot_for_wo.get(date, {})

        status = row.get("status") or "XX"

        # Odd check-in count is an error, but WO/Holiday handling below can clear it
        has_checkin_error = False
        if cii := checkins.get(date):
            if cii.cnt % 2 != 0:
                has_checkin_error = True

        if date in od:
            status = "OD"
            date_time = datetime.combine(
                getdate(date), get_time(day_shift_det.start_time)
            )
            if first_in_last_out := get_checkins(employee, date_time):
                row["in_time"] = get_time(first_in_last_out[0].get("time"))
                row["out_time"] = get_time(first_in_last_out[-1].get("time"))
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours
            else:
                row["total_pay_hrs"] = row.get("total_pay_hrs") or timedelta(0)
        elif date in wo and (not date_of_joining or date >= date_of_joining):
            status = "WO"  # weekly off
            date_time = datetime.combine(
                getdate(date), get_time(day_shift_det.start_time)
            )

            # Get check-ins for this WO date
            # Note: get_checkins() may return check-ins from previous day's night shift
            # that ended on this WO date (e.g., 31-Jan 19:59 IN, 01-Feb 08:00 OUT)
            if first_in_last_out := get_checkins(employee, date_time):
                # Filter check-ins by checking if they have a linked Attendance record
                # Check-ins WITH attendance field: belong to a previous shift (e.g., 31-Jan night shift)
                # Check-ins WITHOUT attendance field: likely incomplete OT work on WO day
                for ci in first_in_last_out:
                    # Check if this check-in is linked to an Attendance record
                    if ci.get("employee_checkin") in linked_checkin_ids:
                        # This check-in belongs to a previous shift's attendance record
                        # Don't show times to avoid confusion (previous shift's data)
                        has_checkin_error = (
                            False  # No error - it's from a valid previous attendance
                        )
                        row["in_time"] = ""
                        row["out_time"] = ""
                    else:
                        # This check-in has no attendance record (incomplete OT work on WO)
                        # Show the check-in times for review
                        row["in_time"] = get_time(first_in_last_out[0].get("time"))
                        row["out_time"] = get_time(first_in_last_out[-1].get("time"))
            else:
                # No check-ins found for this WO date - clean WO
                has_checkin_error = False

            # Add OT hours if OT Log exists (created 1-2 days after work)
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours
            row["status"] = status
        elif (date in holidays) and (not date_of_joining or date >= date_of_joining):
            if row.get("status") in ["LWP", "PL", "CL", "SL", "ML", "WFH"]:
                pass
            else:
                status = "H"
                row["net_wrk_hrs"] = timedelta(hours=day_shift_hours)
                row["total_pay_hrs"] = timedelta(hours=day_shift_hours)
        else:
            status = "XX"

        if has_checkin_error:
            row["status"] = "ERR"
            row["net_wrk_hrs"] = timedelta(0)
            row["total_pay_hrs"] = timedelta(0)

        # ------------------------------------------------------------------
        # STEP 3: Resolve OT hours for this date
        # ------------------------------------------------------------------

        # Default predefined OT from OT Details (if exists & approved)
        predefined_ot_hrs = None
        ot_detail = ot_details_map.get(date)

        if ot_detail and ot_detail.get("allow") == 1 and row.get("ot_hours"):
            predefined_ot_hrs = row.get("ot_hours")

        # CASE 1 rows hold comma-joined out times, use only the last one
        last_out_time = row.get("out_time")
        if isinstance(last_out_time, str):
            last_out_time = last_out_time.split(",")[-1].strip() or None

        ot_hours, ot_status = resolve_ot_hours(
            attendance_date=date,
            shift_end_time=get_time(day_shift_det.end_time),
            out_time=last_out_time,
            threshold_min=30,
            predefined_hrs=predefined_ot_hrs,
        )

        # Apply resolved OT to row
        row["ot_hours"] = ot_hours
        row["ot_status"] = ot_status

        temp = {
            "login_date": date,
            "shift": f"{format_time(day_shift_det.get('start_time'))} To {format_time(day_shift_det.get('end_time'))}",
            "status": status,
            "employee": employee,
            "employee_name": emp_det.get("employee_name"),
            "company": emp_det.get("company"),
            "branch": emp_det.get("branch"),
            "department": emp_det.get("department"),
            "designation": emp_det.get("designation"),
            "old_punch_id": emp_det.get("old_punch_id"),
            "middle_name": emp_det.get("middle_name"),
            "gender": emp_det.get("gender"),
            "date_of_birth": emp_det.get("date_of_birth"),
            "date_of_joining": emp_det.get("date_of_joining"),
            "allowed_personal_hours": emp_det.get("allowed_personal_hours"),
            "attendance_date": date,
            "shift_hours": day_shift_hours,
        }
        if not row.get("spent_hours"):
            row["spent_hours"] = None

        # --------------------------------------------------
        # GLOBAL OVERRIDE: Show comma-separated IN/OUT
        # for EVERY date if multiple check-ins exist
        # --------------------------------------------------
        if len(times) > 1:
            row["in_time"] = tin_time_str
            row["out_time"] = out_time_str

        temp.update(row)
        result.append(temp)
    return result


def get_date_range(start_date, end_date):
    import datetime

    start_date = getdate(start_date)
    end_date = getdate(end_date)

    date_range = []
    delta = datetime.timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        date_range.append(current_date)
        current_date += delta

    return date_range


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


def resolve_ot_hours(
    attendance_date, shift_end_time, out_time, threshold_min=30, predefined_hrs=None
):
    """
    Resolve OT hours using frappe utilities.

    Priority:
    1. Predefined OT hours (Approved)
    2. Auto-calculated OT (shift end + threshold)
    """

    # Approved OT (from OT Details or OT Log)
    if predefined_hrs:
        return predefined_hrs, "Approved"

    # Missing data → no OT
    if not attendance_date or not shift_end_time or not out_time:
        return None, ""

    # Normalize values using frappe utils
    attendance_date = getdate(attendance_date)
    shift_end_time = get_time(shift_end_time)
    out_time = get_time(out_time)

    # Build datetime safely
    shift_end_dt = get_datetime(f"{attendance_date} {shift_end_time}")
    out_dt = get_datetime(f"{attendance_date} {out_time}")

    # If employee left before or at shift end → NO OT
    if out_dt <= shift_end_dt:
        return None, ""

    diff = out_dt - shift_end_dt

    # Threshold check
    if diff < timedelta(minutes=threshold_min):
        return None, ""

    # Valid OT
    return diff, "Pending"
