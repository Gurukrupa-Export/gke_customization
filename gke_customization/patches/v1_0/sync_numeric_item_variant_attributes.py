"""Bring every Item's attribute rows for a numeric Item Attribute in line with the attribute.

ERPNext checks a new variant against its *template's* row: `Item.validate_variant` reads
`numeric_values` off that row, and a row that is not numeric must find the value in the
attribute's own list - which a numeric attribute does not have. So a template whose row says
``numeric_values = 0`` refuses every value: "Attribute Value 7.0 is not valid for the selected
attribute Distance Between Kadi To Mugappu".

Only the Item form copies these columns from the attribute (`item.js` `add_fetch`). Templates
that arrived by Data Import or a script kept the default 0 and a 0/0/0 range - 449 of them for
"Distance Between Kadi To Mugappu" alone, from the 2026-08-08 import.

The range goes with the flag: a numeric row with an increment of 0 is refused too ("Increment
for Attribute ... cannot be 0"). Rows of list attributes are not touched.
"""

import frappe


def execute():
	frappe.db.sql(
		"""
		update `tabItem Variant Attribute` iva
		join   `tabItem Attribute` ia on ia.name = iva.attribute
		set    iva.numeric_values = 1,
		       iva.from_range = ia.from_range,
		       iva.to_range = ia.to_range,
		       iva.increment = ia.increment
		where  iva.parenttype = 'Item'
		and    ia.numeric_values = 1
		and    (
		           ifnull(iva.numeric_values, 0) = 0
		           or ifnull(iva.from_range, 0) != ia.from_range
		           or ifnull(iva.to_range, 0) != ia.to_range
		           or ifnull(iva.increment, 0) != ia.increment
		       )
		"""
	)
