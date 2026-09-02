import re

import frappe
from frappe import _
from frappe.utils import flt, getdate
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
    COMPONENT_EVAL_GLOBALS,
    SALARY_COMPONENT_FLAGS,
    SalaryStructureAssignment,
    _safe_eval,
)
from hrms.payroll.utils import sanitize_expression, throw_error_message

# Custom fields available only on Salary Slip.
# Seed them during Salary Structure Assignment evaluation to avoid NameError.
SLIP_ONLY_FORMULA_FIELDS = (
    "extra_working_hours",
    "hourly_rate",
    "actual_working_hours",
    "target_working_hours",
    "shift_hours",
    "custom_extra_payment_days",
    "custom_month",
    "consider_working_hours",
    "_is_pf_applicable",
    "_is_physical_handicap",
)

_SLIP_ONLY_FIELD_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(fieldname) for fieldname in SLIP_ONLY_FORMULA_FIELDS)
    + r")\b"
)


def references_slip_only_fields(*expressions) -> bool:
    return any(
        expression and _SLIP_ONLY_FIELD_PATTERN.search(expression)
        for expression in expressions
    )


class CustomSalaryStructureAssignment(SalaryStructureAssignment):
    def _get_component_eval_context(self) -> frappe._dict:
        data = super()._get_component_eval_context()

        # Seed slip-only fields with safe defaults.
        for fieldname in SLIP_ONLY_FORMULA_FIELDS:
            if fieldname == "custom_month":
                data.custom_month = getdate(data.start_date).month
            else:
                data[fieldname] = 0

        return data

    def _evaluate_component_table(self, rows, data: frappe._dict) -> list:
        # Skip evaluation of formulas that depend on Salary Slip-only fields.
        # They will be evaluated later during Salary Slip creation.
        evaluated_components = []

        for struct_row in rows:
            condition = sanitize_expression(struct_row.condition)
            formula = sanitize_expression(struct_row.formula)
            amount = flt(struct_row.amount)
            deferred = references_slip_only_fields(condition, formula)

            try:
                if deferred:
                    default_amount = (
                        0 if struct_row.amount_based_on_formula and formula else amount
                    )
                else:
                    if condition and not _safe_eval(
                        condition, COMPONENT_EVAL_GLOBALS.copy(), data
                    ):
                        continue

                    if struct_row.amount_based_on_formula and formula:
                        default_amount = flt(
                            _safe_eval(formula, COMPONENT_EVAL_GLOBALS.copy(), data),
                            struct_row.precision("amount"),
                        )
                    else:
                        default_amount = amount

            except NameError as ne:
                throw_error_message(
                    struct_row,
                    ne,
                    title=_("Name error"),
                    description=_("This error can be due to missing or deleted field."),
                )
            except SyntaxError as se:
                throw_error_message(
                    struct_row,
                    se,
                    title=_("Syntax error"),
                    description=_("This error can be due to invalid syntax."),
                )
            except Exception as exc:
                throw_error_message(
                    struct_row,
                    exc,
                    title=_("Error in formula or condition"),
                    description=_(
                        "This error can be due to invalid formula or condition."
                    ),
                )
                raise

            data[struct_row.abbr] = default_amount

            evaluated_component_row = frappe._dict(
                default_amount=default_amount,
                amount=amount,
                condition=condition,
                formula=formula,
                precision=struct_row.precision("amount"),
            )

            for field in SALARY_COMPONENT_FLAGS:
                evaluated_component_row[field] = struct_row.get(field)

            evaluated_components.append(evaluated_component_row)

        return evaluated_components
