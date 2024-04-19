# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeePenalty(Document):
	pass
#     def before_submit(self):
#         create_employee_advance(self)

# def create_employee_advance(self):
#     for employee in self.employee_penalty_approval:
#         approved_status = employee.status 
#         approved_status = 'Approved'
#         if approved_status:
#             #   frappe.throw('here')
#               employee_advance = frappe.new_doc("Employee Advance")
#               employee_advance.employee = self.employee
#               employee_advance.advance_amount = self.total_penalty_amount
#               employee_advance.advance_type = 'Penalty'
#               employee_advance.purpose = 'Advance Penalty'
#               employee_advance.advance_account = ' '
#               employee_advance.exchange_rate = '1.0'
#               employee_advance.save()
#         frappe.msgprint(str('Employee Advance is created'))