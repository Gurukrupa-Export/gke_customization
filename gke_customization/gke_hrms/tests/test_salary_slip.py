"""Tests for the Salary Slip and Salary Structure Assignment customizations.

Run:
	bench --site <site-name> run-tests --app gke_customization --module gke_customization.gke_hrms.tests.test_salary_slip
"""

import frappe
from frappe.tests import IntegrationTestCase

from gke_customization.overrides.salary_slip import seed_slip_only_formula_fields
from gke_customization.overrides.salary_structure_assignment import (
    SLIP_ONLY_FORMULA_FIELDS,
    CustomSalaryStructureAssignment,
    references_slip_only_fields,
)


class SalaryComponentRowStub(frappe._dict):
    """Minimal stand-in for a Salary Detail row."""

    def __init__(self, abbr="TST", **values):
        defaults = {
            "abbr": abbr,
            "condition": None,
            "formula": None,
            "amount": 0,
            "amount_based_on_formula": 0,
        }
        super().__init__({**defaults, **values})

    def precision(self, fieldname):
        return 2


def evaluate_rows(rows, data=None):
    data = data if data is not None else frappe._dict()
    return CustomSalaryStructureAssignment._evaluate_component_table(
        None, rows, data
    ), data


class TestSeedSlipOnlyFormulaFields(IntegrationTestCase):
    def test_unset_numeric_fields_default_to_zero(self):
        slip = frappe._dict(start_date="2026-03-01")
        seed_slip_only_formula_fields(slip)

        for fieldname in SLIP_ONLY_FORMULA_FIELDS:
            if fieldname != "custom_month":
                self.assertEqual(slip.get(fieldname), 0, fieldname)

    def test_existing_values_are_kept(self):
        slip = frappe._dict(start_date="2026-03-01", hourly_rate=150, shift_hours=8)
        seed_slip_only_formula_fields(slip)

        self.assertEqual(slip.hourly_rate, 150)
        self.assertEqual(slip.shift_hours, 8)

    def test_custom_month_defaults_to_start_date_month(self):
        slip = frappe._dict(start_date="2026-03-01")
        seed_slip_only_formula_fields(slip)

        self.assertEqual(slip.custom_month, 3)

    def test_existing_custom_month_is_kept(self):
        slip = frappe._dict(start_date="2026-03-01", custom_month=7)
        seed_slip_only_formula_fields(slip)

        self.assertEqual(slip.custom_month, 7)

    def test_custom_month_stays_unset_without_start_date(self):
        slip = frappe._dict()
        seed_slip_only_formula_fields(slip)

        self.assertIsNone(slip.get("custom_month"))


class TestReferencesSlipOnlyFields(IntegrationTestCase):
    def test_detects_slip_only_field_in_formula(self):
        self.assertTrue(
            references_slip_only_fields("hourly_rate * extra_working_hours")
        )

    def test_detects_slip_only_field_in_condition(self):
        self.assertTrue(references_slip_only_fields(None, "custom_month == 4"))

    def test_ignores_partial_word_matches(self):
        self.assertFalse(references_slip_only_fields("base_hourly_rate_total * 2"))

    def test_empty_expressions_are_not_deferred(self):
        self.assertFalse(references_slip_only_fields(None, ""))


class TestEvaluateComponentTable(IntegrationTestCase):
    def test_plain_formula_is_evaluated(self):
        row = SalaryComponentRowStub(
            "BS", amount_based_on_formula=1, formula="base * 0.5"
        )
        components, data = evaluate_rows([row], frappe._dict(base=20000))

        self.assertEqual(components[0].default_amount, 10000)
        self.assertEqual(data.BS, 10000)

    def test_fixed_amount_is_used_without_formula(self):
        row = SalaryComponentRowStub("FX", amount=2500)
        components, data = evaluate_rows([row])

        self.assertEqual(components[0].default_amount, 2500)
        self.assertEqual(data.FX, 2500)

    def test_slip_only_formula_is_deferred_with_zero_amount(self):
        row = SalaryComponentRowStub(
            "OT",
            amount=500,
            amount_based_on_formula=1,
            formula="hourly_rate * extra_working_hours",
        )
        components, data = evaluate_rows([row])

        self.assertEqual(components[0].default_amount, 0)
        self.assertEqual(data.OT, 0)

    def test_slip_only_condition_defers_fixed_amount(self):
        row = SalaryComponentRowStub(
            "FA", amount=700, condition="consider_working_hours == 1"
        )
        components, data = evaluate_rows([row])

        self.assertEqual(components[0].default_amount, 700)

    def test_falsy_condition_skips_the_row(self):
        row = SalaryComponentRowStub("SK", amount=900, condition="base > 100000")
        components, data = evaluate_rows([row], frappe._dict(base=20000))

        self.assertEqual(components, [])
        self.assertNotIn("SK", data)

    def test_later_row_can_use_earlier_component(self):
        first = SalaryComponentRowStub("BS", amount=10000)
        second = SalaryComponentRowStub(
            "HR", amount_based_on_formula=1, formula="BS * 0.4"
        )
        components, data = evaluate_rows([first, second])

        self.assertEqual([row.default_amount for row in components], [10000, 4000])

    def test_unknown_name_raises_validation_error(self):
        row = SalaryComponentRowStub(
            "NE", amount_based_on_formula=1, formula="missing_field * 2"
        )

        with self.assertRaises(frappe.ValidationError):
            evaluate_rows([row])

    def test_invalid_syntax_raises_validation_error(self):
        row = SalaryComponentRowStub("SE", amount_based_on_formula=1, formula="base *")

        with self.assertRaises(frappe.ValidationError):
            evaluate_rows([row], frappe._dict(base=1))

    def test_division_by_zero_raises_validation_error(self):
        row = SalaryComponentRowStub(
            "DZ", amount_based_on_formula=1, formula="base / 0"
        )

        with self.assertRaises(frappe.ValidationError):
            evaluate_rows([row], frappe._dict(base=1))
