# Copyright (c) 2023, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now,getdate
from frappe.model.document import Document

class ItemGatepass(Document):
	# pass
	def before_insert(self):
		current_date = getdate()
		current_year = current_date.year
		self.year = current_year
		max_sequence = frappe.db.get_list("Item Gatepass", pluck="sequence")
		max_sequence.sort()
		if max_sequence:
			sequence = int(max_sequence[-1]) + 1
			sequence = f"{sequence:04}"
		else:
			sequence = '0001'
		self.sequence = sequence

