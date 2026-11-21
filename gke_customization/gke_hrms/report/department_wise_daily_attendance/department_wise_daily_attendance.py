# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
from datetime import time as dtime

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Date, Max, Min
from frappe.utils import add_days, escape_html, formatdate, get_time, getdate, today


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

    attendance_maps = get_attendance_maps(date, [e.name for e in employees])
    return build_attendance_rows(employees, attendance_maps)


def get_attendance_maps(date, employee_names):
    return frappe._dict(
        shift_type_map=get_shift_type_map(),
        checkin_map=get_checkin_details_map(date, employee_names),
        remark_map=get_remark_map(date, employee_names),
    )


def build_attendance_rows(employees, attendance_maps):
    shift_type_map = attendance_maps.shift_type_map
    checkin_map = attendance_maps.checkin_map
    remark_map = attendance_maps.remark_map

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
            row["status"] = _("Absent")
            summary["absent"] += 1

        elif cnt % 2 != 0:
            # odd number of punches means the last in/out isn't paired
            # (forgot to check out, or an odd extra punch) - needs manual review
            row["status"] = _("Error")
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
                half_day_threshold is not None
                and worked is not None
                and worked < half_day_threshold
            ):
                # came in after the first-half cutoff (can never make the
                # threshold hours within the shift), or simply worked fewer
                # hours than the threshold -> Half Day either way
                row["status"] = _("Half Day")
                summary["half_day"] += 1
            else:
                row["status"] = _("Present")
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
    """Departments where `user_id` is listed in custom_user_group. Returns None when there is no user_id."""
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


def get_shift_type_map():
    ShiftType = frappe.qb.DocType("Shift Type")

    rows = (
        frappe.qb.from_(ShiftType).select(
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
            & ~(
                (EmployeeCheckin.skip_auto_attendance == "1")
                & (
                    (EmployeeCheckin.attendance.isnull())
                    | (EmployeeCheckin.attendance == "")
                )
            )
        )
        .groupby(EmployeeCheckin.employee)
    ).run(as_dict=True)

    return {row.employee: row for row in rows}


def get_remark_map(date, employee_names):
    """employee -> list of remarks, e.g. ["OT Request", "Attendance Request (On Duty)"]."""
    remark_map = {}

    for emp in get_ot_request_employees(date, employee_names):
        remark_map.setdefault(emp, []).append(_("OT Request"))

    for emp, reason in get_attendance_request_employees(date, employee_names):
        label = (
            _("Attendance Request ({0})").format(reason)
            if reason
            else _("Attendance Request")
        )
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
        {
            "label": _("Total Employees"),
            "value": summary["total_employees"],
            "indicator": "Blue",
            "datatype": "Int",
        },
        {
            "label": _("Present"),
            "value": summary["present"],
            "indicator": "Green",
            "datatype": "Int",
        },
        {
            "label": _("Absent"),
            "value": summary["absent"],
            "indicator": "Red",
            "datatype": "Int",
        },
        {
            "label": _("Half Day"),
            "value": summary["half_day"],
            "indicator": "Yellow",
            "datatype": "Int",
        },
        {
            "label": _("Late Entry"),
            "value": summary["late_entry"],
            "indicator": "Orange",
            "datatype": "Int",
        },
        {
            "label": _("Early Exit"),
            "value": summary["early_exit"],
            "indicator": "Orange",
            "datatype": "Int",
        },
        {
            "label": _("Error"),
            "value": summary["error"],
            "indicator": "Red",
            "datatype": "Int",
        },
    ]


# ---------------------------------------------------------------------------
# Send Mail button - emails this report to each department's manager(s)
# ---------------------------------------------------------------------------
def get_branch_hr_email_map(departments):
    """department -> HR users (Branch.custom_user_group) for every branch that has an
    active employee in that department."""
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


def render_email_html(department, date, rows, summary):
    rows_html = (
        "".join(
            f"""
		<tr>
			<td>{escape_html(r['employee_name'])}</td>
			<td>{escape_html(r['employee'])}</td>
			<td>{escape_html(r['shift'])}</td>
			<td>{r['in_time']}</td>
			<td>{r['out_time']}</td>
			<td>{escape_html(r['status'])}</td>
			<td>{r['late_entry']}</td>
			<td>{r['early_exit']}</td>
			<td>{escape_html(r['remark'])}</td>
		</tr>"""
            for r in rows
        )
        or f"<tr><td colspan='9' style='text-align:center;'>{_('No employees found')}</td></tr>"
    )

    return f"""
	<h3>{_("Daily Attendance Report")} — {escape_html(department)} — {formatdate(date, "dd-mm-yyyy")}</h3>
	<p>{frappe.local.site}</p>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{_("Employee Name")}</th><th>{_("Employee ID")}</th><th>{_("Shift")}</th>
				<th>{_("In Time")}</th><th>{_("Out Time")}</th>
				<th>{_("Status")}</th><th>{_("Late Entry")}</th><th>{_("Early Exit")}</th><th>{_("Remark")}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	<h4 style="margin-top:16px;">{_("Department Summary")}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>{_("Total Employees")}</td><td>{summary['total_employees']}</td></tr>
		<tr><td>{_("Present")}</td><td>{summary['present']}</td></tr>
		<tr><td>{_("Absent")}</td><td>{summary['absent']}</td></tr>
		<tr><td>{_("Half Day")}</td><td>{summary['half_day']}</td></tr>
		<tr><td>{_("Late Entry")}</td><td>{summary['late_entry']}</td></tr>
		<tr><td>{_("Early Exit")}</td><td>{summary['early_exit']}</td></tr>
		<tr><td>{_("Error")}</td><td>{summary['error']}</td></tr>
	</table>
	"""


@frappe.whitelist()
def send_daily_attendance_report(date=None, department=None):
    """Emails this report to each matching department's manager(s).
    department=None -> every department that has a manager set in
    custom_user_group. department=<name> -> just that one.
    Returns {"sent": [...], "skipped": [...]} so the caller (the report's
    Send Mail button) can show what actually happened."""

    date = getdate(date) if date else get_report_date()

    manager_email_map = get_department_manager_email_map(department)
    departments = [department] if department else list(manager_email_map)

    employees_by_department = {}
    for emp in get_employees(frappe._dict({"department": department})):
        if emp.department in departments:
            employees_by_department.setdefault(emp.department, []).append(emp)

    employee_names = [
        emp.name for employees in employees_by_department.values() for emp in employees
    ]
    attendance_maps = (
        get_attendance_maps(date, employee_names) if employee_names else None
    )
    branch_hr_email_map = get_branch_hr_email_map(departments) if departments else {}

    sent = []
    skipped = []

    for dept in departments:
        try:
            department_employees = employees_by_department.get(dept)
            if not department_employees:
                skipped.append(dept)
                continue

            rows, summary = build_attendance_rows(department_employees, attendance_maps)

            manager_emails = manager_email_map.get(dept)
            if not manager_emails:
                frappe.log_error(
                    title="Daily Attendance Report — no manager in custom_user_group",
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

            html = render_email_html(dept, date, rows, summary)
            frappe.sendmail(
                recipients=manager_string,
                cc=cc,
                sender="alerts@gkexport.com",
                subject=f"Daily Attendance Report — {dept} — {formatdate(date, 'dd-mm-yyyy')}",
                message=html,
                now=True,
                expose_recipients="header",
            )
            sent.append({"department": dept, "managers": manager_emails})
        except Exception:
            frappe.log_error(
                title=f"Daily Attendance Report failed for {dept}",
                message=frappe.get_traceback(),
            )
            continue

    return {"sent": sent, "skipped": skipped}
