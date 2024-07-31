# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document

class CustomerOrderForm(Document):
	def on_cancel(self):
		frappe.db.set_value('Titan Order Form',self.name,'workflow_state','Cancelled')


@frappe.whitelist()
def set_customer_code_logic(customer_code,titan_code):
	if customer_code == 'CU0010':
		data_json = set_titan_code(customer_code,titan_code)
	# elif customer_code == 'CU0122':
	# 	data_json = set_reliance_code(customer_code,titan_code)
	return data_json

def set_titan_code(customer_code,titan_code):
	data_json = {}

	if len(titan_code) >1:
		metal_touch = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[:2],'customer':customer_code},'parent')
		data_json['metal_touch'] = metal_touch
	
	
	# design_code = frappe.db.get_value('Customer Theme Code',{'theme_code':titan_code[2:9],'customer_code':customer_code},'parent')
	# data_json['design_code'] = design_code
	design_code = ''
	if len(titan_code) >2:
		design_code = frappe.db.get_value('Customer Theme Code',{'theme_code':titan_code[2:9],'customer_code':customer_code},'parent')
		data_json['design_code'] = design_code

	# titan_category = get_cateogry(titan_code)
	
	if len(titan_code)>6:
		design_code = frappe.db.sql(f"""select design_code, design_code_2 from `tabTitan Design Information Sheet` ttdis where fourteen_digit_set_code like '{titan_code[:6]}%'""",as_dict=1)[0]['design_code']
		design_code_2 = frappe.db.sql(f"""select design_code, design_code_2 from `tabTitan Design Information Sheet` ttdis where fourteen_digit_set_code like '{titan_code[:6]}%'""",as_dict=1)[0]['design_code_2']
		data_json['design_code'] = design_code
		data_json['design_code_2'] = design_code_2

	if design_code:
		data_json['metal_colour'] = frappe.db.get_value('Titan Design Information Sheet',{'design_code':design_code},'metal_colour')

		

		if len(titan_code) > 9:
			size_data = get_size(customer_code,titan_code,design_code)
			data_json['size_data'] = size_data

		if frappe.db.get_value('Item',design_code,'item_category') in ['Nose Pin','Earrings']:
			if len(titan_code) > 10:
				finding_data = get_finding(titan_code)
				data_json['finding_data'] = finding_data
		else:
			data_json['finding_data'] = ''
			
		if len(titan_code) >12:
			stone_data = get_stone(customer_code,titan_code)
		# 	# stone_data = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[12:14],'customer':customer_code},'parent')
			data_json['stone_data'] = stone_data
			# data_json['stone_type'] = stone_data.parent
			# stone_quality = frappe.db.get_value('Customer Attributes Table',{'code':stone_data.description,'customer':customer_code},'parent')
			# data_json['stone_quality'] = stone_quality

			
			design_code = frappe.db.get_value('Titan Design Information Sheet',{'fourteen_digit_set_code':titan_code},'design_code')
			if design_code:
				data_json['design_code_2'] = frappe.db.get_value('Titan Design Information Sheet',{'fourteen_digit_set_code':titan_code},'design_code_2')
	
	return data_json

def get_size(customer,titan_code,design_code):
	item_category = frappe.db.get_value('Item',design_code,'item_category')
	
	if titan_code[0] == 'U':
		size_data = frappe.db.get_value('Titan Size Master',{'customer':customer,'code':titan_code[9],'item_category':item_category,'country':'United States'},'product_size')
	else:
		size_data = frappe.db.get_value('Titan Size Master',{'customer':customer,'code':titan_code[9],'item_category':item_category,'country':'India'},'product_size')

	# size_data = frappe.db.sql(f"""SELECT name, inner_dia ,circumference  from  `tabTitan Size by Category` ttsbc  where gk_category ='{bom_data.item_category}' and name like '{titan_code[9]}%'""",as_dict=1)
	return size_data

def get_stone(customer_code,titan_code):
	# titan_prolif = []
	# for i in frappe.get_doc('Item Attribute','Titan Prolif').item_attribute_values:
	# 	titan_prolif.append(i.attribute_value)
	stonre_data = frappe.db.sql(f"""select parent from `tabAttribute Value For  Customer Theme Code` tavfctc where customer = '{customer_code}' and details = 'PROLIF' and code='{titan_code[12:14]}'""",as_dict=1)

	# for j in frappe.db.sql(f'''select code,customer from `tabCustomer Attributes Table` tcat WHERE code = "{titan_code[12:14]}" and customer = "CU0010"'''):
	# # frappe.db.get_list('Customer Attributes Table',filters={'code':titan_code[12:14],'customer':'CU0010'},pluck='parent'):
	# 	if j in titan_prolif:
	return stonre_data[0]['parent']

def get_finding(titan_code):
	# titan_finding_category = []
	# for i in frappe.get_doc('Item Attribute','Titan Finding').item_attribute_values:
	# 	titan_finding_category.append(i.attribute_value)
	finding_data = frappe.db.sql(f"""select parent from `tabAttribute Value For  Customer Theme Code` tavfctc where customer = 'CU0010' and details = 'FINDING' and code='{titan_code[10]}'""",as_dict=1)
	# for j in frappe.db.sql(f'''select code,customer from `tabCustomer Attributes Table` tcat WHERE code = "{titan_code[10]}" and customer = "CU0010"'''):
	# # frappe.db.get_list('Customer Attributes Table',filters={'code':titan_code[10],'customer':'CU0010'},pluck='parent'):
	# 	if j in titan_finding_category:
	# 		return j
	return finding_data[0]['parent']
		
# def set_reliance_code(customer_code,titan_code):
# 	data_json = {}
# 	if len(titan_code) >= 1:
# 		metal_touch = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[:1],'customer':customer_code,'description':'Metal Touch'},'parent')
# 		data_json['metal_touch'] = metal_touch
# 	if len(titan_code) > 1:
# 		if titan_code[1:2] == 'D':
# 			data_json['productivity'] = 'Studded'
# 		else:
# 			data_json['productivity'] = 'Plain'
# 		# metal_type = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[1:2],'customer':customer_code,'description':'Metal Type'},'parent')
# 		# data_json['metal_type'] = metal_type
# 	if len(titan_code) > 2:
# 		if titan_code[2:5].upper() == 'MSR' or titan_code[2:5].upper() == 'PDC' or titan_code[2:5].upper() == 'ECN':
# 			data_json['chain'] = 'Yes'
# 		else:
# 			data_json['chain'] = 'No'
# 		design_code = frappe.db.get_value('Customer Theme Code',{'theme_code':titan_code[2:11],'customer_code':customer_code},'parent')
# 		data_json['design_code'] = design_code
# 	if len(titan_code) > 11:
# 		category = frappe.db.get_value('Item',{'name':data_json['design_code']},'item_category')
# 		size = frappe.db.get_value('Reliance Size Master',{'item_category':category,'code':titan_code[11:13]},'product_size')
# 		data_json['size'] = size
# 	if len(titan_code) > 13:
# 		if titan_code[13:15] == 'B2':
# 			data_json['qty'] = 2
# 		else:
# 			data_json['qty'] = 1
# 		finding_data = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[13:15],'customer':customer_code,'description':'Finding Type'},'parent')
# 		data_json['finding_data'] = finding_data

# 	if len(titan_code) > 15:
# 		metal_colour = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[15],'customer':customer_code,'description':'Metal Colour'},'parent')
# 		data_json['metal_colour'] = metal_colour
# 	if len(titan_code) > 16:
# 		diamond_quality = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[16:18],'customer':customer_code,'description':'Diamond Quality'},'parent')
# 		data_json['diamond_quality'] = diamond_quality

# 	return data_json

def demo():
	return

@frappe.whitelist()
def get_order_form_detail(design_code):		
	order_design_code = frappe.db.sql(f"""select ti.name, ti.custom_cad_order_id, tod.name,
		tod.metal_type,tod.metal_touch,tod.metal_colour,tod.metal_target,tod.diamond_target,
		tod.product_size,tod.feature,tod.rhodium_,tod.enamal,tod.gemstone_type1,tod.gemstone_quality,
		tod.qty,tod.diamond_quality
		from `tabItem` as ti 
		left join `tabOrder` as tod on tod.name = ti.custom_cad_order_id and ti.name = tod.item
		where tod.item = '{design_code}'
	""", as_dict=1)

	# frappe.throw(f"{order_design_code}")

	return order_design_code

@frappe.whitelist()
def get_quotation(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	if source_name:
		quotation_data = frappe.db.sql(f"""
			select tqi.item_code,ti.custom_cad_order_id,tqi.parent,tqi.order_form_id,
			tod.metal_type,tod.metal_touch,tod.metal_colour,tod.metal_target,tod.diamond_target,
			tod.product_size,tod.feature,tod.rhodium_,tod.enamal,tod.gemstone_type1,tod.gemstone_quality,
			tod.qty,tod.diamond_quality
			from `tabQuotation Item` as tqi 
			left join `tabItem` as ti
			on ti.name = tqi.item_code
			left join `tabOrder` as tod on tod.name = tqi.order_form_id and ti.name = tod.item
			where tqi.parent = '{source_name}'
		""", as_dict=1)

		# quotation_data = frappe.db.sql(f"""
		# 	select tqi.item_code,ti.custom_cad_order_id,tqi.parent,
		# 	tod.metal_type,tod.metal_touch,tod.metal_colour,tod.metal_target,tod.diamond_target,
		# 	tod.product_size,tod.feature,tod.rhodium_,tod.enamal,tod.gemstone_type1,tod.gemstone_quality,
		# 	tod.qty,tod.diamond_quality
		# 	from `tabQuotation Item` as tqi 
		# 	left join `tabItem` as ti
		# 	on ti.name = tqi.item_code
		# 	left join `tabOrder` as tod on tod.name = tqi.order_form_id
		# 	where tqi.parent = '{source_name}'
		# """, as_dict=1)

		# frappe.throw(f"{quotation_data}")
	
	for i in quotation_data:
		target_doc.append("customer_order_form_detail",{
			"design_code": i.get("item_code"),
			"quotation": i.get("parent"),
			"order_id": i.get("order_form_id"),
			"metal_type": i.get("metal_type"),
			"metal_touch": i.get("metal_touch"),
			"metal_target": i.get("metal_target"),
			"metal_colour": i.get("metal_colour"),
			"feature": i.get("feature"),
			"diamond_target": i.get("diamond_target"),
			"diamond_quality": i.get("diamond_quality"),
			"gemstone_type": i.get("gemstone_type1"),
			"gemstone_quality": i.get("gemstone_quality"),
			"product_size": i.get("product_size"),
			"enamal": i.get("enamal"),
			"no_of_pcs": i.get("qty"),
			"rhodium": i.get("rhodium_"),
		})

	return target_doc