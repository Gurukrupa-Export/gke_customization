# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, get_datetime, format_time, formatdate
from datetime import timedelta

def get_columns():
    return [
		{"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
		{"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 160},
		{"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 110},
		{"label": "In Time", "fieldname": "in_time", "fieldtype": "Data", "width": 90},
		{"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data", "width": 90},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Data", "width": 90},
		{"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Data", "width": 110},
	]


def get_manager_departments(user_id):
	"""Departments where `user_id` is listed in custom_user_group. None = no filter (all departments)."""
	if not user_id:
		return None
	return frappe.get_all(
		"User Group Member",
		filters={"parenttype": "Department", "parentfield": "custom_user_group", "user": user_id},
		pluck="parent",
	)
 
 
def get_employees_on_leave(emp_ids, date):
	"""Approved Leave Applications covering `date`, keyed by employee id,
		so we can show who's on leave (and what type) in the report."""
	if not emp_ids:
		return {}
	rows = frappe.get_all(
		"Leave Application",
		filters={
			"employee": ["in", emp_ids],
			"status": "Approved",
			"from_date": ["<=", date],
			"to_date": [">=", date],
			"docstatus": 1,
		},
		fields=["employee", "leave_type", "from_date", "to_date"],
	)
	return {r.employee: r for r in rows}
 
 
def get_checkin_info(employee, date):
	"""Return (in_time, out_time, shift) from today's Employee Checkin rows.
		in_time/out_time are raw datetimes (or None); shift is whatever the
		checkin recorded, if any."""
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
		},
		fields=["log_type", "time", "shift"],
		order_by="time asc",
	)
	if not checkins:
		return None, None, None

	in_times = [c.time for c in checkins if c.log_type == "IN"]
	out_times = [c.time for c in checkins if c.log_type == "OUT"]

	in_time = min(in_times) if in_times else None
	out_time = max(out_times) if out_times else None
	shift = next((c.shift for c in checkins if c.shift), None)

	return in_time, out_time, shift
 
 
def is_late_entry(shift_name, in_time, date):
	"""Compare in_time against Shift Type start_time (+ grace period, if enabled)."""
	if not shift_name or not in_time:
		return False

	shift = frappe.db.get_value(
		"Shift Type",
		shift_name,
		["start_time", "enable_late_entry_marking", "late_entry_grace_period"],
		as_dict=True,
	)
	if not shift or shift.start_time is None:
		return False

	shift_start_dt = get_datetime(f"{date} 00:00:00") + shift.start_time
	grace_minutes = shift.late_entry_grace_period or 0
	if not shift.enable_late_entry_marking:
		grace_minutes = 0

	threshold = shift_start_dt + timedelta(minutes=grace_minutes)
	return get_datetime(in_time) > threshold
 
 
def build_rows_for_department(department, date):
	employees = frappe.get_all(
		"Employee",
		filters={"department": department, "status": "Active"},
		fields=["name", "employee_name", "default_shift", "company"],
	)
	if not employees:
		return []

	emp_ids = [e.name for e in employees]
	leave_by_emp = get_employees_on_leave(emp_ids, date)

	rows = []
	for emp in employees:
		base = {
			"employee_id": emp.name,
			"employee_name": emp.employee_name,
			"department": department,
			"company": emp.company,
		}

		if emp.name in leave_by_emp:
			rows.append({
				**base,
				"shift": "", "in_time": "", "out_time": "",
				"status": "On Leave", "late_entry": "",
				"leave_type": leave_by_emp[emp.name].leave_type or "",
			})
			continue

		in_time, out_time, checkin_shift = get_checkin_info(emp.name, date)

		if not in_time:
			rows.append({
				**base,
				"shift": emp.default_shift or "", "in_time": "", "out_time": "",
				"status": "Absent", "late_entry": "", "leave_type": "",
			})
			continue

		shift = checkin_shift or emp.default_shift
		late = is_late_entry(shift, in_time, date)
		rows.append({
			**base,
			"shift": shift or "",
			"in_time": format_time(get_datetime(in_time)),
			"out_time": format_time(get_datetime(out_time)) if out_time else "-",
			"status": "Present",
			"late_entry": "Yes" if late else "No",
			"leave_type": "",
		})

	return rows
 
 
def build_summary_rows(data):
	total = len(data)
	present = sum(1 for r in data if r["status"] == "Present")
	absent = sum(1 for r in data if r["status"] == "Absent")
	leave = sum(1 for r in data if r["status"] == "On Leave")
	late = sum(1 for r in data if r["late_entry"] == "Yes")
 
	return [
		{"status": "Present", "late_entry": present},
		{"status": "Absent", "late_entry": absent},
		{"status": "On Leave", "late_entry": leave},
		{"status": "Late Entry", "late_entry": late},
		{"status": "Total", "late_entry": total},
	]
 
 
def execute(filters=None):
	filters = frappe._dict(filters or {})
	date = filters.get("date") or nowdate()
	company = filters.get("company")
	department = filters.get("department")
	manager = filters.get("manager")
 
	dept_filters = {"disabled": 0}
	if company:
		dept_filters["company"] = company
	if department:
		dept_filters["name"] = department
 
	allowed_departments = None
	if manager:
		user_id = frappe.db.get_value("Employee", manager, "user_id")
		allowed_departments = get_manager_departments(user_id) or []
 
	departments = frappe.get_all("Department", filters=dept_filters, pluck="name", order_by="name asc")
	if allowed_departments is not None:
		departments = [d for d in departments if d in allowed_departments]
 
	columns = get_columns()
	data = []
	for dept in departments:
		rows = build_rows_for_department(dept, date)
		rows.sort(key=lambda r: r["employee_name"] or "")
		data.extend(rows)
 
	data.extend(build_summary_rows(data))
 
	return columns, data

"""for auto mail at 10 AM """

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

def build_department_report(department, date):
	"""Return (present_rows, leave_rows, absent_rows, summary_dict) for one
	department, or None if empty."""
	employees = frappe.get_all(
		"Employee",
		filters={"department": department, "status": "Active"},
		fields=["name", "employee_name", "default_shift"],
	)
	if not employees:
		return None
 
	emp_ids = [e.name for e in employees]
	leave_by_emp = get_employees_on_leave(emp_ids, date)
 
	summary = {"Total Employees": len(employees), "Present": 0, "Absent": 0, "On Leave": 0, "Late Entry": 0}
	present_rows = []
	leave_rows = []
	absent_rows = []
 
	for emp in employees:
		if emp.name in leave_by_emp:
			summary["On Leave"] += 1
			leave = leave_by_emp[emp.name]
			leave_rows.append({
				"employee_name": emp.employee_name,
				"employee_id": emp.name,
				"department": department,
				"leave_type": leave.leave_type or "",
				"from_date": leave.from_date,
				"to_date": leave.to_date,
			})
			continue
 
		in_time, out_time, checkin_shift = get_checkin_info(emp.name, date)
 
		if not in_time:
			summary["Absent"] += 1
			absent_rows.append({
				"employee_name": emp.employee_name,
				"employee_id": emp.name,
				"department": department,
				"shift": emp.default_shift or "",
			})
			continue
 
		summary["Present"] += 1
		shift = checkin_shift or emp.default_shift
		late = is_late_entry(shift, in_time, date)
		if late:
			summary["Late Entry"] += 1
 
		present_rows.append({
			"employee_name": emp.employee_name,
			"employee_id": emp.name,
			"department": department,
			"shift": shift or "",
			"in_time": format_time(get_datetime(in_time)),
			"out_time": format_time(get_datetime(out_time)) if out_time else "-",
			"status": "Present",
			"late_entry": "Yes" if late else "No",
		})
 
	return present_rows, leave_rows, absent_rows, summary
 
 
def render_absent_table(absent_rows):
	if not absent_rows:
		return ""

	rows_html = "".join(f"""
		<tr>
			<td>{i}</td>
			<td>{r['employee_name']}</td>
			<td>{r['employee_id']}</td>
			<td>{r['shift']}</td>
		</tr>""" for i, r in enumerate(absent_rows, start=1))

	return f"""
	<h4 style="margin-top:16px;">Absent</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>Sr No</th><th>Employee Name</th><th>Employee ID</th><th>Shift</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	"""
 
 
def render_leave_table(leave_rows):
	if not leave_rows:
		return ""

	rows_html = "".join(f"""
		<tr>
			<td>{i}</td>
			<td>{r['employee_name']}</td>
			<td>{r['employee_id']}</td>
			<td>{r['leave_type']}</td>
			<td>{r['from_date']}</td>
			<td>{r['to_date']}</td>
		</tr>""" for i, r in enumerate(leave_rows, start=1))

	return f"""
	<h4 style="margin-top:16px;">On Leave</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>Sr No</th><th>Employee Name</th><th>Employee ID</th><th>Leave Type</th>
				<th>From Date</th><th>To Date</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	"""
 
 
def render_email_html(department, date, rows, leave_rows, absent_rows, summary):
	rows_html = "".join(f"""
		<tr>
			<td>{i}</td>
			<td>{r['employee_name']}</td>
			<td>{r['employee_id']}</td>
			<td>{r['department']}</td>
			<td>{r['shift']}</td>
			<td>{r['in_time']}</td>
			<td>{r['out_time']}</td>
			<td>{r['status']}</td>
			<td>{r['late_entry']}</td>
		</tr>""" for i, r in enumerate(rows, start=1)) or "<tr><td colspan='9' style='text-align:center;'>No employees present</td></tr>"

	return f"""
	<h3>Present Report — {department} — {formatdate(date, "dd-mm-yyyy")}</h3>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>Sr No</th><th>Employee Name</th><th>Employee ID</th><th>Department</th>
				<th>Shift</th><th>In Time</th><th>Out Time</th>
				<th>Attendance Status</th><th>Late Entry</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	{render_leave_table(leave_rows)}
	{render_absent_table(absent_rows)}
	<h4 style="margin-top:16px;">Department Summary</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>Total Employees</td><td>{summary['Total Employees']}</td></tr>
		<tr><td>Present</td><td>{summary['Present']}</td></tr>
		<tr><td>Absent</td><td>{summary['Absent']}</td></tr>
		<tr><td>Leave</td><td>{summary['On Leave']}</td></tr>
		<tr><td>Late Entry</td><td>{summary['Late Entry']}</td></tr>
	</table>
	"""

@frappe.whitelist()
def send_morning_present_report(date=None, department=None):
	"""Emails the present report to each matching department's manager(s).
	department=None -> every department that has a manager set in
	custom_user_group. department=<name> -> just that one.
	Returns {"sent": [...], "skipped": [...]} so the caller (the report's
	Send Mail button) can show what actually happened."""

	date = date or nowdate()
 
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
		result = build_department_report(dept, date)
 
		if not result:
			skipped.append(dept)
			continue
		rows, leave_rows,absent_rows, summary = result
 
		manager_emails = get_department_manager_emails(dept)
		if not manager_emails:
			frappe.log_error(
				title="Morning Present Report — no manager in custom_user_group",
				message=f"Department: {dept}",
			)
			skipped.append(dept)
			continue

		html = render_email_html(dept, date, rows, leave_rows, absent_rows, summary)
		frappe.sendmail(
			recipients=manager_emails,
			cc=["angat_p@gkexport.com","hr_srt@gkexport.com"],
			sender="alerts@gkexport.com",
			subject=f"Present Report — {dept} — {formatdate(date, 'dd-mm-yyyy')}",
			message=html,
			now=True,
		)
		sent.append({"department": dept, "managers": manager_emails})
 
	return {"sent": sent, "skipped": skipped}