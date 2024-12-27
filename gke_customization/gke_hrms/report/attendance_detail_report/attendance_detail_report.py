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
			"fieldname": "Employee_name",
			"fieldtype": "Data",
			"label": _("Employee Name"),
			"width": 0,
			"hidden": 1,
		},
        {
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
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
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "options": "Designation",
            "width": 150
        },
        {
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift Type",
			"width": 120,
		},
        {
			"label": _("Attendance Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 130,
		},
        {
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
        {
            "label": _("Late Entry Time"),
            "fieldname": "late_entry_time",
            "fieldtype": "Time",
            "width": 150
        },
        {
            "label": _("Early Out Time"),
            "fieldname": "early_out_time",
            "fieldtype": "Time",
            "width": 150
        }
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    
    query =  f"""
    SELECT 
        e.name AS employee, 
        e.employee_name AS employee_name,
        e.department AS department,
        e.designation AS designation,
        e.default_shift AS shift,
        e.company as company,
        a.status as status,
        a.attendance_date AS attendance_date, 
        TIME_FORMAT(ec_in.time, '%H:%i:%s') AS late_entry_time,
        TIME_FORMAT(ec_out.time, '%H:%i:%s') AS early_out_time
    FROM 
        `tabEmployee` e
    RIGHT JOIN 
        `tabAttendance` a ON e.name = a.employee
    LEFT JOIN 
        `tabEmployee Checkin` ec_in ON ec_in.employee = e.name
        AND ec_in.log_type = 'IN'
        AND DATE(ec_in.shift_start) = a.attendance_date
        AND TIME(ec_in.time) > ADDTIME(TIME(ec_in.shift_start), '00:05:59')
    LEFT JOIN 
        `tabEmployee Checkin` ec_out ON ec_out.employee = e.name
        AND ec_out.log_type = 'OUT'
        AND DATE(ec_out.shift_start) = a.attendance_date
        AND TIME(ec_out.time) < TIME(ec_out.shift_end)
    WHERE 
        e.status = 'Active'
    {conditions}
    ORDER BY 
        a.attendance_date DESC;
"""
    
    data = frappe.db.sql(query, as_dict=1)
    return data

def get_conditions(filters):
    filter_list = []

    # Apply filters based on the inputs from JS
    if filters.get("company"):
        filter_list.append(f'''e.company = "{filters.get("company")}" ''')

    if filters.get("from_date"):
        filter_list.append(f'''a.attendance_date >= "{filters.get("from_date")}" ''')

    if filters.get("to_date"):
        filter_list.append(f'''a.attendance_date <= "{filters.get("to_date")}" ''')

    if filters.get("department"):
        filter_list.append(f'''e.department = "{filters.get("department")}" ''')

    if filters.get("designation"):
        filter_list.append(f'''e.designation = "{filters.get("designation")}" ''')

    if filters.get("default_shift"):
        filter_list.append(f'''e.default_shift = "{filters.get("default_shift")}" ''')

    if filters.get("status"):
        filter_list.append(f'''a.status = "{filters.get("status")}" ''')

    if filters.get("employee"):
        filter_list.append(f'''e.name = "{filters.get("employee")}" ''')

    # Construct the WHERE clause based on available filters
    if filter_list:
        conditions = "AND " + " AND ".join(filter_list)
    else:
        conditions = ""

    return conditions
