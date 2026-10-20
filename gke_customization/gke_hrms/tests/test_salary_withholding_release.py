"""Tests for the Salary Withholding Release flow.

Covers the Payroll Entry release overrides and the Journal Entry hooks that
keep the withholding cycle, salary slip and release rows in sync.

Run:
	bench --site <site-name> run-tests --app gke_customization --module gke_customization.gke_hrms.tests.test_salary_withholding_release
"""

import json

import frappe

from gke_customization.gke_hrms.tests.payroll_base import NET_PAY, PayrollTestCase


class TestSalaryWithholdingRelease(PayrollTestCase):
    def setUp(self):
        self.set_employee_wise_accounting(True)

    def get_releases(self, journal_entry: str) -> list[dict]:
        return frappe.get_all(
            "Salary Withholding Release",
            filters={"journal_entry": journal_entry},
            fields=["name", "amount", "status"],
        )

    def get_pending_amount(self, entry, employee: str) -> float:
        pending = {
            row["employee"]: row["amount"] for row in entry.get_withheld_salaries()
        }
        return pending.get(employee, 0)

    # ---------- pending amounts ----------

    def test_pending_amount_ignores_statistical_component(self):
        entry, employees = self.create_withheld_payroll()
        self.assertEqual(self.get_pending_amount(entry, employees[0]), NET_PAY)

    def test_slip_is_withheld_when_withholding_is_active(self):
        entry, employees = self.create_withheld_payroll()
        self.assertEqual(self.get_slip_status(employees[0], entry.name), "Withheld")

    # ---------- validation ----------

    def test_release_amount_above_pending_is_rejected(self):
        entry, employees = self.create_withheld_payroll()
        with self.assertRaises(frappe.ValidationError):
            entry.make_bank_entry(
                for_withheld_salaries=True,
                employees=employees,
                release_amounts={employees[0]: NET_PAY + 1},
            )

    def test_zero_release_amount_is_rejected(self):
        entry, employees = self.create_withheld_payroll()
        with self.assertRaises(frappe.ValidationError):
            entry.make_bank_entry(
                for_withheld_salaries=True,
                employees=employees,
                release_amounts={employees[0]: 0},
            )

    def test_employee_without_pending_salary_is_rejected(self):
        entry, employees = self.create_withheld_payroll()
        self.release_withheld_salaries(entry, employees)
        with self.assertRaises(frappe.ValidationError):
            entry.make_bank_entry(for_withheld_salaries=True, employees=employees)

    def test_release_row_rejects_non_positive_amount(self):
        entry, employees = self.create_withheld_payroll()
        withholding = frappe.get_doc(
            "Salary Withholding", self.get_cycle(employees[0]).parent
        )
        withholding.append(
            "custom_release_history",
            {"amount": 0, "status": "Draft", "payroll_entry": entry.name},
        )
        with self.assertRaises(frappe.ValidationError):
            withholding.save(ignore_permissions=True)

    # ---------- creating the release entry ----------

    def test_default_release_is_full_pending_amount(self):
        entry, employees = self.create_withheld_payroll()
        journal_entry = self.release_withheld_salaries(entry, employees, submit=False)

        releases = self.get_releases(journal_entry.name)
        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0].amount, NET_PAY)
        self.assertEqual(releases[0].status, "Draft")

    def test_json_string_inputs_are_accepted(self):
        entry, employees = self.create_withheld_payroll()
        journal_entry = entry.make_bank_entry(
            for_withheld_salaries=True,
            employees=json.dumps(employees),
            release_amounts=json.dumps({employees[0]: 4000}),
        )

        releases = self.get_releases(journal_entry.name)
        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0].amount, 4000)

    def test_draft_journal_entry_blocks_second_release(self):
        entry, employees = self.create_withheld_payroll()
        self.release_withheld_salaries(
            entry, employees, {employees[0]: 4000}, submit=False
        )

        self.assertEqual(self.get_pending_amount(entry, employees[0]), 0)

    def test_deleting_draft_journal_entry_removes_draft_releases(self):
        entry, employees = self.create_withheld_payroll()
        journal_entry = self.release_withheld_salaries(entry, employees, submit=False)

        frappe.delete_doc("Journal Entry", journal_entry.name, force=True)

        self.assertEqual(self.get_releases(journal_entry.name), [])
        self.assertEqual(self.get_pending_amount(entry, employees[0]), NET_PAY)

    # ---------- submit ----------

    def test_partial_release_keeps_slip_withheld(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        journal_entry = self.release_withheld_salaries(
            entry, employees, {employee: 4000}
        )

        cycle = self.get_cycle(employee)
        self.assertEqual(cycle.custom_released_amount, 4000)
        self.assertFalse(cycle.is_salary_released)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Withheld")
        self.assertEqual(self.get_releases(journal_entry.name)[0].status, "Released")
        self.assertEqual(self.get_pending_amount(entry, employee), NET_PAY - 4000)

    def test_full_release_marks_slip_submitted_and_cycle_released(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        journal_entry = self.release_withheld_salaries(entry, employees)

        cycle = self.get_cycle(employee)
        self.assertEqual(cycle.custom_released_amount, NET_PAY)
        self.assertTrue(cycle.is_salary_released)
        self.assertEqual(cycle.journal_entry, journal_entry.name)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Submitted")

    def test_partial_then_remaining_release_completes_cycle(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        self.release_withheld_salaries(entry, employees, {employee: 4000})
        self.release_withheld_salaries(entry, employees)

        cycle = self.get_cycle(employee)
        self.assertEqual(cycle.custom_released_amount, NET_PAY)
        self.assertTrue(cycle.is_salary_released)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Submitted")

    def test_lump_sum_mode_release_is_submitted(self):
        self.set_employee_wise_accounting(False)
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        self.release_withheld_salaries(entry, employees)

        self.assertEqual(self.get_cycle(employee).custom_released_amount, NET_PAY)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Submitted")

    def test_each_employee_is_released_by_own_amount(self):
        entry, employees = self.create_withheld_payroll(employee_count=2)
        first, second = employees
        self.release_withheld_salaries(entry, employees, {first: 3000, second: 5000})

        self.assertEqual(self.get_cycle(first).custom_released_amount, 3000)
        self.assertEqual(self.get_cycle(second).custom_released_amount, 5000)

    # ---------- cancel ----------

    def test_cancelling_full_release_restores_withheld_state(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        journal_entry = self.release_withheld_salaries(entry, employees)

        journal_entry.cancel()

        cycle = self.get_cycle(employee)
        self.assertEqual(cycle.custom_released_amount, 0)
        self.assertFalse(cycle.is_salary_released)
        self.assertFalse(cycle.journal_entry)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Withheld")
        self.assertEqual(self.get_releases(journal_entry.name)[0].status, "Cancelled")
        self.assertEqual(self.get_pending_amount(entry, employee), NET_PAY)

    def test_cancelling_partial_release_reduces_released_amount(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        self.release_withheld_salaries(entry, employees, {employee: 4000})
        second_entry = self.release_withheld_salaries(
            entry, employees, {employee: 2000}
        )

        second_entry.cancel()

        self.assertEqual(self.get_cycle(employee).custom_released_amount, 4000)
        self.assertEqual(self.get_slip_status(employee, entry.name), "Withheld")

    def test_cancelling_other_entry_keeps_cycle_journal_entry(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        self.release_withheld_salaries(entry, employees, {employee: 4000})
        final_entry = self.release_withheld_salaries(entry, employees)
        first_release = frappe.get_all(
            "Salary Withholding Release",
            filters={"amount": 4000, "status": "Released"},
            pluck="journal_entry",
        )[0]

        frappe.get_doc("Journal Entry", first_release).cancel()

        cycle = self.get_cycle(employee)
        self.assertEqual(cycle.journal_entry, final_entry.name)
        self.assertEqual(cycle.custom_released_amount, NET_PAY - 4000)

    def test_released_amount_never_goes_below_zero(self):
        entry, employees = self.create_withheld_payroll()
        employee = employees[0]
        journal_entry = self.release_withheld_salaries(
            entry, employees, {employee: 4000}
        )
        cycle = self.get_cycle(employee)
        frappe.db.set_value(
            "Salary Withholding Cycle", cycle.name, "custom_released_amount", 1000
        )

        journal_entry.cancel()

        self.assertEqual(self.get_cycle(employee).custom_released_amount, 0)
