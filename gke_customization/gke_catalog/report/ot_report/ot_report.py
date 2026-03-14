from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, flt, add_months, get_first_day, get_last_day, date_diff, add_days
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.utils.holiday_list import get_holiday_dates_between
from datetime import datetime

OT_GRACE_SECS = 1800  # 30 minutes — minimum extra time to qualify as OT


def execute(filters=None):
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


@frappe.whitelist()
def get_month_range():
    months = []
    today  = getdate()
    for i in range(24):
        d = add_months(today, -i)
        months.append(d.strftime("%b %Y"))
    return months


def get_columns():
    return [
        {"label": "Month",               "fieldname": "month",               "fieldtype": "Data",     "width": 90},
        {"label": "Company",             "fieldname": "company",             "fieldtype": "Data",     "width": 140},
        {"label": "Branch",              "fieldname": "branch",              "fieldtype": "Data",     "width": 140},
        {"label": "Name",                "fieldname": "emp_name",            "fieldtype": "Data",     "width": 220},
        {"label": "Punch ID",            "fieldname": "punch_id",            "fieldtype": "Data",     "width": 100},
        {"label": "Main Department",     "fieldname": "main_department",     "fieldtype": "Data",     "width": 180},
        {"label": "Department",          "fieldname": "department",          "fieldtype": "Data",     "width": 180},
        {"label": "Designation",         "fieldname": "designation",         "fieldtype": "Data",     "width": 160},
        {"label": "Salary",              "fieldname": "salary",              "fieldtype": "Currency", "width": 120},
        {"label": "Gross Salary",        "fieldname": "gross_salary",        "fieldtype": "Currency", "width": 120},
        {"label": "OT Hours",            "fieldname": "ot",                  "fieldtype": "Float",    "width": 80},
        {"label": "Target Hours",        "fieldname": "target_hours",        "fieldtype": "Float",    "width": 110},
        {"label": "Total Working Hours", "fieldname": "total_working_hours", "fieldtype": "Float",    "width": 160},
        {"label": "OT Amount",           "fieldname": "ot_amount",           "fieldtype": "Currency", "width": 120},
    ]


# ─────────────────────────────────────────────
# BATCH PRE-FETCHERS
# ─────────────────────────────────────────────

def get_all_salary_slips_for_rows(rows):
    if not rows:
        return {}

    combos = set()
    for row in rows:
        ot_month_date = getdate(row.ot_month_date)
        combos.add((row.employee, ot_month_date.month, ot_month_date.year))

    if not combos:
        return {}

    where_parts = " OR ".join([
        f"(ss.employee = '{emp}' AND MONTH(ss.start_date) = {m} AND YEAR(ss.start_date) = {y})"
        for emp, m, y in combos
    ])

    slips = frappe.db.sql(f"""
        SELECT
            employee,
            MONTH(start_date)          AS slip_month,
            YEAR(start_date)           AS slip_year,
            actual_working_hours,
            target_working_hours,
            extra_working_hours,
            total_working_days,
            shift_hours                AS ss_shift_hours,
            ctc,
            net_pay,
            gross_pay,
            base_gross_pay
        FROM `tabSalary Slip` ss
        WHERE ss.docstatus = 1
        AND ({where_parts})
    """, as_dict=1)

    result = {}
    for s in slips:
        key = (s['employee'], int(s['slip_month']), int(s['slip_year']))
        result[key] = s
    return result


def get_all_ot_logs_batch(from_date, to_date):
    """Batch fetch OT logs grouped by employee + month using attn_ot_hrs."""
    rows = frappe.db.sql(f"""
        SELECT
            employee,
            DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01')) AS ot_month_date,
            attendance_date,
            attn_ot_hrs
        FROM `tabOT Log`
        WHERE is_cancelled = 0
        AND attendance_date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    # {(employee, month_date): {att_date: secs}}
    result = {}
    for r in rows:
        key      = (r['employee'], r['ot_month_date'])
        att_date = r['attendance_date']
        secs     = r['attn_ot_hrs'].total_seconds() if r['attn_ot_hrs'] else 0
        result.setdefault(key, {})
        result[key][att_date] = result[key].get(att_date, 0) + secs
    return result


def get_all_attendance_batch(from_date, to_date):
    """Batch fetch attendance with shift info for all employees."""
    rows = frappe.db.sql(f"""
        SELECT
            at.employee,
            at.attendance_date,
            at.working_hours,
            at.status,
            at.in_time,
            at.out_time,
            at.late_entry,
            at.early_exit,
            at.leave_type,
            st.shift_hours      AS att_shift_hours,
            st.start_time,
            st.end_time,
            st.early_exit_grace_period
        FROM `tabAttendance` at
        LEFT JOIN `tabEmployee` emp ON at.employee = emp.name
        LEFT JOIN `tabShift Type` st ON emp.default_shift = st.name
        WHERE at.docstatus = 1
        AND at.attendance_date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    result = {}
    for r in rows:
        result.setdefault(r['employee'], []).append(r)
    return result


def get_all_personal_out_logs_batch(from_date, to_date):
    rows = frappe.db.sql(f"""
        SELECT employee, date, total_hours
        FROM `tabPersonal Out Log`
        WHERE is_cancelled = 0
        AND date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    result = {}
    for r in rows:
        emp  = r['employee']
        dt   = r['date']
        secs = r['total_hours'].total_seconds() if r['total_hours'] else 0
        result.setdefault(emp, {})
        result[emp][dt] = result[emp].get(dt, 0) + secs
    return result


def get_all_leave_applications_batch(from_date, to_date):
    rows = frappe.db.sql(f"""
        SELECT
            la.employee,
            la.leave_type,
            la.from_date,
            la.to_date,
            la.total_leave_days,
            lt.is_ppl
        FROM `tabLeave Application` la
        LEFT JOIN `tabLeave Type` lt ON la.leave_type = lt.name
        WHERE la.docstatus = 1
        AND la.status = 'Approved'
        AND lt.is_ppl = 1
        AND (
            la.from_date BETWEEN '{from_date}' AND '{to_date}'
            OR la.to_date BETWEEN '{from_date}' AND '{to_date}'
            OR (la.from_date < '{from_date}' AND la.to_date > '{to_date}')
        )
    """, as_dict=1)

    result = {}
    for r in rows:
        result.setdefault(r['employee'], []).append(r)
    return result


def get_all_holidays_batch(from_date, to_date):
    rows = frappe.db.sql(f"""
        SELECT parent AS holiday_list, holiday_date, weekly_off
        FROM `tabHoliday`
        WHERE holiday_date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    result = {}
    for r in rows:
        result.setdefault(r['holiday_list'], []).append(r)
    return result


def get_all_employee_meta(employee_list):
    if not employee_list:
        return {}

    placeholders = ", ".join([f"'{e}'" for e in employee_list])
    rows = frappe.db.sql(f"""
        SELECT
            name,
            holiday_list,
            date_of_joining,
            relieving_date,
            allowed_personal_hours
        FROM `tabEmployee`
        WHERE name IN ({placeholders})
    """, as_dict=1)

    return {r['name']: r for r in rows}


def get_all_ssa_bases(employee_list):
    if not employee_list:
        return {}

    placeholders = ", ".join([f"'{e}'" for e in employee_list])
    rows = frappe.db.sql(f"""
        SELECT employee, base
        FROM `tabSalary Structure Assignment`
        WHERE docstatus = 1
        AND employee IN ({placeholders})
        ORDER BY from_date DESC
    """, as_dict=1)

    result = {}
    for r in rows:
        if r['employee'] not in result:
            result[r['employee']] = flt(r['base'])
    return result


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def td_to_secs(td):
    if td is None:
        return 0
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    return 0


def get_time_secs(t):
    """Convert in_time / out_time (timedelta or datetime) to seconds since midnight."""
    if t is None:
        return None
    if hasattr(t, 'total_seconds'):
        return t.total_seconds()
    if hasattr(t, 'hour'):
        return t.hour * 3600 + t.minute * 60 + t.second
    return None


# ─────────────────────────────────────────────
# FALLBACK CALCULATOR
# ─────────────────────────────────────────────

def calculate_working_hours_fallback(
    employee,
    month_start,
    month_end,
    shift_hours,
    shift_start_td,
    shift_end_td,
    early_exit_grace,
    total_working_days,
    attendance_rows,
    ot_log_map,
    pol_map,
    leave_apps,
    holidays,
    allowed_personal_hours_td,
    date_of_joining,
    relieving_date,
):
    shift_hours      = flt(shift_hours) or 10.0
    shift_start_secs = td_to_secs(shift_start_td)
    shift_end_secs   = td_to_secs(shift_end_td)

    # Clip to DOJ / relieving date
    actual_start = getdate(month_start)
    actual_end   = getdate(month_end)
    if date_of_joining:
        doj = getdate(date_of_joining)
        if getdate(month_start) < doj <= getdate(month_end):
            actual_start = doj
    if relieving_date:
        rd = getdate(relieving_date)
        if getdate(month_start) <= rd < getdate(month_end):
            actual_end = rd

    # Classify holidays
    non_weekly_holiday_dates = {
        h['holiday_date'] for h in holidays
        if not h.get('weekly_off') and actual_start <= h['holiday_date'] <= actual_end
    }
    weekly_off_dates = {
        h['holiday_date'] for h in holidays
        if h.get('weekly_off') and actual_start <= h['holiday_date'] <= actual_end
    }

    # LWP leave types
    lwp_leave_types = set(frappe.db.get_all(
        "Leave Type", filters={"is_lwp": 1}, pluck="name"
    ) or [])

    # PPL leave hours
    leave_hours = 0.0
    for la in leave_apps:
        la_from    = max(getdate(la['from_date']), actual_start)
        la_to      = min(getdate(la['to_date']), actual_end)
        days       = date_diff(la_to, la_from) + 1 if date_diff(la_to, la_from) >= 0 else 0
        leave_hours = leave_hours + (days * shift_hours)

    # Holiday hours (non-weekly, not attended)
    attendance_dates        = {r['attendance_date'] for r in attendance_rows}
    non_attended_holidays   = [d for d in non_weekly_holiday_dates if d not in attendance_dates]
    holiday_hours           = len(non_attended_holidays) * shift_hours

    # Per-day accumulators
    total_net_wrk_secs  = 0.0
    totals_ot_secs      = 0.0          # from OT Log
    totals_att_ot_secs  = 0.0          # from attendance out_time > shift_end (NEW)
    totals_late_secs    = 0.0
    totals_early_secs   = 0.0
    totals_p_out_secs   = 0.0
    total_late_marks    = 0

    for row in attendance_rows:
        att_date    = row['attendance_date']
        if att_date < actual_start or att_date > actual_end:
            continue

        in_time     = row.get('in_time')
        out_time    = row.get('out_time')
        working_hrs = flt(row.get('working_hours') or 0)
        late_entry  = int(row.get('late_entry') or 0)
        early_exit  = int(row.get('early_exit') or 0)
        leave_type  = row.get('leave_type')
        status      = row.get('status')

        p_out_secs       = pol_map.get(att_date, 0)
        totals_p_out_secs = totals_p_out_secs + p_out_secs

        in_s  = get_time_secs(in_time)
        out_s = get_time_secs(out_time)

        # ── Attendance-derived OT (NEW) ──────────────────────────
        # If out_time is available and employee stayed beyond shift_end
        att_ot_secs = 0.0
        if out_s is not None and shift_end_secs > 0:
            extra_secs = out_s - shift_end_secs
            if extra_secs > OT_GRACE_SECS:          # more than 30 mins
                att_ot_secs = extra_secs
        totals_att_ot_secs = totals_att_ot_secs + att_ot_secs
        # ─────────────────────────────────────────────────────────

        # ── Regular working hours (capped at shift_end) ──────────
        if status == 'On Leave' and leave_type and leave_type not in lwp_leave_types:
            net_secs = shift_hours * 3600

        elif working_hrs == 0.0:
            net_secs = 0.0

        elif early_exit_grace and not early_exit:
            if in_s is not None:
                late_secs        = max(0, in_s - shift_start_secs)
                totals_late_secs = totals_late_secs + late_secs
                net_secs         = (shift_hours * 3600) - late_secs - p_out_secs
            else:
                net_secs = (shift_hours * 3600) - p_out_secs

        else:
            if out_s is not None and in_s is not None:
                spent_secs = out_s - in_s

                # Cap at shift_end — extra time beyond shift already captured as att_ot_secs
                if out_s > shift_end_secs:
                    spent_secs = spent_secs - (out_s - shift_end_secs)

                if not late_entry and in_s > shift_start_secs:
                    spent_secs = spent_secs + (in_s - shift_start_secs)
                if in_s < shift_start_secs:
                    spent_secs = spent_secs - (shift_start_secs - in_s)

                spent_secs = spent_secs - p_out_secs
                net_secs   = spent_secs
            else:
                net_secs = working_hrs * 3600 - p_out_secs

            if in_s is not None and late_entry:
                totals_late_secs = totals_late_secs + max(0, in_s - shift_start_secs)

            if out_s is not None and early_exit:
                totals_early_secs = totals_early_secs + max(0, shift_end_secs - out_s)

        total_net_wrk_secs = total_net_wrk_secs + max(0, net_secs)
        total_late_marks   = total_late_marks + late_entry

        # OT from OT Log for this day
        if att_date in (ot_log_map or {}):
            totals_ot_secs = totals_ot_secs + ot_log_map[att_date]

    # OT on weekly offs and non-weekly holidays (OT Log only — no attendance cap logic)
    for dt in weekly_off_dates:
        if dt in (ot_log_map or {}):
            totals_ot_secs = totals_ot_secs + ot_log_map[dt]
    for dt in non_weekly_holiday_dates:
        if dt in (ot_log_map or {}):
            totals_ot_secs = totals_ot_secs + ot_log_map[dt]

    # ── Final OT: OT Log takes priority, attendance-derived as fallback ──
    # Take MAX so whichever is higher wins
    final_ot_secs = max(totals_ot_secs, totals_att_ot_secs)

    netwrk_hrs           = flt(total_net_wrk_secs / 3600, 2)
    actual_working_hours = flt(netwrk_hrs + leave_hours + holiday_hours, 2)

    # Late mark penalty
    if total_late_marks:
        late_mark_matrix = {0: 0, 1: 5, 2: 10, 3: 15}
        no_of_late_marks = total_late_marks // 5
        late_count       = late_mark_matrix.get(no_of_late_marks, 15) / 10
        actual_working_hours = actual_working_hours - flt(late_count * shift_hours, 2)

    # Refund hours
    allowed_ph  = flt(td_to_secs(allowed_personal_hours_td) / 3600, 2) if allowed_personal_hours_td else 0
    late_hrs    = flt(totals_late_secs / 3600, 2)
    early_hrs   = flt(totals_early_secs / 3600, 2)
    p_out_hrs   = flt(totals_p_out_secs / 3600, 2)
    refund_hrs  = min(allowed_ph, flt(late_hrs + early_hrs + p_out_hrs, 2))

    actual_working_hours = flt(actual_working_hours + refund_hrs, 2)
    ot_hours             = flt(final_ot_secs / 3600, 2)
    target_working_hours = flt(shift_hours * total_working_days, 2)

    return actual_working_hours, target_working_hours, ot_hours


# ─────────────────────────────────────────────
# ORIGINAL HELPERS
# ─────────────────────────────────────────────

def get_payment_days_for_employee(employee, month_start, month_end):
    emp = frappe.db.get_value(
        "Employee", employee,
        ["date_of_joining", "relieving_date", "status"],
        as_dict=True
    )

    month_start = getdate(month_start)
    month_end   = getdate(month_end)

    if emp.date_of_joining and getdate(emp.date_of_joining) > month_end:
        return 0

    actual_start = month_start
    if emp.date_of_joining and getdate(emp.date_of_joining) > month_start:
        actual_start = getdate(emp.date_of_joining)

    actual_end = month_end
    if emp.relieving_date and getdate(emp.relieving_date) < month_end:
        actual_end = getdate(emp.relieving_date)

    if actual_end < actual_start:
        return 0

    payment_days = date_diff(actual_end, actual_start) + 1

    try:
        holiday_list = get_holiday_list_for_employee(employee)
        if holiday_list:
            holidays = get_holiday_dates_between(holiday_list, str(actual_start), str(actual_end))
            payment_days = payment_days - len(holidays)
    except Exception:
        pass

    return max(payment_days, 0)


# ─────────────────────────────────────────────
# MAIN get_data
# ─────────────────────────────────────────────

def get_data(filters):
    params     = get_params(filters)
    conditions = get_conditions(filters)
    mode       = params.get("mode")

    if mode == "single_month":
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         = 1
                AND MONTH(ss.start_date) = %(ss_month)s
                AND YEAR(ss.start_date)  = %(ss_year)s
        """
    else:
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         = 1
                AND MONTH(ss.start_date) = MONTH(ot.ot_month_date)
                AND YEAR(ss.start_date)  = YEAR(ot.ot_month_date)
        """

    month_filter_condition = ""
    if mode == "multi_month" and params.get("month_dates"):
        placeholders           = ", ".join(["'{}'".format(d) for d in params["month_dates"]])
        month_filter_condition = "AND DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01')) IN ({})".format(placeholders)

    ot_group_by = "DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))"

    rows = frappe.db.sql("""
        SELECT
            CONCAT(
                CASE MONTH(ot.ot_month_date)
                    WHEN 1  THEN 'Jan' WHEN 2  THEN 'Feb' WHEN 3  THEN 'Mar'
                    WHEN 4  THEN 'Apr' WHEN 5  THEN 'May' WHEN 6  THEN 'Jun'
                    WHEN 7  THEN 'Jul' WHEN 8  THEN 'Aug' WHEN 9  THEN 'Sep'
                    WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                END,
                ' ', YEAR(ot.ot_month_date)
            )                                                              AS `month`,

            e.name                                                         AS `employee`,
            ot.ot_month_date                                               AS `ot_month_date`,
            e.company                                                      AS `company`,
            COALESCE(NULLIF(e.branch, ''), '')                             AS `branch`,
            e.employee_name                                                AS `emp_name`,
            e.old_punch_id                                                 AS `punch_id`,
            COALESCE(NULLIF(e.custom_operation, ''), 'N/A')               AS `main_department`,
            e.department                                                   AS `department`,
            e.designation                                                  AS `designation`,
            IFNULL(ss.net_pay, 0)                                          AS `salary`,
            IFNULL(e.ctc, 0)                                               AS `gross_salary`,
            ROUND(ot.total_ot_hrs, 2)                                      AS `ot`,
            IFNULL(ss.total_working_days, 0)                               AS `ss_total_working_days`,
            IFNULL(ss.target_working_hours, 0)                             AS `ss_target_working_hours`,
            IFNULL(ss.actual_working_hours, 0)                             AS `ss_actual_working_hours`,
            IFNULL(ss.extra_working_hours, 0)                              AS `ss_extra_working_hours`,
            IFNULL(st.shift_hours, 0)                                      AS `shift_hours`,
            IFNULL(st.start_time, NULL)                                    AS `shift_start`,
            IFNULL(st.end_time, NULL)                                      AS `shift_end`,
            IFNULL(st.early_exit_grace_period, 0)                         AS `early_exit_grace`

        FROM `tabEmployee` e

        INNER JOIN (
            SELECT
                employee,
                {ot_group_by}                          AS ot_month_date,
                SUM(TIME_TO_SEC(attn_ot_hrs)) / 3600.0 AS total_ot_hrs
            FROM `tabOT Log`
            WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
              AND is_cancelled = 0
              AND attn_ot_hrs  > 0
              {month_filter_condition}
            GROUP BY
                employee,
                {ot_group_by}
        ) ot ON ot.employee = e.name

        LEFT JOIN `tabShift Type` st
            ON st.name = e.default_shift

        {salary_slip_join}

        LEFT JOIN `tabDepartment` d
            ON d.name = e.department

        WHERE
            e.status = 'Active'
            {conditions}

        ORDER BY
            ot.ot_month_date,
            e.branch,
            e.custom_operation,
            e.department,
            e.employee_name

    """.format(
        ot_group_by=ot_group_by,
        salary_slip_join=salary_slip_join,
        month_filter_condition=month_filter_condition,
        conditions=conditions,
    ), params, as_dict=True)

    if not rows:
        return []

    from_date    = params.get("from_date")
    to_date      = params.get("to_date")
    employee_ids = list({r['employee'] for r in rows})

    emp_meta_map  = get_all_employee_meta(employee_ids)
    ssa_base_map  = get_all_ssa_bases(employee_ids)
    att_map       = get_all_attendance_batch(from_date, to_date)
    pol_map_batch = get_all_personal_out_logs_batch(from_date, to_date)
    leave_map     = get_all_leave_applications_batch(from_date, to_date)
    holidays_map  = get_all_holidays_batch(from_date, to_date)
    ot_logs_batch = get_all_ot_logs_batch(from_date, to_date)

    data = []
    for row in rows:
        shift_hours   = flt(row.shift_hours or 0) or 10.0
        ot_hrs        = flt(row.ot or 0)
        ctc           = flt(row.gross_salary or 0)
        ot_month_date = getdate(row.ot_month_date)
        month_start   = get_first_day(ot_month_date)
        month_end     = get_last_day(ot_month_date)
        employee      = row.employee

        has_salary_slip = (
            row.ss_target_working_hours and flt(row.ss_target_working_hours) > 0
        ) or (
            row.ss_actual_working_hours and flt(row.ss_actual_working_hours) > 0
        )

        if has_salary_slip:
            # ── Path 1: Salary Slip exists ──
            actual_working_hours = flt(row.ss_actual_working_hours or 0)
            target_working_hours = flt(row.ss_target_working_hours or 0)

            if not target_working_hours:
                if row.ss_total_working_days:
                    target_working_hours = flt(row.ss_total_working_days) * shift_hours
                else:
                    target_working_hours = get_payment_days_for_employee(
                        employee, month_start, month_end
                    ) * shift_hours

            # Use ss.extra_working_hours if available, else fallback
            if flt(row.ss_extra_working_hours) > 0:
                ot_hrs = flt(row.ss_extra_working_hours)
            else:
                # ── Path 1 OT fallback: MAX(ot_log, attendance_derived) ──
                ot_log_map  = ot_logs_batch.get((employee, row.ot_month_date), {})
                ot_log_secs = sum(ot_log_map.values())

                all_att_rows   = att_map.get(employee, [])
                month_att_rows = [
                    r for r in all_att_rows
                    if month_start <= r['attendance_date'] <= month_end
                ]
                shift_end_secs = td_to_secs(row.shift_end)
                att_ot_secs    = 0.0
                for r in month_att_rows:
                    out_s = get_time_secs(r.get('out_time'))
                    if out_s is not None and shift_end_secs > 0:
                        extra = out_s - shift_end_secs
                        if extra > OT_GRACE_SECS:
                            att_ot_secs = att_ot_secs + extra

                ot_hrs = flt(max(ot_log_secs, att_ot_secs) / 3600, 2)

        else:
            # ── Path 2: No Salary Slip — full fallback ──
            emp_meta     = emp_meta_map.get(employee, {})
            holiday_list = emp_meta.get('holiday_list') or ''
            holidays     = holidays_map.get(holiday_list, [])

            month_holidays = [
                h for h in holidays
                if month_start <= h['holiday_date'] <= month_end
            ]

            holiday_dates_this_month = {h['holiday_date'] for h in month_holidays}
            total_days_in_month      = date_diff(month_end, month_start) + 1
            total_working_days       = sum(
                1 for i in range(total_days_in_month)
                if add_days(month_start, i) not in holiday_dates_this_month
            )

            all_att_rows   = att_map.get(employee, [])
            month_att_rows = [
                r for r in all_att_rows
                if month_start <= r['attendance_date'] <= month_end
            ]

            ot_log_map = ot_logs_batch.get((employee, row.ot_month_date), {})
            pol_emp    = pol_map_batch.get(employee, {})
            pol_month  = {
                dt: secs for dt, secs in pol_emp.items()
                if month_start <= dt <= month_end
            }

            actual_working_hours, target_working_hours, ot_hrs = calculate_working_hours_fallback(
                employee                  = employee,
                month_start               = month_start,
                month_end                 = month_end,
                shift_hours               = shift_hours,
                shift_start_td            = row.shift_start,
                shift_end_td              = row.shift_end,
                early_exit_grace          = flt(row.early_exit_grace or 0),
                total_working_days        = total_working_days,
                attendance_rows           = month_att_rows,
                ot_log_map                = ot_log_map,
                pol_map                   = pol_month,
                leave_apps                = leave_map.get(employee, []),
                holidays                  = month_holidays,
                allowed_personal_hours_td = emp_meta.get('allowed_personal_hours'),
                date_of_joining           = emp_meta.get('date_of_joining'),
                relieving_date            = emp_meta.get('relieving_date'),
            )

            if not ctc:
                ctc = flt(ssa_base_map.get(employee) or 0)

        # ── OT Amount ──
        if target_working_hours > 0 and ctc > 0 and ot_hrs > 0:
            ot_amount = round((ctc / target_working_hours) * ot_hrs, 2)
        else:
            ot_amount = 0

        row.target_hours        = round(flt(target_working_hours), 2)
        row.total_working_hours = round(flt(actual_working_hours) + flt(ot_hrs), 2)
        row.ot                  = round(flt(ot_hrs), 2)
        row.ot_amount           = ot_amount

        row.pop("employee",                None)
        row.pop("ot_month_date",           None)
        row.pop("ss_total_working_days",   None)
        row.pop("ss_target_working_hours", None)
        row.pop("ss_actual_working_hours", None)
        row.pop("ss_extra_working_hours",  None)
        row.pop("shift_hours",             None)
        row.pop("shift_start",             None)
        row.pop("shift_end",               None)
        row.pop("early_exit_grace",        None)

        data.append(row)

    return data


# ─────────────────────────────────────────────
# CONDITIONS / PARAMS
# ─────────────────────────────────────────────

def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("AND e.company = %(company)s")
    if filters.get("branch"):
        conditions.append("AND e.branch = %(branch)s")
    if filters.get("department"):
        conditions.append("AND e.department = %(department)s")
    if filters.get("employee"):
        conditions.append("AND e.name = %(employee)s")

    return " ".join(conditions)


def get_params(filters):
    month_str   = filters.get("month") or ""
    months_str  = filters.get("months") or ""
    from_date   = filters.get("from_date")
    to_date     = filters.get("to_date")
    ss_month    = None
    ss_year     = None
    month_dates = []

    if month_str:
        try:
            parsed    = datetime.strptime(month_str, "%b %Y")
            ss_month  = parsed.month
            ss_year   = parsed.year
            from_date = get_first_day(parsed).strftime("%Y-%m-%d")
            to_date   = get_last_day(parsed).strftime("%Y-%m-%d")
            mode      = "single_month"
        except Exception:
            mode = "date_range"

    elif months_str:
        selected_months = [m.strip() for m in months_str.split(",") if m.strip()]
        parsed_months   = []
        for m in selected_months:
            try:
                parsed_months.append(datetime.strptime(m, "%b %Y"))
            except Exception:
                pass

        if parsed_months:
            parsed_months.sort()
            from_date   = get_first_day(parsed_months[0]).strftime("%Y-%m-%d")
            to_date     = get_last_day(parsed_months[-1]).strftime("%Y-%m-%d")
            month_dates = [d.strftime("%Y-%m-01") for d in parsed_months]
            mode        = "multi_month"
        else:
            mode = "date_range"

    else:
        mode = "date_range"

    if not from_date:
        from_date = "2025-04-01"
    if not to_date:
        to_date = getdate().strftime("%Y-%m-%d")

    return {
        "company":     filters.get("company"),
        "branch":      filters.get("branch"),
        "department":  filters.get("department"),
        "employee":    filters.get("employee"),
        "from_date":   from_date,
        "to_date":     to_date,
        "ss_month":    ss_month,
        "ss_year":     ss_year,
        "mode":        mode,
        "month_dates": month_dates,
    }
