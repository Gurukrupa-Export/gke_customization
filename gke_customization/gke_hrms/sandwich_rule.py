"""
Sandwich Rule shared by the Leave Application events and the daily scheduler.

A block of continuous holidays and weekly offs (containing at least one public holiday)
is converted to Leave Without Pay only when:
    - the day before and the day after the block are each Casual Leave, Half Day or Absent
    - and Casual Leave is involved (applied now, or on one of the two sides)

It never applies when a side is Present, Sick Leave, Marriage Leave, Outdoor Duty or
covered by an Attendance Request. Weekly offs are never converted.
"""

import frappe
from frappe.utils import add_days, getdate

SANDWICH_SIDE_STATUSES = {"Casual Leave", "Half Day", "Absent"}
LOOKUP_PADDING_DAYS = 10


def is_sandwiched(left_status, right_status, casual_leave_applied=False):
	if left_status not in SANDWICH_SIDE_STATUSES or right_status not in SANDWICH_SIDE_STATUSES:
		return False

	return casual_leave_applied or "Casual Leave" in (left_status, right_status)


def get_sandwiched_holidays(
	public_holidays,
	weekly_offs,
	candidate_holidays,
	get_status,
	attendance_request_dates,
	casual_leave_applied=False,
):
	"""
	Returns the set of public holidays that become Leave.

	get_status(date) returns "Absent", "Half Day", a leave type name or "Present".
	"""
	non_working_days = public_holidays | weekly_offs
	sandwiched_holidays = set()
	checked_days = set()

	for holiday in sorted(candidate_holidays):
		if holiday in checked_days:
			continue

		block_start = holiday
		while add_days(block_start, -1) in non_working_days:
			block_start = add_days(block_start, -1)

		block_end = holiday
		while add_days(block_end, 1) in non_working_days:
			block_end = add_days(block_end, 1)

		block_days = []
		current_day = block_start
		while current_day <= block_end:
			block_days.append(current_day)
			current_day = add_days(current_day, 1)
		checked_days.update(block_days)

		left_day = add_days(block_start, -1)
		right_day = add_days(block_end, 1)

		if any(day in attendance_request_dates for day in block_days + [left_day, right_day]):
			continue

		if is_sandwiched(get_status(left_day), get_status(right_day), casual_leave_applied):
			sandwiched_holidays.update(day for day in block_days if day in public_holidays)

	return sandwiched_holidays


def get_day_status_map(employees, from_date, to_date):
	"""Returns {(employee, date): status} for submitted attendance between the dates."""
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", employees],
			"docstatus": 1,
			"attendance_date": ["between", [from_date, to_date]],
		},
		fields=["employee", "attendance_date", "status", "leave_type"],
	)

	status_map = {}
	for attendance in attendances:
		if attendance.status == "On Leave":
			status = attendance.leave_type or "On Leave"
		elif attendance.status in ("Absent", "Half Day"):
			status = attendance.status
		else:
			status = "Present"

		status_map[(attendance.employee, getdate(attendance.attendance_date))] = status

	return status_map


def get_attendance_request_dates(employees, from_date, to_date):
	"""Returns {employee: set of dates} covered by submitted Attendance Requests."""
	attendance_requests = frappe.get_all(
		"Attendance Request",
		filters={
			"employee": ["in", employees],
			"docstatus": 1,
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		fields=["employee", "from_date", "to_date"],
	)

	request_dates = {}
	for request in attendance_requests:
		current_day = max(getdate(request.from_date), getdate(from_date))
		last_day = min(getdate(request.to_date), getdate(to_date))
		dates = request_dates.setdefault(request.employee, set())

		while current_day <= last_day:
			dates.add(current_day)
			current_day = add_days(current_day, 1)

	return request_dates
