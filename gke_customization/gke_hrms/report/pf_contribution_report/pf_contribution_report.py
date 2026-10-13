# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.dateutils import get_dates_from_timegrain, get_period
from frappe.utils import today, add_to_date

def execute(filters=None):
	columns = get_columns(filters)
	data = get_pf_data(filters)
	return columns, data

def get_pf_data(filters=None):
	# month_name = filters.get("month")
	# year = filters.get("year")

	# month_info_map = {
	# 	"January": ("01", "31"), "February": ("02", "28"), "March": ("03", "31"),
	# 	"April": ("04", "30"), "May": ("05", "31"), "June": ("06", "30"),
	# 	"July": ("07", "31"), "August": ("08", "31"), "September": ("09", "30"),
	# 	"October": ("10", "31"), "November": ("11", "30"), "December": ("12", "31")
	# }

	# month_data = month_info_map.get(month_name)
	# month_num = month_data[0]
	# last_day = month_data[1]

	# year_int = ''
	# if month_name == "February":
	# 	year_int = int(year)
	# 	if (year_int % 4 == 0 and year_int % 100 != 0) or (year_int % 400 == 0):
	# 		last_day = "29"

	# start_date = f"{year}-{month_num}-01"
	# end_date = f"{year}-{month_num}-{last_day}"

	start_date = filters.get("from_date")
	end_date = filters.get("to_date")
 
	emp_condition = ""
	if filters.get("employee"):
		emp_list = filters.get("employee")
		formatted_emps = ", ".join([f"'{e}'" for e in emp_list])
		emp_condition = f"AND ss.employee IN ({formatted_emps})"

	# Round(Least(Ifnull(basic.basic, 0), 15000) * 0.0367, 2) AS er_share,
	sql_query = f"""
		SELECT
			u.employee,
			u.employee_name,
			u.department,
			u.designation,
			u.total_working_days,
			u.payment_days,
			u.actual_working_hours,
			u.gross_pay,
			u.total_deduction,
			u.rounded_total,
			u.uan,
			u.absent_days,
			u.epf_wage,
			u.epf_wage AS edli_wage,
			u.eps_wage,
			u.ee_share,
			u.eps_con,
			u.ee_share - u.eps_con AS er_share,
			u.ncp_days,
			0 AS Refund
		FROM (
			SELECT
				t.*,
				IF(t.eps_wage * t.eps_rate - FLOOR(t.eps_wage * t.eps_rate) = 0.5,
				2 * ROUND(t.eps_wage * t.eps_rate / 2, 0),
				ROUND(t.eps_wage * t.eps_rate, 0)) AS eps_con
			FROM (
				SELECT
					ss.employee,
					UPPER(TRIM(IFNULL(NULLIF(TRIM(emp.name_as_per_aadhar), ''), ss.employee_name))) AS employee_name,
					ss.department,
					ss.designation,
					ss.total_working_days,
					ss.payment_days,
					ss.actual_working_hours,
					ROUND(ss.gross_pay, 0) AS gross_pay,
					ss.total_deduction,
					ss.rounded_total,
					emp.uan_number AS uan,
					ss.absent_days,
					LEAST(ROUND(IFNULL(b.basic, 0), 0), p.wage_ceiling) AS epf_wage,
					CASE WHEN IFNULL(TIMESTAMPDIFF(YEAR, emp.date_of_birth, CURDATE()), 0) < p.eps_age_limit
						THEN LEAST(ROUND(IFNULL(b.basic, 0), 0), p.wage_ceiling) ELSE 0 END AS eps_wage,
					ROUND(LEAST(ROUND(IFNULL(b.basic, 0), 0), p.wage_ceiling) * p.ee_rate, 0) AS ee_share,
					p.eps_rate AS eps_rate,
					CASE WHEN IFNULL(ss.absent_days, 0) <> 0
						THEN ROUND(ss.absent_days, 0)
						ELSE ROUND(IFNULL(ss.total_working_days, 0) - ROUND(IFNULL(ss.payment_days, 0), 0), 0)
					END AS ncp_days
				FROM `tabSalary Slip` ss
				CROSS JOIN (
					SELECT
						25000  AS wage_ceiling,
						0.12   AS ee_rate,
						0.0833 AS eps_rate,
						58     AS eps_age_limit
				) p
				LEFT JOIN `tabEmployee` emp ON emp.name = ss.employee
				LEFT JOIN (
					SELECT parent, SUM(CASE WHEN salary_component = 'Basic' THEN amount ELSE 0 END) AS basic
					FROM `tabSalary Detail`
					GROUP BY parent
				) b ON b.parent = ss.name
		WHERE 
			ss.docstatus = 1 AND 
			ss.start_date >= '{start_date}'
			AND ss.end_date <= '{end_date}'
			AND ss.company = '{filters.get("company")}'
			AND emp.uan_number IS NOT NULL
			AND ss._is_pf_applicable = 1
			{emp_condition}
			) t
		) u
		ORDER BY u.employee_name
		"""
	# frappe.msgprint("<pre>" + sql_query + "</pre>")
	data = frappe.db.sql(sql_query, as_dict=True)
	# frappe.msgprint(f"{data}")
	
	data += get_totals(data, filters.get("employee"), filters)
	return data

@frappe.whitelist()
def get_totals(data, employee=None, filters=None):
	totals = {
		"company": "Total",
		"branch": "",
		"employee_name": "Total Employees: {}".format(len(data)),
		"gross_pay": sum(row.get("gross_pay", 0) for row in data),
		"epf_wage": sum(row.get("epf_wage", 0) for row in data),
		"edli_wage": sum(row.get("edli_wage", 0) for row in data),
		"eps_wage": sum(row.get("eps_wage", 0) for row in data),
		"ee_share": sum(row.get("ee_share", 0) for row in data),
		"eps_con": sum(row.get("eps_con", 0) for row in data),
		"er_share": sum(row.get("er_share", 0) for row in data),
		"ncp_days": sum(row.get("ncp_days", 0) for row in data),
	}
	return [totals]

def get_columns(filters=None):
    columns = [
		{"fieldname": "uan", "label": "UAN", "fieldtype": "Data", "width": 120},
		{"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 160},
		{"fieldname": "gross_pay", "label": "Gross Pay", "fieldtype": "Currency", "width": 100},
		{"fieldname": "epf_wage", "label": "EPF Wage", "fieldtype": "Currency", "width": 100},
		{"fieldname": "edli_wage", "label": "EDLI Wage", "fieldtype": "Currency", "width": 100},
		{"fieldname": "eps_wage", "label": "EPS Wage", "fieldtype": "Currency", "width": 100},
		{"fieldname": "ee_share", "label": "EE Share", "fieldtype": "Currency", "width": 100},
		{"fieldname": "eps_con", "label": "EPS Contr.", "fieldtype": "Currency", "width": 100},
		{"fieldname": "er_share", "label": "ER Share", "fieldtype": "Currency", "width": 100},
		{"fieldname": "ncp_days", "label": "NCP Days", "fieldtype": "Float", "width": 80},
		{"fieldname": "Refund", "label": "Refund", "fieldtype": "Int", "width": 80}
	]
    
    return columns

@frappe.whitelist()
def get_month_range():
	end = today()
	start = add_to_date(end, months=-12)
	periodic_range = get_dates_from_timegrain(start, end, "Monthly")
	periods = [get_period(row) for row in periodic_range]
	periods.reverse()
	return periods