# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CustomerOrderForm(Document):
	def on_cancel(self):
		frappe.db.set_value('Titan Order Form',self.name,'workflow_state','Cancelled')

@frappe.whitelist()
def set_customer_code_logic(customer_code,titan_code):
	if customer_code == 'CU0010':
		data_json = set_titan_code(customer_code,titan_code)
	elif customer_code == 'CU0122':
		data_json = set_reliance_code(customer_code,titan_code)
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

	if design_code:
		# bom_data = frappe.db.get_value('BOM',{'item':design_code,'is_active':1,'is_default':1},['metal_colour','metal_type_','metal_purity','item_category'],as_dict=1)
		# data_json['metal_type_'] = bom_data.metal_type_
		# data_json['metal_colour'] = bom_data.metal_colour
		# data_json['metal_purity'] = bom_data.metal_purity

		# if len(titan_code) > 9:
		# # 	size_data = get_size(titan_code,bom_data)
		# 	data_json['size_data'] = product_size

		if len(titan_code) > 10:
			finding_data = get_finding(titan_code)
			data_json['finding_data'] = finding_data
			
		if len(titan_code) >11:
			stone_data = get_stone(titan_code)
			# stone_data = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[12:14],'customer':customer_code},'parent')
			data_json['stone_data'] = stone_data
			# data_json['stone_type'] = stone_data.parent
			# stone_quality = frappe.db.get_value('Customer Attributes Table',{'code':stone_data.description,'customer':customer_code},'parent')
			# data_json['stone_quality'] = stone_quality
	return data_json

def get_size(titan_code,bom_data):
	size_data = frappe.db.sql(f"""SELECT name, inner_dia ,circumference  from  `tabTitan Size by Category` ttsbc  where gk_category ='{bom_data.item_category}' and name like '{titan_code[9]}%'""",as_dict=1)
	return size_data

def get_stone(titan_code):
	titan_prolif = []
	for i in frappe.get_doc('Item Attribute','Titan Prolif').item_attribute_values:
		titan_prolif.append(i.attribute_value)

	for j in frappe.db.sql(f'''select code,customer from `tabCustomer Attributes Table` tcat WHERE code = "{titan_code[12:14]}" and customer = "CU0010"'''):
	# frappe.db.get_list('Customer Attributes Table',filters={'code':titan_code[12:14],'customer':'CU0010'},pluck='parent'):
		if j in titan_prolif:
			return j

def get_finding(titan_code):
	titan_finding_category = []
	for i in frappe.get_doc('Item Attribute','Titan Finding').item_attribute_values:
		titan_finding_category.append(i.attribute_value)
	
	for j in frappe.db.sql(f'''select code,customer from `tabCustomer Attributes Table` tcat WHERE code = "{titan_code[10]}" and customer = "CU0010"'''):
	# frappe.db.get_list('Customer Attributes Table',filters={'code':titan_code[10],'customer':'CU0010'},pluck='parent'):
		if j in titan_finding_category:
			return j
		
def set_reliance_code(customer_code,titan_code):
	data_json = {}
	if len(titan_code) >= 1:
		metal_touch = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[:1],'customer':customer_code,'description':'Metal Touch'},'parent')
		data_json['metal_touch'] = metal_touch
	if len(titan_code) > 1:
		if titan_code[1:2] == 'D':
			data_json['productivity'] = 'Studded'
		else:
			data_json['productivity'] = 'Plain'
		# metal_type = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[1:2],'customer':customer_code,'description':'Metal Type'},'parent')
		# data_json['metal_type'] = metal_type
	if len(titan_code) > 2:
		if titan_code[2:5].upper() == 'MSR' or titan_code[2:5].upper() == 'PDC' or titan_code[2:5].upper() == 'ECN':
			data_json['chain'] = 'Yes'
		else:
			data_json['chain'] = 'No'
		design_code = frappe.db.get_value('Customer Theme Code',{'theme_code':titan_code[2:11],'customer_code':customer_code},'parent')
		data_json['design_code'] = design_code
	if len(titan_code) > 11:
		category = frappe.db.get_value('Item',{'name':data_json['design_code']},'item_category')
		size = frappe.db.get_value('Reliance Size Master',{'item_category':category,'code':titan_code[11:13]},'product_size')
		data_json['size'] = size
	if len(titan_code) > 13:
		if titan_code[13:15] == 'B2':
			data_json['qty'] = 2
		else:
			data_json['qty'] = 1
		finding_data = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[13:15],'customer':customer_code,'description':'Finding Type'},'parent')
		data_json['finding_data'] = finding_data

	if len(titan_code) > 15:
		metal_colour = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[15],'customer':customer_code,'description':'Metal Colour'},'parent')
		data_json['metal_colour'] = metal_colour
	if len(titan_code) > 16:
		diamond_quality = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[16:18],'customer':customer_code,'description':'Diamond Quality'},'parent')
		data_json['diamond_quality'] = diamond_quality

	return data_json

