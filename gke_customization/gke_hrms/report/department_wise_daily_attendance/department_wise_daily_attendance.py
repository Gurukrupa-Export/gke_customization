# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
from datetime import time as dtime

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Date, Max, Min
from frappe.utils import add_days, escape_html, formatdate, get_time, getdate, today

from gke_customization.gke_hrms.report.department_wise_daily_utils import (
    get_departments_with_managers,
    get_manager_departments,
    send_department_report_emails,
)

DAILY_ATTENDANCE_FIXED_CC = ["angat_p@gkexport.com"]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("date"):
        filters.date = today()

    columns = get_columns()
    data, summary = get_data(filters)
    report_summary = get_report_summary(summary, get_report_date(filters))

    return columns, data, None, None, report_summary


def get_report_date(filters=None):
    """Return the filter date, or yesterday when no date is given (the scheduler default)."""
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

        elif cnt % 2 != 0:
            # odd number of punches means the last in/out isn't paired
            # (forgot to check out, or an odd extra punch) - needs manual review
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
                half_day_threshold is not None
                and worked is not None
                and worked < half_day_threshold
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


def render_email_html(department, date, rows, summary):
    row_fields = (
        "employee_name",
        "employee",
        "shift",
        "in_time",
        "out_time",
        "status",
        "late_entry",
        "early_exit",
        "remark",
    )
    rows_html = "".join(
        """
		<tr>
			{0}
		</tr>""".format(
            "\n\t\t\t".join(
                "<td>{0}</td>".format(escape_html(row[field])) for field in row_fields
            )
        )
        for row in rows
    ) or "<tr><td colspan='9' style='text-align:center;'>{0}</td></tr>".format(
        _("No employees found")
    )

    return """
	<h3>Daily Attendance Report - {department} - {date}</h3>
	<p>{site}</p>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:13px;">
		<thead style="background:#f2f2f2;">
			<tr>
				<th>{employee_name_label}</th><th>{employee_id_label}</th><th>{shift_label}</th>
				<th>{in_time_label}</th><th>{out_time_label}</th>
				<th>{status_label}</th><th>{late_entry_label}</th><th>{early_exit_label}</th><th>{remark_label}</th>
			</tr>
		</thead>
		<tbody>{rows_html}</tbody>
	</table>
	<h4 style="margin-top:16px;">{summary_label}</h4>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
		<tr><td>{total_employees_label}</td><td>{total_employees}</td></tr>
		<tr><td>{present_label}</td><td>{present}</td></tr>
		<tr><td>{absent_label}</td><td>{absent}</td></tr>
		<tr><td>{half_day_label}</td><td>{half_day}</td></tr>
		<tr><td>{late_entry_label}</td><td>{late_entry}</td></tr>
		<tr><td>{early_exit_label}</td><td>{early_exit}</td></tr>
		<tr><td>{error_label}</td><td>{error}</td></tr>
	</table>
	""".format(
        department=escape_html(department),
        date=formatdate(date, "dd-mm-yyyy"),
        site=escape_html(frappe.local.site),
        rows_html=rows_html,
        employee_name_label=_("Employee Name"),
        employee_id_label=_("Employee ID"),
        shift_label=_("Shift"),
        in_time_label=_("In Time"),
        out_time_label=_("Out Time"),
        status_label=_("Status"),
        late_entry_label=_("Late Entry"),
        early_exit_label=_("Early Exit"),
        remark_label=_("Remark"),
        summary_label=_("Department Summary"),
        total_employees_label=_("Total Employees"),
        present_label=_("Present"),
        absent_label=_("Absent"),
        half_day_label=_("Half Day"),
        error_label=_("Error"),
        **summary,
    )


@frappe.whitelist()
def send_daily_attendance_report(date=None, department=None):
    """Email this report to the managers of each department.

    department=None sends to every department that has a manager in custom_user_group,
    department=<name> sends to that one only.
    Returns {"sent": [...], "skipped": [...]} for the report's Send Mail button.
    """
    date = date or get_report_date()

    def build_report(dept):
        rows, summary = get_data(frappe._dict({"department": dept, "date": date}))
        if not rows:
            return None
        return rows, summary

    def render_html(dept, report):
        rows, summary = report
        return render_email_html(dept, date, rows, summary)

    def get_subject(dept):
        return "Daily Attendance Report - {0} - {1}".format(
            dept, formatdate(date, "dd-mm-yyyy")
        )

    return send_department_report_emails(
        departments=get_departments_with_managers(department),
        build_report=build_report,
        render_html=render_html,
        get_subject=get_subject,
        log_title="Daily Attendance Report - no manager in custom_user_group",
        fixed_cc=DAILY_ATTENDANCE_FIXED_CC,
    )
