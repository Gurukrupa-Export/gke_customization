import frappe
from frappe.utils import cint

def execute(filters=None):
    if not filters:
        filters = {}

    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("ss.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("ss.branch = %(branch)s")
        values["branch"] = filters.get("branch")

    if filters.get("employee"):
        conditions.append("ss.employee = %(employee)s")
        values["employee"] = filters.get("employee")

    # Custom date filter replacing year and month filters
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("ss.start_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters.get("from_date")
        values["to_date"] = filters.get("to_date")
    elif filters.get("from_date"):
        conditions.append("ss.start_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    elif filters.get("to_date"):
        conditions.append("ss.start_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    # Updated hold status filter to work with status field instead of custom field
    if filters.get("hold_status") == "Yes":
        conditions.append("ss.status = 'Withheld'")
    elif filters.get("hold_status") == "No":
        conditions.append("ss.status = 'Submitted'")

    # Only include submitted salary slips and show Submitted/Withheld status
    conditions.append("ss.docstatus = 1")
    conditions.append("ss.status IN ('Submitted', 'Withheld')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            ss.employee,
            ss.employee_name,
            ss.company,
            ss.branch,
            MONTHNAME(ss.start_date) AS month_name,
            YEAR(ss.start_date) AS year,
            ss.gross_pay,
            ss.total_deduction,
            ss.net_pay,
            ss.status AS status,
            ss.name AS salary_slip_code,
            IF(ss.status = 'Withheld', 'Yes', 'No') AS withheld,
            DATE_FORMAT(ss.start_date, '%%m/%%Y') AS date
        FROM
            `tabSalary Slip` ss
        WHERE
            {where_clause}
        ORDER BY
            ss.start_date DESC, ss.employee
    """

    data = frappe.db.sql(query, values, as_dict=True)

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": "Month", "fieldname": "month_name", "fieldtype": "Data", "width": 90},
        {"label": "Year", "fieldname": "year", "fieldtype": "Int", "width": 80},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 120},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Salary Slip Code", "fieldname": "salary_slip_code", "fieldtype": "Link", "options": "Salary Slip", "width": 180},
        {"label": "Withheld", "fieldname": "withheld", "fieldtype": "Data", "width": 80},
        {"label": "Date (Month/Year)", "fieldname": "date", "fieldtype": "Data", "width": 100},
    ]

    return columns, data
