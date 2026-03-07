# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeSurveyForm(Document):
	pass



@frappe.whitelist(allow_guest=True)
def get_survey_form_question(template_name):
    template = frappe.db.get_values("Survey Question Table", {"parent": template_name}, "*")
    return template

@frappe.whitelist(allow_guest=True)
def get_employee(employee_id):
    employee = frappe.db.get_value("Employee", {"name": employee_id}, ["employee_name", "company", "department", "branch", "designation"], as_dict=True)
    return employee