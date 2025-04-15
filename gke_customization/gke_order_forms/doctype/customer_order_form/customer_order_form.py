# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _
from frappe.model.document import Document

class CustomerOrderForm(Document):
	def before_save(self):
		if self.docstatus == 'Draft' or  not self.customer_order_form_detail:
			frappe.throw('Fill atleast one row in table')
		set_data(self)
		# calculate_qty(self)

def calculate_qty(self):
	total_qty = 0
	for row in self.customer_order_form_detail:
		total_qty += row.no_of_pcs
	self.product_qty = total_qty

@frappe.whitelist()
def get_order_form_detail(design_code):		
	order_design_code = frappe.db.sql(f"""
		select ti.name, ti.custom_cad_order_id, tod.name,
			tod.metal_type,tod.metal_touch,tod.metal_colour,tod.metal_target,tod.diamond_target,
			tod.product_size,tod.feature,tod.rhodium_,tod.enamal,tod.gemstone_type1,tod.gemstone_quality,
			tod.qty,tod.diamond_quality
		from `tabItem` as ti 
		left join `tabOrder` as tod 
			on tod.name = ti.custom_cad_order_id and ti.name = tod.item
		where tod.item = '{design_code}'
	""", as_dict=1)

	return order_design_code

# get detail from quotation doctype
@frappe.whitelist()
def get_quotation(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	if source_name:
		# frappe.throw(f"{source_name}")
		quotation_data = frappe.db.sql(f"""
			select 
				tq.party_name,tq.customer_name,
				# titd.theme_code,
				tqi.item_code,ti.custom_cad_order_id,
				tqi.parent,tqi.order_form_id,
				tqi.item_category,tqi.item_subcategory,
				tod.metal_type,tod.metal_touch,tod.metal_colour,
				tod.metal_target,tod.diamond_target,
				tod.product_size,tod.feature,tod.rhodium_,tod.enamal,
				tod.gemstone_type1,tod.gemstone_quality,
				tod.qty,tod.diamond_quality,
				ti.master_bom,
				titd.theme_code
			from `tabQuotation Item` as tqi 
			left join `tabQuotation` as tq
				on tq.name = tqi.parent
			left join `tabItem` as ti
				on ti.name = tqi.item_code
			left join `tabItem Theme Code Detail` as titd
				on titd.parent = ti.name and titd.customer = tq.party_name
			left join `tabOrder` as tod 
				on tod.name = tqi.order_form_id and ti.name = tod.item
			where tqi.parent = '{source_name}'
		""", as_dict=1)
	
	# frappe.throw(f"{quotation_data}")
	for i in quotation_data:
		# if i.get("theme_code"):
			target_doc.append("customer_order_form_detail",{
				"design_code": i.get("item_code"),
				"design_code_bom": i.get("master_bom"), 
				"customer_code": i.get("party_name"),
				"customer_name": i.get("customer_name"),
				"category": i.get("item_category"),
				"subcategory": i.get("item_subcategory"),
				"quotation": i.get("parent"),
				"order_id": i.get("order_form_id"),
				# "metal_type": i.get("metal_type"),
				# "metal_touch": i.get("metal_touch"),
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
		# else: 
		# 	frappe.throw(_("Please Set Theme Code in Item {0}")
		# 		.format(i.get("item_code"))
		# 		)
	return target_doc

def set_data(self):
	if self.customer_order_form_detail:
		for row in self.customer_order_form_detail:
			if row.digit14_code:
				json_14digit = get_14code_detail(row.digit14_code, row.customer_code)
				if isinstance(json_14digit, dict):
					row.theme_code = json_14digit.get("theme_code")
					row.design_code = json_14digit.get("design_code")
					row.design_code_bom = json_14digit.get("bom")
					row.category = json_14digit.get("item_category")
					row.subcategory = json_14digit.get("item_subcategory")
					row.setting_type = json_14digit.get("setting_type")
					row.metal_type = json_14digit.get("metal_type")
					row.metal_touch = json_14digit.get("metal_touch")
					row.metal_colour = json_14digit.get("metal_colour")
					row.diamond_quality = json_14digit.get("stone_data")
					row.finding = json_14digit.get("finding_data")
					row.customer_product_size = json_14digit.get("size_data")
					row.image = json_14digit.get("design_image")
					row.serial_no = json_14digit.get("serial_no")
					# from bom
					row.feature = json_14digit.get("feature")
					row.metal_target = json_14digit.get("metal_target")
					row.diamond_target = json_14digit.get("diamond_target")
					row.product_size = json_14digit.get("product_size")
					row.chain = json_14digit.get("chain")
					row.rhodium = json_14digit.get("rhodium")
			if row.digit18_code:
				json_18digit = get_18code_detail(row.digit18_code, row.customer_code)
				if isinstance(json_18digit, dict):
					row.theme_code = json_18digit.get("theme_code")
					row.design_code = json_18digit.get("design_code")
					row.design_code_bom = json_18digit.get("bom")
					row.category = json_18digit.get("item_category")
					row.subcategory = json_18digit.get("item_subcategory")
					row.setting_type = json_18digit.get("setting_type")
					row.metal_type = json_18digit.get("metal_type")
					row.metal_touch = json_18digit.get("metal_touch")
					row.metal_colour = json_18digit.get("metal_colour")
					row.diamond_quality = json_18digit.get("stone_data")
					row.finding = json_18digit.get("finding_data")
					row.customer_product_size = json_18digit.get("size_data")
					row.image = json_18digit.get("design_image")
					row.serial_no = json_18digit.get("serial_no")
					# from bom
					row.feature = json_18digit.get("feature")
					row.metal_target = json_18digit.get("metal_target")
					row.diamond_target = json_18digit.get("diamond_target")
					row.product_size = json_18digit.get("product_size")
					row.chain = json_18digit.get("chain")
					row.rhodium = json_18digit.get("rhodium")
			if row.digit15_code:
				json_15digit = get_15code_detail(row.digit15_code, row.customer_code)
				if isinstance(json_15digit, dict):
					row.theme_code = json_15digit.get("theme_code")
					row.product_type = json_15digit.get("product_type")
					row.design_code = json_15digit.get("design_code")
					row.design_code_bom = json_15digit.get("bom")
					row.category = json_15digit.get("item_category")
					row.subcategory = json_15digit.get("item_subcategory")
					row.setting_type = json_15digit.get("setting_type")
					row.metal_type = json_15digit.get("metal_type")
					row.metal_touch = json_15digit.get("metal_touch")
					row.metal_colour = json_15digit.get("metal_color")
					row.diamond_quality = json_15digit.get("stone_data")
					row.finding = json_15digit.get("finding_data")
					row.customer_product_size = json_15digit.get("size_data")
					row.image = json_15digit.get("design_image")
					row.serial_no = json_15digit.get("serial_no")
					# from bom
					row.feature = json_15digit.get("feature")
					row.metal_target = json_15digit.get("metal_target")
					row.diamond_target = json_15digit.get("diamond_target")
					row.product_size = json_15digit.get("product_size")
					row.chain = json_15digit.get("chain")
					row.rhodium = json_15digit.get("rhodium")
			if row.theme_code and self.flow_type == 'PROTO':
				# if row.customer_name in ("Novel"):
					theme_data = get_item_detail(row.theme_code, row.customer_code)
					if isinstance(theme_data, dict):
						row.design_code = theme_data.get("design_code")
						row.design_code_bom = theme_data.get("bom")
						row.category = theme_data.get("item_category")
						row.subcategory = theme_data.get("item_subcategory")
						row.setting_type = theme_data.get("setting_type")
						row.metal_type = theme_data.get("metal_type")
						row.image = theme_data.get("design_image")
						row.serial_no = theme_data.get("serial_no")
						# from bom
						row.feature = theme_data.get("feature")
						row.metal_target = theme_data.get("metal_target")
						row.diamond_target = theme_data.get("diamond_target")
						row.product_size = theme_data.get("product_size")
						row.chain = theme_data.get("chain")
						row.rhodium = theme_data.get("rhodium")

			if row.sku_code:
				json_skucode = get_sku_code_detail(row.sku_code, row.customer_code)
				if isinstance(json_skucode, dict):
					row.theme_code = json_skucode.get("theme_code")
					# row.product_type = json_skucode.get("product_type")
					row.design_code = json_skucode.get("design_code")
					row.design_code_bom = json_skucode.get("bom")
					row.category = json_skucode.get("item_category")
					row.subcategory = json_skucode.get("item_subcategory")
					row.setting_type = json_skucode.get("setting_type")
					row.metal_type = json_skucode.get("metal_type")
					row.metal_touch = json_skucode.get("metal_touch")
					row.metal_colour = json_skucode.get("metal_color")
					row.diamond_quality = json_skucode.get("diamond_quality")
					row.customer_product_size = json_skucode.get("product_size")
					row.image = json_skucode.get("design_image")
					row.serial_no = json_skucode.get("serial_no")
					# from bom
					row.feature = json_skucode.get("feature")
					row.metal_target = json_skucode.get("metal_target")
					row.diamond_target = json_skucode.get("diamond_target")
					row.product_size = json_skucode.get("product_size")
					row.chain = json_skucode.get("chain")
					row.rhodium = json_skucode.get("rhodium")
					row.diamond_weight = json_skucode.get("diamond_weight")
					row.max_diamond = json_skucode.get("max_diamond")
					row.min_diamond = json_skucode.get("min_diamond")
					row.metal_and_finding_weight = json_skucode.get("metal_and_finding_weight")

@frappe.whitelist()
def get_temp_bom_details(design_code, bom):
	# feature,metal_target,diamond_target,product_size,chain,rhodium,
	bom_detail = frappe.db.get_value("BOM",{'item': design_code, 'name': bom, 'bom_type': 'Template'}, 
		['feature','metal_target','diamond_target','product_size','chain','rhodium','diamond_weight','metal_and_finding_weight'])
	
	return bom_detail

#for novel, in proto they give only theme_code
@frappe.whitelist()
def get_item_detail(theme_code, customer):
	data_json = {}
	design_code = frappe.db.get_value('Item Theme Code Detail', {'customer': customer, 'theme_code': theme_code}, 'parent')
	if design_code:
		data_json['design_code'] = design_code
	else:
		frappe.throw(f"Please Set the Theme code <b>{theme_code}</b> in Item ")

	# details from design information sheet as per design code
	if design_code:
		design_sheet = frappe.db.get_value('Customer Design Information Sheet', {'customer_code': customer, 'design_code': design_code}, 
				['bom','item_category','item_subcategory','setting_type','metal_type','design_image','serial_no'])
		
		if design_sheet:
			bom_detail = get_temp_bom_details(design_code, design_sheet[0])
			data_json['bom'] = design_sheet[0]
			data_json['item_category'] = design_sheet[1]
			data_json['item_subcategory'] = design_sheet[2]
			data_json['setting_type'] = design_sheet[3]
			data_json['metal_type'] = design_sheet[4]
			data_json['design_image'] = design_sheet[5]
			data_json['serial_no'] = design_sheet[6]
		if bom_detail:
			data_json['feature'] = bom_detail[0]
			data_json['metal_target'] = bom_detail[1]
			data_json['diamond_target'] = bom_detail[2]
			data_json['product_size'] = bom_detail[3]
			data_json['chain'] = bom_detail[4]
			data_json['rhodium'] = bom_detail[5]
	
	return data_json


# get detail from 14 digit code 
@frappe.whitelist()
def get_14code_detail(digit14_code, customer):
	data_json = {}

	# metal touch
	if len(digit14_code) > 1:
		metal_touch = frappe.db.get_value('Customer Metal Touch Detail',{'code_touch': digit14_code[:2], 'parent': customer}, 'gk_metal_touch' )
		data_json['metal_touch'] = metal_touch
		
	# theme code and design code 
	design_code = ''
	if len(digit14_code) > 2: 
		theme_code = digit14_code[2:9]
		data_json['theme_code'] = theme_code

		design_code = frappe.db.get_value('Item Theme Code Detail', {'customer': customer, 'theme_code': theme_code}, 'parent')
		if design_code:
			data_json['design_code'] = design_code
		else:
			frappe.throw(f"Please Set the Theme code <b>{theme_code}</b> in Item ")

		# details from design information sheet as per design code
		# 'metal_touch',
		if design_code:
			design_sheet = frappe.db.get_value('Customer Design Information Sheet', 
					{'customer_code': customer, 'design_code': design_code}, 
					['bom','item_category','item_subcategory','setting_type','metal_type','metal_colour','design_image','serial_no'])
			# frappe.throw(f"{bom_detail}")
			if design_sheet:
				bom_detail = get_temp_bom_details(design_code, design_sheet[0])
				data_json['bom'] = design_sheet[0]
				data_json['item_category'] = design_sheet[1]
				data_json['item_subcategory'] = design_sheet[2]
				data_json['setting_type'] = design_sheet[3]
				data_json['metal_type'] = design_sheet[4]
				# data_json['metal_touch'] = design_sheet[5]
				data_json['metal_colour'] = design_sheet[5]
				data_json['design_image'] = design_sheet[6]
				data_json['serial_no'] = design_sheet[7]
			if bom_detail:
				# data_json[feature,metal_target,diamond_target,product_size,chain,rhodium]
				data_json['feature'] = bom_detail[0]
				data_json['metal_target'] = bom_detail[1]
				data_json['diamond_target'] = bom_detail[2]
				data_json['product_size'] = bom_detail[3]
				data_json['chain'] = bom_detail[4]
				data_json['rhodium'] = bom_detail[5]

	if design_code:
		# for size as per category
		if len(digit14_code) > 9:
			size_data = get_size(customer, digit14_code, design_code)
			data_json['size_data'] = size_data
	
		# finding data
		if len(digit14_code) > 10:
			finding_data = frappe.db.get_value('Customer Finding Detail',{'code_finding': digit14_code[10], 'parent': customer}, 'description_finding' )
			if finding_data:
				data_json['finding_data'] = finding_data
			else:
				data_json['finding_data'] = ''
		
		# diamond Quality
		if len(digit14_code) > 12:
			stone_data = frappe.db.get_value('Customer Prolif Detail',{'code_prolif': digit14_code[12:14], 'parent': customer}, 'gk_d' )
			if stone_data:
				data_json['stone_data'] = stone_data
			else:
				data_json['stone_data'] = ''
				
	return data_json

# get size from titan size master
def get_size(customer,titan_code,design_code):
	item_category = frappe.db.get_value('Item',design_code,'item_category')
	
	if titan_code[0] == 'U':
		size_data = frappe.db.get_value('Titan Size Master',{'customer':customer,'code':titan_code[9],'item_category':item_category,'country':'United States'},'product_size')
	else:
		size_data = frappe.db.get_value('Titan Size Master',{'customer':customer,'code':titan_code[9],'item_category':item_category,'country':'India'},'product_size')

	return size_data

@frappe.whitelist()
def get_18code_detail(digit18_code, customer):
	data_json = {}

	# metal touch
	if len(digit18_code) > 1:
		metal_touch = frappe.db.get_value('Customer Metal Touch Detail',{'code_touch': digit18_code[0], 'parent': customer}, 'gk_metal_touch' )
		data_json['metal_touch'] = metal_touch
	
	if len(digit18_code) > 2:
		metal_type = frappe.db.get_value('Customer Metal Type Detail',{'code_type': digit18_code[1], 'parent': customer}, 'gk_metal_type' )
		data_json['metal_type'] = metal_type
	
	design_code = ''
	if len(digit18_code) > 3: 
		theme_code = digit18_code[2:11]
		data_json['theme_code'] = theme_code

		design_code = frappe.db.get_value('Item Theme Code Detail', {'customer': customer, 'theme_code': theme_code}, 'parent')
		if design_code:
			data_json['design_code'] = design_code
		else:
			frappe.throw(f"Please Set the Theme code <b>{theme_code}</b> in Item ")
	
	# 	# details from design information sheet as per design code
		if design_code:
			design_sheet = frappe.db.get_value('Customer Design Information Sheet', 
						{'customer_code': customer, 'design_code': design_code}, 
					['bom','item_category','item_subcategory','setting_type','design_image','serial_no'])
			
			if design_sheet:
				bom_detail = get_temp_bom_details(design_code, design_sheet[0])
				data_json['bom'] = design_sheet[0]
				data_json['item_category'] = design_sheet[1]
				data_json['item_subcategory'] = design_sheet[2]
				data_json['setting_type'] = design_sheet[3]
				data_json['design_image'] = design_sheet[4]
				data_json['serial_no'] = design_sheet[5]
			if bom_detail:
				data_json['feature'] = bom_detail[0]
				data_json['metal_target'] = bom_detail[1]
				data_json['diamond_target'] = bom_detail[2]
				data_json['product_size'] = bom_detail[3]
				data_json['chain'] = bom_detail[4]
				data_json['rhodium'] = bom_detail[5]

	if design_code:
	# 	# for size as per category
		if len(digit18_code) > 11:
			size_data = get_realiance_size(customer, digit18_code[11:13], design_code)
			data_json['size_data'] = size_data
	
		# finding data
		if len(digit18_code) > 13:
			finding_data = frappe.db.get_value('Customer Finding Detail',{'code_finding': digit18_code[13:15], 'parent': customer}, 'description_finding' )
			if finding_data:
				data_json['finding_data'] = finding_data
			else:
				data_json['finding_data'] = ''
		
		if len(digit18_code) > 15:
			metal_color = frappe.db.get_value('Customer Metal Color Detail',{'code_color': digit18_code[15], 'parent': customer}, 'gk_metal_color' )
			if metal_color:
				data_json['metal_color'] = metal_color
			else:
				data_json['metal_color'] = ''

		# diamond Quality
		if len(digit18_code) > 16:
			stone_data = frappe.db.get_value('Customer Prolif Detail',{'code_prolif': digit18_code[16:18], 'parent': customer}, 'gk_d' )
			if stone_data:
				data_json['stone_data'] = stone_data
			else:
				data_json['stone_data'] = ''
	# frappe.throw(f"{data_json}")
	return data_json

# get size from titan size master
def get_realiance_size(customer,reliance_code,design_code):
	item_category = frappe.db.get_value('Item',design_code,'item_category')
	size_data = frappe.db.get_value('Reliance Size Master',{'customer':customer,'code':reliance_code,'item_category':item_category},'product_size')
	
	return size_data

@frappe.whitelist()
def get_15code_detail(digit15_code, customer):
	data_json = {}
	if len(digit15_code) > 1:
		product_type = digit15_code[0]
		if product_type == 'D':
			data_json['product_type'] = 'Studded - DIS'

	# metal touch
	if len(digit15_code) > 2:
		metal_touch = frappe.db.get_value('Customer Metal Touch Detail',{'code_touch': digit15_code[1], 'parent': customer}, 'gk_metal_touch' )
		data_json['metal_touch'] = metal_touch
		
	design_code = ''
	if len(digit15_code) > 13: 
		theme_code = digit15_code[8:15]
		data_json['theme_code'] = theme_code

		design_code = frappe.db.get_value('Item Theme Code Detail', {'customer': customer, 'theme_code': theme_code}, 'parent')
		if design_code:
			data_json['design_code'] = design_code
		else:
			frappe.throw(f"Please Set the Theme code <b>{theme_code}</b> in Item ")
	
	# 	# details from design information sheet as per design code
		if design_code:
			design_sheet = frappe.db.get_value('Customer Design Information Sheet', {'customer_code': customer, 'design_code': design_code}, 
					['bom','item_category','item_subcategory','setting_type','metal_type','design_image','serial_no'])
			
			if design_sheet:
				bom_detail = get_temp_bom_details(design_code, design_sheet[0])
				data_json['bom'] = design_sheet[0]
				data_json['item_category'] = design_sheet[1]
				data_json['item_subcategory'] = design_sheet[2]
				data_json['setting_type'] = design_sheet[3]
				data_json['metal_type'] = design_sheet[4]
				data_json['design_image'] = design_sheet[5]
				data_json['serial_no'] = design_sheet[6]
			if bom_detail:
				data_json['feature'] = bom_detail[0]
				data_json['metal_target'] = bom_detail[1]
				data_json['diamond_target'] = bom_detail[2]
				data_json['product_size'] = bom_detail[3]
				data_json['chain'] = bom_detail[4]
				data_json['rhodium'] = bom_detail[5]

	if design_code:
		# for size as per category
		if len(digit15_code) > 2:
			size_data = get_novel_size(customer, digit15_code[2], design_code)
			data_json['size_data'] = size_data
	
	if len(digit15_code) > 3:
		metal_color = frappe.db.get_value('Customer Metal Color Detail',{'code_color': digit15_code[3], 'parent': customer}, 'gk_metal_color' )
		if metal_color:
			data_json['metal_color'] = metal_color
		else:
			data_json['metal_color'] = ''

	# finding data
	if len(digit15_code) > 4:
		finding_data = frappe.db.get_value('Customer Finding Detail',{'code_finding': digit15_code[4], 'parent': customer}, 'description_finding' )
		if finding_data:
			data_json['finding_data'] = finding_data
		else:
			data_json['finding_data'] = ''
	

	# diamond Quality
	if len(digit15_code) > 6:
		stone_data = frappe.db.get_value('Customer Prolif Detail',{'code_prolif': digit15_code[5:7], 'parent': customer}, 'gk_d' )
		if stone_data:
			data_json['stone'] = stone_data
		else:
			data_json['stone'] = ''

	# frappe.throw(f"{data_json}")
	return data_json

# get size from titan size master
def get_novel_size(customer,novel_code,design_code):
	item_category = frappe.db.get_value('Item',design_code,'item_category')
	
	size_data = frappe.db.get_value('Novel Size Master',{'customer':customer,'code':novel_code,'item_category':item_category},'product_size')
	
	return size_data

def get_sku_code_detail(sku_code, customer):
	data_json = {}
	len_sku = len(sku_code)

	design_code = ''
	if len_sku > 7:
		theme_code = sku_code[0:7]
		data_json['theme_code'] = theme_code
		
		design_code = frappe.db.get_value('Item Theme Code Detail', {'customer': customer, 'theme_code': theme_code}, 'parent')
		if design_code:
			data_json['design_code'] = design_code
		else:
			frappe.throw(f"Please Set the Theme code <b>{theme_code}</b> in Item ")
		
		if design_code:
			design_sheet = frappe.db.get_value('Customer Design Information Sheet', {'customer_code': customer, 'design_code': design_code}, 
					['bom','item_category','item_subcategory','setting_type','metal_type','design_image','serial_no'])
			
			if design_sheet:
				bom_detail = get_temp_bom_details(design_code, design_sheet[0])
				data_json['bom'] = design_sheet[0] 
				data_json['item_category'] = design_sheet[1]
				data_json['item_subcategory'] = design_sheet[2]
				data_json['setting_type'] = design_sheet[3]
				data_json['metal_type'] = design_sheet[4]
				data_json['design_image'] = design_sheet[5]
				data_json['serial_no'] = design_sheet[6]
			if bom_detail:
				data_json['feature'] = bom_detail[0]
				data_json['metal_target'] = bom_detail[1]
				data_json['diamond_target'] = bom_detail[2]
				data_json['product_size'] = bom_detail[3]
				data_json['chain'] = bom_detail[4]
				data_json['rhodium'] = bom_detail[5]
				data_json['diamond_weight'] = bom_detail[6]
				data_json['metal_and_finding_weight'] = bom_detail[7]
				
				data_json.update(set_diamond_tolerance(data_json['diamond_weight'], customer))

	if len_sku > 10:
		metal_data = sku_code[8:10]
		if metal_data in ['1Y', '2Y', '1R', '2R']:
			metal_touch = frappe.db.get_value('Customer Metal Touch Detail',{'code_touch': metal_data, 'parent': customer}, 'gk_metal_touch' )
			metal_color = frappe.db.get_value('Customer Metal Color Detail',{'code_color': sku_code[9], 'parent': customer}, 'gk_metal_color' )
			
			data_json['metal_color'] = metal_color if metal_color else ''
			data_json['metal_touch'] = metal_touch if metal_touch else ''
			data_json['metal_type'] = 'Gold'
			
		if metal_data in ['YG','RG','WG']:
			metal_touch = frappe.db.get_value('Customer Metal Touch Detail',{'code_touch': metal_data, 'parent': customer}, 'gk_metal_touch' )
			metal_color = frappe.db.get_value('Customer Metal Color Detail',{'code_color': sku_code[8], 'parent': customer}, 'gk_metal_color' )
			metal_type = frappe.db.get_value('Customer Metal Type Detail',{'code_type': sku_code[9], 'parent': customer}, 'gk_metal_type' )
			
			data_json['metal_color'] = metal_color if metal_color else ''
			data_json['metal_type'] = metal_type if metal_type else 'Gold'
			data_json['metal_touch'] = metal_touch

	if len_sku > 14:
		diamond_quality = sku_code[10:14]
		if diamond_quality:
			stone_data = frappe.db.get_value('Customer Prolif Detail',{'code_prolif': diamond_quality, 'parent': customer}, 'gk_d' )
			if stone_data:
				data_json['diamond_quality'] = stone_data

	if len_sku > 16:
		product_size = sku_code[15:17]
		data_json['product_size'] = product_size
	
	# frappe.throw(f"{data_json}")
	return data_json

def set_diamond_tolerance(diamond_weight, customer):
	data_json = {}
	if diamond_weight:
		tolerance_data = frappe.db.get_all('Diamond Tolerance Table',
			filters={'weight_type': 'Weight wise', 'parent': customer}, 
			fields=['from_diamond', 'to_diamond', 'plus_percent', 'minus_percent'])

		for row in tolerance_data:
			if row['from_diamond'] <= diamond_weight <= row['to_diamond']:
				plus_percent = row['plus_percent']
				minus_percent = row['minus_percent']

				max_diamond_weight = diamond_weight + plus_percent
				min_diamond_weight = diamond_weight - minus_percent
				
				data_json['max_diamond'] = round(max_diamond_weight, 3)
				data_json['min_diamond'] = round(min_diamond_weight, 3)

	return data_json