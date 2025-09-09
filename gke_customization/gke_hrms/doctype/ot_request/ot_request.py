# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta

class OTRequest(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-OT-.#####"
			else:
				series = f"{company_abbr}-OT-.#####"

			self.name = frappe.model.naming.make_autoname(series)
		
	
	def validate(self):		
		for child in self.order_request:
			if child.ot_hours:
				try:
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

@frappe.whitelist()
def fill_employee_details(department,department_head,branch, gender=None):
	filters = {
		'department': department,
		'reports_to': department_head,
		'status': 'Active'
	}
	if branch:
		filters.update({ 'branch': branch })
	
	if gender:
		filters.update({ 'gender': gender })
		
	employees = frappe.db.get_all("Employee",
			filters = filters,
			fields = ['name','employee_name']
		)

	if employees:
		return employees
	else:
		frappe.msgprint(f"There is no Employees for Selected Department Head.")