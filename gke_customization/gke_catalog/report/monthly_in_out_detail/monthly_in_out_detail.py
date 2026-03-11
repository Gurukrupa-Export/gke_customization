# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_data(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")
    department = filters.get("department")
    branch = filters.get("branch")
    employee = filters.get("employee")

    if not (from_date and to_date and company and department):
        frappe.msgprint(_("Please select Company, Department, From Date and To Date"))
        return []

    conditions = [
        "mil.company = %s",
        "mil.department = %s", 
        "mil.attendance_date BETWEEN %s AND %s"
    ]
    params = [company, department, from_date, to_date]

    if branch:
        conditions.append("emp.branch = %s")
        params.append(branch)

    # **HIERARCHY LOGIC**: Manager + Direct Reportees
    if employee:
        # Get manager + employees who report directly to him
        reportees_query = """
            SELECT name FROM `tabEmployee` 
            WHERE (name = %s OR reports_to = %s)
        """
        reportees = frappe.db.sql(reportees_query, [employee, employee])
        employee_names = [r[0] for r in reportees]
        
        if employee_names:
            placeholders = ", ".join(["%s"] * len(employee_names))
            conditions.append(f"mil.employee IN ({placeholders})")
            params.extend(employee_names)
    else:
        conditions.append("1=1")  # No employee filter

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            mil.name AS id,
            mil.employee AS employee,
            mil.employee_name AS employee_name,
            emp.branch AS branch,
            mil.department AS department,
            emp.designation AS designation,
            mil.company AS company,
            mil.attendance_date AS attendance_date,
            mil.shit_type AS shift_type,
            mil.shift_hours AS shift_hours,
            mil.status AS status,
            mil.in_time AS in_time,
            mil.out_time AS out_time,
            mil.spent_hrs AS spent_hrs,
            mil.net_wrk_hrs AS net_wrk_hrs,
            mil.p_out_hrs AS p_out_hrs,
            mil.late_hrs AS late_hrs,
            mil.early_hrs AS early_hrs,
            mil.ot_hrs AS ot_hrs
        FROM
            `tabMonthly In-Out Log` mil
        LEFT JOIN `tabEmployee` emp ON mil.employee = emp.name
        WHERE {where_clause}
        ORDER BY
            mil.attendance_date DESC,
            mil.employee
    """

    data = frappe.db.sql(query, params, as_dict=True)
    
    # **VISUAL HIERARCHY**: Indent reportees
    if employee and data:
        data = add_hierarchy_indentation(data, employee)
    
    return data

def add_hierarchy_indentation(data, manager):
    """Add ↳ indentation for direct reportees"""
    for row in data:
        # Check if employee reports directly to manager
        if frappe.db.exists("Employee", {"name": row.employee, "reports_to": manager}):
            row.employee_name =  row.employee_name
            row.designation =  row.designation
    return data

def get_columns(filters=None):
    return [
        {"label": _("ID"), "fieldname": "id", "fieldtype": "Link", "options": "Monthly In-Out Log", "width": 180},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": _("Attendance Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 120},
        {"label": _("Shift Type"), "fieldname": "shift_type", "fieldtype": "Data", "width": 140},
        {"label": _("Shift Hours"), "fieldname": "shift_hours", "fieldtype": "Float", "width": 100, "precision": 2},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("In Time"), "fieldname": "in_time", "fieldtype": "Time", "width": 100},
        {"label": _("Out Time"), "fieldname": "out_time", "fieldtype": "Time", "width": 100},
        {"label": _("Spent Hrs"), "fieldname": "spent_hrs", "fieldtype": "Float", "width": 100, "precision": 2},
        {"label": _("Net Wrk Hrs"), "fieldname": "net_wrk_hrs", "fieldtype": "Float", "width": 110, "precision": 2},
        {"label": _("P.Out Hrs"), "fieldname": "p_out_hrs", "fieldtype": "Float", "width": 100, "precision": 2},
        {"label": _("Late Hrs"), "fieldname": "late_hrs", "fieldtype": "Float", "width": 100, "precision": 2},
        {"label": _("Early Hrs"), "fieldname": "early_hrs", "fieldtype": "Float", "width": 100, "precision": 2},
        {"label": _("OT Hrs"), "fieldname": "ot_hrs", "fieldtype": "Float", "width": 100, "precision": 2}
    ]
