# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ItemRequest(Document):
	def before_save(self):
		if self.workflow_state == 'Approved':
			self.status = 'Approved'
	
	# def on_submit(self):
	# 	ctype = self.consumable_type
	# 	frappe.throw(f"{ctype.replace('_','').upper()}")

		# item_doc = frappe.new_doc("Item")
		# item_doc.name 
		# return

