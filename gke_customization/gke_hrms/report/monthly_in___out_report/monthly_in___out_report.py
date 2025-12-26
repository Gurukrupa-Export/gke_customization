# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.dateutils import get_dates_from_timegrain, get_period
from datetime import timedelta, datetime
from frappe.utils import flt, getdate, add_days, format_time, today, add_to_date, get_time
	

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	company = filters.get("company")
	branch = filters.get("branch")
	departments = filters.get("department")  # MultiSelect
	employee = filters.get("employee")

	# If required filters not selected → no data
	if not (from_date and to_date and company and departments):
		return []

	conditions = []
	values = {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}

	conditions.append("emp.status = 'Active'")
	conditions.append("emp.company = %(company)s")

	if employee:
		conditions.append("emp.reports_to = %(employee)s")
		values["employee"] = employee

	if branch:
		conditions.append("emp.branch = %(branch)s")
		values["branch"] = branch

	# MultiSelect department
	if isinstance(departments, list):
		dept_list = departments
	else:
		dept_list = departments.split(",")

	conditions.append("emp.department IN %(departments)s")
	values["departments"] = tuple(dept_list)

	query = f"""
		SELECT 
			emp.name AS employee,
			emp.employee_name AS employee_name,
			d.work_date AS date,

			CASE
				WHEN h.holiday_date IS NOT NULL
					THEN 'Holiday'

				WHEN hl.weekly_off IS NOT NULL
					AND FIND_IN_SET(
						DAYNAME(d.work_date),
						REPLACE(hl.weekly_off, ' ', '')
					) > 0
					THEN 'WO'

				WHEN att.status IS NOT NULL
					THEN att.status

				ELSE 'Absent'
			END AS attendance_status,

			att.shift AS shift,
			TIME(att.in_time) AS in_time,
			TIME(att.out_time) AS out_time,
			emp.department

		FROM `tabEmployee` emp

		JOIN (
			WITH RECURSIVE dates AS (
				SELECT %(from_date)s AS work_date
				UNION ALL
				SELECT DATE_ADD(work_date, INTERVAL 1 DAY)
				FROM dates
				WHERE work_date < %(to_date)s
			)
			SELECT work_date FROM dates
		) d

		LEFT JOIN `tabHoliday List` hl
			ON hl.name = emp.holiday_list

		LEFT JOIN `tabHoliday` h
			ON h.parent = emp.holiday_list
			AND h.holiday_date = d.work_date

		LEFT JOIN `tabAttendance` att
			ON att.employee = emp.name
			AND att.attendance_date = d.work_date
			AND att.docstatus = 1

		WHERE {" AND ".join(conditions)}
		ORDER BY emp.name, d.work_date
	"""

	data = frappe.db.sql(query, values, as_dict=True)

	# data = frappe.throw(f"{frappe.session.user}")
	return data

def get_columns(filters=None):
	columns = [
		{
			"label": "Employee",
			"fieldname": "employee",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "Employee Name",
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200
		},
		# {
		# 	"label": "Company",
		# 	"fieldname": "company",
		# 	"fieldtype": "Data",
		# 	"width": 150
		# },
		# {
		# 	"label": "Branch",
		# 	"fieldname": "branch",
		# 	"fieldtype": "Data",
		# 	"width": 150
		# },
		{
			"label": "Department",
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "Date",
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": "Shift",
			"fieldname": "shift",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": "In Time",
			"fieldname": "in_time",
			"fieldtype": "Time",
			"width": 100
		},
		{
			"label": "Out Time",
			"fieldname": "out_time",
			"fieldtype": "Time",
			"width": 100
		},
		{
			"label": "Attendance Status",
			"fieldname": "attendance_status",
			"fieldtype": "Data",
			"width": 300
		},
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