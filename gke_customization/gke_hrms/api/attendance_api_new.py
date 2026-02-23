# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, get_datetime, add_to_date, get_time, format_time, flt
from datetime import timedelta
from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date

STATUS = {
	"Absent": "A",
	"Present": "P",
	"Half Day": "HD",
	"Privilege Leave": "PL",
	"Casual Leave": "CL",
	"Sick Leave": "SL",
	"Leave Without Pay": "LWP",
	"Outdoor Duty": "OD",
	"Work From Home": "WFH",
	"Maternity Leave": "ML",
    "Marraige Leavve": "ML"
}


@frappe.whitelist(allow_guest=True)
def attendance(from_date=None, to_date=None, employee=None):

	if not from_date or not to_date or not employee:
		return []

	if not frappe.db.exists("Employee", employee):
		return []

	filters = {
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"company": frappe.db.get_value("Employee", employee, "company")
	}
	data = get_data(filters)
	return data


def get_date_range(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not from_date or not to_date:
        return []

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    date_list = []
    current_date = from_date

    while current_date <= to_date:
        date_list.append(current_date)
        current_date = add_days(current_date, 1)

    return date_list


def get_employee_holiday_and_weekoff(employee, company, from_date, to_date):
    hl_name = frappe.db.get_value("Employee", employee, "holiday_list")

    # fallback to shift holiday list
    if not hl_name:
        shift_type = frappe.db.get_value("Employee", employee, "default_shift")
        if shift_type:
            hl_name = frappe.db.get_value("Shift Type", shift_type, "holiday_list")

    # fallback to company default holiday list
    if not hl_name and company:
        hl_name = frappe.db.get_value("Company", company, "default_holiday_list")

    if not hl_name:
        return [], []

    holidays = frappe.get_all(
        "Holiday",
        {"parent": hl_name, "holiday_date": ["between", [from_date, to_date]]},
        ["holiday_date", "weekly_off"],
        ignore_permissions=1
    )

    wo = [row.holiday_date for row in holidays if row.weekly_off]
    holiday_dates = [row.holiday_date for row in holidays if not row.weekly_off]

    return holiday_dates, wo


def get_employee_shift(employee, date):
    # shift assignment for specific date
    shift_type = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": employee,
            "start_date": ["<=", date],
			"status": "Active",
            "docstatus": 1
        },
        "shift_type",
        order_by="start_date desc"
    )

    if not shift_type:
        shift_type = frappe.db.get_value("Employee", employee, "default_shift")

    if not shift_type:
        return None, None, None

    start_time, end_time = frappe.db.get_value("Shift Type", shift_type, ["start_time", "end_time"])

    return start_time, end_time, shift_type


def get_employee_checkins(employee, date):
    start_time, end_time, shift_type = get_employee_shift(employee, date)

    attendance = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date, "docstatus": 1})
    attendance_data = {}
    if attendance:
        attendance_data = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": date, "docstatus": 1}, ["name", "in_time", "out_time"], as_dict=1)

    if attendance_data and attendance_data.get("in_time") and attendance_data.get("out_time"):
        start_dt = get_datetime(attendance_data.in_time)
        end_dt = get_datetime(attendance_data.out_time)
    # fallback if shift not found
    elif not start_time or not end_time:
        start_dt = get_datetime(str(date) + " 00:00:00")
        end_dt = add_to_date(start_dt, days=1)
    else:
        start_dt = get_datetime(f"{date} {start_time}")
        end_dt = get_datetime(f"{date} {end_time}")

        # night shift handling
        if get_time(end_time) < get_time(start_time):
            end_dt = add_to_date(end_dt, days=1)

        # add buffer (important)
        start_dt = add_to_date(start_dt, minutes=-90)  # -1.5 hrs buffer
        end_dt = add_to_date(end_dt, minutes=90)       # +1.5 hrs buffer

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [start_dt, end_dt]]
        },
        fields=["time", "log_type"],
        order_by="time asc"
    )

    in_times = []
    out_times = []

    for i, row in enumerate(checkins):
        if i % 2 == 0:
            in_times.append(row.time.strftime("%H:%M:%S"))
        else:
            out_times.append(row.time.strftime("%H:%M:%S"))

    error_status = ""
    if len(checkins) % 2 != 0:
        error_status = "ERR"

    return in_times, out_times, error_status


def get_holiday_weekoff_map(employee_list, company, from_date, to_date):
	"""
	Returns:
	{
		"EMP-0001": {"holidays": [...], "weekoffs": [...]},
		"EMP-0002": {"holidays": [...], "weekoffs": [...]}
	}
	"""

	if not employee_list:
		return {}

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	# 1) Fetch employee holiday_list + default_shift
	employees = frappe.get_all(
		"Employee",
		filters={"name": ["in", employee_list]},
		fields=["name", "holiday_list", "default_shift"],
		ignore_permissions=1
	)

	emp_map = {e.name: e for e in employees}

	# 2) Fetch shift holiday_list
	shift_types = list({e.default_shift for e in employees if e.default_shift})

	shift_map = {}
	if shift_types:
		shifts = frappe.get_all(
			"Shift Type",
			filters={"name": ["in", shift_types]},
			fields=["name", "holiday_list"],
			ignore_permissions=1
		)
		shift_map = {s.name: s.holiday_list for s in shifts}

	# 3) Company fallback holiday list
	company_holiday_list = None
	if company:
		company_holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	# 4) Resolve holiday list per employee
	emp_holiday_list = {}
	for emp in employee_list:
		row = emp_map.get(emp)

		hl = row.holiday_list if row and row.holiday_list else None

		if not hl and row and row.default_shift:
			hl = shift_map.get(row.default_shift)

		if not hl:
			hl = company_holiday_list

		emp_holiday_list[emp] = hl

	# 5) Unique holiday lists
	holiday_lists = list({hl for hl in emp_holiday_list.values() if hl})

	holiday_map = {emp: {"holidays": [], "weekoffs": []} for emp in employee_list}

	if not holiday_lists:
		return holiday_map

	# 6) Fetch all holidays in one query
	holidays = frappe.get_all(
		"Holiday",
		filters={
			"parent": ["in", holiday_lists],
			"holiday_date": ["between", [from_date, to_date]]
		},
		fields=["parent", "holiday_date", "weekly_off"],
		order_by="holiday_date asc",
		ignore_permissions=1
	)

	# 7) Group by holiday list
	holiday_list_map = {}

	for row in holidays:
		if row.parent not in holiday_list_map:
			holiday_list_map[row.parent] = {"holidays": [], "weekoffs": []}

		if row.weekly_off:
			holiday_list_map[row.parent]["weekoffs"].append(row.holiday_date)
		else:
			holiday_list_map[row.parent]["holidays"].append(row.holiday_date)

	# 8) Assign holiday/weekoff per employee
	for emp, hl in emp_holiday_list.items():
		if hl and hl in holiday_list_map:
			holiday_map[emp] = holiday_list_map[hl]

	return holiday_map


def _format_time_value(val):
    """Format timedelta/time-like value to HH:MM:SS string or None."""
    if val is None:
        return None
    if isinstance(val, timedelta):
        total_secs = int(val.total_seconds())
        if total_secs == 0:
            return "0:00:00"
        h = total_secs // 3600
        m = (total_secs % 3600) // 60
        s = total_secs % 60
        return f"{h}:{m:02d}:{s:02d}"
    return str(val) if val else None


def get_data(filters):
	employee = filters.get("employee")
	company = filters.get("company")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not employee or not from_date or not to_date:
		frappe.throw("Please select Employee, From Date and To Date")
		return []


	date_range = get_date_range(filters)
	employee_list = [employee]
	holiday_map = get_holiday_weekoff_map(employee_list, company, from_date, to_date)

	# Fetch employee details once (not per date)
	employee_details = frappe.db.get_value(
		"Employee", employee,
		[
			"employee_name", "company", "branch", "department", "designation",
			"old_punch_id", "middle_name", "gender", "date_of_birth",
			"date_of_joining", "allowed_personal_hours", "default_shift"
		],
		as_dict=1
	) or {}

	# Fetch OT approval details from OT Log
	ot_details = frappe.get_all(
		"OT Log",
		{
			"employee": employee,
			"attendance_date": ["in", date_range],
			"is_cancelled": 0,
			"allow": 1
		},
		["attendance_date", "allow", "allowed_ot"]
	)

	ot_details_map = {
		row.attendance_date: {
			"hrs": row.allowed_ot,
			"allow": row.allow
		}
		for row in ot_details
	}

	# Get shift details for OT resolution
	default_shift = employee_details.get("default_shift")
	shift_det = None
	if default_shift:
		shift_det = frappe.db.get_value(
			"Shift Type", default_shift,
			["start_time", "end_time", "shift_hours"],
			as_dict=1
		)

	attendance_details = {}

	for emp in employee_list:
		attendance_details[emp] = {}

		for date in date_range:
			res = get_attendance_details_by_date(company, emp, date) or frappe._dict()

			if res and res.get("records", []):
				data = res.get("records")[0]
				attendance_details[emp][date] = data
			else:
				attendance_details[emp][date] = {}

	final_data = process_data(attendance_details, date_range, holiday_map, employee_details, ot_details_map, shift_det)

	return final_data


def process_data(attendance_details, date_range, holiday_map, employee_details, ot_details_map, shift_det):
	report_data = []

	for emp, emp_dates in attendance_details.items():
		emp_holidays = holiday_map.get(emp, {}).get("holidays", [])
		emp_weekoffs = holiday_map.get(emp, {}).get("weekoffs", [])

		for date in date_range:
			record = emp_dates.get(date, {}) or {}

			attendance_status = record.get("status")

			if not attendance_status:
				if date in emp_holidays:
					attendance_status = "H"
				elif date in emp_weekoffs:
					attendance_status = "WO"
				else:
					attendance_status = "XX"

			if attendance_status not in ['Absent', 'On Leave']:
				all_in_times, all_out_times, error_status = get_employee_checkins(emp, date)
				attendance_status = error_status if error_status else attendance_status
			else:
				all_in_times, all_out_times = [], []

			# Resolve "On Leave" back to actual leave type for STATUS mapping
			if attendance_status == "On Leave":
				leave_type = frappe.db.get_value(
					"Attendance",
					{"employee": emp, "attendance_date": date, "docstatus": 1},
					"leave_type"
				)
				if leave_type:
					attendance_status = leave_type

			start_time, end_time, assigned_shift_type = get_employee_shift(emp, date)

			# Build shift display string
			if start_time and end_time:
				shift_display = f"{format_time(start_time)} TO {format_time(end_time)}"
			else:
				shift_display = record.get("shift_type") or ""

			# Determine in_time and out_time
			# Use checkin-based times if available, otherwise fall back to record data
			if all_in_times:
				in_time = all_in_times[0]
			else:
				in_time = _format_time_value(record.get("in_time"))

			if all_out_times:
				out_time = all_out_times[-1]
			else:
				out_time = _format_time_value(record.get("out_time"))

			# ------------------------------------------------------------------
			# Resolve OT hours for this date
			# ------------------------------------------------------------------
			# Get shift end time for OT calculation
			ot_shift_end = get_time(end_time) if end_time else (get_time(shift_det.end_time) if shift_det else None)

			# Default predefined OT from OT Details (if exists & approved)
			predefined_ot_hrs = None
			ot_detail = ot_details_map.get(date)

			if ot_detail and ot_detail.get("allow") == 1:
				predefined_ot_hrs = ot_detail.get("hrs")

			# Call OT resolve
			ot_hours, ot_status = resolve_ot_hours(
				attendance_date=date,
				shift_in_time=start_time,
				shift_end_time=ot_shift_end,
				in_time=in_time,
				out_time=out_time,
				threshold_min=30,
				predefined_hrs=predefined_ot_hrs
			)

	
			if ot_hours and ot_status == "Approved":
				total_pay_hrs = (ot_hours or timedelta(0)) + (record.get("net_wrk_hrs") or timedelta(0))
			else:
				total_pay_hrs = (record.get("net_wrk_hrs") or timedelta(0))

			# Get shift_hours for holiday calculation
			shift_hours = record.get("shift_hours") or (shift_det.shift_hours if shift_det else 0)

			# ------------------------------------------------------------------
			# Rule: Holiday logic
			# ------------------------------------------------------------------
			if date in emp_holidays:
				if attendance_status in ["LWP", "PL", "CL", "SL", "ML", "WFH",
											"Leave Without Pay", "Privilege Leave",
											"Casual Leave", "Sick Leave",
											"Maternity Leave", "Work From Home"]:
					pass  # Keep leave status as-is
				else:
					attendance_status = "H"
					net_wrk_hrs_val = timedelta(hours=flt(shift_hours))
					total_pay_hrs = net_wrk_hrs_val
			else:
				net_wrk_hrs_val = None

			row = {
				"login_date": str(record.get("login_date") or date),
				"shift": shift_display,
				"status": STATUS.get(attendance_status, attendance_status),
				"employee": record.get("employee") or emp,
				"employee_name": record.get("employee_name") or employee_details.get("employee_name"),
				"company": record.get("company") or employee_details.get("company"),
				"branch": employee_details.get("branch"),
				"department": record.get("department") or employee_details.get("department"),
				"designation": record.get("designation") or employee_details.get("designation"),
				"old_punch_id": record.get("punch_id") or employee_details.get("old_punch_id"),
				"middle_name": employee_details.get("middle_name"),
				"gender": employee_details.get("gender"),
				"date_of_birth": str(employee_details.get("date_of_birth")) if employee_details.get("date_of_birth") else None,
				"date_of_joining": str(employee_details.get("date_of_joining")) if employee_details.get("date_of_joining") else None,
				"allowed_personal_hours": _format_time_value(employee_details.get("allowed_personal_hours")),
				"attendance_date": str(record.get("login_date") or date),
				"shift_hours": record.get("shift_hours"),
				"shift_name": record.get("shift_type") or assigned_shift_type or "",
				"in_time": in_time,
				"out_time": out_time,
				"spent_hours": _format_time_value(record.get("spent_hrs")),
				"late_entry": record.get("late") or 0,
				"late_hrs": _format_time_value(record.get("late_hrs")),
				"early_hrs": _format_time_value(record.get("early_hrs")),
				"p_out_hrs": _format_time_value(record.get("p_out_hrs")),
				"net_wrk_hrs": _format_time_value(net_wrk_hrs_val) if net_wrk_hrs_val is not None else (_format_time_value(record.get("net_wrk_hrs")) or "0:00:00"),
				"lh": record.get("lh") or 0,
				"ot_hours": _format_time_value(ot_hours),
				"attendance_request": record.get("attendance_request"),
				"total_pay_hrs": _format_time_value(total_pay_hrs) or "0:00:00",
				"ot_status": ot_status
			}

			report_data.append(row)

	return report_data



def resolve_ot_hours(
    attendance_date,
    shift_in_time,
    shift_end_time,
    in_time,
    out_time,
    threshold_min=30,
    predefined_hrs=None
):
    """
    OT Calculation based on:
    1) Early coming (before shift start)
    2) Late going (after shift end)

    OT = (shift_start - in_time if early) + (out_time - shift_end if late)

    Handles night shifts properly.
    """

    # Approved OT
    if predefined_hrs:
        return predefined_hrs, "Approved"

    # Missing data
    if not attendance_date or not shift_in_time or not shift_end_time or not in_time or not out_time:
        return None, ""

    attendance_date = getdate(attendance_date)

    shift_in_time = get_time(shift_in_time)
    shift_end_time = get_time(shift_end_time)
    in_time = get_time(in_time)
    out_time = get_time(out_time)

    shift_in_dt = get_datetime(f"{attendance_date} {shift_in_time}")
    shift_end_dt = get_datetime(f"{attendance_date} {shift_end_time}")
    in_dt = get_datetime(f"{attendance_date} {in_time}")
    out_dt = get_datetime(f"{attendance_date} {out_time}")

    # Night shift support
    if shift_end_dt <= shift_in_dt:
        shift_end_dt += timedelta(days=1)

    if out_dt <= in_dt:
        out_dt += timedelta(days=1)

    # Calculate Early OT
    early_ot = timedelta(0)
    if in_dt < shift_in_dt:
        early_ot = shift_in_dt - in_dt

    # Calculate Late OT
    late_ot = timedelta(0)
    if out_dt > shift_end_dt:
        late_ot = out_dt - shift_end_dt

    total_ot = early_ot + late_ot

    # Threshold
    if total_ot < timedelta(minutes=threshold_min):
        return None, ""

    return total_ot, "Pending"
