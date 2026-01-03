# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_site_path,today, getdate
import os 
from openpyxl import Workbook
from datetime import date

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	company = filters.get("company")
	branch = filters.get("branch")

	conditions = []
	values = {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}

	if branch:
		conditions.append("AND e.branch = %(branch)s")
		values["branch"] = branch
    
	condition_query = ""
	if conditions:
		condition_query = " AND " + " AND ".join(conditions)

	# frappe.throw(f"{values}")
	query = f"""
		SELECT 
			ss.company AS company, 
			ss.branch AS branch, 
			ss.department AS department, 
			ss.designation AS designation, 
			ss.employee AS employee_id,
			ss.employee_name AS employee_name, 
			ss.employee AS employee_id, 
			MAX(ss.gross_pay) AS gross_pay, 
			MAX(ss.net_pay) AS net_pay,
			sd.amount AS esic_amount,
			ss.payment_days as present_days,
			ss.absent_days,
			ss.custom_gross_salary as ctc,
			ss.total_working_days,
			ss.leave_without_pay as leave_days,
			ss.custom_month,
			e.status,
			e.relieving_date,
			e.date_of_birth
		FROM 
			`tabSalary Slip` AS ss
		JOIN 
			`tabSalary Detail` AS sd ON ss.name = sd.parent
		JOIN 
			`tabEmployee` AS e ON ss.employee = e.employee
		WHERE 
    		sd.salary_component = 'Employees State Insurance Corporation' 
			# AND ss.docstatus = 1
			# AND e.name IN ('GEPL - 01779','GEPL - 01683')
			AND ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s

			{condition_query}
		GROUP BY 
			ss.employee
	"""

	data = frappe.db.sql(query, values, as_dict=True)
	totals = get_totals(data, filters.get("employee"))
	data += totals
	
	return data

def get_totals(data, employee=None):
	totals = {
		"company": "Total",
		"branch": "",
		"employee_id": "",
		"employee_name": "Employee Count: {}".format(len(data)),
		"employee_count": len(data),
		"gross_pay": sum((row.get("gross_pay") or 0) for row in data),
		"esic_amount": sum((row.get("esic_amount") or 0) for row in data),
	}
	return [totals]

def get_columns(filters=None):
	columns = [
		{
			"label": "Company",
			"fieldname": "company",
			"fieldtype": "Data",
			"width": 200
		}, 
		{
			"label": "Branch",
			"fieldname": "branch",
			"fieldtype": "Data",
			"width": 200
		}, 
		{
			"label": "Employee",
			"fieldname": "employee_id",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "Employee Name",
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": "Gross Pay",
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": "ESIC Amount",
			"fieldname": "esic_amount",
			"fieldtype": "Currency",
			"width": 120
		}
		 
	]
	return columns


@frappe.whitelist()
def export_txt(filters=None):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	data = get_data(filters)

	# 🔹 Create workbook & sheet
	wb = Workbook()
	ws = wb.active
	ws.title = "ESIC Report"

	# 🔹 Column Headers
	headers = [
		"IP Number \n (10 Digits)",
		"IP Name IP Name \n (Only alphabets and space)",
		"No of Days for which wages paid/payable during the month",
		"Total Monthly Wages",
		"Reason Code",
		"Last Working Day \n (Format DD/MM/YYYY  or DD-MM-YYYY)"
	]

	ws.append(headers)

	# 🔹 Data Rows
	for row in data:
		if row.get("company") == "Total":
			continue

		esic_number = frappe.db.get_value("Employee", row.get("employee_id"), "_esic_number")
		emp_name = frappe.db.get_value("Employee", row.get("employee_id"), "name_as_per_aadhar")
		dob = row.get("date_of_birth")
		age = 0
		if dob:
			today_date = getdate(today())
			dob_date = getdate(dob)
			age = today_date.year - dob_date.year - (
				(today_date.month, today_date.day) < (dob_date.month, dob_date.day)
			)
		
		code = 0  # Reason Code
		date = ""
		if (row.get("leave_days") or 0) > 0 or (row.get("payment_days") == 0):
			code = 1
		elif row.get("status") == "Left" or (
			row.get("status") == "Inactive" and row.get("relieving_date") 
		):
			if row.get("present_days") > 1:
				code = 2
				date = row.get("relieving_date").strftime("%d-%m-%Y")
			else:
				code = 2
		elif row.get("relieving_date") and age > 58:
			code = 3
			date = row.get("relieving_date").strftime("%d-%m-%Y")
		elif row.get("custom_month") in [4,10]:
			code = 4
		else:
			code = 0

		ws.append([
			esic_number,
			emp_name,
			round(row.get("present_days") or 0),
			round(row.get("gross_pay") or 0),
			code,
			date
		])

	# 🔹 Save file
	file_name = "esic_export.xlsx"
	file_path = get_site_path("public", "files", file_name)
	wb.save(file_path)

	# 🔹 Return download URL
	return f"/files/{file_name}"
