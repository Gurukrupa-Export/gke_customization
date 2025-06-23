# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ConsumableMaster(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-CSM-.#####"
			else:
				series = f"{company_abbr}-CSM-.#####"

			self.name = frappe.model.naming.make_autoname(series)

	def before_save(self):
		if self.consumable_items:
			for row in self.consumable_items:
				if row.item_code:
					item = frappe.db.get_value("Item",{'name': row.item_code},['item_name','variant_of'],as_dict=True)
					if item.variant_of:
						attribute_value = frappe.db.get_value(
							"Item Variant Attribute",
							{'parent': row.item_code,'attribute': 'Consumable Type'},
							['attribute_value'])
						row.item_name = attribute_value
					else:
						row.item_name = item.item_name