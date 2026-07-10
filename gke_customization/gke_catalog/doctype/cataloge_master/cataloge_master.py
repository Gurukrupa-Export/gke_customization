# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CatalogeMaster(Document):
	pass
	# def before_insert(self):
	# 	if self.customer and not self.diamond_quality:

	# 		customer = frappe.get_doc("Customer", self.customer)
	# 		for row in customer.diamond_grades:
	# 			self.append("diamond_quality", {
	# 				"diamond_quality": row.diamond_quality
	# 			})
