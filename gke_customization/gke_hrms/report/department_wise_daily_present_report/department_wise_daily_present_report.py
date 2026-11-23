# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import escape_html, format_time, formatdate, get_datetime, nowdate

from gke_customization.gke_hrms.report.department_wise_daily_utils import (
    get_departments_with_managers,
    get_employee_checkins_for_date,
    get_in_out_and_shift,
    get_manager_departments,
    send_department_report_emails,
)

MORNING_PRESENT_FIXED_CC = ["angat_p@gkexport.com"]


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


def get_employees_on_leave(employee_ids, date):
    """Approved Leave Applications covering `date`, keyed by employee."""
    if not employee_ids:
        return {}

    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": ["in", employee_ids],
            "status": "Approved",
            "from_date": ["<=", date],
            "to_date": [">=", date],
            "docstatus": 1,
        },
        fields=["employee", "leave_type", "from_date", "to_date"],
    )
    return {leave.employee: leave for leave in leaves}


def get_shift_type_map(shift_names):
    if not shift_names:
        return {}

    shift_types = frappe.get_all(
        "Shift Type",
        filters={"name": ["in", list(shift_names)]},
        fields=[
            "name",
            "start_time",
            "enable_late_entry_marking",
            "late_entry_grace_period",
        ],
    )
    return {shift_type.name: shift_type for shift_type in shift_types}


def is_late_entry(shift, in_time, date):
    """Compare in_time against the Shift Type start_time plus the grace period, if enabled."""
    if not shift or not in_time or shift.start_time is None:
        return False

    shift_start = get_datetime(f"{date} 00:00:00") + shift.start_time
    grace_minutes = shift.late_entry_grace_period or 0
    if not shift.enable_late_entry_marking:
        grace_minutes = 0

    threshold = shift_start + timedelta(minutes=grace_minutes)
    return get_datetime(in_time) > threshold


def get_rows_by_department(departments, date):
    """Return ({department: [rows]}, {employee: leave}) for the active employees of the given departments.

    Rows keep the Employee list order within each department.
    """
    if not departments:
        return {}, {}

    employees = frappe.get_all(
        "Employee",
        filters={"department": ["in", departments], "status": "Active"},
        fields=["name", "employee_name", "default_shift", "company", "department"],
    )
    if not employees:
        return {}, {}

    employee_ids = [employee.name for employee in employees]
    leave_by_employee = get_employees_on_leave(employee_ids, date)
    checkins_by_employee = get_employee_checkins_for_date(employee_ids, date)

    in_out_and_shift_by_employee = {
        employee: get_in_out_and_shift(checkins)
        for employee, checkins in checkins_by_employee.items()
    }
    shift_names = {
        employee.default_shift for employee in employees if employee.default_shift
    }
    shift_names.update(
        shift for _in, _out, shift in in_out_and_shift_by_employee.values() if shift
    )
    shift_type_map = get_shift_type_map(shift_names)

    rows_by_department = {}
    for employee in employees:
        row = build_employee_row(
            employee,
            date,
            leave_by_employee.get(employee.name),
            in_out_and_shift_by_employee.get(employee.name, (None, None, None)),
            shift_type_map,
        )
        rows_by_department.setdefault(employee.department, []).append(row)

    return rows_by_department, leave_by_employee


def build_employee_row(employee, date, leave, in_out_and_shift, shift_type_map):
    row = {
        "employee_id": employee.name,
        "employee_name": employee.employee_name,
        "department": employee.department,
        "company": employee.company,
    }

    if leave:
        row.update(
            {
                "shift": "",
                "in_time": "",
                "out_time": "",
                "status": "On Leave",
                "late_entry": "",
                "leave_type": leave.leave_type or "",
            }
        )
        return row

    in_time, out_time, checkin_shift = in_out_and_shift
    if not in_time:
        row.update(
            {
                "shift": employee.default_shift or "",
                "in_time": "",
                "out_time": "",
                "status": "Absent",
                "late_entry": "",
                "leave_type": "",
            }
        )
        return row

    shift = checkin_shift or employee.default_shift
    late = is_late_entry(shift_type_map.get(shift), in_time, date)
    row.update(
        {
            "shift": shift or "",
            "in_time": format_time(get_datetime(in_time)),
            "out_time": format_time(get_datetime(out_time)) if out_time else "-",
            "status": "Present",
            "late_entry": "Yes" if late else "No",
            "leave_type": "",
        }
    )
    return row


def build_summary_rows(data):
    total = len(data)
    present = sum(1 for row in data if row["status"] == "Present")
    absent = sum(1 for row in data if row["status"] == "Absent")
    leave = sum(1 for row in data if row["status"] == "On Leave")
    late = sum(1 for row in data if row["late_entry"] == "Yes")

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

    department_filters = {"disabled": 0}
    if company:
        department_filters["company"] = company
    if department:
        department_filters["name"] = department

    allowed_departments = None
    if manager:
        user_id = frappe.db.get_value("Employee", manager, "user_id")
        allowed_departments = get_manager_departments(user_id) or []

    departments = frappe.get_all(
        "Department", filters=department_filters, pluck="name", order_by="name asc"
    )
    if allowed_departments is not None:
        departments = [dept for dept in departments if dept in allowed_departments]

    rows_by_department, _leave_by_employee = get_rows_by_department(departments, date)

    data = []
    for dept in departments:
        rows = rows_by_department.get(dept, [])
        rows.sort(key=lambda row: row["employee_name"] or "")
        data.extend(rows)

    data.extend(build_summary_rows(data))

    return get_columns(), data


def build_department_email_report(rows, leave_by_employee):
    """Return (present_rows, leave_rows, absent_rows, summary) for one department's rows, or None if empty."""
    if not rows:
        return None

    present_rows = [row for row in rows if row["status"] == "Present"]
    absent_rows = [row for row in rows if row["status"] == "Absent"]
    leave_rows = []
    for row in rows:
        if row["status"] != "On Leave":
            continue
        leave = leave_by_employee[row["employee_id"]]
        leave_rows.append(
            {
                "employee_name": row["employee_name"],
                "employee_id": row["employee_id"],
                "leave_type": row["leave_type"],
                "from_date": leave.from_date,
                "to_date": leave.to_date,
            }
        )

    summary = {
        "Total Employees": len(rows),
        "Present": len(present_rows),
        "Absent": len(absent_rows),
        "On Leave": len(leave_rows),
        "Late Entry": sum(1 for row in present_rows if row["late_entry"] == "Yes"),
    }
    return present_rows, leave_rows, absent_rows, summary


def render_table_rows(rows, fields):
    return "".join(
        """
		<tr>
			<td>{0}</td>
			{1}
		</tr>""".format(
            index,
            "\n\t\t\t".join(
                "<td>{0}</td>".format(escape_html(row[field])) for field in fields
            ),
        )
        for index, row in enumerate(rows, start=1)
    )


def render_absent_table(absent_rows):
    if not absent_rows:
        return ""

    return """
	<h4 style="margin-top:16px;">{heading}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{sr_no_label}</th><th>{employee_name_label}</th><th>{employee_id_label}</th><th>{shift_label}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	""".format(
        heading=_("Absent"),
        sr_no_label=_("Sr No"),
        employee_name_label=_("Employee Name"),
        employee_id_label=_("Employee ID"),
        shift_label=_("Shift"),
        rows_html=render_table_rows(
            absent_rows, ("employee_name", "employee_id", "shift")
        ),
    )


def render_leave_table(leave_rows):
    if not leave_rows:
        return ""

    return """
	<h4 style="margin-top:16px;">{heading}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{sr_no_label}</th><th>{employee_name_label}</th><th>{employee_id_label}</th><th>{leave_type_label}</th>
				<th>{from_date_label}</th><th>{to_date_label}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	""".format(
        heading=_("On Leave"),
        sr_no_label=_("Sr No"),
        employee_name_label=_("Employee Name"),
        employee_id_label=_("Employee ID"),
        leave_type_label=_("Leave Type"),
        from_date_label=_("From Date"),
        to_date_label=_("To Date"),
        rows_html=render_table_rows(
            leave_rows,
            ("employee_name", "employee_id", "leave_type", "from_date", "to_date"),
        ),
    )


def render_email_html(department, date, rows, leave_rows, absent_rows, summary):
    present_fields = (
        "employee_name",
        "employee_id",
        "department",
        "shift",
        "in_time",
        "out_time",
        "status",
        "late_entry",
    )
    rows_html = render_table_rows(
        rows, present_fields
    ) or "<tr><td colspan='9' style='text-align:center;'>{0}</td></tr>".format(
        _("No employees present")
    )

    return """
	<h3>Present Report - {department} - {date}</h3>
	<p>{site}</p>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{sr_no_label}</th><th>{employee_name_label}</th><th>{employee_id_label}</th><th>{department_label}</th>
				<th>{shift_label}</th><th>{in_time_label}</th><th>{out_time_label}</th>
				<th>{attendance_status_label}</th><th>{late_entry_label}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	{leave_table}
	{absent_table}
	<h4 style="margin-top:16px;">{summary_label}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>{total_employees_label}</td><td>{total_employees}</td></tr>
		<tr><td>{present_label}</td><td>{present}</td></tr>
		<tr><td>{absent_label}</td><td>{absent}</td></tr>
		<tr><td>{leave_label}</td><td>{on_leave}</td></tr>
		<tr><td>{late_entry_label}</td><td>{late_entry}</td></tr>
	</table>
	""".format(
        department=escape_html(department),
        date=formatdate(date, "dd-mm-yyyy"),
        site=escape_html(frappe.local.site),
        rows_html=rows_html,
        leave_table=render_leave_table(leave_rows),
        absent_table=render_absent_table(absent_rows),
        sr_no_label=_("Sr No"),
        employee_name_label=_("Employee Name"),
        employee_id_label=_("Employee ID"),
        department_label=_("Department"),
        shift_label=_("Shift"),
        in_time_label=_("In Time"),
        out_time_label=_("Out Time"),
        attendance_status_label=_("Attendance Status"),
        late_entry_label=_("Late Entry"),
        summary_label=_("Department Summary"),
        total_employees_label=_("Total Employees"),
        present_label=_("Present"),
        absent_label=_("Absent"),
        leave_label=_("Leave"),
        total_employees=summary["Total Employees"],
        present=summary["Present"],
        absent=summary["Absent"],
        on_leave=summary["On Leave"],
        late_entry=summary["Late Entry"],
    )


@frappe.whitelist()
def send_morning_present_report(date=None, department=None):
    """Email the present report to the managers of each department.

    department=None sends to every department that has a manager in custom_user_group,
    department=<name> sends to that one only.
    Returns {"sent": [...], "skipped": [...]} for the report's Send Mail button.
    """
    date = date or nowdate()
    departments = get_departments_with_managers(department)
    rows_by_department, leave_by_employee = get_rows_by_department(departments, date)

    def build_report(dept):
        return build_department_email_report(
            rows_by_department.get(dept), leave_by_employee
        )

    def render_html(dept, report):
        rows, leave_rows, absent_rows, summary = report
        return render_email_html(dept, date, rows, leave_rows, absent_rows, summary)

    def get_subject(dept):
        return "Present Report - {0} - {1}".format(dept, formatdate(date, "dd-mm-yyyy"))

    return send_department_report_emails(
        departments=departments,
        build_report=build_report,
        render_html=render_html,
        get_subject=get_subject,
        log_title="Morning Present Report - no manager in custom_user_group",
        fixed_cc=MORNING_PRESENT_FIXED_CC,
    )
