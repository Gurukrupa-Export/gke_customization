# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PreOrderForm(Document):
	def validate(self, method=None):
		if self.workflow_state == "Approved":
			for row in self.pre_order_form_details:
				error_messages = []

				# Check for missing fields
				missing_fields = []
				if not row.design_type:
					missing_fields.append("Design Type")
				if not row.item_metal_colour:
					missing_fields.append("Item Metal Colour")
				if not row.item_setting_type:
					missing_fields.append("Item Setting Type")
				if not row.bom__metal_touch:
					missing_fields.append("BOM Metal Touch")
				if not row.bom__metal_colour:
					missing_fields.append("BOM Metal Colour")
				if not row.bom_setting_type:
					missing_fields.append("BOM Setting Type")

				# Check for Mod-specific fields
				if row.design_type == "Mod - Old Stylebio & Tag No":
					if not row.mod_reason:
						missing_fields.append("Mod Reason")
					if not row.mod_remarks:
						missing_fields.append("Mod Remarks")

				if missing_fields:
					error_messages.append(f"Missing required fields: {', '.join(missing_fields)}")

				# Check for invalid status
				if row.status == "Pending":
					error_messages.append("Status should not be 'Pending'. It must be one of: 'No Item No BOM', 'Item Created', 'BOM Created', 'Done'.")

				# Throw all errors for the row if any
				if error_messages:
					frappe.throw(
						f"Pre Order Form Details (Row #{row.idx}):<br>" + "<br>".join(error_messages)
					)

