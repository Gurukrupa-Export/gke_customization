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

The Journal Entry is the source of truth for the money paid: its amounts may
have been edited after the release rows were recorded from the Payroll Entry
dialog, so on submit each release row is settled (and its amount re-synced)
against the entry's payroll payable debit lines, not the recorded amount.

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
        fields=[
            "name",
            "parent",
            "payroll_entry",
            "salary_withholding_cycle",
            "amount",
        ],
    )
    if not releases:
        return

    cancel = method == "on_cancel"
    precision = frappe.get_precision("Salary Slip", "net_pay")
    cycle_names = list({r.salary_withholding_cycle for r in releases})
    actual_amounts = get_actual_release_amounts(doc, releases)

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

    cycle_updates = {}  # cycle_name -> {field: value}
    release_updates = {}  # release_name -> {field: value}; amount synced to the JE
    release_status_names = []
    submitted_slips, withheld_slips = [], []
    employees = set()
    withholdings = set()

    for release in releases:
        cycle = cycle_by_name.get(release.salary_withholding_cycle)
        if not cycle:
            continue
        slip = slip_by_cycle.get(release.salary_withholding_cycle)

        # on submit follow the money actually paid per the JE; on cancel revert
        # exactly what the submit applied (the row amount was synced on submit)
        amount = flt(
            release.amount
            if cancel
            else actual_amounts.get(release.name, release.amount)
        )
        if not cancel and amount != flt(release.amount):
            release_updates[release.name] = {"amount": amount}

        released_amount = flt(cycle.custom_released_amount) + flt(
            -amount if cancel else amount
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

        employees.add(
            frappe.db.get_value("Salary Withholding", release.parent, "employee")
        )
        withholdings.add(release.parent)

    # --- batched writes ---
    if cycle_updates:
        frappe.db.bulk_update("Salary Withholding Cycle", cycle_updates)

    if release_updates:
        frappe.db.bulk_update("Salary Withholding Release", release_updates)

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


def get_actual_release_amounts(doc, releases: list[dict]) -> dict[str, float]:
    """Return the actual released amount for each salary withholding release.

    The amounts are calculated from the Journal Entry's Payroll Payable debit lines,
    as these may have been modified after the release records were created.

    For employee-wise payrolls, amounts are matched using the employee (party) on
    the Journal Entry line. For lump-sum payrolls, the amount can only be matched
    when there is a single release record; otherwise, the recorded release amount
    is retained.
    """
    JEAccount = frappe.qb.DocType("Journal Entry Account")

    payable_debits = (
        frappe.qb.from_(JEAccount)
        .select(
            JEAccount.reference_name,
            JEAccount.party,
            JEAccount.debit_in_account_currency,
        )
        .where(
            (JEAccount.parent == doc.name)
            & (JEAccount.reference_type == "Payroll Entry")
            & (JEAccount.debit_in_account_currency > 0)
        )
    ).run(as_dict=True)

    paid_by_entry = {}  # payroll entry -> {party: amount}; party is None in lump-sum mode
    for line in payable_debits:
        per_party = paid_by_entry.setdefault(line.reference_name, {})
        per_party[line.party] = per_party.get(line.party, 0) + flt(
            line.debit_in_account_currency
        )

    # single batched lookup instead of one frappe.db.get_value per unique parent
    parents = list({release.parent for release in releases})
    employees = dict(
        frappe.get_all(
            "Salary Withholding",
            filters={"name": ("in", parents)},
            fields=["name", "employee"],
            as_list=True,
        )
    )

    entry_release_counts = {}
    for release in releases:
        entry_release_counts[release.payroll_entry] = (
            entry_release_counts.get(release.payroll_entry, 0) + 1
        )

    actual = {}
    for release in releases:
        per_party = paid_by_entry.get(release.payroll_entry)
        if not per_party:
            continue

        employee = employees.get(release.parent)
        if employee and employee in per_party:
            actual[release.name] = flt(per_party[employee])
        elif len(per_party) == 1 and None in per_party:
            if entry_release_counts[release.payroll_entry] == 1:
                actual[release.name] = flt(per_party[None])

    return actual


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
