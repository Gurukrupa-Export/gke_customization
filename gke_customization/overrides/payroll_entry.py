# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""
Selective and partial release of withheld salaries, until the equivalent of
frappe/hrms PR #5119 is released. Extends the stock Payroll Entry behaviour with:

1. Individual release: `make_bank_entry` accepts an `employees` list, so only the
   selected employees' withheld salaries are paid out.
2. Partial release: `make_bank_entry` additionally accepts `release_amounts`
   ({employee: amount}), so only a part of an employee's withheld salary is paid.

Release bookkeeping is kept in the read-only "Salary Withholding Release" child
table on the Salary Withholding doc (Release History) instead of the stock
`Salary Withholding Cycle.journal_entry` link, because the stock Journal Entry
hook full-releases every cycle linked to it. The link is only written back once a
cycle is settled in full, so the stock hook stays dormant and partial releases
keep the salary slip in "Withheld" status until the cycle is fully settled.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


class CustomPayrollEntry(PayrollEntry):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.payroll.doctype.payroll_employee_detail.payroll_employee_detail import (
			PayrollEmployeeDetail,
		)

	# end: auto-generated types

	def get_statistical_components(self) -> set[str]:
		"""Components that carry no payable amount, fetched once instead of per salary detail"""
		return set(
			frappe.get_all("Salary Component", filters={"statistical_component": 1}, pluck="name")
		)

	@frappe.whitelist()
	def get_withheld_salaries(self) -> list[dict]:
		"""Returns the employee wise amount pending release, to be listed in the release dialog.

		The pending amount is the withheld salary slip's payable amount minus whatever
		has already been released against its withholding cycle via submitted
		Journal Entries. Cycles whose release entry is still a draft are excluded
		entirely, so an in-flight release cannot be paid twice.
		"""
		salary_details = self.get_salary_slip_details(for_withheld_salaries=True)
		if not salary_details:
			return []

		employee_names = {row.employee: row.employee_name for row in self.employees}
		statistical_components = self.get_statistical_components()

		amounts = {}
		loan_repayments = {}
		for salary_detail in salary_details:
			loan_repayments.setdefault(
				salary_detail.employee, flt(salary_detail.get("total_loan_repayment"))
			)
			amounts.setdefault(salary_detail.employee, 0)

			if salary_detail.salary_component in statistical_components:
				continue

			if salary_detail.parentfield == "earnings":
				amounts[salary_detail.employee] += flt(salary_detail.amount)
			elif salary_detail.parentfield == "deductions":
				amounts[salary_detail.employee] -= flt(salary_detail.amount)

		released_amounts = self.get_released_amounts(salary_details)

		withheld_salaries = []
		for employee, amount in sorted(amounts.items()):
			pending = (
				flt(amount)
				- flt(loan_repayments.get(employee, 0))
				- flt(released_amounts.get(employee, 0))
			)
			if pending <= 0:
				continue

			withheld_salaries.append(
				{
					"employee": employee,
					"employee_name": employee_names.get(employee)
					or frappe.db.get_value("Employee", employee, "employee_name"),
					"amount": pending,
				}
			)

		return withheld_salaries

	def get_released_amounts(self, salary_details: list[dict]) -> dict[str, float]:
		"""Already-released amount per employee, for the withholding cycles in salary_details"""
		cycle_employee = {
			row.salary_withholding_cycle: row.employee
			for row in salary_details
			if row.salary_withholding_cycle
		}
		if not cycle_employee:
			return {}

		released = {}
		cycles = frappe.get_all(
			"Salary Withholding Cycle",
			filters={"name": ("in", list(cycle_employee))},
			fields=["name", "custom_released_amount"],
		)
		for cycle in cycles:
			amount = flt(cycle.custom_released_amount)
			if amount:
				employee = cycle_employee[cycle.name]
				released[employee] = released.get(employee, 0) + amount

		return released

	def get_withholding_cycles_pending_release(self) -> list[str]:
		"""Returns this entry's withholding cycles whose release entry is waiting to be submitted.

		A cycle is only pending while its release Journal Entry still exists as a
		draft, so a cycle left pointing at a deleted or cancelled entry stays
		eligible for another release.
		"""
		Release = frappe.qb.DocType("Salary Withholding Release")
		JournalEntry = frappe.qb.DocType("Journal Entry")

		return (
			frappe.qb.from_(Release)
			.inner_join(JournalEntry)
			.on(JournalEntry.name == Release.journal_entry)
			.select(Release.salary_withholding_cycle)
			.distinct()
			.where(
				(Release.payroll_entry == self.name)
				& (Release.status == "Draft")
				& (JournalEntry.docstatus == 0)
			)
		).run(pluck=True)

	def get_salary_slip_details(
		self, for_withheld_salaries: bool = False, employees: list[str] | None = None
	) -> list[dict]:
		SalarySlip = frappe.qb.DocType("Salary Slip")
		SalaryDetail = frappe.qb.DocType("Salary Detail")

		query = (
			frappe.qb.from_(SalarySlip)
			.join(SalaryDetail)
			.on(SalarySlip.name == SalaryDetail.parent)
			.select(
				SalarySlip.name,
				SalarySlip.employee,
				SalarySlip.salary_structure,
				SalarySlip.salary_withholding_cycle,
				SalaryDetail.salary_component,
				SalaryDetail.amount,
				SalaryDetail.parentfield,
			)
			.where(
				(SalarySlip.docstatus == 1)
				& (SalarySlip.start_date >= self.start_date)
				& (SalarySlip.end_date <= self.end_date)
				& (SalarySlip.payroll_entry == self.name)
				& (
					(SalaryDetail.do_not_include_in_total == 0)
					| (
						(SalaryDetail.do_not_include_in_total == 1)
						& (SalaryDetail.do_not_include_in_accounts == 0)
					)
				)
			)
		)

		if "lending" in frappe.get_installed_apps():
			query = query.select(SalarySlip.total_loan_repayment)

		if for_withheld_salaries:
			query = query.where(SalarySlip.status == "Withheld")

			if pending_release := self.get_withholding_cycles_pending_release():
				query = query.where(SalarySlip.salary_withholding_cycle.notin(pending_release))
		else:
			query = query.where(SalarySlip.status != "Withheld")

		if employees is not None:
			if not employees:
				return []
			query = query.where(SalarySlip.employee.isin(employees))

		return query.run(as_dict=True)

	@frappe.whitelist()
	def make_bank_entry(
		self,
		for_withheld_salaries: bool = False,
		employees: list[str] | str | None = None,
		release_amounts: dict[str, float] | str | None = None,
	) -> Document | None:
		"""Pays out the withheld salaries of `employees`, or of every eligible employee when it is None.

		`release_amounts` ({employee: amount}) releases only a part of an employee's
		withheld salary; employees without an entry are released in full.

		Both arguments are parsed here rather than downstream because whitelisted
		methods are called over HTTP, where they arrive as JSON strings.
		"""
		self.check_permission("write")
		self.employee_based_payroll_payable_entries = {}
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)

		employees = frappe.parse_json(employees)
		release_amounts = frappe.parse_json(release_amounts) or {}

		salary_slip_total = 0
		salary_details = self.get_salary_slip_details(for_withheld_salaries, employees)
		statistical_components = self.get_statistical_components()

		# per-employee payable tracked regardless of the accounting mode, to cap release amounts
		employee_payables = {}

		for salary_detail in salary_details:
			if salary_detail.salary_component in statistical_components:
				continue

			parent_field = salary_detail.parentfield
			if parent_field in ("earnings", "deductions"):
				if employee_wise_accounting_enabled:
					self.set_employee_based_payroll_payable_entries(
						parent_field,
						salary_detail.employee,
						salary_detail.amount,
						salary_detail.salary_structure,
					)

				payable = employee_payables.setdefault(
					salary_detail.employee,
					{
						"earnings": 0.0,
						"deductions": 0.0,
						"loan_repayment": 0.0,
						"salary_structure": salary_detail.salary_structure,
					},
				)

				if parent_field == "earnings":
					salary_slip_total += flt(salary_detail.amount)
					payable["earnings"] += flt(salary_detail.amount)
				elif parent_field == "deductions":
					salary_slip_total -= flt(salary_detail.amount)
					payable["deductions"] += flt(salary_detail.amount)

		total_loan_repayment = self.process_loan_repayments_for_bank_entry(salary_details) or 0
		salary_slip_total -= total_loan_repayment

		# per-employee loan repayment, same derivation as the bank entry total
		for salary_detail in salary_details:
			employee_payables.setdefault(
				salary_detail.employee,
				{
					"earnings": 0.0,
					"deductions": 0.0,
					"loan_repayment": 0.0,
					"salary_structure": salary_detail.salary_structure,
				},
			)["loan_repayment"] = flt(salary_detail.get("total_loan_repayment"))

		for payable in employee_payables.values():
			payable["net_payable"] = (
				flt(payable["earnings"]) - flt(payable["deductions"]) - flt(payable["loan_repayment"])
			)

		if for_withheld_salaries and release_amounts:
			release_amounts = self.validate_release_amounts(release_amounts, employee_payables)
			# employees without an explicit amount are released in full
			for employee, payable in employee_payables.items():
				if flt(payable["net_payable"]) > 0:
					release_amounts.setdefault(employee, flt(payable["net_payable"]))

			salary_slip_total = self.apply_release_caps(
				release_amounts, employee_payables, employee_wise_accounting_enabled
			)

		bank_entry = None

		if salary_slip_total > 0:
			remark = "withheld salaries" if for_withheld_salaries else "salaries"
			bank_entry = self.set_accounting_entries_for_bank_entry(
				salary_slip_total, remark, employee_wise_accounting_enabled
			)

			if for_withheld_salaries:
				self.create_salary_withholding_releases(
					salary_details, bank_entry.name, release_amounts, employee_payables
				)

		return bank_entry

	def validate_release_amounts(
		self, release_amounts: dict, employee_payables: dict
	) -> dict[str, float]:
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		validated = {}

		for employee, amount in release_amounts.items():
			payable = employee_payables.get(employee)
			if not payable or flt(payable["net_payable"], precision) <= 0:
				frappe.throw(
					_("No withheld salary is pending release for employee {0}").format(
						frappe.bold(employee)
					),
					title=_("Invalid Selection"),
				)

			amount = flt(amount)
			if amount <= 0:
				frappe.throw(
					_("Release amount for employee {0} must be greater than zero").format(
						frappe.bold(employee)
					),
					title=_("Invalid Release Amount"),
				)

			if flt(amount, precision) > flt(payable["net_payable"], precision):
				frappe.throw(
					_("Release amount for employee {0} ({1}) cannot exceed the pending amount {2}").format(
						frappe.bold(employee), amount, payable["net_payable"]
					),
					title=_("Invalid Release Amount"),
				)

			validated[employee] = flt(amount, precision)

		return validated

	def apply_release_caps(
		self,
		release_amounts: dict[str, float],
		employee_payables: dict,
		employee_wise_accounting_enabled: bool,
	) -> float:
		"""Replaces the employee-wise accounting entries with the capped release amounts, so the
		Journal Entry pays exactly what was asked for. The lump-sum mode needs no state change;
		the caller simply passes the capped total on to the Journal Entry."""
		if employee_wise_accounting_enabled:
			self.employee_based_payroll_payable_entries = {
				employee: {
					"earnings": amount,
					"deductions": 0,
					"salary_structure": employee_payables.get(employee, {}).get("salary_structure"),
				}
				for employee, amount in release_amounts.items()
			}

		return sum(flt(amount) for amount in release_amounts.values())

	def create_salary_withholding_releases(
		self,
		salary_details: list[dict],
		bank_entry: str,
		release_amounts: dict[str, float],
		employee_payables: dict,
	) -> None:
		"""Records the per-employee release against the bank entry in the withholding's
		read-only Release History, to be applied to the withholding cycles when the
		Journal Entry is submitted."""
		cycle_by_employee = {}
		for salary_detail in salary_details:
			cycle_by_employee.setdefault(
				salary_detail.employee, salary_detail.salary_withholding_cycle
			)

		for employee, cycle in cycle_by_employee.items():
			if release_amounts:
				amount = flt(release_amounts.get(employee))
			else:
				amount = flt(employee_payables.get(employee, {}).get("net_payable"))

			if amount <= 0:
				continue

			frappe.get_doc(
				{
					"doctype": "Salary Withholding Release",
					"parent": frappe.db.get_value("Salary Withholding Cycle", cycle, "parent"),
					"parenttype": "Salary Withholding",
					"parentfield": "custom_release_history",
					"payroll_entry": self.name,
					"salary_withholding_cycle": cycle,
					"journal_entry": bank_entry,
					"amount": amount,
					"posting_date": self.posting_date,
					"status": "Draft",
				}
			).insert(ignore_permissions=True)

	@frappe.whitelist()
	def has_bank_entries(self) -> dict[str, bool]:
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")

		bank_entries = (
			frappe.qb.from_(je)
			.inner_join(jea)
			.on(je.name == jea.parent)
			.select(je.name)
			.where(
				((je.voucher_type == "Bank Entry") | (je.voucher_type == "Cash Entry"))
				& (jea.reference_name == self.name)
				& (jea.reference_type == "Payroll Entry")
			)
		).run(as_dict=True)

		# unlike stock, based on pending amounts rather than the employee flags, so the
		# button stays available while a partially released employee still has a balance
		return {
			"has_bank_entries": bool(bank_entries),
			"has_bank_entries_for_withheld_salaries": not bool(self.get_withheld_salaries()),
		}
