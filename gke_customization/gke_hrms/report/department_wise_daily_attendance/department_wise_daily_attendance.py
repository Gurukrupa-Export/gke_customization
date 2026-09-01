# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from datetime import timedelta, datetime, time as dtime
from frappe import _
from frappe.utils import getdate, get_time, today, add_days, formatdate
from frappe.query_builder.functions import Count, Date, Min, Max

def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data, summary = get_data(filters)
	report_summary = get_report_summary(summary, get_report_date(filters))

	return columns, data, None, None, report_summary


def get_report_date(filters=None):
	if filters and filters.get("date"):
		return getdate(filters.get("date"))
	return getdate(add_days(today(), -1))


def get_columns():
	return [
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 180,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("In Time"),
			"fieldname": "in_time",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Out Time"),
			"fieldname": "out_time",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Late Entry"),
			"fieldname": "late_entry",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Early Going"),
			"fieldname": "early_exit",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "Data",
			"width": 220,
			"align": "left",
		},
	]


def get_data(filters):
	date = get_report_date(filters)

	employees = get_employees(filters)
	if not employees:
		return [], get_empty_summary()

	employee_names = [e.name for e in employees]

	shift_type_map = get_shift_type_map()
	checkin_map = get_checkin_details_map(date, employee_names)
	remark_map = get_remark_map(date, employee_names)

	summary = get_empty_summary()
	data = []

	for emp in employees:
		summary["total_employees"] += 1

		shift_name = emp.default_shift
		shift = shift_type_map.get(shift_name)
		shift_label = get_shift_label(shift_name, shift_type_map)

		row = {
			"department": emp.department,
			"employee": emp.name,
			"employee_name": emp.employee_name,
			"shift": shift_label,
			"in_time": "",
			"out_time": "",
			"late_entry": "",
			"early_exit": "",
			"status": "",
			"remark": ", ".join(remark_map.get(emp.name, [])),
		}

		checkin = checkin_map.get(emp.name)
		cnt = checkin.cnt if checkin else 0

		if cnt == 0:
			row["status"] = "Absent"
			summary["absent"] += 1

		elif cnt != 2:
			# anything other than a clean one in + one out (1 punch = forgot
			# to check out, 3+ punches = ambiguous, needs manual review)
			row["status"] = "Error"
			row["in_time"] = format_time_value(checkin.first_time)
			summary["error"] += 1

		else:
			in_time = checkin.first_time
			out_time = checkin.last_time
			row["in_time"] = format_time_value(in_time)
			row["out_time"] = format_time_value(out_time)

			worked = out_time - in_time if in_time and out_time else None
			half_day_threshold = get_half_day_threshold(shift)
			shift_start = to_timedelta(shift.start_time) if shift else None
			shift_end = to_timedelta(shift.end_time) if shift else None

			in_time_delta = to_timedelta(in_time)

			if shift_start is not None:
				late_delta = in_time_delta - shift_start
				if late_delta >= timedelta(minutes=5):
					row["late_entry"] = format_timedelta_label(late_delta)
					summary["late_entry"] += 1

			if shift_end is not None:
				early_delta = shift_end - to_timedelta(out_time)
				if early_delta >= timedelta(minutes=5):
					row["early_exit"] = format_timedelta_label(early_delta)
					summary["early_exit"] += 1

			second_half_arrival = (
				shift_start is not None
				and half_day_threshold is not None
				and in_time_delta >= shift_start + half_day_threshold
			)

			if second_half_arrival or (
				half_day_threshold is not None and worked is not None and worked < half_day_threshold
			):
				# came in after the first-half cutoff (can never make the
				# threshold hours within the shift), or simply worked fewer
				# hours than the threshold -> Half Day either way
				row["status"] = "Half Day"
				summary["half_day"] += 1
			else:
				row["status"] = "Present"
				summary["present"] += 1

		data.append(row)

	return data, summary


def get_half_day_threshold(shift):
	"""Shift Type.working_hours_threshold_for_half_day is stored as a float
	number of hours (e.g. 4.5), not a time of day."""
	if not shift or not shift.working_hours_threshold_for_half_day:
		return None
	return timedelta(hours=shift.working_hours_threshold_for_half_day)


def get_employees(filters):
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.from_(Employee)
		.select(
			Employee.name,
			Employee.employee_name,
			Employee.department,
			Employee.default_shift,
		)
		.where(Employee.status == "Active")
		.orderby(Employee.department)
		.orderby(Employee.employee_name)
	)

	if filters.get("department"):
		query = query.where(Employee.department == filters.get("department"))
	if filters.get("company"):
		query = query.where(Employee.company == filters.get("company"))
	if filters.get("employee"):
		query = query.where(Employee.name == filters.get("employee"))

	if filters.get("manager"):
		user_id = frappe.db.get_value("Employee", filters.get("manager"), "user_id")
		allowed_departments = get_manager_departments(user_id) or []
		if not allowed_departments:
			return []
		query = query.where(Employee.department.isin(allowed_departments))

	return query.run(as_dict=True)


def get_manager_departments(user_id):
	"""Departments where `user_id` is listed in custom_user_group. None = no filter (all departments)."""
	if not user_id:
		return None
	return frappe.get_all(
		"User Group Member",
		filters={"parenttype": "Department", "parentfield": "custom_user_group", "user": user_id},
		pluck="parent",
	)


def get_shift_type_map():
	ShiftType = frappe.qb.DocType("Shift Type")

	rows = (
		frappe.qb.from_(ShiftType)
		.select(
			ShiftType.name,
			ShiftType.start_time,
			ShiftType.end_time,
			ShiftType.working_hours_threshold_for_half_day,
		)
	).run(as_dict=True)

	return {row.name: row for row in rows}


def get_checkin_details_map(date, employee_names):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")

	rows = (
		frappe.qb.from_(EmployeeCheckin)
		.select(
			EmployeeCheckin.employee,
			Count(EmployeeCheckin.name).as_("cnt"),
			Min(EmployeeCheckin.time).as_("first_time"),
			Max(EmployeeCheckin.time).as_("last_time"),
		)
		.where(
			(Date(EmployeeCheckin.time) == date)
			& (EmployeeCheckin.employee.isin(employee_names))
		)
		.groupby(EmployeeCheckin.employee)
	).run(as_dict=True)

	return {row.employee: row for row in rows}


def get_remark_map(date, employee_names):
	"""employee -> list of remarks, e.g. ["OT Request", "Attendance Request (On Duty)"]."""
	remark_map = {}

	for emp in get_ot_request_employees(date, employee_names):
		remark_map.setdefault(emp, []).append("OT Request")

	for emp, reason in get_attendance_request_employees(date, employee_names):
		label = f"Attendance Request ({reason})" if reason else "Attendance Request"
		remark_map.setdefault(emp, []).append(label)

	return remark_map


def get_ot_request_employees(date, employee_names):
	OTRequest = frappe.qb.DocType("OT Request")
	OvertimeRequestDetails = frappe.qb.DocType("Overtime Request Details")

	rows = (
		frappe.qb.from_(OTRequest)
		.join(OvertimeRequestDetails)
		.on(OvertimeRequestDetails.parent == OTRequest.name)
		.select(OvertimeRequestDetails.employee_id)
		.where(
			(OTRequest.date == date)
			& (OTRequest.docstatus != 2)
			& (OvertimeRequestDetails.employee_id.isin(employee_names))
		)
		.distinct()
	).run(as_dict=True)

	return [row.employee_id for row in rows]


def get_attendance_request_employees(date, employee_names):
	AttendanceRequest = frappe.qb.DocType("Attendance Request")

	rows = (
		frappe.qb.from_(AttendanceRequest)
		.select(AttendanceRequest.employee, AttendanceRequest.reason)
		.where(
			(AttendanceRequest.from_date <= date)
			& (AttendanceRequest.to_date >= date)
			& (AttendanceRequest.docstatus != 2)
			& (AttendanceRequest.employee.isin(employee_names))
		)
	).run(as_dict=True)

	return [(row.employee, row.reason) for row in rows]


def get_shift_label(shift_name, shift_type_map):
	if not shift_name:
		return ""
	shift = shift_type_map.get(shift_name)
	if not shift:
		return shift_name
	return f"{shift_name} ({format_time_value(shift.start_time)} - {format_time_value(shift.end_time)})"


def to_timedelta(value):
	if value is None:
		return None
	if isinstance(value, timedelta):
		return value
	if isinstance(value, datetime):
		value = value.time()
	if isinstance(value, dtime):
		return timedelta(hours=value.hour, minutes=value.minute, seconds=value.second)
	try:
		t = get_time(value)
		return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
	except Exception:
		return None


def format_timedelta_label(delta):
	total_seconds = int(delta.total_seconds())
	hours, remainder = divmod(total_seconds, 3600)
	minutes, seconds = divmod(remainder, 60)
	return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_time_value(value):
	if not value:
		return ""
	try:
		t = get_time(value)
		return t.strftime("%H:%M:%S")
	except Exception:
		return str(value)


def get_empty_summary():
	return {
		"total_employees": 0,
		"present": 0,
		"absent": 0,
		"half_day": 0,
		"late_entry": 0,
		"early_exit": 0,
		"error": 0,
	}


def get_report_summary(summary, date):
	return [
		{
			"label": _("Report Date"),
			"value": getdate(date).strftime("%d-%m-%Y"),
			"indicator": "Blue",
			"datatype": "Data",
		},
		{"label": _("Total Employees"), "value": summary["total_employees"], "indicator": "Blue", "datatype": "Int"},
		{"label": _("Present"), "value": summary["present"], "indicator": "Green", "datatype": "Int"},
		{"label": _("Absent"), "value": summary["absent"], "indicator": "Red", "datatype": "Int"},
		{"label": _("Half Day"), "value": summary["half_day"], "indicator": "Yellow", "datatype": "Int"},
		{"label": _("Late Entry"), "value": summary["late_entry"], "indicator": "Orange", "datatype": "Int"},
		{"label": _("Early Exit"), "value": summary["early_exit"], "indicator": "Orange", "datatype": "Int"},
		{"label": _("Error"), "value": summary["error"], "indicator": "Red", "datatype": "Int"},
	]


# ---------------------------------------------------------------------------
# Send Mail button - emails this report to each department's manager(s)
# ---------------------------------------------------------------------------


def get_department_manager_emails(department):
	"""Users listed in Department.custom_user_group (Table MultiSelect,
	child doctype 'User Group Member', field 'user')."""
	emails = frappe.get_all(
		"User Group Member",
		filters={
			"parenttype": "Department",
			"parentfield": "custom_user_group",
			"parent": department,
		},
		pluck="user",
	)
	return [e for e in emails if e]


def render_email_html(department, date, rows, summary):
	rows_html = "".join(f"""
		<tr>
			<td>{r['employee_name']}</td>
			<td>{r['employee']}</td>
			<td>{r['shift']}</td>
			<td>{r['in_time']}</td>
			<td>{r['out_time']}</td>
			<td>{r['status']}</td>
			<td>{r['late_entry']}</td>
			<td>{r['early_exit']}</td>
			<td>{r['remark']}</td>
		</tr>""" for r in rows) or "<tr><td colspan='9' style='text-align:center;'>No employees found</td></tr>"

	return f"""
	<h3>Daily Attendance Report — {department} — {formatdate(date, "dd-mm-yyyy")}</h3>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>Employee Name</th><th>Employee ID</th><th>Shift</th>
				<th>In Time</th><th>Out Time</th>
				<th>Status</th><th>Late Entry</th><th>Early Exit</th><th>Remark</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	<h4 style="margin-top:16px;">Department Summary</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>Total Employees</td><td>{summary['total_employees']}</td></tr>
		<tr><td>Present</td><td>{summary['present']}</td></tr>
		<tr><td>Absent</td><td>{summary['absent']}</td></tr>
		<tr><td>Half Day</td><td>{summary['half_day']}</td></tr>
		<tr><td>Late Entry</td><td>{summary['late_entry']}</td></tr>
		<tr><td>Early Exit</td><td>{summary['early_exit']}</td></tr>
		<tr><td>Error</td><td>{summary['error']}</td></tr>
	</table>
	"""


@frappe.whitelist()
def send_daily_attendance_report(date=None, department=None):
	"""Emails this report to each matching department's manager(s).
	department=None -> every department that has a manager set in
	custom_user_group. department=<name> -> just that one.
	Returns {"sent": [...], "skipped": [...]} so the caller (the report's
	Send Mail button) can show what actually happened."""

	date = date or get_report_date()

	departments = frappe.get_all(
		"User Group Member",
		filters={"parenttype": "Department", "parentfield": "custom_user_group"},
		pluck="parent",
		distinct=True,
	)
	if department:
		departments = [department]

	sent = []
	skipped = []

	for dept in departments:
		rows, summary = get_data(frappe._dict({"department": dept, "date": date}))

		if not rows:
			skipped.append(dept)
			continue

		manager_emails = get_department_manager_emails(dept)
		if not manager_emails:
			frappe.log_error(
				title="Daily Attendance Report — no manager in custom_user_group",
				message=f"Department: {dept}",
			)
			skipped.append(dept)
			continue

		html = render_email_html(dept, date, rows, summary)
		frappe.sendmail(
			recipients=manager_emails,
			cc=["angat_p@gkexport.com","hr_srt@gkexport.com"],
			sender="alerts@gkexport.com",
			subject=f"Daily Attendance Report — {dept} — {formatdate(date, 'dd-mm-yyyy')}",
			message=html,
			now=True,
		)
		sent.append({"department": dept, "managers": manager_emails})

	return {"sent": sent, "skipped": skipped}
