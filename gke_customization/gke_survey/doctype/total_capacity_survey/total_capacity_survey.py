# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TotalCapacitySurvey(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		
		# Naming series using company and branchabbreviation 
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-TCS-.#####"
			else:
				series = f"{company_abbr}-TCS-.#####"
			self.name = frappe.model.naming.make_autoname(series)

