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
        {"label": "Branch",              "fieldname": "branch",              "fieldtype": "Data",     "width": 140},
        {"label": "Name",                "fieldname": "emp_name",            "fieldtype": "Data",     "width": 220},
        {"label": "Punch ID",            "fieldname": "punch_id",            "fieldtype": "Data",     "width": 100},
        {"label": "Main Department",     "fieldname": "main_department",     "fieldtype": "Data",     "width": 180},
        {"label": "Department",          "fieldname": "department",          "fieldtype": "Data",     "width": 180},
        {"label": "Designation",         "fieldname": "designation",         "fieldtype": "Data",     "width": 160},
        {"label": "Salary",              "fieldname": "salary",              "fieldtype": "Currency", "width": 120},
        {"label": "Gross Salary",        "fieldname": "gross_salary",        "fieldtype": "Currency", "width": 120},
        {"label": "OT",                  "fieldname": "ot",                  "fieldtype": "Float",    "width": 80},
        {"label": "Target Hours",        "fieldname": "target_hours",        "fieldtype": "Float",    "width": 110},
        {"label": "Total Working Hours", "fieldname": "total_working_hours", "fieldtype": "Float",    "width": 160},
    ]


def get_data(filters):
    params     = get_params(filters)
    conditions = get_conditions(filters)
    month_mode = params.get("month_mode")  # True = single month, False = date range

    if month_mode:
        # Salary slip joined on exact month + year
        salary_slip_join = """
            LEFT JOIN `tabSalary Slip` ss
                ON  ss.employee          = e.name
                AND ss.docstatus         = 1
                AND MONTH(ss.start_date) = %(ss_month)s
                AND YEAR(ss.start_date)  = %(ss_year)s
        """
    else:
        # Salary slip joined across the full date range — any slip that overlaps
        salary_slip_join = """
            LEFT JOIN (
                SELECT
                    employee,
                    SUM(net_pay)              AS net_pay,
                    MAX(target_working_hours) AS target_working_hours,
                    NULL                      AS start_date
                FROM `tabSalary Slip`
                WHERE docstatus   = 1
                  AND start_date >= %(from_date)s
                  AND end_date   <= %(to_date)s
                GROUP BY employee
            ) ss ON ss.employee = e.name
        """

    data = frappe.db.sql("""
        SELECT
            COALESCE(
                DATE_FORMAT(ss.start_date, '%%b %%Y'),
                ot.ot_month
            )                                                              AS `month`,

            COALESCE(NULLIF(e.branch, ''), 'Head Office')                 AS `branch`,
            e.employee_name                                                AS `emp_name`,
            e.old_punch_id                                                 AS `punch_id`,
            COALESCE(NULLIF(e.custom_operation, ''), 'N/A')               AS `main_department`,
            d.department_name                                              AS `department`,
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
            , 2)                                                           AS `total_working_hours`

        FROM `tabEmployee` e

        INNER JOIN (
            SELECT
                employee,
                DATE_FORMAT(MIN(attendance_date), '%%b %%Y') AS ot_month,
                SUM(TIME_TO_SEC(attn_ot_hrs)) / 3600.0       AS total_ot_hrs
            FROM `tabOT Log`
            WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
              AND is_cancelled = 0
              AND attn_ot_hrs  > 0
            GROUP BY employee
        ) ot ON ot.employee = e.name

        LEFT JOIN (
            SELECT
                employee,
                COUNT(name) AS working_days
            FROM `tabAttendance`
            WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
              AND docstatus = 1
              AND status NOT IN ('Absent', 'On Leave')
            GROUP BY employee
        ) att ON att.employee = e.name

        LEFT JOIN `tabShift Type` st
            ON st.name = e.default_shift

        {salary_slip_join}

        LEFT JOIN `tabDepartment` d
            ON d.name = e.department

        WHERE
            e.status = 'Active'
            {conditions}

        ORDER BY
            e.branch,
            e.custom_operation,
            d.department_name,
            e.employee_name
    """.format(
        salary_slip_join=salary_slip_join,
        conditions=conditions
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
    month_str = filters.get("month") or ""
    from_date = filters.get("from_date")
    to_date   = filters.get("to_date")

    # Determine mode: month filter takes priority if filled
    if month_str:
        try:
            parsed   = datetime.strptime(month_str, "%b %Y")
            ss_month = parsed.month
            ss_year  = parsed.year
            # Override from/to date to match the selected month exactly
            from_date = get_first_day(parsed).strftime("%Y-%m-%d")
            to_date   = get_last_day(parsed).strftime("%Y-%m-%d")
            month_mode = True
        except Exception:
            month_mode = False
            ss_month   = None
            ss_year    = None
    else:
        month_mode = False
        ss_month   = None
        ss_year    = None

    # Fall back to current month if neither month nor date range provided
    if not from_date:
        from_date = get_first_day(getdate()).strftime("%Y-%m-%d")
    if not to_date:
        to_date = get_last_day(getdate()).strftime("%Y-%m-%d")

    return {
        "company":    filters.get("company"),
        "branch":     filters.get("branch"),
        "department": filters.get("department"),
        "employee":   filters.get("employee"),
        "from_date":  from_date,
        "to_date":    to_date,
        "ss_month":   ss_month,
        "ss_year":    ss_year,
        "month_mode": month_mode,
    }
