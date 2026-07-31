from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, flt, add_months, get_first_day, get_last_day
from datetime import datetime, timedelta


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
        {"label": "OT Hours",            "fieldname": "ot_hours",            "fieldtype": "Float",    "width": 80},
        {"label": "Target Hours",        "fieldname": "target_hours",        "fieldtype": "Float",    "width": 110},
        {"label": "Total Working Hours", "fieldname": "total_working_hours", "fieldtype": "Float",    "width": 160},
        {"label": "OT Amount",           "fieldname": "ot_amount",           "fieldtype": "Currency", "width": 120},
    ]


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
    mode        = "date_range"

    if month_str:
        try:
            parsed   = datetime.strptime(month_str, "%b %Y")
            ss_month = parsed.month
            ss_year  = parsed.year
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


def td_to_secs(td):
    if td is None:
        return 0
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    return 0


def get_time_secs(t):
    if t is None:
        return None
    if hasattr(t, 'total_seconds'):
        return t.total_seconds()
    if hasattr(t, 'hour'):
        return t.hour * 3600 + t.minute * 60 + t.second
    return None


def get_data(filters):
    params     = get_params(filters)
    conditions = get_conditions(filters)
    mode       = params.get("mode")
    from_date  = params.get("from_date")
    to_date    = params.get("to_date")

    # ── Salary Slip join: include Draft (0) AND Submitted (1) ──
    if mode == "single_month":
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         IN (0, 1)
                AND MONTH(ss.start_date) = %(ss_month)s
                AND YEAR(ss.start_date)  = %(ss_year)s
        """
    else:
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         IN (0, 1)
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
            COALESCE(NULLIF(e.branch, ''), 'N/A')                         AS `branch`,
            e.employee_name                                                AS `emp_name`,
            e.old_punch_id                                                 AS `punch_id`,
            COALESCE(NULLIF(e.custom_operation, ''), 'N/A')               AS `main_department`,
            e.department                                                   AS `department`,
            e.designation                                                  AS `designation`,
            IFNULL(ss.net_pay, 0)                                          AS `salary`,
            IFNULL(e.ctc, 0)                                               AS `gross_salary`,
            IFNULL(ss.target_working_hours, 0)                             AS `ss_target_working_hours`,
            IFNULL(ss.actual_working_hours, 0)                             AS `ss_actual_working_hours`,
            IFNULL(ss.extra_working_hours, 0)                              AS `ss_extra_working_hours`,
            IFNULL(st.shift_hours, 0)                                      AS `default_shift_hours`,
            e.holiday_list                                                 AS `holiday_list`,
            e.date_of_joining                                              AS `date_of_joining`,
            e.relieving_date                                               AS `relieving_date`

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

    # ── Batch fetch attendance (with per-row shift details) ──
    att_rows_all = frappe.db.sql(f"""
        SELECT
            at.employee,
            at.attendance_date,
            at.working_hours,
            at.out_time,
            at.shift                    AS att_shift_name,
            st.shift_hours              AS att_shift_hours,
            st.end_time                 AS att_shift_end
        FROM `tabAttendance` at
        LEFT JOIN `tabShift Type` st ON st.name = at.shift
        WHERE at.docstatus = 1
        AND at.attendance_date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    att_map = {}
    for r in att_rows_all:
        att_map.setdefault(r['employee'], []).append(r)

    # ── Batch fetch OT Logs ──
    ot_log_rows = frappe.db.sql(f"""
        SELECT
            employee,
            DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01')) AS ot_month_date,
            SUM(TIME_TO_SEC(attn_ot_hrs)) / 3600.0 AS total_ot_hrs
        FROM `tabOT Log`
        WHERE is_cancelled = 0
        AND attn_ot_hrs > 0
        AND attendance_date BETWEEN '{from_date}' AND '{to_date}'
        GROUP BY employee,
            DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))
    """, as_dict=1)

    ot_log_map = {}
    for r in ot_log_rows:
        ot_log_map[(r['employee'], str(r['ot_month_date']))] = flt(r['total_ot_hrs'])

    # ── Batch fetch holidays ──
    holiday_rows = frappe.db.sql(f"""
        SELECT parent AS holiday_list, holiday_date
        FROM `tabHoliday`
        WHERE holiday_date BETWEEN '{from_date}' AND '{to_date}'
    """, as_dict=1)

    holidays_map = {}
    for r in holiday_rows:
        holidays_map.setdefault(r['holiday_list'], set()).add(r['holiday_date'])

    OT_GRACE_SECS = 1800

    data = []
    for row in rows:
        employee      = row['employee']
        ot_month_date = getdate(row['ot_month_date'])
        month_start   = get_first_day(ot_month_date)
        month_end     = get_last_day(ot_month_date)
        ctc           = flt(row['gross_salary'] or 0)

        all_att   = att_map.get(employee, [])
        month_att = [
            r for r in all_att
            if month_start <= r['attendance_date'] <= month_end
        ]

        # ── Total Working Hours = SUM(attendance.working_hours) ──
        # att.working_hours already includes OT time for all employees
        total_working_hours = round(
            sum(flt(r.get('working_hours') or 0) for r in month_att), 2
        )

        # ── OT Hours: MAX(OT Log, attendance-derived) ──
        ot_log_hrs = ot_log_map.get((employee, str(row['ot_month_date'])), 0)

        att_ot_secs = 0.0
        for r in month_att:
            row_end_s = td_to_secs(r.get('att_shift_end'))
            out_s     = get_time_secs(r.get('out_time'))
            if out_s is not None and row_end_s > 0:
                extra = out_s - row_end_s
                if extra > OT_GRACE_SECS:
                    att_ot_secs += extra

        att_ot_hrs = flt(att_ot_secs / 3600, 2)
        ot_hours   = round(max(ot_log_hrs, att_ot_hrs), 2)

        # ── Target Hours ──
        ss_target = flt(row['ss_target_working_hours'] or 0)

        if ss_target > 0:
            # Path 1: Salary Slip exists (Draft or Submitted) — use ss.target_working_hours
            target_hours = ss_target

        else:
            # Path 2: No Salary Slip — compute from payment days × dominant shift hours

            # Dominant shift_hours from attendance this month
            shift_count = {}
            for r in month_att:
                sn = r.get('att_shift_name')
                sh = flt(r.get('att_shift_hours') or 0)
                if sn and sh > 0:
                    if sn not in shift_count:
                        shift_count[sn] = {'count': 0, 'shift_hours': sh}
                    shift_count[sn]['count'] += 1

            if shift_count:
                dominant  = max(shift_count.items(), key=lambda x: x[1]['count'])
                shift_hrs = dominant[1]['shift_hours']
            else:
                shift_hrs = flt(row['default_shift_hours'] or 0) or 10.0

            # Clamp period to DOJ / relieving date
            doj          = row.get('date_of_joining')
            rd           = row.get('relieving_date')
            actual_start = month_start
            actual_end   = month_end

            if doj and getdate(doj) > month_start:
                actual_start = getdate(doj)
            if rd and getdate(rd) < month_end:
                actual_end = getdate(rd)

            # Subtract holidays within clamped period
            holiday_list  = row.get('holiday_list') or ''
            holiday_dates = holidays_map.get(holiday_list, set())
            month_holidays = {
                d for d in holiday_dates
                if actual_start <= d <= actual_end
            }

            total_days   = (actual_end - actual_start).days + 1
            payment_days = sum(
                1 for i in range(total_days)
                if (actual_start + timedelta(days=i)) not in month_holidays
            )
            target_hours = round(flt(payment_days * shift_hrs), 2)

        # ── OT Amount ──
        if target_hours > 0 and ctc > 0 and ot_hours > 0:
            ot_amount = round((ctc / target_hours) * ot_hours, 2)
        else:
            ot_amount = 0

        data.append({
            "month":               row['month'],
            "company":             row['company'],
            "branch":              row['branch'],
            "emp_name":            row['emp_name'],
            "punch_id":            row['punch_id'],
            "main_department":     row['main_department'],
            "department":          row['department'],
            "designation":         row['designation'],
            "salary":              row['salary'],
            "gross_salary":        ctc,
            "ot_hours":            ot_hours,
            "target_hours":        round(flt(target_hours), 2),
            "total_working_hours": total_working_hours,
            "ot_amount":           ot_amount,
        })

    return data
