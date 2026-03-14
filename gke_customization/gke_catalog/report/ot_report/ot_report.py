from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day, date_diff, add_days
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.utils.holiday_list import get_holiday_dates_between
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


def get_payment_days_for_employee(employee, month_start, month_end):
    """
    Mirrors salary slip get_payment_days() logic:
    payment_days = date_diff(actual_end, actual_start) + 1 - holidays
    Accounts for joining date and relieving date.
    """
    emp = frappe.db.get_value(
        "Employee", employee,
        ["date_of_joining", "relieving_date", "status"],
        as_dict=True
    )

    month_start = getdate(month_start)
    month_end   = getdate(month_end)

    # Employee joined after the month ends — no payment days
    if emp.date_of_joining and getdate(emp.date_of_joining) > month_end:
        return 0

    # actual_start_date: max of month start and joining date
    actual_start = month_start
    if emp.date_of_joining and getdate(emp.date_of_joining) > month_start:
        actual_start = getdate(emp.date_of_joining)

    # actual_end_date: min of month end and relieving date
    actual_end = month_end
    if emp.relieving_date and getdate(emp.relieving_date) < month_end:
        actual_end = getdate(emp.relieving_date)

    # If relieving before month starts — no payment days
    if actual_end < actual_start:
        return 0

    payment_days = date_diff(actual_end, actual_start) + 1

    # Subtract holidays
    try:
        holiday_list = get_holiday_list_for_employee(employee)
        if holiday_list:
            holidays = get_holiday_dates_between(holiday_list, str(actual_start), str(actual_end))
            payment_days -= len(holidays)
    except Exception:
        pass

    return max(payment_days, 0)


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
        placeholders = ", ".join(["'{}'".format(d) for d in params["month_dates"]])
        month_filter_condition = "AND DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01')) IN ({})".format(placeholders)

    ot_group_by  = "DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))"
    att_group_by = "DATE(CONCAT(YEAR(attendance_date), '-', LPAD(MONTH(attendance_date), 2, '0'), '-01'))"

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
            IFNULL(st.shift_hours, 0)                                      AS `shift_hours`

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
        att_group_by=att_group_by,
        salary_slip_join=salary_slip_join,
        month_filter_condition=month_filter_condition,
        conditions=conditions,
    ), params, as_dict=True)

    # --- Post-process: calculate target_hours, total_working_hours, ot_amount ---
    data = []
    for row in rows:
        shift_hours   = row.shift_hours or 0
        ot_hrs        = row.ot or 0
        ctc           = row.gross_salary or 0
        ot_month_date = getdate(row.ot_month_date)

        # Month boundaries for this row
        month_start = get_first_day(ot_month_date)
        month_end   = get_last_day(ot_month_date)

        # Step 1: use ss.target_working_hours if available
        if row.ss_target_working_hours and row.ss_target_working_hours > 0:
            working_days = None  # not needed
            target_hours = row.ss_target_working_hours

        # Step 2: use ss.total_working_days * shift_hours
        elif row.ss_total_working_days and row.ss_total_working_days > 0:
            working_days = row.ss_total_working_days
            target_hours = working_days * shift_hours

        # Step 3: calculate payment_days using get_payment_days logic
        else:
            working_days = get_payment_days_for_employee(
                row.employee, month_start, month_end
            )
            target_hours = working_days * shift_hours

        # OT Amount = (CTC / target_hours) * OT Hours
        if target_hours and target_hours > 0 and ctc > 0:
            ot_amount = round((ctc / target_hours) * ot_hrs, 2)
        else:
            ot_amount = 0

        row.target_hours        = round(target_hours, 2)
        row.total_working_hours = round(target_hours + ot_hrs, 2)
        row.ot_amount           = ot_amount

        # Remove internal fields not needed in output
        row.pop("employee",                 None)
        row.pop("ot_month_date",            None)
        row.pop("ss_total_working_days",    None)
        row.pop("ss_target_working_hours",  None)
        row.pop("shift_hours",              None)

        data.append(row)

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
    month_str   = filters.get("month") or ""
    months_str  = filters.get("months") or ""
    from_date   = filters.get("from_date")
    to_date     = filters.get("to_date")
    ss_month    = None
    ss_year     = None
    month_dates = []

    # Priority 1: Single month
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

    # Priority 2: Multiple months
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

    # Priority 3: Date range
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
