# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# is_prepared_report = False
def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	conditions = get_conditions(filters)

	if conditions:
		data = frappe.db.sql(f"""
			SELECT 
				at.employee, at.employee_name, 
				at.company, at.shift,
				at.department, at.attendance_date, 
				COUNT(tec.name) AS punch_count
			FROM 
				`tabAttendance` AS at
			LEFT JOIN 
				`tabEmployee Checkin` AS tec ON tec.attendance = at.name
			{conditions}
			GROUP BY 
				at.employee, at.attendance_date
			HAVING 
				punch_count > 0
			ORDER BY 
				at.attendance_date ASC;
			""", as_dict=1)

	return data

def get_columns(filters=None):
	columns = [
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Employee ID"),
			"fieldname": "employee",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Punch Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 150
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 250
		},		
		# {
		# 	"label": _("Punch Times"),
		# 	"fieldname": "time",
		# 	"fieldtype": "Data",
		# 	"hidden":1
		# },
		{
			"label": _("Punch Count"),
			"fieldname": "punch_count",
			"fieldtype": "Data",
			"width": 100
		},
	]
	return columns

def get_conditions(filters):

	filter_list = []

	if filters.get("company"):
		filter_list.append(f'''at.company = "{filters.get("company")}"''')
	
	if filters.get("from_date") and filters.get("to_date"):
		filter_list.append(f'''at.attendance_date Between "{filters.get("from_date")}" and "{filters.get("to_date")}" ''')

	if filters.get("department"):
		filter_list.append(f'''at.department = "{filters.get("department")}"''')

	if filters.get("employee"):
		filter_list.append(f'''at.employee = "{filters.get("employee")}"''')
	

	conditions = "where (at.in_time IS NOT NULL OR at.out_time IS NOT NULL) AND at.out_time IS NULL  and " + " and ".join(filter_list)
	if conditions!='where ':
		return conditions
