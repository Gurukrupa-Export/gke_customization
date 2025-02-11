import frappe
from frappe import _
import hrms
from hrms.payroll.doctype.employee_incentive.employee_incentive import EmployeeIncentive


class CustomEmployeeIncentive(EmployeeIncentive):
    def on_submit(self):
        company = frappe.db.get_value("Employee", self.employee, "company")

        additional_salary = frappe.new_doc("Additional Salary")
        additional_salary.employee = self.employee
        additional_salary.currency = self.currency
        additional_salary.salary_component = self.salary_component
        additional_salary.amount = self.incentive_amount
        additional_salary.payroll_date = self.payroll_date
        additional_salary.company = company
        additional_salary.ref_doctype = self.doctype
        additional_salary.ref_docname = self.name
        
        if self.custom_system_generated_incentive and self.custom_system_generated_incentive > 0:
            additional_salary.overwrite_salary_structure_amount = 1
        else:
            additional_salary.overwrite_salary_structure_amount = 0

        additional_salary.submit()
    