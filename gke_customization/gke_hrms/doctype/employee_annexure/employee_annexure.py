# # Copyright (c) 2025, Gurukrupa Export and contributors
# # For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeAnnexure(Document):
    def autoname(self):
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        if company_abbr:
            if self.branch:
                branch_short = self.branch.split("-")[-2]
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
            else:
                existing = frappe.db.exists(
                    "Employee Annexure",
                    {
                        "employee_job_offer": self.employee_job_offer,
                        "name": ["!=", self.name],
                    },
                )
            if existing:
                link = frappe.utils.get_link_to_form("Employee Annexure", existing)
                frappe.throw(
                    f"Employee Annexure already exists for this employee , {link}"
                )

        if not self.salary_structure:
            frappe.throw("Select a Salary Structure before saving.")

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
            component_values[abbr] = amount
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
            for key in list(context.keys()):
                val = context[key]
                if isinstance(val, str):
                    try:
                        context[key] = float(val)
                    except ValueError:
                        pass
            return frappe.safe_eval(formula, context)
        except Exception:
            return 0
