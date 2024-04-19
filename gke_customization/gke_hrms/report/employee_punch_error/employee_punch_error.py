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
				employee,employee_name,
				DATE(time) AS date,
				COUNT(*) AS punch_count
				FROM `tabEmployee Checkin` {conditions}
			GROUP BY employee HAVING COUNT(*) % 2 != 0 AND (COUNT(*) = 1 OR COUNT(*) = 3 OR COUNT(*) = 5 OR COUNT(*) = 7)""", as_dict=1)
	else:
		data = frappe.db.sql(f"""SELECT 
				employee,employee_name,
				DATE(time) AS date,
				COUNT(*) AS punch_count
				FROM `tabEmployee Checkin` WHERE DATE(time) = CURDATE()
			GROUP BY employee HAVING COUNT(*) % 2 != 0 AND (COUNT(*) = 1 OR COUNT(*) = 3 OR COUNT(*) = 5 OR COUNT(*) = 7)""", as_dict=1)
	
	# frappe.throw(str(data))
	return data

def get_columns(filters=None):
	columns = [
		{
			"label": _("Employee ID"),
			"fieldname": "employee",
			"fieldtype": "Data"
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data"
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
			"fieldtype": "Data"
		},
	]
	return columns

def get_conditions(filters):

	filter_list = []

	if filters.get("employee"):
		filter_list.append(f'''employee = "{filters.get("employee")}"''')


	if filters.get("date"):
		filter_list.append(f'''DATE(time) = "{filters.get("date")}"''')

	conditions = "where " + " and ".join(filter_list)
	if conditions!='where ':
		return conditions
