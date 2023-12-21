# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from erpnext.setup.utils import get_exchange_rate

class RepairOrder(Document):
	pass



@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)
		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)
		quotation.conversion_rate = exchange_rate
		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")

		quotation.quotation_to = "Customer"
		field_map = {
 			# target : source
			"company": "company",
			"party_name": "customer_code",
			"order_type": "order_type",
			"diamond_quality": "diamond_quality"
		}
		for target_field, source_field in field_map.items():
			quotation.set(target_field,source.get(source_field))
		service_types = frappe.db.get_values("Service Type 2", {"parent": source.name},"service_type1")
		for service_type in service_types:
			quotation.append("service_type",{"service_type1": service_type})

	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	snd_order = frappe.db.get_value("Repair Order", source_name, "*")

	target_doc.append("items", {
		"branch": snd_order.get("branch"),
		"project": snd_order.get("project"),
		"item_code": snd_order.get("item"),
		"serial_no": snd_order.get("tag_no"),
		"metal_colour": snd_order.get("metal_colour"),
		"metal_purity": snd_order.get("metal_purity"),
		"metal_touch": snd_order.get("metal_touch"),
		"gemstone_quality": snd_order.get("gemstone_quality"),
		"item_category" : snd_order.get("category"),
		"diamond_quality": snd_order.get("diamond_quality"),
		"item_subcategory": snd_order.get("subcategory"),
		"setting_type": snd_order.get("setting_type"),
		"delivery_date": snd_order.get("delivery_date"),
		"order_form_type": "Serial No and Design Code Order",
		"order_form_id": snd_order.get("name"),
		"salesman_name": snd_order.get("salesman_name"),
		"order_form_date": snd_order.get("order_date"),
		"po_no": snd_order.get("po_no")
	})
	set_missing_values(snd_order, target_doc)

	return target_doc