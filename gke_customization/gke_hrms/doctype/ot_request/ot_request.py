# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta



class OTRequest(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if not company_abbr:
			frappe.throw(f"Abbreviation not found for company: {self.company}")

		# Extract branch short code
		branch_short = self.branch.split('-')[-2]  # Extract "ST" from "GEPL-ST"

		# Naming series using company abbreviation
		series = f"OT-{company_abbr}-{branch_short}-.#####"
		self.name = frappe.model.naming.make_autoname(series)
		
		# return 
	
	def validate(self):
		# if not self.company or not self.branch:
		# 	frappe.throw("Company and Branch are required to generate the OT Request name.")
		
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
					# total_hours = ot_time.hour + (ot_time.minute / 60) + (ot_time.second / 3600)
					if isinstance(ot_time, timedelta):
						total_hours = ot_time.total_seconds() / 3600  # Correct way to get total hours from timedelta
					else:
						total_hours = ot_time.hour + (ot_time.minute / 60) + (ot_time.second / 3600)
					
					# Set food eligibility based on total hours (1 hour or more is eligible)
					child.food_eligibility = "Eligible" if total_hours > 1 else "Not Eligible"
				except ValueError:
					frappe.throw(f"Invalid time format for ot_hours: {child.ot_hours}")


	# def before_save(self):
	# 	if self.workflow_state == 'Send For Approval':
	# 		for row in self.hr_approver:
	# 			row.status = self.workflow_state

	# def before_submit(self):
	# 	if self.workflow_state == 'Approved':
	# 		for row in self.hr_approver:
	# 			row.status = self.workflow_state
	# 	if self.workflow_state == 'Rejected':
	# 		for row in self.hr_approver:
	# 			row.status = self.workflow_state	


@frappe.whitelist()
def fill_employee_details(department, gender=None):
    gender_filter = "" if not gender else "AND gender = %s"
    gender_value = [gender] if gender else []
    
    employees = frappe.db.sql(f'''
        SELECT name, employee_name FROM `tabEmployee`
        WHERE department = %s AND status = 'Active' {gender_filter}
    ''', [department] + gender_value, as_dict=1)
    
    return employees
