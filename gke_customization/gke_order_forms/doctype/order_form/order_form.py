# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.item_variant import (
	ItemVariantExistsError,
	copy_attributes_to_variant,
	get_variant,
	make_variant_item_code,
	validate_item_variant_attributes,
)
from frappe.utils import (
	cint,
	cstr,
	flt,
	formatdate,
	get_link_to_form,
	getdate,
	now_datetime,
	nowtime,
	strip,
	strip_html,
)


class OrderForm(Document):
	def on_submit(self):
		create_cad_orders(self)

	# def on_cancel(self):
	# 	delete_auto_created_cad_order(self)

	def validate(self):
		
		self.validate_category_subcaegory()

	def validate_category_subcaegory(self):
		for row in self.get("order_details"):
			if row.subcategory:
				parent = frappe.db.get_value("Attribute Value", row.subcategory, "parent_attribute_value")
				if row.category != parent:
					frappe.throw(_(f"Category & Sub Category mismatched in row #{row.idx}"))


def create_cad_orders(self):
	doclist = []
	for row in self.order_details:
		docname = make_cad_order(row.name, parent_doc = self)
		# frappe.db.set_value('Order Form Detail',row.name,'cad_order_id',docname)
		doclist.append(get_link_to_form("Order", docname))

	if doclist:
		msg = _("The following {0} were created: {1}").format(
				frappe.bold(_("Orders")), "<br>" + ", ".join(doclist)
			)
		frappe.msgprint(msg)

def delete_auto_created_cad_order(self):
	for row in frappe.get_all("Order", filters={"order_form": self.name}):
		frappe.delete_doc("Order", row.name)

def make_cad_order(source_name, target_doc=None, parent_doc = None):
	def set_missing_values(source, target):
		target.cad_order_form_detail = source.name
		target.cad_order_form = source.parent
		target.index = source.idx
	
	
	design_type = frappe.get_doc('Order Form Detail',source_name).design_type
	item_type = frappe.get_doc('Order Form Detail',source_name).item_type
	# as_per_serial_no = frappe.get_doc('Order Form Detail',source_name).as_per_serial_no
	mod_reason = frappe.get_doc('Order Form Detail',source_name).mod_reason
	design_id = frappe.get_doc('Order Form Detail',source_name).design_id
	is_repairing = frappe.get_doc('Order Form Detail',source_name).is_repairing
	if design_type == 'Mod':
		# if as_per_serial_no == 1:
		# 	item_type = "No Variant No Suffix"
		# 	bom_or_cad = 'New BOM'
		if is_repairing == 1:
			bom_or_cad = frappe.get_doc('Order Form Detail',source_name).bom_or_cad
			item_type = frappe.get_doc('Order Form Detail',source_name).item_type
		else:
			# if is_repairing == 1:
			# 	bom_or_cad = frappe.get_doc('Order Form Detail',source_name).bom_or_cad
			# 	if frappe.get_doc('Order Form Detail',source_name).item_type == 'New Template & Variant':
			# 		item_type = 'New Template & Variant'
			# 	else:
			# 		if mod_reason == 'No Design Change':
			# 			item_type = "Only Variant"
			# 		else:
			# 			item_type = "Suffix Of Variant"
			# else:
			variant_of = frappe.db.get_value("Item",design_id,"variant_of")
			attribute_list = make_atribute_list(source_name)
			validate_variant_attributes(variant_of,attribute_list)
			bom = frappe.db.get_value('Item',design_id,'master_bom')
			if bom==None:
				frappe.throw(f'BOM is not available for {design_id}')
			if mod_reason == 'No Design Change':
				item_type = "Only Variant"
				# bom_or_cad = 'CAD'
				# if not is_repairing:
				bom_or_cad = workflow_state_maker(source_name)
			elif mod_reason == 'Attribute Change':
				item_type = "Only Variant"
				bom_or_cad = 'Check'
			else:
				item_type = "Suffix Of Variant"
				bom_or_cad = 'CAD'
					# bom_or_cad = workflow_state_maker(source_name)
	elif design_type == 'Sketch Design':
		item_type = "No Variant No Suffix"
		bom_or_cad = 'CAD'
	elif design_type == 'As Per Serial No':
		item_type = "No Variant No Suffix"
		bom_or_cad = 'New BOM'
	else:
		item_type = 'Template and Variant'
		bom_or_cad = 'CAD'

		
	doc = get_mapped_doc(
		"Order Form Detail",
		source_name,
		{
			"Order Form Detail": {
				"doctype": "Order" 
			}
		},target_doc, set_missing_values
	)

	for entity in parent_doc.get("service_type",[]):
		doc.append("service_type", {"service_type1": entity.service_type1})
	doc.parcel_place = parent_doc.parcel_place
	doc.company = parent_doc.company
	doc.form_remarks = parent_doc.remarks
	doc.india = parent_doc.india
	doc.usa = parent_doc.usa
	doc.india_states = parent_doc.india_states

	doc.age_group = parent_doc.age_group
	doc.alphabetnumber = parent_doc.alphabetnumber
	doc.animalbirds = parent_doc.animalbirds
	doc.collection = parent_doc.collection
	doc.design_style = parent_doc.design_style
	doc.gender = parent_doc.gender
	doc.lines_rows = parent_doc.lines_rows
	doc.language = parent_doc.language
	doc.occasion = parent_doc.occasion
	doc.religious = parent_doc.religious
	doc.shapes = parent_doc.shapes
	doc.zodiac = parent_doc.zodiac
	doc.rhodium = parent_doc.rhodium

	doc.item_type = item_type
	doc.bom_or_cad = bom_or_cad
	
	doc.save()
	
	return doc.name

def make_atribute_list(source_name):
	order_form_details = frappe.get_doc('Order Form Detail',source_name)
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{order_form_details.subcategory}' and in_item_variant=1""",as_list=1
	)

	final_list = {}
	for i in all_variant_attribute:
		new_i = i[0].replace(' ','_').lower()
		final_list[i[0]] = order_form_details.get_value(new_i)
		
	return final_list
# def set_item_type(source_name):
# 	doc = frappe.get_doc('Order Form Detail',source_name)
	
# 	# all_variant_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_item_variant':1},fields=['item_attribute'])
# 	all_variant_attribute = frappe.db.sql(
# 		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
# 	)
# 	# suffix_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'suffix':1},fields=['item_attribute'])
# 	suffix_attribute = frappe.db.sql(
# 		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and suffix=1""",as_dict=1
# 	)
# 	# print(suffix_attribute)

# 	all_attribute_list = []
# 	for variant_attribut in all_variant_attribute:
# 		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_')
# 		all_attribute_list.append(item_attribute)
	
# 	# bom_detail = frappe.db.get_value('BOM',{'is_active':1,'item':doc.design_id},all_attribute_list,as_dict=1)
# 	bom = frappe.db.get_value('Item',doc.design_id,'master_bom')
# 	if bom==None:
# 		frappe.throw(f'BOM is not available for {doc.design_id}')
# 	bom_detail = frappe.db.get_value('BOM',doc.bom,all_attribute_list,as_dict=1)
	
# 	all_item_type = []
# 	for attribute in suffix_attribute:
# 		item_attribute = attribute['item_attribute'].lower().replace(' ','_')
# 		if bom_detail[item_attribute] != frappe.db.get_value('Order Form Detail',source_name,item_attribute):
# 			item_type = 'Suffix Of Variant'
# 		else:
# 			item_type = 'Only Variant'
# 		all_item_type.append(item_type)
	
# 	if 'Suffix Of Variant' in all_item_type:
# 		item_type = 'Suffix Of Variant'
# 	else:
# 		item_type = 'Only Variant'

# 	return item_type


def workflow_state_maker(source_name):

	doc = frappe.get_doc('Order Form Detail',source_name)

	# all_variant_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_item_variant':1},fields=['item_attribute'])
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
	)

	all_attribute_list = []
	for variant_attribut in all_variant_attribute:
		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_')
		all_attribute_list.append(item_attribute)
	
	
	# bom_detail = frappe.db.get_value('BOM',{'is_active':1,'is_default':1,'item':doc.design_id},all_attribute_list,as_dict=1)
	bom_detail = frappe.db.get_value('BOM',doc.bom,all_attribute_list,as_dict=1)
	# cad_attribute_list = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_cad_flow':1},fields=['item_attribute'])
	cad_attribute_list = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_cad_flow=1""",as_dict=1
	)
	

	all_bom_or_cad = []

	for i in cad_attribute_list:
		item_attribute = i['item_attribute'].lower().replace(' ','_')
		if str(bom_detail[item_attribute]) != str(frappe.db.get_value('Order Form Detail',source_name,item_attribute)):
			bom_or_cad = 'CAD'
		else:
			bom_or_cad = 'New BOM'
		all_bom_or_cad.append(bom_or_cad)
	
	
	if 'CAD' in all_bom_or_cad:
		bom_or_cad = 'CAD'
	else:
		bom_or_cad = 'New BOM'

	frappe.throw(f"{bom_or_cad}")
	return bom_or_cad


@frappe.whitelist()
def make_order_form(source_name,target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Order Form")
	else:
		target_doc = frappe.get_doc(target_doc)

	titan_order_form = frappe.db.get_value("Titan Order Form", source_name, "*")

	target_doc.append("order_details", {
		"category": titan_order_form.get("item_category"),
		"design_by": "Our Design",
		"design_type": "Mod",
		"design_id": titan_order_form.get("design_code"),
		"titan_code": titan_order_form.get("titan_code"),
		"subcategory": titan_order_form.get("item_subcategory"),
		"bom": titan_order_form.get("bom"),
		"serial_no_bom": titan_order_form.get("serial_no_bom"),
		"tag_no": titan_order_form.get("serial_no"),
		"metal_type": titan_order_form.get("metal_type"),
		"metal_touch": titan_order_form.get("metal_touch"),
		"metal_purity": titan_order_form.get("metal_purity"),
		"metal_colour": titan_order_form.get("metal_colour"),
		"product_size": titan_order_form.get("product_size"),
		"setting_type": titan_order_form.get("setting_type"),
		"delivery_date": titan_order_form.get("delivery_date"),
		"enamal": titan_order_form.get("enamal"),
		"rhodium": titan_order_form.get("rhodium"),
	})


	return target_doc


# @frappe.whitelist()
# def get_metal_color_varinat(metal_colour,design_id):
# 	variant_of = frappe.db.get_value('Item',{'name':design_id},'variant_of')
# 	all_variant = frappe.db.get_all('Item',filters={'variant_of':variant_of},pluck='name')
# 	for i in all_variant:
# 		print(frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= 'Metal Colour'""",as_dict=1))
# 		if metal_colour == frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= 'Metal Colour'""",as_dict=1)[0]['attribute_value']:
# 			return i
		
# def check_varinat(source_name):
# 	row = frappe.get_doc('Order Form Detail',source_name)
# 	# variant_of,item_subcategory = frappe.db.get_value('Item',{'name':row.design_id},['variant_of','item_subcategory'])
# 	# all_variant = frappe.db.get_all('Item',filters={'variant_of':variant_of},pluck='name')

# 	item_subcategory = row.subcategory
# 	all_attribute = frappe.db.sql(f"""select item_attribute  from `tabAttribute Value Item Attribute Detail` taviad  where parent = '{item_subcategory}' and in_item_variant =1""",as_dict=1)
# 	a = []
# 	for i in all_variant:
# 		variant_attrbute_value_list = []
# 		for j in all_attribute:
# 			attribute_value = frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= '{j['item_attribute']}'""",as_dict=1)
# 			if attribute_value:
# 				variant_attrbute_value_list.append(attribute_value[0]['attribute_value'])
# 			else:
# 				variant_attrbute_value_list.append('')
# 		a.append([i,variant_attrbute_value_list])
	
# 	current_data = []
# 	for k in all_attribute:
# 		av = frappe.db.get_value('Order Form Detail',row.name,k['item_attribute'].replace(' ','_').lower())
# 		if type(av) == float:
# 			av = "{:g}".format(av)
# 		current_data.append(av)


# 	is_present = any(current_data == sublist[1] for sublist in a)
	
# 	if is_present:
# 		matching_sublist = next(sublist for sublist in a if current_data == sublist[1])
# 		first_element = matching_sublist[0]
# 		return first_element
	# else:
	# 	return row.design_id

@frappe.whitelist()
def get_bom_details(design_id,doc):
	doc = json.loads(doc)
	item_subcategory = frappe.db.get_value("Item",design_id,"item_subcategory")

	fg_bom = frappe.db.get_value("BOM",{"tag_no":doc["tag_no"],"item":design_id},"name")
	master_bom = fg_bom
	if not fg_bom:
		temp_bom = frappe.db.get_value("Item",design_id,"master_bom")
		master_bom = temp_bom
	
	if not master_bom:
		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item',design_id)}</b> is not set")
	all_item_attributes = []

	for i in frappe.get_doc("Attribute Value",item_subcategory).item_attributes:
		all_item_attributes.append(i.item_attribute.replace(' ','_').lower())
	
	# frappe.throw(f"{all_item_attributes}")
	with_value = frappe.db.get_value("BOM",master_bom,all_item_attributes,as_dict=1)
	with_value['master_bom'] = master_bom
	return with_value


def validate_variant_attributes(variant_of,attribute_list):
	args = attribute_list
	variant = get_variant(variant_of, args)
	if variant:
		frappe.throw(
			_("Item variant <b>{0}</b> exists with same attributes").format(get_link_to_form("Item",variant)), ItemVariantExistsError
		)

@frappe.whitelist()
def get_metal_purity(metal_type,metal_touch,customer):
	metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` where parent = '{customer}' and metal_type = '{metal_type}' and metal_touch = '{metal_touch}'""",as_dict=1)
	return metal_purity


@frappe.whitelist()
def get_sketh_details(design_id):
	
	db_data = frappe.db.sql(f"select name,attribute, attribute_value from `tabItem Variant Attribute` where parent = '{design_id}'",as_dict=1)
	final_data = {}
	sketch_order_id = frappe.db.get_value("Item",design_id,"custom_sketch_order_id")
	final_data['item_category'] = frappe.db.get_value("Item",design_id,"item_category")
	final_data['item_subcategory'] = frappe.db.get_value("Item",design_id,"item_subcategory")
	final_data['setting_type'] = frappe.db.get_value("Item",design_id,"setting_type")
	final_data['sub_setting_type1'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sub_setting_type1")
	final_data['sub_setting_type2'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sub_setting_type2")
	final_data['qty'] = frappe.db.get_value("Sketch Order",sketch_order_id,"qty")
	final_data['metal_type'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_type")
	final_data['metal_touch'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_touch")
	final_data['metal_colour'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_colour")
	final_data['metal_target'] = frappe.db.get_value("Item",design_id,"approx_gold")
	final_data['diamond_target'] = frappe.db.get_value("Item",design_id,"approx_diamond")
	final_data['product_size'] = frappe.db.get_value("Sketch Order",sketch_order_id,"product_size")
	final_data['sizer_type'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sizer_type")
	final_data['length'] = frappe.db.get_value("Sketch Order",sketch_order_id,"length")
	final_data['width'] = frappe.db.get_value("Sketch Order",sketch_order_id,"width")
	final_data['height'] = frappe.db.get_value("Sketch Order",sketch_order_id,"height")
	for i in db_data:
		if i.attribute_value in [None,'']:
			continue
		final_data[i.attribute.lower().replace(' ','_')]=i.attribute_value
	return final_data