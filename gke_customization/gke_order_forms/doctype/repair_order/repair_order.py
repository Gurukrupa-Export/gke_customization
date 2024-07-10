# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document,json
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc

class RepairOrder(Document):	
	def on_submit(self):
		if self.required_design == 'Manual':
			if self.workflow_state == 'Create Sketch' and not self.sketch_order_form:
				order_form_id = create_sketch(self)
				frappe.msgprint("New Sketch Order Form Created: {0}".format(get_link_to_form("Sketch Order Form",order_form_id)))

		if self.required_design == 'CAD':
			if self.workflow_state == 'Create CAD' and not self.sketch_order_form:
				order_form_id = create_cad(self,sketch_item_code=self.item)
				frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		
		if self.required_design == 'No':
			if self.product_type in ['Company Goods','Customer Goods (Company Manufactured)']:
				# self.item = self.new_item_code
				self.new_item_code = self.item
				frappe.db.set_value('Item',self.item,'custom_repair_order',self.name)
				frappe.db.set_value('Item',self.item,'custom_repair_order_form',self.serial_and_design_code_order_form)
				new_bom_doc = create_bom(self,self.new_item_code)
				self.new_bom = new_bom_doc
			else:
				item_template = create_item_template_from_order(self)
				updatet_item_template(item_template)
				item_variant = create_variant_of_template_from_order(item_template,self.name)
				update_item_variant(item_variant,item_template)
				frappe.msgprint(("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
				frappe.db.set_value(self.doctype, self.name, "item", item_variant)	

	def on_update_after_submit(self):
		if self.required_design == 'Manual':
			if self.workflow_state == 'Create CAD' and not self.order_form:
				sketch_item_code = frappe.db.get_list('Item',filters={'custom_sketch_order_form_id': self.sketch_order_form},fields=['name'])[0]['name']
				if not sketch_item_code:
					frappe.throw("Sketch Order Form Item is not created")
				order_form_id = create_cad(self,sketch_item_code)
				frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		# return
# 	# def validate(self):
# 	# 	populate_child_table(self)

		
def create_cad(self,sketch_item_code):
	
	order_form_doc = frappe.new_doc("Order Form")
	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.branch = self.branch
	order_form_doc.salesman_name = self.salesman_name
	order_form_doc.customer_code = self.customer_code
	order_form_doc.order_date = self.order_date
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.project = self.project
	order_form_doc.parcel_place = self.parcel_place
	order_form_doc.po_no = self.po_no
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.diamond_quality = self.diamond_quality
	order_form_doc.service_type = self.service_type
	order_form_doc.repair_order = self.name
	set_value_in_cad_child_table(order_form_doc,self,sketch_item_code)
	
	set_design_attributes_in_order_forms(order_form_doc,self)
	
	order_form_doc.save()
	frappe.db.set_value('Repair Order',self.name,'order_form',order_form_doc.name)
	return order_form_doc.name

def create_sketch(self):
	order_form_doc = frappe.new_doc("Sketch Order Form")

	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.branch = self.branch
	order_form_doc.salesman_name = self.salesman_name

	order_form_doc.customer_code = self.customer_code
	order_form_doc.order_date = self.order_date
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.project = self.project
	order_form_doc.design_by = "Customer Design"
	order_form_doc.po_no = self.po_no
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.repair_order = self.name
	set_value_in_sketch_child_table(order_form_doc,self)
	set_design_attributes_in_order_forms(order_form_doc,self)
	order_form_doc.save()
	frappe.db.set_value('Repair Order',self.name,'sketch_order_form',order_form_doc.name)
	return order_form_doc.name

def set_value_in_cad_child_table(order_form_doc,self,sketch_item_code):
	order_details = order_form_doc.append("order_details", {})
	if self.required_design == 'Manual':
		order_details.design_type = 'Sketch Design'
	elif self.required_design == 'CAD':
		order_details.design_type = 'Mod'

	if self.product_type == 'Company Goods':
		order_details.design_by = 'Our Design'
	else:
		order_details.design_by = 'Customer Design'

	# frappe.throw(f"{sketch_item_code}")
	order_details.bom_or_cad = workflow_state_maker(self)
	order_details.item_type = set_item_type(self)
	order_details.is_repairing = 1
	order_details.design_id = sketch_item_code
	order_details.tag_no = self.tag_no
	order_details.bom = self.bom
	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.metal_target = self.metal_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1
	subcategory_attributes = frappe.db.sql(f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{self.subcategory}' and in_cad = 1""",as_dict=1)
	for i in subcategory_attributes:
		a = getattr(self, i['item_attribute'].replace(' ','_').lower().replace('item_subcategory','subcategory').replace('item_category','category').replace('custom_metal_target','metal_target'))
		setattr(order_details, i['item_attribute'].replace(' ','_').lower(), a)


def set_value_in_sketch_child_table(order_form_doc,self):
	order_details = order_form_doc.append("order_details", {})
	order_details.design_type = 'Mod'
	# order_details.item_type = 'Only Variant'
	order_details.is_repairing = 1
	order_details.tag__design_id = self.item
	order_details.tag_id = self.tag_no
	order_details.master_bom_no = self.bom
	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.metal_target = self.metal_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1
	order_details.budget = 0
	subcategory_attributes = frappe.db.sql(f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{self.subcategory}' and in_cad = 1""",as_dict=1)
	for i in subcategory_attributes:
		a = getattr(self, i['item_attribute'].replace(' ','_').lower().replace('item_subcategory','subcategory').replace('item_category','category').replace('custom_metal_target','metal_target'))
		setattr(order_details, i['item_attribute'].replace(' ','_').lower(), a)
	
def set_design_attributes_in_order_forms(order_form_doc,self):
	item_doc = frappe.db.sql(f"""select parentfield,design_attribute from `tabDesign Attribute - Multiselect` where parent='{self.item}'""",as_dict=1)
	
	age_group = order_form_doc.append("age_group", {})
	alphabetnumber = order_form_doc.append("alphabetnumber", {})
	animalbirds = order_form_doc.append("animalbirds", {})
	collection = order_form_doc.append("collection", {})
	design_style = order_form_doc.append("design_style", {})
	gender = order_form_doc.append("gender", {})
	lines_rows = order_form_doc.append("lines_rows", {})
	language = order_form_doc.append("language", {})
	occasion = order_form_doc.append("occasion", {})
	rhodium = order_form_doc.append("rhodium", {})
	religious = order_form_doc.append("religious", {})
	shapes = order_form_doc.append("shapes", {})
	zodiac = order_form_doc.append("zodiac", {})
	
	for i in item_doc:
		if i['parentfield'] == 'custom_age_group':
			if i['design_attribute']:
				age_group.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_alphabetnumber':
			if i['design_attribute']:
				alphabetnumber.design_attribute = i['design_attribute']		

		elif i['parentfield'] == 'custom_animalbirds':
			if i['design_attribute']:
				animalbirds.design_attribute = i['design_attribute']		

		elif i['parentfield'] == 'custom_collection':
			if i['design_attribute']:
				collection.design_attribute = i['design_attribute']		

		elif i['parentfield'] == 'custom_design_style':
			if i['design_attribute']:
				design_style.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_gender':
			if i['design_attribute']:
				gender.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_lines__rows':
			if i['design_attribute']:
				lines_rows.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_language':
			if i['design_attribute']:
				language.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_occasion':
			if i['design_attribute']:
				occasion.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_rhodium':
			if i['design_attribute']:
				rhodium.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_religious':
			if i['design_attribute']:
				religious.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_shapes':
			if i['design_attribute']:
				shapes.design_attribute = i['design_attribute']
				
		elif i['parentfield'] == 'custom_zodiac':
			if i['design_attribute']:
				zodiac.design_attribute = i['design_attribute']
	
	# if order_form_doc.rhodium == []:
	# 	frappe.throw("IF")
	# else:
	# 	# frappe.throw("ELSE")
	# 	frappe.throw(str((order_form_doc.rhodium[0])))
	# return "YES"

def workflow_state_maker(self):
	if self.product_type in ['Company Goods','Customer Goods (Company Manufactured)']:
		bom_or_cad = 'Duplicate BOM'
	else:
		bom_or_cad = 'CAD'
	return bom_or_cad

def set_item_type(self):
	if self.product_type == 'Customer Goods (Other Company Manufactured)':
		item_type = 'Template and Variant'
	elif self.product_type in ['Company Goods','Customer Goods (Company Manufactured)'] and self.repair_type =='Modify Raw Material':
		item_type = 'Only Variant'
	elif self.product_type in ['Company Goods','Customer Goods (Company Manufactured)'] and self.repair_type =='Modify Product':
		item_type = 'Suffix Of Variant'
	return item_type

def create_item_template_from_order(source_name, target_doc=None):
	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1
		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		target.item_group = source.subcategory + " - T",

	doc = get_mapped_doc(
		"Repair Order",
		source_name.name,
		{
			"Repair Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)

	
	doc.save()
	return doc.name

def create_variant_of_template_from_order(item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Repair Order'
		target.item_group = frappe.db.get_value('Repair Order',source_name,'subcategory') + " - V",
		target.custom_repair_order = source_name
		target.custom_repair_order_form = frappe.db.get_value('Repair Order',source_name,'cad_order_form')
		target.item_code = f'{item_template}-001'
		target.sequence = item_template[2:7]
		subcateogy = frappe.db.get_value('Item',item_template,'item_subcategory')
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': subcateogy,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			try:
				attribute_value = frappe.db.get_value('Repair Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':attribute_value
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')

	doc = get_mapped_doc(
		"Repair Order",
		source_name,
		{
			"Repair Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					# "india":"india",
					# "india_states":"india_states",
					# "usa":"usa",
					# "usa_states":"usa_states",
					# "age_group":"custom_age_group",
					# "alphabetnumber":"custom_alphabetnumber",
					# "animalbirds":"custom_animalbirds",
					# "collection":"custom_collection",
					# "design_style":"custom_design_style",
					# "gender":"custom_gender",
					# "lines_rows":"custom_lines__rows",
					# "language":"custom_language",
					# "occasion":"custom_occasion",
					# "rhodium":"custom_rhodium",
					# "shapes":"custom_religious",
					# "religious":"custom_shapes",
					# "zodiac":"custom_zodiac",
				} 
			}
		},target_doc, post_process
	)
	
	doc.save()
	return doc.name


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
		"custom_new_item_code":snd_order.get("new_item_code"),
		"custom_new_bom":snd_order.get("new_bom"),

	})
	set_missing_values(snd_order, target_doc)

	return target_doc

def updatet_item_template(item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template,
		"custom_repair_order":"",
		"custom_repair_order_form":"",
	})

def update_item_variant(item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})


def create_bom(self,item_variant):
	bom_doc = frappe.get_doc("BOM",self.bom)
	new_bom_doc = frappe.new_doc("BOM")
	new_bom_doc = bom_doc
	new_bom_doc.docstatus = 0
	new_bom_doc.name = ''
	new_bom_doc.is_active = 1
	new_bom_doc.is_default = 1
	new_bom_doc.bom_type = 'Template'
	new_bom_doc.item = item_variant
	new_bom_doc.custom_order_form_type = 'Repair Order'
	new_bom_doc.custom_cad_order_form_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_form_id")
	new_bom_doc.custom_order_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_id")
	new_bom_doc.custom_repair_order_form_id = frappe.db.get_value("Item",item_variant,"custom_repair_order_form")
	new_bom_doc.custom_repair_order_id = frappe.db.get_value("Item",item_variant,"custom_repair_order")
	new_bom_doc.save()
	return new_bom_doc.name