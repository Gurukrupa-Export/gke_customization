# Copyright (c) 2024, Gurukrupa Export and contributors
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
		data = frappe.db.sql(f"""
			SELECT 							   	
				CASE 
					WHEN MONTH(ss.start_date) = 1 THEN 'January'
					WHEN MONTH(ss.start_date) = 2 THEN 'February'
					WHEN MONTH(ss.start_date) = 3 THEN 'March'
					WHEN MONTH(ss.start_date) = 4 THEN 'April'
					WHEN MONTH(ss.start_date) = 5 THEN 'May'
					WHEN MONTH(ss.start_date) = 6 THEN 'June'
					WHEN MONTH(ss.start_date) = 7 THEN 'July'
					WHEN MONTH(ss.start_date) = 8 THEN 'August'
					WHEN MONTH(ss.start_date) = 9 THEN 'September'
					WHEN MONTH(ss.start_date) = 10 THEN 'October'
					WHEN MONTH(ss.start_date) = 11 THEN 'November'
					WHEN MONTH(ss.start_date) = 12 THEN 'December'
				END AS month_name,
				ss.start_date as date,	   
				ep.ctc,				
				ep.custom_variable_in,
				ROUND(ss.gross_pay,0),
				ROUND(ss.gross_pay * (ep.custom_variable_in / 100),0) AS gross_pay_amt
			FROM `tabEmployee` AS ep
			JOIN `tabSalary Slip` AS ss ON ss.employee_name = ep.employee_name
			{conditions} 
			""")

	return data

def get_columns(filters=None):
	columns = [ 
		{
			"label": _("Month"),
			"fieldname": "month_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 130
		},
		{
			"label": _("CTC"),
			"fieldname": "ctc",
			"fieldtype": "Currency",
			"width": 100
		},		
		{
			"label": _("Variable"),
			"fieldname": "custom_variable_in",
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Variable Amount"),
			"fieldname": "gross_pay_amt",
			"fieldtype": "Currency",
			"width": 180
		},
	]
	return columns

def get_conditions(filters):

	filter_list = []

	if filters.get("employee"):
		filter_list.append(f'''ep.name = "{filters.get("employee")}"''')
	 

	conditions = "where " + " and ".join(filter_list) + " and ss.status = 'Submitted'"
	if conditions!='where ':
		return conditions