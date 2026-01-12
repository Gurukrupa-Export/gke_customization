# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_site_path,today, getdate
import os

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
            ss.custom_gross_salary,
			ss.absent_days,
			e.date_of_birth,
			ss.payment_days,
			ss.total_working_days,
			/* Gross Pay counted once */
			MAX(ss.gross_pay) AS gross_pay,

			/* PF amount only if age < 58 */
			SUM(
				CASE 
					WHEN sd.salary_component = 'Provident Fund'
						#  AND TIMESTAMPDIFF(YEAR, e.date_of_birth, ss.end_date) < 58
					THEN sd.amount
					ELSE 0
				END
			) AS pf_amount,

			MAX(
			    CASE 
			        WHEN sd.salary_component = 'Basic' 
					THEN sd.amount
					ELSE 0
				END
			) AS epf_wages,
			
			MAX(
			    CASE 
			        WHEN sd.salary_component = 'Advance' 
					THEN sd.amount
					ELSE 0
				END
			) AS refund_advance,

			e.gender AS gender

		FROM 
			`tabSalary Slip` ss
		JOIN 
			`tabSalary Detail` sd 
				ON ss.name = sd.parent
		JOIN 
			`tabEmployee` e 
				ON ss.employee = e.name

		WHERE 
			ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s
			# AND ss.docstatus = 1
			# AND ss.status = 'Submitted'

			/* Only employees whose PF is deducted */
			AND EXISTS (
				SELECT 1
				FROM `tabSalary Detail` sd_pf
				WHERE sd_pf.parent = ss.name
				  AND sd_pf.salary_component = 'Provident Fund'
				  AND sd_pf.amount > 0
			)
			{condition_query}
		GROUP BY ss.employee
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
		"pf_amount": sum((row.get("pf_amount") or 0) for row in data),
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
			"label": "PF Amount",
			"fieldname": "pf_amount",
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

	lines = []
	for row in data:
	# skip total row if present
		if row.get("company") == "Total":
			continue

		age = 0
		dob = row.get("date_of_birth")
		if dob:
			today_date = getdate(today())
			dob_date = getdate(dob)
			age = today_date.year - dob_date.year - (
				(today_date.month, today_date.day) < (dob_date.month, dob_date.day)
			)

		# only include employees with age < 58
		if row.get("employee_id") :
			# and age < 58:
			gross_pay = round(row.get("gross_pay") or 0)
			uan_number = frappe.db.get_value("Employee", row["employee_id"], "uan_number")
			name_as_per_aadhar = frappe.db.get_value("Employee", row["employee_id"], "name_as_per_aadhar")
			# epf_wages = round(row.get("epf_wages") or 0)
			
			basic_ear = round(row.get("epf_wages") or 0)
			eps_wages = 0
			
			epf_wages = 15000 if basic_ear > 15000 else basic_ear

			if age >= 58:
				eps_wages = 0
			else:
				eps_wages = 15000 if basic_ear > 15000 else basic_ear

			edli_wages = 15000 if basic_ear > 15000 else basic_ear
			ctc = round(float(row.get("custom_gross_salary") or 0)) 

			if basic_ear < 15000:
				epf_contribution = round((basic_ear or 0) * 0.12)
				if age >= 58:
					eps_contribution = 0
				else:
					eps_contribution = round((basic_ear or 0) * 0.0833)
			else:	
				epf_contribution = round(row.get("pf_amount") or 0)
				eps_contribution = round(15000 * 0.0833)
			contribution = (epf_contribution - eps_contribution) or 0


			ncp = 0
			total_working_days = row.get("total_working_days") or 0
			payment_days = row.get("payment_days") or 0

			if row.get("absent_days"):
				ncp = round(row.get("absent_days") or 0)
			else:
				ncp = round(total_working_days - payment_days)

			refund_advance = row.get("refund_advance") or 0

			# 100982928420#~#Bhikhubhai Maheshbhai Modi#~#22589#~#14065
			# #~#14065#~#14065#~#1688
			# #~#1688#~#0#~#0#~#0

			lines.append(
				f"{uan_number}#~#{name_as_per_aadhar}#~#{gross_pay}#~#{epf_wages}"
				f"#~#{eps_wages}#~#{edli_wages}#~#{epf_contribution}"
				f"#~#{eps_contribution}#~#{contribution}#~#{ncp}#~#{refund_advance}"
			)

	content = "\n".join(lines)

	file_name = "pf_export.txt"
	file_path = get_site_path("public", "files", file_name)

	with open(file_path, "w", encoding="utf-8") as f:
		f.write(content)

	return f"/files/{file_name}"

# def export_txt(filters=None):
# 	if isinstance(filters, str):
# 		filters = frappe.parse_json(filters)

# 	data = get_data(filters)

# 	lines = []
# 	for row in data:
# 		if row.get("company") == "Total":
#             pass

# 		age = 0
# 		dob = row.get("date_of_birth")
# 		if dob:
# 			today_date = getdate(today())
# 			dob_date = getdate(dob)
# 			age = today_date.year - dob_date.year - (
# 				(today_date.month, today_date.day) < (dob_date.month, dob_date.day)
# 			)
# 		if row.get("employee_id") and age < 58:
# 			gross_pay = round(row.get("gross_pay"))
# 			uan_number = frappe.db.get_value("Employee", row["employee_id"], "uan_number")
# 			name_as_per_aadhar = frappe.db.get_value("Employee", row["employee_id"], "name_as_per_aadhar")
# 			epf_wages = round(row['epf_wages']) or 0
# 			eps_wages = epf_wages
# 			edli_wages = epf_wages
# 			epf_contribution = round((epf_wages or 0) * 0.12)
# 			eps_contribution = round((epf_wages or 0) * 0.0833)
# 			contribution = (epf_contribution - eps_contribution) or 0
# 			ncp = row.get("absent_days") or 0
# 			refund_advance = row.get("refund_advance") or 0

		
# 		lines.append(
# 			f"{uan_number}#~#{name_as_per_aadhar}#~#{gross_pay}#~#{epf_wages}#~#{eps_wages}#~#{edli_wages}#~#{epf_contribution}#~#{eps_contribution}#~#{contribution}#~#{ncp}#~#{refund_advance}"
# 		)

# 	content = "\n".join(lines)

# 	file_name = "pf_export.txt"
# 	file_path = get_site_path("public", "files", file_name)

# 	with open(file_path, "w", encoding="utf-8") as f:
# 		f.write(content)

# 	return f"/files/{file_name}"