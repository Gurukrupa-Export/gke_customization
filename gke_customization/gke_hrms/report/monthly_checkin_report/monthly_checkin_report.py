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
	department = filters.get("department") 
	employee = filters.get("employee")

	# If required filters not selected → no data
	if not (from_date and to_date and company and department):
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
		conditions.append("""
			(
				emp.reports_to = %(employee)s
				OR emp.name = %(employee)s
			)
		""")
		values["employee"] = employee


	if branch:
		conditions.append("emp.branch = %(branch)s")
		values["branch"] = branch

	if department:
		conditions.append("emp.department = %(department)s")
		values["department"] = department
	
	query = f"""
		SELECT 
			emp.name AS employee,
			emp.employee_name AS employee_name,
			emp.old_punch_id,
			d.work_date AS date,
			COALESCE(att.shift, ec.shift, emp.default_shift) AS shift,

			/* 📌 Attendance Status */
			CASE
				/* 🎉 Holiday */
				WHEN h.holiday_date IS NOT NULL AND h.weekly_off = 0
					# THEN CONCAT('Holiday - ', h.description)
					THEN 'Holiday'

				/* 💤 Weekly Off */
				WHEN h.holiday_date IS NOT NULL AND h.weekly_off = 1
					THEN 'WO'

				WHEN att.status IS NOT NULL
					THEN att.status

				ELSE 'ERR'
			END AS attendance_status,

			/* Late - hours */
			CASE
				WHEN att.late_entry = 1 
					AND att.in_time IS NOT NULL 
					AND st.start_time IS NOT NULL
				THEN TIMEDIFF(TIME(att.in_time), st.start_time)
				ELSE NULL
			END AS late_hrs,

			/* Early hours */
			CASE
				WHEN att.early_exit = 1
					AND att.out_time IS NOT NULL 
					AND st.end_time IS NOT NULL
				THEN TIMEDIFF(st.end_time, TIME(att.out_time))
				ELSE NULL
			END AS early_hrs,

			/* ALL IN TIMES */
			ec.all_in_times AS in_time,

			/* ALL OUT TIMES */
			ec.all_out_times AS out_time,

			emp.department,
			CASE
				WHEN att.late_entry = 1 THEN 'L'
				ELSE ''
			END AS late,
    		ot.allowed_ot as ott_hrs

		FROM `tabEmployee` emp

		/* Generate date range */
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

		/* Holiday mapping */
		LEFT JOIN `tabHoliday` h
			ON h.parent = emp.holiday_list
		AND h.holiday_date = d.work_date

		/* Attendance (status + time) */
		LEFT JOIN `tabAttendance` att
			ON att.employee = emp.name
		AND att.attendance_date = d.work_date
		AND att.docstatus = 1

		/* Shift Type to get start/end time */
		LEFT JOIN `tabShift Type` st
			ON st.name = att.shift
		
		LEFT JOIN `tabOT Log` ot
    		ON ot.employee = emp.name 
			AND ot.attendance_date = att.attendance_date
			AND ot.is_cancelled = 0

		/* 🔴 THIS IS THE KEY PART */
		LEFT JOIN (
			SELECT
				employee,shift,
				DATE(time) AS checkin_date,

				GROUP_CONCAT(
					CASE WHEN log_type = 'IN'
						THEN TIME_FORMAT(time, '%%H:%%i:%%s')
					END
					ORDER BY time
					SEPARATOR ', '
				) AS all_in_times,

				GROUP_CONCAT(
					CASE WHEN log_type = 'OUT'
						THEN TIME_FORMAT(time, '%%H:%%i:%%s')
					END
					ORDER BY time
					SEPARATOR ', '
				) AS all_out_times

			FROM `tabEmployee Checkin`
			GROUP BY employee, DATE(time)
		) ec
			ON ec.employee = emp.name
			AND ec.checkin_date = d.work_date

		WHERE {" AND ".join(conditions)}
		ORDER BY emp.name, d.work_date
	"""

	data = frappe.db.sql(query, values, as_dict=True)

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
		{
			"label": "Punch ID",
			"fieldname": "old_punch_id",
			"fieldtype": "Data",
			"width": 100
		},
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
			"label": "Attendance Status",
			"fieldname": "attendance_status",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "In Time",
			"fieldname": "in_time",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Out Time",
			"fieldname": "out_time",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Late",
			"fieldname": "late",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Late Hrs",
			"fieldname": "late_hrs",
			"fieldtype": "Time",
			"width": 100
		},
		{
			"label": "Early Hrs",
			"fieldname": "early_hrs",
			"fieldtype": "Time",
			"width": 100
		},
		{
			"label": "OT Hrs",
			"fieldname": "ott_hrs",
			"fieldtype": "Time",
			"width": 100
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