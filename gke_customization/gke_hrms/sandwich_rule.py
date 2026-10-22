"""
Sandwich Rule shared by the Leave Application events and the daily scheduler.

A block of continuous holidays and weekly offs (containing at least one public holiday)
is converted to Leave Without Pay only when:
    - the day before and the day after the block are each Casual Leave, Half Day or Absent
    - and Casual Leave is involved (applied now, or on one of the two sides)

It never applies when a side is Present, Sick Leave, Marriage Leave, Outdoor Duty or
covered by an Attendance Request. Weekly offs are never converted.
"""

from datetime import timedelta

import frappe
from frappe.utils import getdate

ONE_DAY = timedelta(days=1)
SANDWICH_SIDE_STATUSES = {"Casual Leave", "Half Day", "Absent"}
LOOKUP_PADDING_DAYS = 10


def get_dates_between(start_date, end_date):
	dates = []
	current_day = start_date
	while current_day <= end_date:
		dates.append(current_day)
		current_day += ONE_DAY

	return dates


def get_lookup_window(from_date, to_date):
	return (
		getdate(from_date) - timedelta(days=LOOKUP_PADDING_DAYS),
		getdate(to_date) + timedelta(days=LOOKUP_PADDING_DAYS),
	)


def split_holidays(holidays):
	"""Returns (public_holidays, weekly_offs) as sets of dates from Holiday rows."""
	public_holidays = set()
	weekly_offs = set()

	for holiday in holidays:
		holiday_date = getdate(holiday.holiday_date)
		if holiday.weekly_off:
			weekly_offs.add(holiday_date)
		else:
			public_holidays.add(holiday_date)

	return public_holidays, weekly_offs


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
		while block_start - ONE_DAY in non_working_days:
			block_start = block_start - ONE_DAY

		block_end = holiday
		while block_end + ONE_DAY in non_working_days:
			block_end = block_end + ONE_DAY

		block_days = get_dates_between(block_start, block_end)
		checked_days.update(block_days)

		left_day = block_start - ONE_DAY
		right_day = block_end + ONE_DAY

		if attendance_request_dates and any(
			day in attendance_request_dates for day in block_days + [left_day, right_day]
		):
			continue

		if is_sandwiched(get_status(left_day), get_status(right_day), casual_leave_applied):
			sandwiched_holidays.update(day for day in block_days if day in public_holidays)

	return sandwiched_holidays


def get_day_status_map(employees, from_date, to_date):
	"""
	Returns {(employee, date): status} for submitted Absent, Half Day and On Leave attendance.

	Dates missing from the map are Present for the sandwich rule.
	"""
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", employees],
			"docstatus": 1,
			"status": ["in", ["Absent", "Half Day", "On Leave"]],
			"attendance_date": ["between", [from_date, to_date]],
		},
		fields=["employee", "attendance_date", "status", "leave_type"],
	)

	status_map = {}
	for attendance in attendances:
		if attendance.status == "On Leave":
			status = attendance.leave_type or "On Leave"
		else:
			status = attendance.status

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
		first_day = max(getdate(request.from_date), getdate(from_date))
		last_day = min(getdate(request.to_date), getdate(to_date))
		request_dates.setdefault(request.employee, set()).update(get_dates_between(first_day, last_day))

	return request_dates
