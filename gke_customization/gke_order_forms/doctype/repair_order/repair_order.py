# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
# import json
from frappe.model.document import Document,json
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import get_link_to_form

class RepairOrder(Document):
	def on_submit(self):
		create_line_items(self)
	# pass

def create_line_items(self):
	if self.required_design == 'CAD':
		create_cad_order_form(self)
		
	elif self.required_design == 'Manual':
		create_sketch_order_form(self)
		# frappe.throw('Manual')

# 	frappe.msgprint(("New Item Created: {0}".format(get_link_to_form("Order Form",order_form_doc.name))))
	# pass

def create_cad_order_form(self):
	order_form_doc = frappe.new_doc("Order Form")
	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.customer_code = self.customer_code
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.parcel_place = self.parcel_place
	order_form_doc.branch = self.branch
	order_form_doc.salesman_name = self.salesman_name
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.diamond_quality = self.diamond_quality
	order_form_doc.service_type  = self.service_type

	order_details = order_form_doc.append("order_details", {})

	order_details.tag_no = self.tag_no
	order_details.design_id = self.item
	order_details.design_type = 'Mod'

	order_details.design_by = self.design_by

	order_details.category = self.category
	order_details.subcategory = self.subcategory

	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2

	order_details.qty = self.qty

	order_details.metal_type = self.metal_type
	order_details.metal_touch = self.metal_touch
	order_details.metal_purity = self.metal_purity
	order_details.metal_colour = self.metal_colour

	order_details.gold_target = self.gold_target
	order_details.diamond_target = self.diamond_target

	order_details.product_size = self.product_size
	order_details.sizer_type = self.sizer_type

	item_doc = frappe.db.get_list('Design Attribute - Multiselect',filters={'parent':self.item})
	# # frappe.throw(self.item)
	# frappe.throw(str(item_doc.custom_design_style))
	# order_details = order_form_doc.append("age_group", {})

	order_form_doc.save()

def create_sketch_order_form(self):
	order_form_doc = frappe.new_doc("Sketch Order Form")
	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.customer_code = self.customer_code
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.branch = self.branch
	order_form_doc.salesman_name = self.salesman_name
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days


	order_details = order_form_doc.append("order_details", {})

	order_details.tag_id = self.tag_no
	order_details.tag__design_id = self.item
	order_details.design_type = 'Mod'

	order_details.delivery_date = self.delivery_date

	order_details.design_by = self.design_by

	order_details.category = self.category
	order_details.subcategory = self.subcategory

	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2

	order_details.qty = self.qty

	order_details.metal_type = self.metal_type
	order_details.metal_touch = self.metal_touch
	order_details.metal_purity = self.metal_purity
	order_details.metal_colour = self.metal_colour

	order_details.gold_target = self.gold_target
	order_details.diamond_target = self.diamond_target

	order_details.product_size = self.product_size
	order_details.sizer_type = self.sizer_type

	order_details = order_form_doc.append("age_group", {})

	order_form_doc.save()
	pass

# new code start(add customer fileds in dict)
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
			quotation.append("service_type",{"service_type1": service_type[0]})

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
		"order_form_type": "Repair Order",
		"order_form_id": snd_order.get("name"),
		"salesman_name": snd_order.get("salesman_name"),
		"order_form_date": snd_order.get("order_date"),
		"custom_customer_sample": snd_order.get("customer_sample"),
		"custom_customer_voucher_no": snd_order.get("customer_sample_voucher_no"),
		"custom_customer_gold": snd_order.get("customer_gold"),
		"custom_customer_diamond": snd_order.get("customer_diamond"),
		"custom_customer_stone": snd_order.get("customer_stone"),
		"custom_customer_good": snd_order.get("customer_good"),
		"po_no": snd_order.get("po_no"),
		"custom_repair_type": snd_order.get("repair_type"),
		"custom_product_type": snd_order.get("product_type"),
		"custom_serial_id_bom": snd_order.get("bom"),
		"custom_bom_weight": snd_order.get("bom_weight"),
		"custom_customer_weight": snd_order.get("customer_weight"),
		"custom_required_design":snd_order.get("required_design"),

	})
	set_missing_values(snd_order, target_doc)

	return target_doc
# new code end(add customer fileds in dict)