# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters=None):
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 220,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Attendance"),
            "fieldname": "attendance",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Last Check-in Date"),
            "fieldname": "last_checkin_date",
            "fieldtype": "Date",
            "width": 130
        }
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
    SELECT 
        e.employee AS employee,
        e.employee_name AS employee_name,
        e.department AS department,
        e.company AS company,
        e.designation AS designation,
        IF(ec_today.employee IS NOT NULL, 'Present', 'Absent') AS attendance,
        MAX(DATE(ec_last.time)) AS last_checkin_date
    FROM `tabEmployee` e
    LEFT JOIN `tabEmployee Checkin` ec_today 
        ON e.employee = ec_today.employee AND DATE(ec_today.time) = CURDATE()
    LEFT JOIN `tabEmployee Checkin` ec_last 
        ON e.employee = ec_last.employee
    {conditions}
    GROUP BY 
        e.employee, e.employee_name, e.department, e.company, e.designation
    HAVING 
        last_checkin_date IS NOT NULL
    ORDER BY 
        e.department ASC;
    """

    data = frappe.db.sql(query, as_dict=1)
    return data

def get_conditions(filters):
    filter_list = []

    if filters.get("company"):
        filter_list.append(f"""e.company = "{filters.get("company")}" """)

    if filters.get("from_date"):
        filter_list.append(f"""ec_last.time >= "{filters.get("from_date")}" """)

    if filters.get("to_date"):
        filter_list.append(f"""ec_last.time <= "{filters.get("to_date")}" """)

    if filters.get("department"):
        filter_list.append(f"""e.department = "{filters.get("department")}" """)

    if filters.get("designation"):
        filter_list.append(f"""e.designation = "{filters.get("designation")}" """)

    if filters.get("employee"):
        filter_list.append(f"""e.employee = "{filters.get("employee")}" """)

    # Construct the WHERE clause based on available filters
    conditions = ""
    if filter_list:
        conditions = "WHERE " + " AND ".join(filter_list)

    return conditions
