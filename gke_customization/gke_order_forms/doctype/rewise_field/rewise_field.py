# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RewiseField(Document):
	def validate(self):
		if not self.item:
			return

		item_doc = frappe.get_doc("Item", self.item)

		# Only update for variants (if needed, remove check if applicable to all items)
		if not item_doc.variant_of:
			return

		# Field to Attribute Mapping
		field_to_attribute = {
			"metal_colour": "Metal Colour",
			"diamond_target": "Diamond Target",
			"stone_changeable": "Stone Changeable",
			"gemstone_type": "Gemstone Type",
			"chain_type": "Chain Type",
			"chain_length": "Chain Length",
			"feature": "Feature",
			"rhodium": "Rhodium",
			"enamal": "Enamal",
			"detachable": "Detachable",
			"capganthan": "Cap/Ganthan",
			"two_in_one": "Two in One",
			"product_size": "Product Size",
			"sizer_type": "Sizer Type",
			"lock_type": "Lock Type",
			"black_bead_line": "Black Bead Line",
			"charm": "Charm",
			"count_of_spiral_turns": "Count of Spiral Turns",
			"number_of_ant": "Number of Ant",
			"back_side_size": "Back Side Size",
			"space_between_mugappu": "Space between Mugappu",
			"distance_between_kadi_to_mugappu": "Distance Between Kadi To Mugappu",
			"back_belt": "Back Belt",
			"back_belt_length": "Back Belt Length"
		}

		updated = False

		for fieldname, attribute in field_to_attribute.items():
			new_value = self.get(fieldname)
			if not new_value:
				continue

			found = False
			for row in item_doc.attributes:
				if row.attribute == attribute:
					found = True
					if row.attribute_value != new_value:
						row.attribute_value = new_value
						updated = True
					break

			if not found:
				item_doc.append("attributes", {
					"attribute": attribute,
					"attribute_value": new_value
				})
				updated = True

		if updated:
			item_doc.save()
			frappe.msgprint(_("Item attributes updated in Item <b>{0}</b>").format(item_doc.name))


@frappe.whitelist()
def get_filtered_item_attributes(item_code):
	attribute_list = [
		"Metal Colour", "Diamond Target", "Stone Changeable", "Gemstone Type", "Chain Type",
		"Chain Length", "Feature", "Rhodium", "Enamal", "Detachable", "Cap/Ganthan", "Two in One",
		"Product Size", "Sizer Type", "Lock Type", "Black Bead Line", "Charm", "Count of Spiral Turns",
		"Number of Ant", "Back Side Size", "Space between Mugappu", "Distance Between Kadi To Mugappu",
		"Back Belt", "Back Belt Length"
	]

	if not item_code:
		return {}

	attributes = frappe.get_all(
		"Item Variant Attribute",
		filters={
			"parent": item_code,
			"attribute": ["in", attribute_list]
		},
		fields=["attribute", "attribute_value"]
	)

	return {attr["attribute"]: attr["attribute_value"] for attr in attributes}


import frappe
from frappe import _

@frappe.whitelist()
def get_order_form_fields(order_form_id):
	doc = frappe.get_doc("Order Form", order_form_id)

	# List of fields to extract
	fields_to_copy = [
		"metal_colour", "diamond_target", "stone_changeable", "gemstone_type", "chain_type",
		"chain_length", "feature", "rhodium", "enamal", "detachable", "capganthan", "two_in_one",
		"product_size", "sizer_type", "lock_type", "black_bead_line", "charm",
		"count_of_spiral_turns", "number_of_ant", "back_side_size", "space_between_mugappu",
		"distance_between_kadi_to_mugappu", "back_belt", "back_belt_length"
	]

	# Return only allowed fields as dict
	return {field: getattr(doc, field, None) for field in fields_to_copy}