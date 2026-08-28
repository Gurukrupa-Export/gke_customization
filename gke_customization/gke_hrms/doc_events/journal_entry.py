# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt
"""
Applies and reverts withheld salary releases when a release Journal Entry is
submitted, cancelled or deleted. Counterpart of gke's Payroll Entry override
(make_bank_entry).

Release records live in the read-only "Release History" child table of the
Salary Withholding doc, including the release amount so a cycle can be settled
partially. The stock hrms hook stays dormant in this flow until a cycle is
settled in full, at which point the stock `journal_entry` link is written back
for display; a cancel reverts everything.

All updates are batched (one query per table) rather than looped per row.
"""
import frappe
from frappe.utils import flt


def update_withholding_release_status(doc, method=None):
	if method not in (None, "on_submit", "on_cancel"):
		return

	releases = frappe.get_all(
		"Salary Withholding Release",
		filters={"journal_entry": doc.name, "status": ("!=", "Cancelled")},
		fields=["name", "parent", "salary_withholding_cycle", "amount"],
	)
	if not releases:
		return

	cancel = method == "on_cancel"
	precision = frappe.get_precision("Salary Slip", "net_pay")
	cycle_names = list({r.salary_withholding_cycle for r in releases})

	cycles = frappe.get_all(
		"Salary Withholding Cycle",
		filters={"name": ("in", cycle_names)},
		fields=["name", "parent", "custom_released_amount", "journal_entry"],
	)
	cycle_by_name = {c.name: c for c in cycles}

	slips = frappe.get_all(
		"Salary Slip",
		filters={"salary_withholding_cycle": ("in", cycle_names), "docstatus": 1},
		fields=["name", "salary_withholding_cycle", "net_pay"],
	)
	slip_by_cycle = {s.salary_withholding_cycle: s for s in slips}

	cycle_updates = {}       # cycle_name -> {field: value}
	release_status_names = []
	submitted_slips, withheld_slips = [], []
	employees = set()
	withholdings = set()

	for release in releases:
		cycle = cycle_by_name.get(release.salary_withholding_cycle)
		if not cycle:
			continue
		slip = slip_by_cycle.get(release.salary_withholding_cycle)

		released_amount = flt(cycle.custom_released_amount) + flt(
			-release.amount if cancel else release.amount
		)
		# a reverted release can never take the running total below zero
		released_amount = max(flt(released_amount, precision), 0)

		fully_released = bool(slip and released_amount >= flt(slip.net_pay, precision))

		update = {
			"custom_released_amount": released_amount,
			"is_salary_released": 1 if fully_released else 0,
		}
		# the stock link points at the entry that settled the cycle in full; until
		# then it stays empty so partial releases never trip the stock hook
		if fully_released and not cancel:
			update["journal_entry"] = doc.name
		elif cancel and cycle.journal_entry == doc.name:
			update["journal_entry"] = None
		cycle_updates[cycle.name] = update

		release_status_names.append(release.name)
		if slip:
			(submitted_slips if fully_released else withheld_slips).append(slip.name)

		employees.add(frappe.db.get_value("Salary Withholding", release.parent, "employee"))
		withholdings.add(release.parent)

	# --- batched writes ---
	if cycle_updates:
		frappe.db.bulk_update("Salary Withholding Cycle", cycle_updates)

	if release_status_names:
		frappe.db.set_value(
			"Salary Withholding Release",
			{"name": ("in", release_status_names)},
			"status",
			"Cancelled" if cancel else "Released",
		)

	_set_salary_slip_status(submitted_slips, "Submitted")
	_set_salary_slip_status(withheld_slips, "Withheld")

	# the payroll flag stays set while the employee has any withheld slip left,
	# so partially released employees keep the release button available
	_set_payroll_employee_withheld_flags(employees)

	for withholding in withholdings:
		frappe.get_doc("Salary Withholding", withholding).set_status(update=True)


def cancel_withholding_releases_on_trash(doc, method=None):
	"""A draft release entry can be deleted outright; mark its release records cancelled
	so the withheld salary becomes releasable again."""
	if doc.docstatus != 0:
		# cancelled entries were already handled by the on_cancel hook
		return
	frappe.db.delete(
		"Salary Withholding Release",
		{"journal_entry": doc.name, "status": "Draft"},
	)


def _set_salary_slip_status(salary_slips: list, status: str) -> None:
	if not salary_slips:
		return
	SalarySlip = frappe.qb.DocType("Salary Slip")
	(
		frappe.qb.update(SalarySlip)
		.set(SalarySlip.status, status)
		.where(SalarySlip.name.isin(salary_slips))
	).run()


def _set_payroll_employee_withheld_flags(employees: set) -> None:
	employees = {e for e in employees if e}
	if not employees:
		return
	still_withheld = set(
		frappe.get_all(
			"Salary Slip",
			filters={
				"employee": ("in", list(employees)),
				"docstatus": 1,
				"status": "Withheld",
			},
			pluck="employee",
		)
	)
	cleared = employees - still_withheld
	PayrollEmployee = frappe.qb.DocType("Payroll Employee Detail")
	if still_withheld:
		(
			frappe.qb.update(PayrollEmployee)
			.set(PayrollEmployee.is_salary_withheld, 1)
			.where(PayrollEmployee.employee.isin(list(still_withheld)))
		).run()
	if cleared:
		(
			frappe.qb.update(PayrollEmployee)
			.set(PayrollEmployee.is_salary_withheld, 0)
			.where(PayrollEmployee.employee.isin(list(cleared)))
		).run()