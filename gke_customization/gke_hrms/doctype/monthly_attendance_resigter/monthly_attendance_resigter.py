# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
from frappe.utils import time_diff_in_seconds,time_diff_in_hours

class MonthlyAttendanceResigter(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"HR-{company_abbr}-{branch_short}-MAR-.#####"
			else:
				series = f"HR-{company_abbr}-MAR-.#####"

			self.name = frappe.model.naming.make_autoname(series)
	
		
@frappe.whitelist()
def get_attendance_data(company,from_date,to_date,branch=None):
	payroll_entry = frappe.db.exists("Payroll Entry",
		{
			"company": company,
			"branch": branch,
			"start_date": from_date,
			"end_date": to_date,
			"docstatus": 1
		})	
	salary_slips = frappe.get_all("Salary Slip",
		filters={
			"company": company,
			"payroll_entry": payroll_entry,
			"docstatus": 1
		},
		fields=["docstatus", "name"])
	
	if not salary_slips:
		frappe.throw("No submitted Salary Slip found for this Payroll Period.")

	url = "http://3.108.219.130:7000/attendance"

	params = {
		"company": company,
		"from_att_date": from_date,
		"to_att_date": to_date
	}

	try:
		response = requests.get(url, params=params, timeout=300)   # 10s timeout safety
		response.raise_for_status()
		data = response.json()
		return data   
	except requests.exceptions.RequestException as e:
		frappe.throw(f"Error fetching API: {e}")

@frappe.whitelist()
def get_attendance_data_btn(company,from_date,to_date):

	url = "http://3.108.219.130:7000/attendance"

	params = {
		"company": company,
		"from_att_date": from_date,
		"to_att_date": to_date
	}

	try:
		response = requests.get(url, params=params, timeout=300)   # 10s timeout safety
		response.raise_for_status()
		data = response.json()
		return data   
	except requests.exceptions.RequestException as e:
		frappe.throw(f"Error fetching API: {e}")