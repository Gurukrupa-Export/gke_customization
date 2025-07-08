# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UpdateCustomerDiamondCriteria(Document):
	pass
		# def validate(self):
		# 	self.update_items_in_diamond_criteria()

		# def update_items_in_diamond_criteria(self):
		# 	data = []
		# 	if not self.customer:
			
		# 		frappe.throw("Customer not selected.")

		# 	customer_doc = frappe.get_doc("Customer", self.customer)


			# for row, customer_row in zip(self.diamond_grades, customer_doc.diamond_grades):
			# for idx, row in enumerate(self.diamond_grades):
			# 		if idx < len(customer_doc.diamond_grades):
			# 			customer_row = self.diamond_grades[idx]
			# 		else:
			# 			customer_row = customer_doc.append(self.diamond_grades[idx])

			# 		customer_row.diamond_quality = row.existing_diamond_quality
			# 		customer_row.diamond_grade_1 = row.existing_grade_1
			# 		customer_row.diamond_grade_2 = row.existing_grade_2
			# 		customer_row.diamond_grade_3 = row.existing_grade_3
			# 		customer_row.diamond_grade_4 = row.existing_grade_4
			# 		data.append(customer_row.as_dict())	

			# customer_doc.set("diamond_grades", [])

			# for row in self.diamond_grades:
			# 	# if row.is_new_diamond_quality == 0:
			# 		data.append(row.as_dict())
			# 		customer_doc.append("diamond_grades", {
			# 			"diamond_quality": row.diamond_quality,
			# 			"diamond_grade_1": row.diamond_grade_1,
			# 			"diamond_grade_2": row.diamond_grade_2,
			# 			"diamond_grade_3": row.diamond_grade_3,
			# 			"diamond_grade_4": row.diamond_grade_4,
			#         })
				# else:
				# 	data.append(row.as_dict())
				# 	customer_doc.append("diamond_grades", {
				# 		"diamond_quality": row.diamond_quality,
				# 		"diamond_grade_1": row.diamond_grade_1,
				# 		"diamond_grade_2": row.diamond_grade_2,
				# 		"diamond_grade_3": row.diamond_grade_3,
				# 		"diamond_grade_4": row.diamond_grade_4,
			    #     })


			# frappe.throw(f"{data}")
# 			customer_doc.save()

# @frappe.whitelist()
# def get_customer_diamond_criteria(customer):
# 	doc = frappe.get_doc("Customer",customer)
# 	return doc



