# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_data(filters=None):
	conditions = get_conditions(filters)
	# frappe.throw(f"{conditions}")
	if conditions: 
		data = frappe.db.sql(f"""
			select 
				distinct(bm.name) as bom,bm.item,
				bm.bom_type,
				bm.is_active,bm.is_default,
				bm.tag_no,
				bm.customer,bm.item_category,
				cod.digit14_code,cod.setting_type,cod.metal_touch,
				bm.metal_weight,bm_finish.metal_weight as bm_finish_metal,
				bm.diamond_weight,bm_finish.diamond_weight as bm_finish_diamond,
				bm.gross_weight,bm_finish.gross_weight as bm_finish_gross_weight,
				bm.total_diamond_pcs,bm.gemstone_weight,cod.line_no 
			from `tabBOM` bm
			left join `tabBOM` bm_finish on bm_finish.item = bm.item and bm_finish.bom_type = 'Finish Goods'
			left join `tabManufacturing Plan Table` mp on mp.item_code = bm.item and mp.customer = bm_finish.customer
			left join `tabSales Order Item` soi on soi.parent = mp.sales_order and soi.item_code = mp.item_code
			left join `tabOrder` od on od.name = soi.order_form_id
			left join `tabCustomer Order Form Detail` cod on cod.parent = od.customer_order_form and cod.design_code = bm.item
				{conditions}
			
		""", as_dict=1)
			# 	mp.parent as manu_plan,mp.sales_order,mp.customer as mp_cust,
			# 	    soi.order_form_id as order_id,od.customer_order_form
	else:
		data = frappe.db.sql(f"""			
			select 
				distinct(bm.name) as bom,bm.item,
				bm.bom_type,
				bm.is_active,bm.is_default,
				bm.tag_no,
				bm.customer,bm.item_category,
				cod.digit14_code,cod.setting_type,cod.metal_touch,
				bm.metal_weight,bm_finish.metal_weight as bm_finish_metal,
				bm.diamond_weight,bm_finish.diamond_weight as bm_finish_diamond,
				bm.gross_weight,bm_finish.gross_weight as bm_finish_gross_weight,
				bm.total_diamond_pcs,bm.gemstone_weight,cod.line_no 
			from `tabBOM` bm
			left join `tabBOM` bm_finish on bm_finish.item = bm.item and bm_finish.bom_type = 'Finish Goods'
			left join `tabManufacturing Plan Table` mp on mp.item_code = bm.item and mp.customer = bm_finish.customer
			left join `tabSales Order Item` soi on soi.parent = mp.sales_order and soi.item_code = mp.item_code
			left join `tabOrder` od on od.name = soi.order_form_id
			left join `tabCustomer Order Form Detail` cod on cod.parent = od.customer_order_form and cod.design_code = bm.item
			where  
				# is_active = 1 and
				# bm.tag_no is not null and
				bm.bom_type = 'Template'
		""", as_dict=1)


	if not data:
		return
		
	return data

def get_columns(filters=None):
	columns = [
		{
			"label": _("BOM"),
			"fieldname": "bom",
			"fieldtype": "Data"
		},
		# {
		# 	"label": _("bom_type"),
		# 	"fieldname": "bom_type",
		# 	"fieldtype": "Data"
		# },
		{
			"label": _("Item Code"),
			"fieldname": "item",
			"fieldtype": "Data"
		},
		{
			"label": _("tag_no"),
			"fieldname": "tag_no",
			"fieldtype": "Data",
		},
		{
			"label": _("customer name"),
			"fieldname": "customer",
			"fieldtype": "Data",
		},
		{
			"label": _("customer digit code"),
			"fieldname": "digit14_code",
			"fieldtype": "Data",
		},
		{
			"label": _("category"),
			"fieldname": "item_category",
			"fieldtype": "Data",
		},
		{
			"label": _("metal touch"),
			"fieldname": "metal_touch",
			"fieldtype": "Data",
		},
		{
			"label": _("setting type"),
			"fieldname": "setting_type",
			"fieldtype": "Data",
		},
		{
			"label": _("metal_weight(in gm)"),
			"fieldname": "metal_weight",
			"fieldtype": "Data"
		},
		{
			"label": _("finish metal_weight(in gm)"),
			"fieldname": "bm_finish_metal",
			"fieldtype": "Data"
		},
		{
			"label": _("gross_weight(in gm)"),
			"fieldname": "gross_weight",
			"fieldtype": "Data"
		},
		{
			"label": _("finish gross_weight(in gm)"),
			"fieldname": "bm_finish_gross_weight",
			"fieldtype": "Data"
		},
		{
			"label": _("diamond_weight(in cts)"),
			"fieldname": "diamond_weight",
			"fieldtype": "Data"
		},
		{
			"label": _("finish diamond_weight(in cts)"),
			"fieldname": "bm_finish_diamond",
			"fieldtype": "Data"
		},
		{
			"label": _("customer gold"),
			# "fieldname": "tag_no",
			"fieldtype": "Data",
		},
		{
			"label": _("diamond pcs"),
			"fieldname": "total_diamond_pcs",
			"fieldtype": "Data",
		},
		{
			"label": _("diamond wt"),
			"fieldname": "diamond_weight",
			"fieldtype": "Data",
		},
		{
			"label": _("customer diamond"),
			# "fieldname": "tag_no",
			"fieldtype": "Data",
		},
		{
			"label": _("stone wt"),
			"fieldname": "gemstone_weight",
			"fieldtype": "Data",
		},
		{
			"label": _("customer stone"),
			# "fieldname": "tag_no",
			"fieldtype": "Data",
		},
		{
			"label": _("other wt"),
			# "fieldname": "tag_no",
			"fieldtype": "Data",
		},
		{
			"label": _("line_no"),
			"fieldname": "line_no",
			"fieldtype": "Data",
		},
	]

	return columns

def get_conditions(filters):
	filter_list = []

	if filters.get("item"):
		filter_list.append(f''' and bm.item = "{filters.get("item")}" ''')
	
	if filters.get("tag_no"):
		filter_list.append(f'''and bm_finish.tag_no = "{filters.get("tag_no")}" ''')
	# is_active = 1 and bm.tag_no is not null and
	conditions ="where  bm.bom_type = 'Template' " + " and ".join(filter_list)
	if conditions!='where ':
		return conditions
	

# select 
# 	bm.bom_type,bm.name as bom,bm.item,
# 	bm.is_active,bm.is_default,
# 	bm.tag_no,bm.metal_weight,bm.gross_weight,
# 	bm.diamond_weight,
# 	bm.customer,bm.item_category,
# 	cod.digit14_code,cod.setting_type,cod.metal_touch,bm.metal_weight,
# 	bm.diamond_weight,bm.total_diamond_pcs,bm.gemstone_weight,cod.line_no

# from `tabBOM` bm
# left join `tabManufacturing Plan Table` mp on mp.item_code = bm.item and mp.customer = bm.customer
# left join `tabSales Order Item` soi on soi.parent = mp.sales_order and soi.item_code = mp.item_code
# left join `tabOrder` od on od.name = soi.order_form_id
# left join `tabCustomer Order Form Detail` cod on cod.parent = od.customer_order_form and cod.design_code = bm.item
# where  
# 	bm.tag_no is not null 
# # 	and bm.item = 'BA00001-001'
# 	and bm.bom_type in ('Template','Finish Goods')
# # 	bm.bom_type = 'Template'