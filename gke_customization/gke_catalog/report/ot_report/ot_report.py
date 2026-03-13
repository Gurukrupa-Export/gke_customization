from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day
from datetime import datetime


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


def get_data(filters):
    params     = get_params(filters)
    conditions = get_conditions(filters)
    mode       = params.get("mode")  # "single_month" | "multi_month" | "date_range"

    # Salary slip join depends on mode
    if mode == "single_month":
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         = 1
                AND MONTH(ss.start_date) = %(ss_month)s
                AND YEAR(ss.start_date)  = %(ss_year)s
        """
    else:
        # multi_month and date_range: match salary slip per row's month
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         = 1
                AND MONTH(ss.start_date) = MONTH(ot.ot_month_date)
                AND YEAR(ss.start_date)  = YEAR(ot.ot_month_date)
        """

    # For multi_month mode, add an IN clause on ot month dates
    month_filter_condition = ""
    if mode == "multi_month" and params.get("month_dates"):
        placeholders = ", ".join(["'{}'".format(d) for d in params["month_dates"]])
        month_filter_condition = "AND DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01')) IN ({})".format(placeholders)

    ot_group_by  = "DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))"
    att_group_by = "DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))"

    data = frappe.db.sql("""
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

            ROUND(
                COALESCE(
                    NULLIF(ss.target_working_hours, 0),
                    att.working_days * st.shift_hours
                ), 2
            )                                                              AS `target_hours`,

            ROUND(
                COALESCE(
                    NULLIF(ss.target_working_hours, 0),
                    att.working_days * st.shift_hours
                ) + IFNULL(ot.total_ot_hrs, 0)
            , 2)                                                           AS `total_working_hours`,

            ROUND(
                CASE
                    WHEN NULLIF(att.working_days, 0) IS NOT NULL
                     AND NULLIF(st.shift_hours, 0)   IS NOT NULL
                     AND NULLIF(e.ctc, 0)            IS NOT NULL
                    THEN
                        (e.ctc / (att.working_days * st.shift_hours)) * ot.total_ot_hrs
                    ELSE 0
                END
            , 2)                                                           AS `ot_amount`

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

        LEFT JOIN (
            SELECT
                employee,
                {att_group_by}  AS att_month_date,
                COUNT(name)     AS working_days
            FROM `tabAttendance`
            WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
              AND docstatus = 1
              {month_filter_condition}
            GROUP BY
                employee,
                {att_group_by}
        ) att
            ON  att.employee       = e.name
            AND att.att_month_date = ot.ot_month_date

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
        att_group_by=att_group_by,
        salary_slip_join=salary_slip_join,
        month_filter_condition=month_filter_condition,
        conditions=conditions,
    ), params, as_dict=True)

    return data


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
    month_str    = filters.get("month") or ""        # single month  e.g. "Feb 2026"
    months_str   = filters.get("months") or ""       # multi month   e.g. "Jan 2026,Feb 2026,Mar 2026"
    from_date    = filters.get("from_date")
    to_date      = filters.get("to_date")
    ss_month     = None
    ss_year      = None
    month_dates  = []

    # --- Priority 1: Single month selected ---
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

    # --- Priority 2: Multiple months selected ---
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
            # from_date = first day of earliest month
            # to_date   = last day of latest month
            from_date   = get_first_day(parsed_months[0]).strftime("%Y-%m-%d")
            to_date     = get_last_day(parsed_months[-1]).strftime("%Y-%m-%d")
            # Build list of first-of-month dates for IN clause
            month_dates = [d.strftime("%Y-%m-01") for d in parsed_months]
            mode        = "multi_month"
        else:
            mode = "date_range"

    # --- Priority 3: Date range ---
    else:
        mode = "date_range"

    # Default: April 2025 to today if nothing provided
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
