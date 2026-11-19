# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeAnnexure(Document):
    def autoname(self):
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        if company_abbr:
            if self.branch:
                branch_parts = self.branch.split("-")
                branch_short = branch_parts[-2] if len(branch_parts) > 1 else self.branch
                series = f"{company_abbr}-{branch_short}-EAX-.#####"
            else:
                series = f"{company_abbr}-EAX-.#####"

            self.name = frappe.model.naming.make_autoname(series)

    def validate(self):
        if self.get("__islocal") or not self.name:
            if self.employee:
                existing = frappe.db.exists(
                    "Employee Annexure",
                    {"employee": self.employee, "name": ["!=", self.name]},
                )
            elif self.employee_job_offer:
                existing = frappe.db.exists(
                    "Employee Annexure",
                    {
                        "employee_job_offer": self.employee_job_offer,
                        "name": ["!=", self.name],
                    },
                )
            else:
                existing = None
            if existing:
                link = frappe.utils.get_link_to_form("Employee Annexure", existing)
                frappe.throw(
                    _("Employee Annexure already exists for this employee, {0}").format(
                        link
                    )
                )

        if not self.salary_structure:
            frappe.throw(_("Select a Salary Structure before saving."))

        self.earnings = []
        self.deductions = []

        base = self.ctc
        gross_pay = base

        custom_state = frappe.db.get_value("Branch", self.branch, "state")
        custom_month = getdate().month
        component_values = {
            "base": base,
            "gross_pay": gross_pay,
            "custom_state": custom_state,
            "custom_month": custom_month,
        }
        convert_numeric_strings(component_values)

        salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)

        earning_component_names = {
            row.salary_component
            for row in salary_structure.earnings
            if row.salary_component
        }
        statistical_components = {
            c.name: c.statistical_component
            for c in frappe.get_all(
                "Salary Component",
                filters={"name": ["in", list(earning_component_names)]},
                fields=["name", "statistical_component"],
            )
        }

        for row in salary_structure.earnings:
            abbr = row.abbr
            amount = self.evaluate_formula(row.formula, component_values)
            amount = round(amount)
            component_values[abbr] = amount

            if amount and not statistical_components.get(row.salary_component):
                self.append(
                    "earnings",
                    {
                        "component": row.salary_component,
                        "amount": amount,
                        "abbr": abbr,
                        "formula": row.formula,
                    },
                )

        for row in salary_structure.deductions:
            abbr = row.abbr
            amount = self.evaluate_formula(row.formula, component_values)
            amount = round(amount)
            if not self.is_esic_applicable:
                if row.abbr == "ESIC":
                    amount = 0
            if row.abbr == "LWF":
                amount = 0
            if not self.is_pf_applicable:
                if row.abbr == "PF":
                    amount = 0
            component_values[abbr] = amount
            if amount:
                self.append(
                    "deductions",
                    {
                        "component": row.salary_component,
                        "amount": amount,
                        "abbr": abbr,
                        "formula": row.formula,
                    },
                )

    def evaluate_formula(self, formula, context):
        if not formula:
            return 0
        try:
            return frappe.safe_eval(formula, context)
        except Exception:
            frappe.log_error(
                title=_("Employee Annexure formula error"),
                message="{0}\n\n{1}".format(formula, frappe.get_traceback()),
            )
            return 0


def convert_numeric_strings(context):
    for key, value in context.items():
        if isinstance(value, str):
            try:
                context[key] = float(value)
            except ValueError:
                pass
