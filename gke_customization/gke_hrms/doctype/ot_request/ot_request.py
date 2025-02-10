# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OTRequest(Document):
	
	def before_save(self):
		if self.workflow_state == 'Send For Approval':
			for row in self.hr_approver:
				row.status = self.workflow_state

	def before_submit(self):
		if self.workflow_state == 'Approved':
			for row in self.hr_approver:
				row.status = self.workflow_state
		if self.workflow_state == 'Rejected':
			for row in self.hr_approver:
				row.status = self.workflow_state	


@frappe.whitelist()
def fill_employee_details(department):
	employees = frappe.db.sql(f"""select name, employee_name from `tabEmployee` where department = '{department}' and status = 'Active'""", as_dict=1)
	return employees


	