# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.model.workflow import apply_workflow

class ItemRequest(Document):
	def after_insert(self):
		if self.select_raw_material and self.workflow_state == "Send to Account":
			apply_workflow(self, "Approve") 

	def before_save(self):
		if self.workflow_state == 'Approved':
			self.status = 'Approved'
	
	def autoname(self):
		type_code_map = {
			'Finding': 'F',
			'Diamond': 'D',
			'Metal': 'M',
			'Gemstone': 'G',
			'Alloy': 'A',
			'Other': 'O'
		}

		# Separate series for consumables
		if self.is_consumable:
			self.name = make_autoname('IRQ-.#####')
			return
		if self.is_asset:
			self.name = make_autoname("IRQ-AS-.#####")
			return

		type_code = type_code_map.get(self.select_raw_material)
		if not type_code:
			frappe.throw("Invalid raw material type selected.")

		# One shared counter for ALL raw material types
		shared_number = make_autoname('IRQ-RAW-.#####')  # one key in tabSeries
		number_part = shared_number.split('-')[-1]       # get just the number

		series = f"IRQ-{type_code}-{number_part}"

		# Final name with type code
		self.name = series

