# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document,json
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc

class RepairOrder(Document):
	def on_submit(self):
		if self.required_design == 'No':
			bom = create_bom(self)
			# order_form_id = create_cad(self)
		# 	frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		# if self.required_design == 'Manual':
		# 	order_form_id = create_sketch(self)
		# 	frappe.msgprint("New Sketch Order Form Created: {0}".format(get_link_to_form("Sketch Order Form",order_form_id)))
		# item_variant = create_line_items(self)
		# create_line_items_bom(self,item_variant)
	
	def on_update_after_submit(self):
		if self.required_design == 'Manual':
			if self.sketch == 1 and not self.sketch_order_form:
				order_form_id = create_sketch(self)
				frappe.msgprint("New Sketch Order Form Created: {0}".format(get_link_to_form("Sketch Order Form",order_form_id)))

			if self.cad == 1 and not self.order_form:
				sketch_item_code = frappe.db.get_list('Item',filters={'custom_sketch_order_form_id': self.sketch_order_form},fields=['name'])
				if not sketch_item_code:
					frappe.throw("Sketch Order Form Item is not created")
				order_form_id = create_cad(self)
				frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))

		if self.required_design == 'CAD':
			if self.cad == 1 and not self.order_form:
				order_form_id = create_cad(self)
				frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		

	# def validate(self):
	# 	populate_child_table(self)

		
def create_cad(self):
	
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
	set_value_in_cad_child_table(order_form_doc,self)

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

	order_form_doc.po_no = self.po_no
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.repair_order = self.name


	set_value_in_sketch_child_table(order_form_doc,self)
	set_design_attributes_in_order_forms(order_form_doc,self)

	order_form_doc.save()

	frappe.db.set_value('Repair Order',self.name,'sketch_order_form',order_form_doc.name)

	return order_form_doc.name

def set_value_in_cad_child_table(order_form_doc,self):
	order_details = order_form_doc.append("order_details", {})
	order_details.design_type = 'Mod'
	if self.product_type == 'Company Goods':
		order_details.design_by = 'Our  Design'
	else:
		order_details.design_by = 'Customer Design'
	order_details.is_repairing = 1
	order_details.design_id = self.item
	order_details.tag_no = self.tag_no
	order_details.bom = self.bom
	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.gold_target = self.gold_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1

def set_value_in_sketch_child_table(order_form_doc,self):
	order_details = order_form_doc.append("order_details", {})
	order_details.design_type = 'Mod'
	order_details.is_repairing = 1
	order_details.tag__design_id = self.item
	order_details.tag_id = self.tag_no
	order_details.master_bom_no = self.bom
	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.subsetting_type = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.gold_target = self.gold_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1


def set_design_attributes_in_order_forms(order_form_doc,self):
	item_doc = frappe.db.sql(f"""select parentfield,design_attribute from `tabDesign Attribute - Multiselect` where parent='{self.item}'""",as_dict=1)
	
	age_group = order_form_doc.append("age_group", {})
	rhodium = order_form_doc.append("rhodium", {})
	design_style = order_form_doc.append("design_style", {})
	occasion = order_form_doc.append("occasion", {})
	gender = order_form_doc.append("gender", {})

	for i in item_doc:
		if i['parentfield'] == 'custom_age_group':
			if i['design_attribute']:
				age_group.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_rhodium':
			if i['design_attribute']:
				rhodium.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_design_style':
			if i['design_attribute']:
				design_style.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_occasion':
			if i['design_attribute']:
				occasion.design_attribute = i['design_attribute']

		elif i['parentfield'] == 'custom_gender':
			if i['design_attribute']:
				gender.design_attribute = i['design_attribute']

	
	# if order_form_doc.rhodium == []:
	# 	frappe.throw("IF")
	# else:
	# 	# frappe.throw("ELSE")
	# 	frappe.throw(str((order_form_doc.rhodium[0])))

# def set_design_attributes_for_item(item_document,self):
# 	item_doc = frappe.db.sql(f"""select parentfield,design_attribute from `tabDesign Attribute - Multiselect` where parent='{self.item}'""",as_dict=1)

# 	age_group = item_document.append("custom_age_group", {})
# 	alphabetnumber = item_document.append("custom_alphabetnumber", {})
# 	animalbirds = item_document.append("custom_animalbirds", {})
# 	collection = item_document.append("custom_collection", {})
# 	design_style = item_document.append("custom_design_style", {})
# 	gender = item_document.append("custom_gender", {})
# 	lines_rows = item_document.append("custom_lines__rows", {})
# 	language = item_document.append("custom_language", {})
# 	occasion = item_document.append("custom_occasion", {})
# 	rhodium = item_document.append("custom_rhodium", {})
# 	shapes = item_document.append("custom_shapes", {})
# 	zodiac = item_document.append("custom_zodiac", {})


# 	for i in item_doc:
# 		if i['parentfield'] == 'custom_age_group':
# 			age_group.design_attribute = i['design_attribute']
			
# 		elif i['parentfield'] == 'custom_alphabetnumber':
# 			alphabetnumber.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_animalbirds':
# 			animalbirds.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_collection':
# 			collection.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_design_style':
# 			design_style.design_attribute = i['design_attribute']
		
# 		elif i['parentfield'] == 'custom_gender':
# 			gender.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_lines__rows':
# 			lines_rows.design_attribute = i['design_attribute']
			
# 		elif i['parentfield'] == 'custom_language':
# 			language.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_occasion':
# 			occasion.design_attribute = i['design_attribute']
			
# 		elif i['parentfield'] == 'custom_shapes':
# 			shapes.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_rhodium':
# 			rhodium.design_attribute = i['design_attribute']

# 		elif i['parentfield'] == 'custom_zodiac':
# 			zodiac.design_attribute = i['design_attribute']



# def updatet_item_template(item_template):
# 	frappe.db.set_value('Item',item_template,{
# 		"is_design_code":0,
# 		"item_code":item_template,
# 		"custom_repair_order":"",
# 		"custom_repair_order_form":"",
# 		"designer":"",
# 	})

# def update_item_variant(item_variant,item_template):
# 	frappe.db.set_value('Item',item_variant,{
# 		"is_design_code":1,
# 		"variant_of" : item_template
# 	})


# def create_line_items(self):
# 	if self.repair_type == 'Modify Product' and self.product_type in ['Company Goods','Customer Goods (Company Manufactured)']:
# 			item_template = create_suffix_template(self)
# 			# frappe.db.set_value('Item',item_template,'modified_from','')
# 			updatet_item_template(item_template)
# 			item_variant = create_suffix_variant(self,item_template,self.name)
# 			frappe.db.set_value('Repair Order',self.name,'design_code',item_variant)
# 			update_item_variant(item_variant,item_template)
# 	else:
# 		item_variant = create_variant(self)
# 	frappe.db.set_value('Repair Order',self.name,'new_design_code',item_variant)
# 	return item_variant


# def populate_child_table(self):
# 	if self.workflow_state == "Assigned":
# 		self.rough_sketch_approval = []
# 		self.final_sketch_approval = []
# 		self.final_sketch_approval_cmo = []
# 		for designer in self.designer_assignment_sketch:
# 			r_s_row = self.get(
# 				"rough_sketch_approval",
# 				{
# 					"designer": designer.designer,
# 					"designer_name": designer.designer_name,
# 				},
# 			)
# 			if not r_s_row:
# 				self.append(
# 					"rough_sketch_approval",
# 					{
# 						"designer": designer.designer,
# 						"designer_name": designer.designer_name,
# 					},
# 				)

# 			self.append(
# 				"final_sketch_approval",
# 				{
# 					"designer": designer.designer,
# 					"designer_name": designer.designer_name,
# 				},
# 			)

# 			self.append(
# 				"final_sketch_approval_cmo",
# 				{
# 					"designer": designer.designer,
# 					"designer_name": designer.designer_name,
# 				},
# 			)

# 			hod_name = frappe.db.get_value("User", {"email": frappe.session.user}, "full_name")
# 			subject = "Sketch Design Assigned"
# 			context = f"Mr. {hod_name} has assigned you a task"
# 			user_id = frappe.db.get_value("Employee", designer.designer, "user_id")
# 			if user_id:
# 				create_system_notification(self, subject, context, [user_id])

# def create_system_notification(self, subject, context, recipients):
# 	if not recipients:
# 		return
# 	notification_doc = {
# 		"type": "Alert",
# 		"document_type": self.doctype,
# 		"document_name": self.name,
# 		"subject": subject,
# 		"from_user": frappe.session.user,
# 		"email_content": context,
# 	}
# 	for user in recipients:
# 		notification = frappe.new_doc("Notification Log")
# 		notification.update(notification_doc)

# 		notification.for_user = user
# 		if (
# 			notification.for_user != notification.from_user
# 			or notification_doc.get("type") == "Energy Point"
# 			or notification_doc.get("type") == "Alert"
# 		):
# 			notification.insert(ignore_permissions=True)


# 	# if self.required_design == 'CAD':
# 	# 	create_cad_order_form(self)
		
# 	# elif self.required_design == 'Manual':
# 	# 	create_sketch_order_form(self)
# 		# frappe.throw('Manual')

# def create_line_items_bom(self,item_variant):
	
# 	if self.product_type in ['Company Goods','Customer Goods (Company Manufactured)']:
# 		if not self.bom:
# 			frappe.throw('BOM is Missing')
# 		bom_doc = frappe.new_doc("BOM")
# 		bom_doc.is_default = 0
# 		bom_doc.is_active = 0
# 		bom_doc.bom_type = "Template"
# 		bom_doc.tag_no = self.tag_no
# 		bom_doc.customer = self.customer_code
# 		bom_doc.item = item_variant
# 		bom_doc.metal_detail = frappe.get_doc('BOM',self.bom).metal_detail
# 		bom_doc.finding_detail = frappe.get_doc('BOM',self.bom).finding_detail
# 		bom_doc.diamond_detail = frappe.get_doc('BOM',self.bom).diamond_detail
# 		bom_doc.gemstone_detail = frappe.get_doc('BOM',self.bom).gemstone_detail
# 		bom_doc.other_detail = frappe.get_doc('BOM',self.bom).other_detail
# 		if self.bom_weight < self.customer_weight:
# 			bom_doc.other_detail = bom_doc.other_detail
# 			other_detail = bom_doc.append("other_detail", {})
# 			other_detail.item_code = 'Customer Goods'
# 			other_detail.qty = 1
# 			other_detail.uom = 'Gram'
# 			other_detail.quantity = self.customer_weight - self.bom_weight
# 		bom_doc.save()		
# 		frappe.msgprint(("New BOM Created: {0}".format(get_link_to_form("BOM",bom_doc.name))))
# 		frappe.db.set_value('Repair Order',self.name,'new_bom',bom_doc.name)

# def create_variant(self,target_doc=None):
# 	db_data = frappe.db.get_list('Item',filters={'name':self.item},fields=['variant_of'],order_by='creation desc')[0]
# 	db_data1 = frappe.db.get_list('Item',filters={'variant_of':db_data['variant_of']},fields=['name'],order_by='creation desc')[0]
# 	index = int(db_data1['name'].split('-')[1]) + 1
# 	suffix = "%.3i" % index
# 	item_code = db_data['variant_of'] + '-' + suffix
# 	user = get_email(frappe.session.user)
# 	def post_process(source, target):
		
# 		target.order_form_type = 'Repair Order'
# 		target.custom_repair_order = self.name
# 		target.designer = frappe.db.get_value("User", user, ["full_name"], as_dict=True)['full_name']
# 		target.has_serial_no = 1
# 		target.variant_of = db_data['variant_of']
# 		target.is_design_code = 1
# 		target.is_stock_item = 1
# 		target.include_item_in_manufacturing = 1
# 		target.item_code = item_code
# 		target.item_group = frappe.db.get_value('Repair Order',self.name,'subcategory') + " - V",
		
# 		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': self.subcategory,'in_item_variant':1},'item_attribute',order_by='idx asc'):
# 			attribute_with = i.item_attribute.lower().replace(' ', '_')	
# 			target.append('attributes',{
# 				'attribute':i.item_attribute,
# 				'variant_of':db_data['variant_of'],
# 				'attribute_value':frappe.db.get_value('Repair Order',self.name,attribute_with)
# 			})
# 		target.sequence = item_code[2:7]
# 		# custom_age_group = frappe.db.sql(f"""select design_attribute from `tabDesign Attribute - Multiselect` where parent='{self.item}' and parentfield = 'custom_age_group'""",as_dict=1)
# 		# frappe.throw(str(custom_age_group))
# 		# target.custom_age_group = frappe.db.sql(f"""select design_attribute from `tabDesign Attribute - Multiselect` where parent='{self.item}' and parentfield = 'custom_age_group'""",as_dict=1)

# 	doc = get_mapped_doc(
# 		"Repair Order",
# 		self.name,
# 		{
# 			"Repair Order": {
# 				"doctype": "Item",
# 				"field_map": {
# 					"category": "item_category",
# 					"subcategory": "item_subcategory",
# 					"setting_type": "setting_type",
# 					"sub_setting_type1": "sub_setting_type",
# 					"sub_setting_type2": "custom_sub_setting_type2",
# 					# "india":"india",
# 					# "india_states":"india_states",
# 					# "usa":"usa",
# 					# "usa_states":"usa_states",
					
# 				} 
# 			}
# 		},target_doc, post_process
# 	)
	
# 	doc.save()
# 	item_doc = frappe.get_doc('Item',doc.name)
# 	set_design_attributes_for_item(item_doc,self)
# 	item_doc.save()
# 	frappe.msgprint(("New Item Created: {0}".format(get_link_to_form("Item",doc.name))))
# 	return doc.name

# def create_suffix_template(self,target_doc=None):
# 	user = get_email(frappe.session.user)
# 	variant_of = frappe.db.get_value("Item",self.item,'variant_of')
# 	if variant_of == None:
# 		frappe.throw(f'Template of {variant_of} is not available')

# 	def post_process(source, target):
# 		target.has_variants = 1
# 		target.is_design_code = 1
# 		query = """
# 		SELECT name, modified_sequence, `sequence`
# 		FROM `tabItem` ti
# 		WHERE name LIKE %s AND has_variants = 1
# 		ORDER BY creation DESC
# 		"""

# 		results = frappe.db.sql(query, (f"%{variant_of}/%",), as_dict=True)
# 		if results:
# 			modified_sequence = int(results[0]['modified_sequence']) + 1
# 			modified_sequence = f"{modified_sequence:02}"
# 		else:
# 			modified_sequence = '01'
		
# 		target.item_code = variant_of + '/' + modified_sequence
# 		target.modified_sequence = modified_sequence
# 		target.item_group = self.subcategory + " - T",
# 		target.designer = frappe.db.get_value("User", user, ["full_name"], as_dict=True)['full_name']
# 		target.order_form_type = 'Repair Order'
# 	doc = get_mapped_doc(
# 		"Repair Order",
# 		self.name,
# 		{
# 			"Repair Order": {
# 				"doctype": "Item",
# 				"field_map": {
# 					"category": "item_category",
# 					"subcategory": "item_subcategory",
# 					"setting_type": "setting_type",
# 				} 
# 			}
# 		},target_doc, post_process
# 	)
# 	doc.save()
# 	return doc.name

# def create_suffix_variant(self,item_template,source_name, target_doc=None):
# 	user = get_email(frappe.session.user)
# 	def post_process(source, target):
# 		target.order_form_type = 'Repair Order'
# 		target.custom_repair_order = source_name
# 		target.custom_repair_order_form = frappe.db.get_value('Repair Order',source_name,'serial_and_design_code_order_form')
# 		target.item_code = item_template[:10] + '-001'
# 		target.sequence = item_template[2:7]
# 		target.item_group = self.subcategory + " - V",
# 		target.designer = frappe.db.get_value("User", user, ["full_name"], as_dict=True)['full_name']

# 		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': self.subcategory,'in_item_variant':1},'item_attribute',order_by='idx asc'):
# 			attribute_with = i.item_attribute.lower().replace(' ', '_')	
# 			target.append('attributes',{
# 				'attribute':i.item_attribute,
# 				'variant_of':item_template,
# 				'attribute_value':frappe.db.get_value('Repair Order',source_name,attribute_with)
# 			})

# 	doc = get_mapped_doc(
# 		"Repair Order",
# 		source_name,
# 		{
# 			"Repair Order": {
# 				"doctype": "Item",
# 				"field_map": {
# 					"category": "item_category",
# 					"subcategory": "item_subcategory",
# 					"setting_type": "setting_type",
# 				} 
# 			}
# 		},target_doc, post_process
# 	)
# 	doc.save()
# 	item_doc = frappe.get_doc('Item',doc.name)
# 	set_design_attributes_for_item(item_doc,self)
# 	item_doc.save()
# 	frappe.msgprint(("New Item Created: {0}".format(get_link_to_form("Item",doc.name))))
# 	return doc.name

# def get_email(user=None):
# 	p = frappe.db.get_value("User", user, ["email"], as_dict=True)
# 	return p 





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


def create_bom(self):
	# if 
	return
