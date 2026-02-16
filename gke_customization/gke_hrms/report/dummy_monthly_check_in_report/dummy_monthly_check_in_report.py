# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, get_datetime, add_to_date, get_time
from gke_customization.gke_hrms.doctype.monthly_in_out_log.monthly_in_out_log import get_attendance_details_by_date

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


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

def get_employee_list(employee):
    """
    Return a list of Employee IDs that report to the given employee, including the employee itself.

    This function fetches all employees whose `reports_to` field matches the provided employee ID.
    It then returns a list containing their employee IDs (`name`) along with the given employee.
    """
    if not employee:
        return []

    employees = frappe.get_all(
    	"Employee",
    	filters={"reports_to": employee, "status": "Active"},
    	fields=["name"]
    )
    # frappe.throw(str(employees))

    employee_ids = [emp["name"] for emp in employees]
    employee_ids.append(employee)

    return employee_ids

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
        return None, None

    start_time, end_time = frappe.db.get_value("Shift Type", shift_type, ["start_time", "end_time"])

    return start_time, end_time


def get_employee_checkins(employee, date):
    start_time, end_time = get_employee_shift(employee, date)

    # fallback if shift not found
    if not start_time or not end_time:
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

    # for row in checkins:
    #     if row.log_type == "IN":
    #         in_times.append(row.time.strftime("%H:%M:%S"))
    #     elif row.log_type == "OUT":
    #         out_times.append(row.time.strftime("%H:%M:%S"))

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



def get_data(filters):
	employee = filters.get("employee")
	company = filters.get("company")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not employee or not from_date or not to_date:
		frappe.throw("Please select Employee, From Date and To Date")
		return []

	date_range = get_date_range(filters)
	employee_list = get_employee_list(employee)
	holiday_map = get_holiday_weekoff_map(employee_list, company, from_date, to_date)

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

	final_data = process_data(attendance_details, date_range, holiday_map)

	return final_data


def get_columns():
	columns = [
		{"label": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 150},
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": "Punch ID", "fieldname": "punch_id", "fieldtype": "Data", "width": 100},
		{"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 150},
		{"label": "Date", "fieldname": "login_date", "fieldtype": "Date", "width": 120},
		{"label": "Shift", "fieldname": "shift_type", "fieldtype": "Data", "width": 120},
		{"label": "Attendance Status", "fieldname": "attendance_status", "fieldtype": "Data", "width": 150},
		{"label": "In Time", "fieldname": "in_time", "fieldtype": "Data", "width": 100},
		{"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data", "width": 100},
		{"label": "Late", "fieldname": "late", "fieldtype": "Data", "width": 100},
		{"label": "Late Hrs", "fieldname": "late_hrs", "fieldtype": "Time", "width": 100},
		{"label": "Early Hrs", "fieldname": "early_hrs", "fieldtype": "Time", "width": 100},
		{"label": "OT Hrs", "fieldname": "ot_hours", "fieldtype": "Time", "width": 100},
	]
	return columns


def process_data(attendance_details, date_range, holiday_map):
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

            if not attendance_status in ['Absent', 'On Leave',]:
                all_in_times, all_out_times, error_status = get_employee_checkins(emp, date)
                attendance_status = error_status if error_status else attendance_status
            else:
                all_in_times, all_out_times = [], []

            employee_details = frappe.db.get_value("Employee", emp, ["employee_name", "old_punch_id", "department", "default_shift"], as_dict=1)

            row = {
                "employee": record.get("employee") or emp,
                "employee_name": record.get("employee_name") or employee_details.get("employee_name"),
                "punch_id": record.get("punch_id") or employee_details.get("old_punch_id"),
                "department": record.get("department") or employee_details.get("department"),
                "login_date": record.get("login_date") or date,
                "shift_type": record.get("shift_type") or employee_details.get("default_shift"),
                "attendance_status": attendance_status,
                "in_time": ", ".join(all_in_times) or "",
                # "in_time": record.get("in_time") or "",
                "out_time": ", ".join(all_out_times) or "",
                # "out_time": record.get("out_time") or "",
                "late": record.get("late") or "",
                "late_hrs": record.get("late_hrs"),
                "early_hrs": record.get("early_hrs"),
                "ot_hours": record.get("ot_hours"),
            }

            report_data.append(row)

    return report_data
