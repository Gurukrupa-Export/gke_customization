# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta



class OTRequest(Document):
	def validate(self):
		for child in self.order_request:
			if child.ot_hours:
				try:
					# Ensure ot_hours is properly converted from string if necessary
					if isinstance(child.ot_hours, str):
						time_format = "%H:%M:%S"
						ot_time = datetime.strptime(child.ot_hours, time_format).time()
					else:
						ot_time = child.ot_hours
					
					# Convert time field (which is a time object) to total hours
					total_hours = ot_time.hour + (ot_time.minute / 60) + (ot_time.second / 3600)
					
					# Set food eligibility based on total hours (1 hour or more is eligible)
					child.food_eligibility = "Eligible" if total_hours > 1 else "Not Eligible"
				except ValueError:
					frappe.throw(f"Invalid time format for ot_hours: {child.ot_hours}")


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
def fill_employee_details(department, gender=None):
    gender_filter = f"AND gender = '{gender}'" if gender else ""
    
    employees = frappe.db.sql(f"""
        SELECT name, employee_name FROM `tabEmployee`
        WHERE department = '{department}' AND status = 'Active' {gender_filter}
    """, as_dict=1)
    
    return employees
