# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	conditions = get_conditions(filters)
	
	if conditions:
		data = frappe.db.sql(f"""SELECT 
				ec.employee,ec.employee_name,
				DATE(ec.time) AS date,
				COUNT(*) AS punch_count,
				e.department,e.company
			FROM `tabEmployee Checkin` as ec
			left join `tabEmployee` as e on e.name = ec.employee
					   {conditions}
			GROUP BY employee HAVING COUNT(*) % 2 != 0 AND (COUNT(*) = 1 OR COUNT(*) = 3 OR COUNT(*) = 5 OR COUNT(*) = 7)""", as_dict=1)
	else:
		data = frappe.db.sql(f"""
			SELECT 
				ec.employee,ec.employee_name,
				DATE(ec.time) AS date,
				COUNT(*) AS punch_count,
				e.department,e.company
			FROM `tabEmployee Checkin` as ec
			left join `tabEmployee` as e on e.name = ec.employee 
			WHERE DATE(ec.time) = CURDATE()
			GROUP BY ec.employee HAVING COUNT(*) % 2 != 0 AND (COUNT(*) = 1 OR COUNT(*) = 3 OR COUNT(*) = 5 OR COUNT(*) = 7)""", as_dict=1)
	
	# frappe.throw(str(data))
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
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 200
		},		
		{
			"label": _("Punch Date"),
			"fieldname": "date",
			"fieldtype": "Date"
		},
		# {
		# 	"label": _("Punch Times"),
		# 	"fieldname": "time",
		# 	"fieldtype": "Data",
		# },
		{
			"label": _("Punch Count"),
			"fieldname": "punch_count",
			"fieldtype": "Data",
			"width": 150
		},
	]
	return columns

def get_conditions(filters):

	filter_list = []

	if filters.get("company"):
		filter_list.append(f'''e.company = "{filters.get("company")}"''')
	
	if filters.get("from_date") and filters.get("to_date"):
		filter_list.append(f'''DATE(ec.time) Between "{filters.get("from_date")}" and "{filters.get("to_date")}" ''')

	if filters.get("department"):
		filter_list.append(f'''e.department = "{filters.get("department")}"''')

	if filters.get("employee"):
		filter_list.append(f'''ec.employee = "{filters.get("employee")}"''')
	

	conditions = "where " + " and ".join(filter_list)
	if conditions!='where ':
		return conditions