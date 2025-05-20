# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TargetsForm(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			series = f"{company_abbr}-OTF-.#####"

			self.name = frappe.model.naming.make_autoname(series)
	
	def validate(self):
		calculate_total(self)	

def calculate_total(self):
    total_open_outright = 0.0
    total_open_outwork = 0.0
    total_close_outright = 0.0
    total_close_outwork = 0.0

    for row in self.order_target_detail:
        target_value = 0.0
        for field in ["target_5", "target_4", "target_3", "target_2", "target_1"]:
            val = getattr(row, field, None)
            if val:
                target_value = float(val or 0)
                break

        if row.setting_type == 'Open' and row.nature == 'Outright':
            total_open_outright += target_value
        if row.setting_type == 'Open' and row.nature == 'Outwork':
            total_open_outwork += target_value
        if row.setting_type == 'Close' and row.nature == 'Outright':
            total_close_outright += target_value
        if row.setting_type == 'Close' and row.nature == 'Outwork':
            total_close_outwork += target_value
        

    self.total_open_outright = total_open_outright
    self.total_open_outwork = total_open_outwork
    self.total_close_outright = total_close_outright
    self.total_close_outwork = total_close_outwork

    if self.total_open_outright and self.total_close_outright:
        self.total_openclose_outright = self.total_open_outright + self.total_close_outright
    
    if self.total_close_outwork and self.total_open_outwork:
        self.total_closeopen_outwork = self.total_close_outwork + self.total_open_outwork
    
    self.total_open_of = self.total_open_outright + self.total_open_outwork
    self.total_close_of = self.total_close_outright + self.total_close_outwork
    self.round_of_total = self.total_open_of + self.total_close_of

