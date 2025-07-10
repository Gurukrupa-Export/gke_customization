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
		if self.supplier:
			create_po(self)

	# def on_cancel(self):
	# 	delete_auto_created_cad_order(self)
	def on_cancel(self):
		if frappe.db.get_list("Order",filters={"cad_order_form":self.name},fields="name"):
			for order in frappe.db.get_list("Order",filters={"cad_order_form":self.name},fields="name"):
				frappe.db.set_value("Order",order["name"],"workflow_state","Cancelled")
				# frappe.throw(f"{order}")
				if frappe.db.get_list("Timesheet",filters={"order":order["name"]},fields="name"):
					for timesheet in frappe.db.get_list("Timesheet",filters={"order",order["name"]},fields="name"):
						frappe.db.set_value("Timesheet",timesheet["name"],"docstatus","2")

		frappe.db.set_value("Order Form",self.name,"workflow_state","Cancelled")
		self.reload()

	def validate(self):
		self.validate_category_subcaegory()
		self.validate_filed_value()
		validate_design_id(self)

		validate_is_mannual(self)
		set_data(self)
		for i in self.order_details:	
			if i.metal_type == "Silver":
				i.metal_colour = "White"
				i.metal_touch = "20KT"
				i.setting_type = "Open"
				i.diamond_type = "AD"
			# return

	def validate_category_subcaegory(self):
		for row in self.get("order_details"):
			if row.subcategory:
				parent = frappe.db.get_value("Attribute Value", row.subcategory, "parent_attribute_value")
				if row.category != parent:
					frappe.throw(_(f"Category & Sub Category mismatched in row #{row.idx}"))
	
	def validate_filed_value(self):
		for row in self.get("order_details"):
			if row.design_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Design Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.design_type not in attribute_list:
					frappe.throw("Design Type is not Correct")

			if row.diamond_quality:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Diamond Quality").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.diamond_quality not in attribute_list:
					frappe.throw("Diamond Quality is not Correct")

			if row.setting_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Setting Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.setting_type not in attribute_list:
					frappe.throw("Setting Type is not Correct")
			
			if row.sub_setting_type1:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Sub Setting Type1").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.sub_setting_type1 not in attribute_list:
					frappe.throw("Setting Type 1 is not Correct")
			
			if row.sub_setting_type2:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Sub Setting Type2").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.sub_setting_type2 not in attribute_list:
					frappe.throw("Setting Type 2 is not Correct")
			
			if row.metal_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Metal Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.metal_type not in attribute_list:
					frappe.throw("Metal Type is not Correct")

			if row.metal_touch:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Metal Touch").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.metal_touch not in attribute_list:
					frappe.throw("Metal Touch is not Correct")

			if row.metal_colour:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Metal Colour").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.metal_colour not in attribute_list:
					frappe.throw("Metal Colour is not Correct")

			if row.diamond_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Diamond Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.diamond_type not in attribute_list:
					frappe.throw("Diamond Type is not Correct")
			
			if row.sizer_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Sizer Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.sizer_type not in attribute_list:
					frappe.throw("Sizer Type is not Correct")

			if row.stone_changeable:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Stone Changeable").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.stone_changeable not in attribute_list:
					frappe.throw("Stone Changeable is not Correct")

			if row.feature:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Feature").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.feature not in attribute_list:
					frappe.throw("Feature is not Correct")

			if row.rhodium:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Rhodium").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.rhodium not in attribute_list:
					frappe.throw("Rhodium is not Correct")

			if row.enamal:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Enamal").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.enamal not in attribute_list:
					frappe.throw("Enamal is not Correct")
			
			if row.gemstone_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Gemstone Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.gemstone_type not in attribute_list:
					frappe.throw("Gemstone Type is not Correct")
			
			if row.gemstone_quality:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Gemstone Quality").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.gemstone_quality not in attribute_list:
					frappe.throw("Gemstone Quality is not Correct")
			
			if row.mod_reason:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Mod Reason").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.mod_reason not in attribute_list:
					frappe.throw("Mod Reason is not Correct")
			
			if row.finding_category:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Finding Category").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.finding_category not in attribute_list:
					frappe.throw("Finding Category is not Correct")

			if row.finding_subcategory:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Finding Sub-Category").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.finding_subcategory not in attribute_list:
					frappe.throw("Finding Sub-Category is not Correct")
			
			if row.finding_size:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Finding Size").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.finding_size not in attribute_list:
					frappe.throw("Finding Size is not Correct")
			
			if row.metal_target_from_range:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Metal Target Range").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.metal_target_from_range not in attribute_list:
					frappe.throw("Metal Target Range is not Correct")

			if row.diamond_target_from_range:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Diamond Target Range").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.diamond_target_from_range not in attribute_list:
					frappe.throw("Diamond Target Range is not Correct")
			
			if row.detachable:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Detachable").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.detachable not in attribute_list:
					frappe.throw("Detachable is not Correct")
			
			if row.lock_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Lock Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.lock_type not in attribute_list:
					frappe.throw("Lock Type is not Correct")
			
			if row.capganthan:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Cap/Ganthan").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.capganthan not in attribute_list:
					frappe.throw("Cap/Ganthan is not Correct")
			
			if row.charm:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Charm").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.charm not in attribute_list:
					frappe.throw("Charm is not Correct")
			
			if row.back_chain:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Back Chain").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.back_chain not in attribute_list:
					frappe.throw("ChBack Chainarm is not Correct")

			if row.back_belt:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Back Belt").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.back_belt not in attribute_list:
					frappe.throw("Back Belt is not Correct")

			if row.black_bead:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Black Bead").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.black_bead not in attribute_list:
					frappe.throw("Black Bead is not Correct")

			if row.two_in_one:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","2 in 1").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.two_in_one not in attribute_list:
					frappe.throw("2 in 1 is not Correct")

			if row.chain_type:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Chain Type").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.chain_type not in attribute_list:
					frappe.throw("Chain Type is not Correct")

			# if row.customer_chain:
			# 	attribute_list = []
			# 	for i in frappe.get_doc("Item Attribute","Black Bead").item_attribute_values:
			# 		attribute_list.append(i.attribute_value)
			# 	if row.customer_chain not in attribute_list:
			# 		frappe.throw("Black Bead is not Correct")

			if row.nakshi_from:
				attribute_list = []
				for i in frappe.get_doc("Item Attribute","Nakshi From").item_attribute_values:
					attribute_list.append(i.attribute_value)
				if row.nakshi_from not in attribute_list:
					frappe.throw("Nakshi From is not Correct")


		



def create_cad_orders(self):
	doclist = []
	for row in self.order_details:
		docname = make_cad_order(row.name, parent_doc = self)
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
	is_finding_order = frappe.get_doc('Order Form Detail',source_name).is_finding_order
	if design_type == 'Mod - Old Stylebio & Tag No':
		if is_repairing == 1:
			bom_or_cad = frappe.get_doc('Order Form Detail',source_name).bom_or_cad
			item_type = frappe.get_doc('Order Form Detail',source_name).item_type
		else:
		# 	variant_of = frappe.db.get_value("Item",design_id,"variant_of")
		# 	bom = frappe.db.get_value('Item',design_id,'master_bom')
		# 	if bom==None:
		# 		frappe.throw(f'BOM is not available for {design_id}')
		# 	attribute_list = make_atribute_list(source_name)
		# 	validate_variant_attributes(variant_of,attribute_list)
		# 	if mod_reason in ['No Design Change','Change in Metal Colour']:
		# 		item_type = "Only Variant"
		# 		# bom_or_cad = workflow_state_maker(source_name)
		# 	elif mod_reason in ['Attribute Change']:
		# 		attribute_list = make_atribute_list(source_name)
		# 		validate_variant_attributes(variant_of,attribute_list)
		# 		item_type = "Only Variant"
		# 		# bom_or_cad = 'Check'
		# 	elif mod_reason == 'Change in Metal Touch':
		# 		item_type = "No Variant No Suffix"
		# 		# bom_or_cad = workflow_state_maker(source_name)
		# 	else:
		# 		attribute_list = make_atribute_list(source_name)
		# 		validate_variant_attributes(variant_of,attribute_list)
		# 		# item_type = "Suffix Of Variant"
		# 		item_type = "Template and Variant"
		# 		# bom_or_cad = 'CAD'

			bom_or_cad = 'Check'
			# if frappe.db.get_value("Item",design_id,"Item_group") == 'Design DNU':
			# 	item_type = "Only Variant"
	elif design_type == 'Sketch Design':
		# variant_of = frappe.db.get_value("Item",design_id,"variant_of")
		# attribute_list = make_atribute_list(source_name)
		# validate_variant_attributes(variant_of,attribute_list)
		# item_type = "No Variant No Suffix"
		item_type = "Only Variant"
		bom_or_cad = 'CAD'
		# bom_or_cad = 'Check'
	elif design_type == 'As Per Design Type':
		item_type = "No Variant No Suffix"
		bom_or_cad = 'New BOM'
	elif is_finding_order:
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
	doc.item_type = item_type
	doc.bom_or_cad = bom_or_cad
	if design_type in ['New Design','Sketch Design']:
		doc.workflow_type = 'CAD'
	
	doc.save()
	if design_type == 'As Per Design Type' and item_type == "No Variant No Suffix" and bom_or_cad == 'New BOM':
		doc.submit()
		frappe.db.set_value("Order",doc.name,"workflow_state","Approved")
	return doc.name

def make_atribute_list(source_name):
	order_form_details = frappe.get_doc('Order Form Detail',source_name)
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` 
		where parent = '{order_form_details.subcategory}' and in_item_variant=1""",as_list=1
	)

	final_list = {}
	for i in all_variant_attribute:
		new_i = i[0].replace(' ','_').replace('/','').lower()
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
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
	)
	all_attribute_list = []
	for variant_attribut in all_variant_attribute:
		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_').replace('/','')
		all_attribute_list.append(item_attribute)
	
	bom_detail = frappe.db.get_value('BOM',doc.bom,all_attribute_list,as_dict=1)
	cad_attribute_list = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_cad_flow=1""",as_dict=1
	)
	
	all_bom_or_cad = []
	for i in cad_attribute_list:
		item_attribute = i['item_attribute'].lower().replace(' ','_')
		if str(bom_detail[item_attribute]).replace(".0","") != str(frappe.db.get_value('Order Form Detail',source_name,item_attribute)):
			bom_or_cad = 'CAD'
		else:
			bom_or_cad = 'New BOM'
		all_bom_or_cad.append(bom_or_cad)
	
	
	if 'CAD' in all_bom_or_cad:
		bom_or_cad = 'CAD'
	else:
		bom_or_cad = 'New BOM'

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
		"design_type": "Mod - Old Stylebio & Tag No",
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

# @frappe.whitelist()
# def get_bom_details(design_id,doc):
# 	doc = json.loads(doc)
# 	if doc['is_finding_order']:
# 		master_bom = frappe.db.get_value("BOM",{"bom_type":"Template","item":design_id},"name",order_by="creation DESC")
# 		frappe.throw(f"{master_bom}//{doc['is_finding_order']}")
	
# 	item_subcategory = frappe.db.get_value("Item",design_id,"item_subcategory")

# 	fg_bom = frappe.db.get_value("BOM",{"bom_type":"Finished Goods","item":design_id},"name",order_by="creation DESC")
# 	master_bom = fg_bom
# 	if not fg_bom:
# 		temp_bom = frappe.db.get_value("Item",design_id,"master_bom")
# 		master_bom = temp_bom
# 	if not master_bom:
# 		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item',design_id)}</b> is not set")
# 	all_item_attributes = []

# 	for i in frappe.get_doc("Attribute Value",item_subcategory).item_attributes:
# 		all_item_attributes.append(i.item_attribute.replace(' ','_').replace('/','').lower())
	
# 	with_value = frappe.db.get_value("BOM",master_bom,all_item_attributes,as_dict=1)
# 	with_value['master_bom'] = master_bom
# 	return with_value
@frappe.whitelist()
def get_bom_details(design_id, doc):
	doc = json.loads(doc)

	if doc['is_finding_order']:
		master_bom = frappe.db.get_value("BOM", {"bom_type": "Template", "item": design_id}, "name", order_by="creation DESC")
		frappe.throw(f"{master_bom}//{doc['is_finding_order']}")

	item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")

	fg_bom = frappe.db.get_value("BOM", {"bom_type": "Finished Goods", "item": design_id}, "name", order_by="creation DESC")
	master_bom = fg_bom or frappe.db.get_value("Item", design_id, "master_bom")

	if not master_bom:
		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item', design_id)}</b> is not set")

	# Prepare attribute keys from subcategory
	attribute_keys = []
	attribute_pairs = []

	for attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
		formatted = attr.item_attribute.replace(' ', '_').replace('/', '').lower()
		attribute_keys.append(formatted)
		attribute_pairs.append((attr.item_attribute, formatted))

	# Get values from Item Variant Attribute table
	variant_attributes = frappe.db.get_all("Item Variant Attribute", filters={"parent": design_id}, fields=["attribute", "attribute_value"])
	variant_map = {d.attribute.replace(' ', '_').replace('/', '').lower(): d.attribute_value for d in variant_attributes}

	# Get fallback values from BOM
	bom_values = frappe.db.get_value("BOM", master_bom, attribute_keys, as_dict=1)

	with_value = {}
	for original_name, formatted_key in attribute_pairs:
		with_value[formatted_key] = variant_map.get(formatted_key) or bom_values.get(formatted_key)

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

@frappe.whitelist()
def get_item_details(item_code):
	item_code = frappe.db.sql(f"""select attribute,attribute_value from `tabItem Variant Attribute` where parent = '{item_code}'""")
	return item_code

@frappe.whitelist()
def item_attribute_query(doctype, txt, searchfield, start, page_len, filters):
	args = {
		'item_attribute': filters.get("item_attribute"),
		"txt": "%{0}%".format(txt),
	}
	condition = ''
	if filters.get("customer_code"):		
		if filters.get("item_attribute") == "Metal Touch":
			args["customer_code"] = filters.get("customer_code")
			condition += "and attribute_value in (select metal_touch from `tabMetal Criteria`  where parent = %(customer_code)s)"

	item_attribute = frappe.db.sql(f"""select attribute_value
			from `tabItem Attribute Value`
				where parent = %(item_attribute)s 
				and attribute_value like %(txt)s {condition}
			""",args)
	return item_attribute if item_attribute else []

@frappe.whitelist()
def get_customer_orderType(customer_code):
	order_type = frappe.db.sql(
		f""" select order_type from `tabOrder Type` where parent= '{customer_code}' """, as_dict=1
	)

	return order_type

@frappe.whitelist()
def get_customer_order_form(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	target_doc = frappe.new_doc("Order Form") if not target_doc else frappe.get_doc(target_doc)

	if source_name:
		customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabCustomer Order Form Detail` 
							WHERE parent = '{source_name}' AND docstatus = 1""", as_dict=1)
	if not customer_order_form:
		frappe.msgprint(_("Please submit the Customer Order Form"))
		return target_doc

	for i in customer_order_form:
		item, order_id = i.get("design_code"), i.get("order_id")
		order_data = frappe.db.sql(f"SELECT * FROM `tabOrder` WHERE name = '{order_id}'", as_dict=1)
		customer_design_code = frappe.db.sql(f"SELECT * FROM `tabBOM` WHERE item = '{item}' AND name = '{i.get('design_code_bom')}'", as_dict=1)
		item_serial = frappe.db.get_value("Serial No", {'item_code': item}, 'name')

		data_source = order_data if order_data else customer_design_code
		if data_source:
			for j in data_source:
				target_doc.append("order_details", {
					"delivery_date": target_doc.delivery_date,
					"design_by": j.get('design_by'),
					"design_type": j.get('design_type'),
					"qty": j.get('qty'),
					"design_id": j.get("item", item),
					"bom": j.get("new_bom", i.get('design_code_bom')),
					"tag_no": item_serial or j.get('tag_no'),
					"diamond_quality": i.get("diamond_quality"),
					"customer_order_form": i.get("parent"),
					"category": i.get("category"),
					"subcategory": i.get("subcategory"),
					"setting_type": i.get("setting_type"),
					"theme_code": i.get("theme_code"),
					"metal_type": i.get("metal_type"),
					"metal_touch": i.get("metal_touch"),
					"metal_colour": i.get("metal_colour"),
					"metal_target": i.get("metal_target"),
					"diamond_target": i.get("diamond_target"),
					"feature": i.get("feature"),
					"product_size": i.get("product_size"),
					"rhodium": i.get("rhodium"),
					"enamal": j.get("enamal"),
					"sub_setting_type1": j.get("sub_setting_type1"),
					"sub_setting_type2": j.get("sub_setting_type2"),
					"sizer_type": j.get("sizer_type"),
					"stone_changeable": j.get("stone_changeable"),
					"detachable": j.get("detachable"),
					"lock_type": j.get("lock_type"),
					"capganthan": j.get("capganthan"),
					"charm": j.get("charm"),
					"back_chain": j.get("back_chain"),
					"back_chain_size": j.get("back_chain_size"),
					"back_belt": j.get("back_belt"),
					"back_belt_length": j.get("back_belt_length"),
					"black_beed_line": j.get("black_beed_line"),
					"back_side_size": j.get("back_side_size"),
					"back_belt_patti": j.get("back_belt_patti"),
					"two_in_one": j.get("two_in_one"),
					"number_of_ant": j.get("number_of_ant"),
					"distance_between_kadi_to_mugappu": j.get("distance_between_kadi_to_mugappu"),
					"space_between_mugappu": j.get("space_between_mugappu"),
					"chain_type": j.get("chain_type"),
					"customer_chain": j.get("customer_chain"),
					"nakshi_weght": j.get("nakshi_weght"),
				})
	return target_doc


def validate_design_id(self):
	for i in self.order_details:
		# If tagno exists, find the latest matching Item by old_tag_no
		if i.tagno:
			latest_item = frappe.db.get_all(
				"Item",
				filters={"old_tag_no": i.tagno},
				fields=["name", "master_bom"],
				order_by="creation desc",
				limit=1
		 )
			if latest_item:
				matched_design_id = latest_item[0].name

				# Set design_id only if not manually overridden
				if not i.design_id or i.design_id == matched_design_id:
					i.design_id = matched_design_id
					if not i.bom:
						i.bom = latest_item[0].master_bom

		# If design_id is set, fetch Item and set master_bom to bom
		if i.design_id:
			item_doc = frappe.get_doc("Item", i.design_id)
			if item_doc.master_bom and not i.bom:
				i.bom = item_doc.master_bom

		# Continue only if design_id and bom are now set
		if i.design_id and i.bom:
			# Manual override check
			is_manual_override = (i.design_type == "Mod - Old Stylebio & Tag No")

			# Check if mod_reason is NOT "Change In Metal Type"
			if i.mod_reason != "Change In Metal Type":

				# Fetch BOM
				bom_doc = frappe.get_doc("BOM", i.bom)

				# Set metal_type and metal_touch from metal_detail
				if bom_doc.metal_detail:
					if not is_manual_override or not i.metal_type:
						i.metal_type = bom_doc.metal_detail[0].metal_type or None
					if not is_manual_override or not i.metal_touch:
						i.metal_touch = bom_doc.metal_detail[0].metal_touch or None
				else:
					frappe.msgprint(f"No metal details found for BOM {i.bom}")

				# Set setting_type, category, subcategory
				if not is_manual_override or not i.setting_type:
					i.setting_type = bom_doc.setting_type or None
				if not is_manual_override or not i.category:
					i.category = bom_doc.item_category or None
				if not is_manual_override or not i.subcategory:
					i.subcategory = bom_doc.item_subcategory or None

				# Attribute mapping: fieldname -> attribute name
				attr_map = {
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
					"back_belt_length": "Back Belt Length",
				}

				# Initialize fields to None if not manual override
				if not is_manual_override:
					for fieldname in attr_map.keys():
						setattr(i, fieldname, None)

				# Set values from attributes if not manually overridden
				for attr in item_doc.attributes:
					for fieldname, attrname in attr_map.items():
						if attr.attribute == attrname:
							if not is_manual_override or not getattr(i, fieldname):
								setattr(i, fieldname, attr.attribute_value)


def validate_is_mannual(self):
	if self.is_mannual:
		errors = []

		for row in self.order_details:
			missing_fields = []

			if not row.stylebio:
				missing_fields.append("'Style Bio'")
			if not row.status:
				missing_fields.append("'Status'")
			if not row.order_details_and_remarks:
				missing_fields.append("'Order Details and Remark'")

			# Set design_id and bom from Item if tagno exists
			if row.tagno:
				existing_item = frappe.db.get_value("Item", {"old_tag_no": row.tagno}, ["name", "master_bom"])
				if existing_item:
					item_name, master_bom = existing_item
					# chnage over here
					if not row.design_id:
						row.design_id = item_name
					# chnage over here
					if not row.bom:  
						row.bom = master_bom
					if master_bom:
						diamond_type = frappe.db.get_value(
							"BOM Diamond Detail", 
							{"parent": master_bom}, 
							"diamond_type"
						)
						# frappe.throw(f"{diamond_type}")
						if diamond_type:
							row.diamond_type = diamond_type

			# if workflow_state == "Creating Item & BOM", design_type is mandatory
			if (
				not row.is_finding_order
				and not row.design_type
				and self.workflow_state == "Approved"
			):
				missing_fields.append("'Design Type' (required in 'Creating Item & BOM')")

			if missing_fields:
				errors.append(f"Row {row.idx} is missing: {', '.join(missing_fields)}")

		if errors:
			frappe.throw("<br>".join(errors))

		# New condition added below:
		if self.workflow_state == "Approved":
			for row in self.order_details:
				if row.status != "Done":
					frappe.throw(f"Row {row.idx}: Status must be 'Done' before you approve. Please update it.")

	else:
		# is_mannual is unchecked validate design_type for non-finding orders
		missing_design_type_rows = []
		for row in self.order_details:
			if not row.is_finding_order and not row.design_type:
				missing_design_type_rows.append(
					f"Row {row.idx}: Design Type is mandatory when 'Is Finding Order' is unchecked and 'Is Mannual' is also unchecked."
				)

		if missing_design_type_rows:
			frappe.throw("<br>".join(missing_design_type_rows))




def set_data(self):
	if self.order_details:
		for i in self.order_details:
			if i.design_type in ['As Per Design Type','Mod - Old Stylebio & Tag No'] and i.design_id:
				try:
					design_id = i.design_id
					item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")
					master_bom = i.bom

					# Prepare a list to hold the item attribute names formatted as per your requirements
					all_item_attributes = []
					
					# Retrieve all item attributes for the given item subcategory
					for item_attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
						# Format the item attribute names by replacing spaces with underscores, removing '/', and converting to lower case
						formatted_attr = item_attr.item_attribute.replace(' ', '_').replace('/', '').lower()
						all_item_attributes.append(formatted_attr)
					
					# Retrieve the values for the specified attributes from the BOM
					attribute_values = frappe.db.get_value("BOM", master_bom, all_item_attributes, as_dict=1)
					
					# Dynamically set the attributes on self with the retrieved values
					for key, value in attribute_values.items():
						if str(key) == "item_category":
							key = "category"
						if str(key) == "item_subcategory":
							key = "subcategory"
						a = getattr(i, key, value)
						if a:
							continue
						# frappe.throw(f"{a}")
						else:
							setattr(i, key, value)
						# Prepare a list to hold the item attribute names formatted as per your requirements
						all_item_attributes = []
						
						# Retrieve all item attributes for the given item subcategory
						for item_attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
							# Format the item attribute names by replacing spaces with underscores, removing '/', and converting to lower case
							formatted_attr = item_attr.item_attribute.replace(' ', '_').replace('/', '').lower()
							
							all_item_attributes.append(formatted_attr)
						
						# Retrieve the values for the specified attributes from the BOM
						attribute_values = frappe.db.get_value("BOM", master_bom, all_item_attributes, as_dict=1)
						# Dynamically set the attributes on self with the retrieved values
						for key, value in attribute_values.items():
							if str(key) == "item_category":
								key = "category"
							if str(key) == "item_subcategory":
								key = "subcategory"
							a = getattr(i, key, value)
							if a:
								continue
							else:
								setattr(i, key, value)
				except:
					frappe.throw(f"Row {i.idx} has Issue.Check BOM first.")


def create_po(self):
	qty = 0
	po_doc = frappe.new_doc("Purchase Order")
	po_doc.supplier = self.supplier
	po_doc.transaction_date = self.delivery_date
	po_doc.company = self.company
	po_doc.branch = self.branch
	po_doc.project = self.project
	po_doc.purchase_type = 'Subcontracting'
	# po_doc.custom_form = "Order Form"
	# po_doc.custom_form_id = self.name
	po_doc.schedule_date = self.delivery_date

	po_item_log = po_doc.append("items", {})
	if self.purchase_type == 'Design':
		po_item_log.item_code = "Design Expness"
	elif self.purchase_type == 'RPT':
		po_item_log.item_code = "RPT Expness"
	elif self.purchase_type == 'Model':
		total_weight = 0
		# qty_18 = 0
		# qty_22 = 0
		item_code = ''
		for i in self.order_details:
			# total_weight += i.total_weight
			if i.metal_touch == '18KT':
				item_code = "Semi Finish Goods 18KT"
			if i.metal_touch == '22KT':
				item_code = "Semi Finish Goods 22KT"
		po_item_log.item_code = item_code
		# po_item_log.total_weight = total_weight
		# po_item_log.weight_per_unit = total_weight/qty_22
	elif self.purchase_type == 'Mould':
		po_item_log.item_code = "Mould Expness"
	
	if self.purchase_type in ['Model']:
		qty_18 = 0
		qty_22 = 0
		for i in self.order_details:
			if i.metal_touch == '18KT':
				qty_18 += i.qty
			if i.metal_touch == '22KT':
				qty_22 += i.qty
		if qty_18:
			qty = qty_18
		else:
			qty = qty_22
	else:
		for i in self.order_details:
			qty+=i.qty
	
	po_item_log.qty = qty
	po_item_log.schedule_date = self.delivery_date
	po_item_log.schedule_date = self.delivery_date
	po_item_log.qty = len(self.order_details)

	# po_doc.set("payment_schedule", [])
	# po_trn_log = po_doc.append("payment_schedule", {})
	# po_trn_log.due_date = self.delivery_date
	# po_trn_log.invoice_portion = 100.0

	
	po_doc.save()
	po_name = po_doc.name
	frappe.db.set_value("Purchase Order",po_name,"custom_form","Order Form")
	frappe.db.set_value("Purchase Order",po_name,"custom_form_id",self.name)
	msg = _("The following {0} is created: {1}").format(
			frappe.bold(_("Purchase Order")), "<br>" + get_link_to_form("Purchase Order", po_name)
		)
	
	frappe.msgprint(msg)

@frappe.whitelist()
def make_from_pre_order_form(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	target_doc = frappe.new_doc("Order Form") if not target_doc else frappe.get_doc(target_doc)

	if source_name:
				customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabPre Order Form Details` 
							WHERE parent = '{source_name}'""", as_dict=1)
		# customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabPre Order Form Details` 
		# 					WHERE parent = '{source_name}' AND docstatus = 1""", as_dict=1)

	# parent = frappe.db.get_value("Pre Order Form Details",source_name)
	target_doc.customer_code = frappe.db.get_value("Pre Order Form",source_name,"customer_code")
	target_doc.order_date = frappe.db.get_value("Pre Order Form",source_name,"order_date")
	target_doc.salesman_name = frappe.db.get_value("Pre Order Form",source_name,"sales_person")
	target_doc.diamond_quality = frappe.db.get_value("Pre Order Form",source_name,"diamond_quality")
	target_doc.branch = frappe.db.get_value("Pre Order Form",source_name,"branch")
	target_doc.order_type = frappe.db.get_value("Pre Order Form",source_name,"order_type")
	target_doc.due_days = frappe.db.get_value("Pre Order Form",source_name,"due_days")
	target_doc.po_no = frappe.db.get_value("Pre Order Form",source_name,"po_no")
	target_doc.delivery_date = frappe.db.get_value("Pre Order Form",source_name,"delivery_date")
	target_doc.pre_order_form = source_name
	# target_doc.branch = frappe.db.get_value("Pre Order Form",source_name,"customer")
	service_types = frappe.db.get_values("Service Type 2", {"parent": source_name},"service_type1")
	for service_type in service_types:
		target_doc.append("service_type",{"service_type1": service_type[0]})
	
	shipping_territories = frappe.db.get_values("Territory Multi Select", {"parent": source_name},"territory")
	for shipping_territory in shipping_territories:
		target_doc.append("parcel_place",{"territory": shipping_territory[0]})

	for i in customer_order_form:
		# frappe.throw(f"{i}")
		# item, order_id = i.get("design_code"), i.get("order_id")
		# order_data = frappe.db.sql(f"SELECT * FROM `tabOrder` WHERE name = '{order_id}'", as_dict=1)
		# customer_design_code = frappe.db.sql(f"SELECT * FROM `tabBOM` WHERE item = '{item}' AND name = '{i.get('design_code_bom')}'", as_dict=1)
		# item_serial = frappe.db.get_value("Serial No", {'item_code': item}, 'name')

		# data_source = order_data if order_data else customer_design_code
		# if data_source:
		# 	for j in data_source:
		if i.status == 'Done':
			design_id = i.item_variant
			item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")
			master_bom = i.bom

			extra_fields = {}

			if item_subcategory and master_bom:
				all_item_attributes = []
				for item_attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
					formatted_attr = item_attr.item_attribute.replace(' ', '_').replace('/', '').lower()
					all_item_attributes.append((item_attr.item_attribute, formatted_attr))

				# Build dict from Item Variant Attributes
				variant_attributes = frappe.db.get_all("Item Variant Attribute",
					filters={"parent": design_id},
					fields=["attribute", "attribute_value"]
				)
				variant_attr_map = {d.attribute.replace(' ', '_').replace('/', '').lower(): d.attribute_value for d in variant_attributes}

				# Fetch fallback values from BOM
				attribute_values = frappe.db.get_value("BOM", master_bom, [f[1] for f in all_item_attributes], as_dict=1)

				for original_name, formatted_name in all_item_attributes:
					value = variant_attr_map.get(formatted_name) or attribute_values.get(formatted_name)
					if value:
						fieldname = "category" if formatted_name == "item_category" else \
									"subcategory" if formatted_name == "item_subcategory" else formatted_name
						extra_fields[fieldname] = value

			target_doc.append("order_details", {
				"design_by":i.design_by,
				"design_type":i.design_type,
				"order_type":i.order_type,
				"delivery_date":frappe.db.get_value("Pre Order Form",source_name,"delivery_date"),
				"diamond_quality":frappe.db.get_value("Pre Order Form",source_name,"diamond_quality"),
				"design_id": i.item_variant,
				"mod_reason":i.mod_reason,
				"bom":i.bom,
				"category":i.new_category,
				"subcategory":i.new_sub_category,
				"metal_target":i.gold_target,
				"diamond_target":i.diamond_target,
				"setting_type":i.bom_setting_type,
				"pre_order_form_details":i.name,
				"diamond_type":"Natural",
				"jewelex_batch_no":i.bulk_order_no,
				"design_image_1":i.design_image,
				**({"metal_touch": i.metal_touch} if i.design_type == "New Design" else {}),
				**({"metal_colour": i.metal_color} if i.design_type == "New Design" else {}),
				**extra_fields
			})
			
	return target_doc




