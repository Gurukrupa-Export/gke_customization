# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import escape_html, format_time, formatdate, get_datetime, nowdate


def get_columns():
    return [
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
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
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 160,
        },
        {
            "label": _("Shift"),
            "fieldname": "shift",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 110,
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
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {
            "label": _("Late Entry"),
            "fieldname": "late_entry",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("Leave Type"),
            "fieldname": "leave_type",
            "fieldtype": "Data",
            "width": 110,
        },
    ]


def get_manager_departments(user_id):
    """Departments where `user_id` is listed in custom_user_group. None = no filter (all departments)."""
    if not user_id:
        return None
    return frappe.get_all(
        "User Group Member",
        filters={
            "parenttype": "Department",
            "parentfield": "custom_user_group",
            "user": user_id,
        },
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


def get_checkin_map(emp_ids, date):
    """Return {employee: (in_time, out_time, shift)} from the Employee Checkin rows on `date`.
    in_time/out_time are raw datetimes (or None); shift is whatever the
    checkin recorded, if any."""
    if not emp_ids:
        return {}

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", emp_ids],
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
        },
        fields=["employee", "log_type", "time", "shift"],
        order_by="time asc",
    )
    checkins_by_employee = {}
    for checkin in checkins:
        checkins_by_employee.setdefault(checkin.employee, []).append(checkin)

    checkin_map = {}
    for employee, employee_checkins in checkins_by_employee.items():
        in_times = [c.time for c in employee_checkins if c.log_type == "IN"]
        out_times = [c.time for c in employee_checkins if c.log_type == "OUT"]

        in_time = min(in_times) if in_times else None
        out_time = max(out_times) if out_times else None
        shift = next((c.shift for c in employee_checkins if c.shift), None)
        checkin_map[employee] = (in_time, out_time, shift)

    return checkin_map


def get_shift_type_map(shift_names):
    shift_names = list({name for name in shift_names if name})
    if not shift_names:
        return {}

    shift_types = frappe.get_all(
        "Shift Type",
        filters={"name": ["in", shift_names]},
        fields=[
            "name",
            "start_time",
            "enable_late_entry_marking",
            "late_entry_grace_period",
        ],
    )
    return {shift_type.name: shift_type for shift_type in shift_types}


def is_late_entry(shift, in_time, date):
    """Compare in_time against Shift Type start_time (+ grace period, if enabled)."""
    if not shift or not in_time or shift.start_time is None:
        return False

    shift_start_dt = get_datetime(f"{date} 00:00:00") + shift.start_time
    grace_minutes = shift.late_entry_grace_period or 0
    if not shift.enable_late_entry_marking:
        grace_minutes = 0

    threshold = shift_start_dt + timedelta(minutes=grace_minutes)
    return get_datetime(in_time) > threshold


def get_active_employees(departments):
    if not departments:
        return []
    return frappe.get_all(
        "Employee",
        filters={"department": ["in", departments], "status": "Active"},
        fields=["name", "employee_name", "default_shift", "company", "department"],
    )


def build_employee_rows(employees, date):
    """One row per employee with status Present, Absent or On Leave.
    `is_present`, `is_absent`, `is_on_leave` and `is_late` are set so callers
    can count and split rows without comparing translated status strings."""
    emp_ids = [e.name for e in employees]
    leave_by_emp = get_employees_on_leave(emp_ids, date)
    checkin_map = get_checkin_map(emp_ids, date)
    shift_type_map = get_shift_type_map(
        [
            checkin_map.get(e.name, (None, None, None))[2] or e.default_shift
            for e in employees
        ]
    )

    rows = []
    for emp in employees:
        row = frappe._dict(
            {
                "employee_id": emp.name,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "company": emp.company,
                "shift": "",
                "in_time": "",
                "out_time": "",
                "status": "",
                "late_entry": "",
                "leave_type": "",
                "from_date": None,
                "to_date": None,
                "is_present": False,
                "is_absent": False,
                "is_on_leave": False,
                "is_late": False,
            }
        )

        leave = leave_by_emp.get(emp.name)
        if leave:
            row.update(
                {
                    "status": _("On Leave"),
                    "leave_type": leave.leave_type or "",
                    "from_date": leave.from_date,
                    "to_date": leave.to_date,
                    "is_on_leave": True,
                }
            )
            rows.append(row)
            continue

        in_time, out_time, checkin_shift = checkin_map.get(emp.name, (None, None, None))

        if not in_time:
            row.update(
                {
                    "shift": emp.default_shift or "",
                    "status": _("Absent"),
                    "is_absent": True,
                }
            )
            rows.append(row)
            continue

        shift = checkin_shift or emp.default_shift
        late = is_late_entry(shift_type_map.get(shift), in_time, date)
        row.update(
            {
                "shift": shift or "",
                "in_time": format_time(get_datetime(in_time)),
                "out_time": format_time(get_datetime(out_time)) if out_time else "-",
                "status": _("Present"),
                "late_entry": _("Yes") if late else _("No"),
                "is_present": True,
                "is_late": late,
            }
        )
        rows.append(row)

    return rows


def get_summary(rows):
    return {
        "Total Employees": len(rows),
        "Present": sum(1 for r in rows if r.is_present),
        "Absent": sum(1 for r in rows if r.is_absent),
        "On Leave": sum(1 for r in rows if r.is_on_leave),
        "Late Entry": sum(1 for r in rows if r.is_late),
    }


def build_summary_rows(data):
    summary = get_summary(data)

    # "Total" stays untranslated: the report JS formatter compares data.status === "Total".
    return [
        {"status": _("Present"), "late_entry": summary["Present"]},
        {"status": _("Absent"), "late_entry": summary["Absent"]},
        {"status": _("On Leave"), "late_entry": summary["On Leave"]},
        {"status": _("Late Entry"), "late_entry": summary["Late Entry"]},
        {"status": "Total", "late_entry": summary["Total Employees"]},
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

    departments = frappe.get_all(
        "Department", filters=dept_filters, pluck="name", order_by="name asc"
    )
    if allowed_departments is not None:
        departments = [d for d in departments if d in allowed_departments]

    rows_by_department = {}
    for row in build_employee_rows(get_active_employees(departments), date):
        rows_by_department.setdefault(row.department, []).append(row)

    columns = get_columns()
    data = []
    for dept in departments:
        rows = rows_by_department.get(dept, [])
        rows.sort(key=lambda r: r["employee_name"] or "")
        data.extend(rows)

    data.extend(build_summary_rows(data))

    return columns, data


# For auto mail at 10 AM


def get_department_manager_email_map(department=None):
    """department -> users listed in Department.custom_user_group (Table MultiSelect,
    child doctype 'User Group Member', field 'user')."""
    filters = {"parenttype": "Department", "parentfield": "custom_user_group"}
    if department:
        filters["parent"] = department

    manager_email_map = {}
    for row in frappe.get_all(
        "User Group Member", filters=filters, fields=["parent", "user"]
    ):
        manager_email_map.setdefault(row.parent, [])
        if row.user:
            manager_email_map[row.parent].append(row.user)
    return manager_email_map


def get_branch_hr_email_map(departments):
    """department -> HR users (Branch.custom_user_group) for every branch that has an
    active employee in that department."""
    if not departments:
        return {}

    department_branches = frappe.get_all(
        "Employee",
        filters={
            "department": ["in", departments],
            "status": "Active",
            "branch": ["is", "set"],
        },
        fields=["department", "branch"],
        distinct=True,
    )
    if not department_branches:
        return {}

    branch_users = frappe.get_all(
        "User Group Member",
        filters={
            "parenttype": "Branch",
            "parentfield": "custom_user_group",
            "parent": ["in", list({row.branch for row in department_branches})],
        },
        fields=["parent", "user"],
    )
    users_by_branch = {}
    for row in branch_users:
        if row.user:
            users_by_branch.setdefault(row.parent, []).append(row.user)

    hr_email_map = {}
    for row in department_branches:
        hr_email_map.setdefault(row.department, []).extend(
            users_by_branch.get(row.branch, [])
        )
    return hr_email_map


def render_absent_table(absent_rows):
    if not absent_rows:
        return ""

    rows_html = "".join(
        f"""
		<tr>
			<td>{i}</td>
			<td>{escape_html(r['employee_name'])}</td>
			<td>{escape_html(r['employee_id'])}</td>
			<td>{escape_html(r['shift'])}</td>
		</tr>"""
        for i, r in enumerate(absent_rows, start=1)
    )

    return f"""
	<h4 style="margin-top:16px;">{_("Absent")}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{_("Sr No")}</th><th>{_("Employee Name")}</th><th>{_("Employee ID")}</th><th>{_("Shift")}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	"""


def render_leave_table(leave_rows):
    if not leave_rows:
        return ""

    rows_html = "".join(
        f"""
		<tr>
			<td>{i}</td>
			<td>{escape_html(r['employee_name'])}</td>
			<td>{escape_html(r['employee_id'])}</td>
			<td>{escape_html(r['leave_type'])}</td>
			<td>{r['from_date']}</td>
			<td>{r['to_date']}</td>
		</tr>"""
        for i, r in enumerate(leave_rows, start=1)
    )

    return f"""
	<h4 style="margin-top:16px;">{_("On Leave")}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{_("Sr No")}</th><th>{_("Employee Name")}</th><th>{_("Employee ID")}</th><th>{_("Leave Type")}</th>
				<th>{_("From Date")}</th><th>{_("To Date")}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	"""


def render_email_html(department, date, rows, leave_rows, absent_rows, summary):
    rows_html = "".join(
        f"""
		<tr>
			<td>{i}</td>
			<td>{escape_html(r['employee_name'])}</td>
			<td>{escape_html(r['employee_id'])}</td>
			<td>{escape_html(r['department'])}</td>
			<td>{escape_html(r['shift'])}</td>
			<td>{r['in_time']}</td>
			<td>{r['out_time']}</td>
			<td>{escape_html(r['status'])}</td>
			<td>{escape_html(r['late_entry'])}</td>
		</tr>"""
        for i, r in enumerate(rows, start=1)
    ) or "<tr><td colspan='9' style='text-align:center;'>{0}</td></tr>".format(
        _("No employees present")
    )

    return f"""
	<h3>{_("Present Report")} — {escape_html(department)} — {formatdate(date, "dd-mm-yyyy")}</h3>
	<p>{frappe.local.site}</p>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{_("Sr No")}</th><th>{_("Employee Name")}</th><th>{_("Employee ID")}</th><th>{_("Department")}</th>
				<th>{_("Shift")}</th><th>{_("In Time")}</th><th>{_("Out Time")}</th>
				<th>{_("Attendance Status")}</th><th>{_("Late Entry")}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	{render_leave_table(leave_rows)}
	{render_absent_table(absent_rows)}
	<h4 style="margin-top:16px;">{_("Department Summary")}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>{_("Total Employees")}</td><td>{summary['Total Employees']}</td></tr>
		<tr><td>{_("Present")}</td><td>{summary['Present']}</td></tr>
		<tr><td>{_("Absent")}</td><td>{summary['Absent']}</td></tr>
		<tr><td>{_("Leave")}</td><td>{summary['On Leave']}</td></tr>
		<tr><td>{_("Late Entry")}</td><td>{summary['Late Entry']}</td></tr>
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

    manager_email_map = get_department_manager_email_map(department)
    departments = [department] if department else list(manager_email_map)

    rows_by_department = {}
    for row in build_employee_rows(get_active_employees(departments), date):
        rows_by_department.setdefault(row.department, []).append(row)

    branch_hr_email_map = get_branch_hr_email_map(departments)

    sent = []
    skipped = []

    for dept in departments:
        try:
            department_rows = rows_by_department.get(dept)
            if not department_rows:
                skipped.append(dept)
                continue

            rows = [r for r in department_rows if r.is_present]
            leave_rows = [r for r in department_rows if r.is_on_leave]
            absent_rows = [r for r in department_rows if r.is_absent]
            summary = get_summary(department_rows)

            manager_emails = manager_email_map.get(dept)
            if not manager_emails:
                frappe.log_error(
                    title="Morning Present Report — no manager in custom_user_group",
                    message=f"Department: {dept}",
                )
                skipped.append(dept)
                continue
            manager_string = ", ".join(manager_emails)

            hr_emails = branch_hr_email_map.get(dept, [])
            fixed_cc = ["angat_p@gkexport.com"]
            cc = [
                e
                for e in dict.fromkeys(fixed_cc + hr_emails)
                if e not in manager_emails
            ]

            html = render_email_html(dept, date, rows, leave_rows, absent_rows, summary)
            frappe.sendmail(
                recipients=manager_string,
                cc=cc,
                sender="alerts@gkexport.com",
                subject=f"Present Report — {dept} — {formatdate(date, 'dd-mm-yyyy')}",
                message=html,
                now=True,
                expose_recipients="header",
            )
            sent.append({"department": dept, "managers": manager_emails})
        except Exception:
            frappe.log_error(
                title=f"Morning Present Report failed for {dept}",
                message=frappe.get_traceback(),
            )
            continue

    return {"sent": sent, "skipped": skipped}
