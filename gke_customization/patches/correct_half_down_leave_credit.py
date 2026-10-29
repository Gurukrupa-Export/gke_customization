# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, getdate

from gke_customization.gke_hrms.doc_events.leave_allocation import round_earned_leaves
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

ROUNDING_OPTION = "0.5 Down"


def execute():
	"""Bring existing attendance based credit in line with the "0.5 Down" rounding.

	Credit was earlier rounded to whole days. The target credit is recomputed from
	attendance and the difference is posted as an extra Leave Ledger Entry.
	"""
	today = getdate()
	leave_types = frappe.get_all(
		"Leave Type",
		filters={"rounding": ROUNDING_OPTION, "is_earned_leave": 1},
		fields=["name", "applicable_after", "max_leaves_allowed"],
	)
	if not leave_types:
		return

	for leave_type in leave_types:
		if not flt(leave_type.applicable_after):
			continue
		correct_leave_type_allocations(leave_type, today)


def correct_leave_type_allocations(leave_type, today):
	allocations = frappe.get_all(
		"Leave Allocation",
		filters={
			"leave_type": leave_type.name,
			"docstatus": 1,
			"from_date": ["<=", today],
			"to_date": [">=", today],
		},
		fields=["name", "employee", "from_date", "leave_policy", "total_leaves_allocated"],
	)
	if not allocations:
		return

	attendance_count = get_attendance_count_by_allocation(allocations, today)
	annual_allocation = get_annual_allocation_by_policy(allocations, leave_type.name)
	balance = get_ledger_balance_by_employee(allocations, leave_type.name)

	for allocation in allocations:
		target = get_target_credit(
			leave_type,
			attendance_count.get(allocation.name, 0),
			annual_allocation.get(allocation.leave_policy),
		)
		difference = flt(target - flt(allocation.total_leaves_allocated), 2)
		if not difference:
			continue

		if flt(balance.get(allocation.employee)) + difference < 0:
			frappe.log_error(
				title="Half Down leave credit not corrected",
				message=f"{allocation.name}: reducing by {abs(difference)} would make the balance negative",
			)
			continue

		post_credit_difference(allocation.name, difference, today)


def get_target_credit(leave_type, attendance_days, annual_allocation):
	earned_units = 0.0
	if attendance_days >= flt(leave_type.applicable_after):
		earned_units = attendance_days / flt(leave_type.applicable_after)

	target = round_earned_leaves(earned_units, ROUNDING_OPTION)

	if leave_type.max_leaves_allowed and target > leave_type.max_leaves_allowed:
		target = leave_type.max_leaves_allowed
	if annual_allocation and target > annual_allocation:
		target = annual_allocation
	return target


def get_attendance_count_by_allocation(allocations, today):
	Attendance = frappe.qb.DocType("Attendance")
	Allocation = frappe.qb.DocType("Leave Allocation")

	rows = (
		frappe.qb.from_(Allocation)
		.inner_join(Attendance)
		.on(
			(Attendance.employee == Allocation.employee)
			& (Attendance.attendance_date >= Allocation.from_date)
			& (Attendance.attendance_date <= today)
		)
		.select(Allocation.name, frappe.qb.functions("COUNT", Attendance.name).as_("days"))
		.where(Allocation.name.isin([d.name for d in allocations]))
		.where(Attendance.docstatus == 1)
		.where(Attendance.status.isin(["Present", "Work From Home"]))
		.groupby(Allocation.name)
		.run(as_dict=True)
	)
	return {row.name: row.days for row in rows}


def get_annual_allocation_by_policy(allocations, leave_type):
	policies = {d.leave_policy for d in allocations if d.leave_policy}
	if not policies:
		return {}

	rows = frappe.get_all(
		"Leave Policy Detail",
		filters={"parent": ["in", list(policies)], "leave_type": leave_type},
		fields=["parent", "annual_allocation"],
	)
	return {row.parent: flt(row.annual_allocation) for row in rows}


def get_ledger_balance_by_employee(allocations, leave_type):
	rows = frappe.get_all(
		"Leave Ledger Entry",
		filters={
			"employee": ["in", list({d.employee for d in allocations})],
			"leave_type": leave_type,
			"docstatus": 1,
			"is_expired": 0,
		},
		fields=["employee", {"SUM": "leaves", "as": "balance"}],
		group_by="employee",
	)
	return {row.employee: flt(row.balance) for row in rows}


def post_credit_difference(allocation_name, difference, today):
	allocation = frappe.get_doc("Leave Allocation", allocation_name)
	new_total = flt(allocation.total_leaves_allocated) + difference

	allocation.db_set("new_leaves_allocated", new_total, update_modified=False)
	allocation.db_set("total_leaves_allocated", new_total, update_modified=False)

	create_leave_ledger_entry(
		allocation,
		{
			"leaves": difference,
			"from_date": today,
			"to_date": allocation.to_date,
			"is_carry_forward": 0,
		},
	)
