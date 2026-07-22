# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_last_day


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# -----------------------------------
# Columns
# -----------------------------------
def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "pan_number",
            "label": _("PAN No"),
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "fieldname": "section",
            "label": _("Section"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "gross_pay",
            "label": _("Gross Pay"),
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "fieldname": "net_pay",
            "label": _("Net Pay"),
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "fieldname": "tds_amount",
            "label": _("TDS Amount"),
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "fieldname": "salary_without_tds",
            "label": _("Salary W/O TDS (Gross)"),
            "fieldtype": "Currency",
            "width": 180,
        },
    ]


# -----------------------------------
# Quarter Logic
# -----------------------------------
def get_quarter_dates(fiscal_year, quarter):

    start_year = int(fiscal_year.split("-")[0])
    end_year = start_year + 1

    if quarter == "Q1":
        return f"{start_year}-04-01", f"{start_year}-06-30"

    elif quarter == "Q2":
        return f"{start_year}-07-01", f"{start_year}-09-30"

    elif quarter == "Q3":
        return f"{start_year}-10-01", f"{start_year}-12-31"

    elif quarter == "Q4":
        return f"{end_year}-01-01", f"{end_year}-03-31"

    return None, None


# -----------------------------------
# Month Logic
# -----------------------------------
def get_month_dates(fiscal_year, month):

    start_year = int(fiscal_year.split("-")[0])
    end_year = start_year + 1

    month_map = {
        "April": (start_year, 4),
        "May": (start_year, 5),
        "June": (start_year, 6),
        "July": (start_year, 7),
        "August": (start_year, 8),
        "September": (start_year, 9),
        "October": (start_year, 10),
        "November": (start_year, 11),
        "December": (start_year, 12),
        "January": (end_year, 1),
        "February": (end_year, 2),
        "March": (end_year, 3),
    }

    if month not in month_map:
        return None, None

    year, month_no = month_map[month]

    first_day = f"{year}-{month_no:02d}-01"
    last_day = str(get_last_day(first_day))

    return first_day, last_day


# -----------------------------------
# Data
# -----------------------------------
def get_data(filters):

    conditions = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            ss.employee AS employee,
            ss.employee_name AS employee_name,
            e.pan_number AS pan_number,
            es.custom_tax_withholding_category AS section,

            SUM(ss.gross_pay) AS gross_pay,
            SUM(ss.net_pay) AS net_pay,

            SUM(COALESCE(es.amount, 0)) AS tds_amount,

            SUM(ss.gross_pay) - SUM(COALESCE(es.amount, 0))
                AS salary_without_tds

        FROM `tabSalary Slip` ss

        INNER JOIN `tabAdditional Salary` es
            ON ss.employee = es.employee

        LEFT JOIN `tabEmployee` e
            ON ss.employee = e.name

        WHERE
            ss.docstatus = 1

            AND es.payroll_date BETWEEN %(from_date)s AND %(to_date)s

            AND es.salary_component LIKE '%%Income%%'

            AND es.custom_reason_for_additional_salary LIKE '%%TDS%%'

            {conditions}

        GROUP BY
            ss.employee,
            ss.employee_name,
            e.pan_number,
            es.custom_tax_withholding_category

        HAVING
            SUM(COALESCE(es.amount,0)) <> 0

        ORDER BY
            ss.employee
        """,
        filters,
        as_dict=True,
    )


    # -----------------------------------
    # Total Row
    # -----------------------------------
    if data:

        total_row = {
            "employee": "Total",
            "employee_name": "",
            "pan_number": "",
            "section": "",

            "gross_pay": sum(
                row.gross_pay or 0 for row in data
            ),

            "net_pay": sum(
                row.net_pay or 0 for row in data
            ),

            "tds_amount": sum(
                row.tds_amount or 0 for row in data
            ),

            "salary_without_tds": sum(
                row.salary_without_tds or 0 for row in data
            ),
        }

        data.append(total_row)


    return data



# -----------------------------------
# Filters
# -----------------------------------
def get_conditions(filters):

    conditions = []

    fiscal_year = filters.get("fiscal_year")

    from_date = None
    to_date = None


    # Month priority
    if filters.get("month"):

        from_date, to_date = get_month_dates(
            fiscal_year,
            filters.get("month")
        )


    # Quarter priority
    elif filters.get("quarter"):

        from_date, to_date = get_quarter_dates(
            fiscal_year,
            filters.get("quarter")
        )


    # Full Fiscal Year
    elif fiscal_year:

        start_year = int(fiscal_year.split("-")[0])
        end_year = start_year + 1

        from_date = f"{start_year}-04-01"
        to_date = f"{end_year}-03-31"


    if from_date and to_date:

        filters["from_date"] = from_date
        filters["to_date"] = to_date


    # Employee filter
    if filters.get("employee"):

        conditions.append(
            "AND ss.employee = %(employee)s"
        )


    # Company filter
    if filters.get("company"):

        conditions.append(
            "AND ss.company = %(company)s"
        )


    return " ".join(conditions)