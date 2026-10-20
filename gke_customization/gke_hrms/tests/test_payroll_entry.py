"""Tests for the Payroll Entry overrides.

Run:
	bench --site <site-name> run-tests --app gke_customization --module gke_customization.gke_hrms.tests.test_payroll_entry
"""

from gke_customization.gke_hrms.tests.payroll_base import PayrollTestCase


class TestPayrollEntryOverrides(PayrollTestCase):
    def setUp(self):
        self.set_employee_wise_accounting(True)

    def create_mixed_payroll(self):
        """One employee with withheld salary and one with a regular salary slip."""
        withheld_employee = self.create_payroll_employee("MW")
        regular_employee = self.create_payroll_employee("MR")
        self.create_salary_withholding(withheld_employee)
        entry = self.create_payroll_entry([withheld_employee, regular_employee])
        self.create_salary_slips(entry, [withheld_employee, regular_employee])
        return entry, withheld_employee, regular_employee

    def get_slip_detail_employees(self, entry, **kwargs) -> set[str]:
        return {row.employee for row in entry.get_salary_slip_details(**kwargs)}

    # ---------- get_salary_slip_details ----------

    def test_regular_details_exclude_withheld_slips(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()

        self.assertEqual(self.get_slip_detail_employees(entry), {regular_employee})

    def test_withheld_details_include_only_withheld_slips(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()

        self.assertEqual(
            self.get_slip_detail_employees(entry, for_withheld_salaries=True),
            {withheld_employee},
        )

    def test_details_are_limited_to_selected_employees(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()

        self.assertEqual(
            self.get_slip_detail_employees(entry, employees=[regular_employee]),
            {regular_employee},
        )
        self.assertEqual(
            self.get_slip_detail_employees(entry, employees=[withheld_employee]), set()
        )

    def test_empty_employee_selection_returns_nothing(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()

        self.assertEqual(entry.get_salary_slip_details(employees=[]), [])
        self.assertEqual(
            entry.get_salary_slip_details(for_withheld_salaries=True, employees=[]), []
        )

    def test_withheld_details_skip_cycles_with_draft_release(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()
        self.release_withheld_salaries(entry, [withheld_employee], submit=False)

        self.assertEqual(
            self.get_slip_detail_employees(entry, for_withheld_salaries=True), set()
        )
        self.assertEqual(len(entry.get_pending_release_entries()), 1)

    # ---------- has_bank_entries ----------

    def test_withheld_salary_button_state_before_release(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()

        status = entry.has_bank_entries()
        self.assertFalse(status["has_bank_entries"])
        self.assertFalse(status["has_bank_entries_for_withheld_salaries"])

    def test_withheld_salary_button_state_after_full_release(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()
        self.release_withheld_salaries(entry, [withheld_employee])

        status = entry.has_bank_entries()
        self.assertTrue(status["has_bank_entries"])
        self.assertTrue(status["has_bank_entries_for_withheld_salaries"])

    def test_withheld_salary_button_stays_available_after_partial_release(self):
        entry, withheld_employee, regular_employee = self.create_mixed_payroll()
        self.release_withheld_salaries(
            entry, [withheld_employee], {withheld_employee: 4000}
        )

        self.assertFalse(
            entry.has_bank_entries()["has_bank_entries_for_withheld_salaries"]
        )
