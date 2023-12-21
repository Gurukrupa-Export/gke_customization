# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns,data

def get_data(filters=None):
	conditions = get_conditions(filters)
	
	if conditions:	
		data = frappe.db.sql(f"""select tcpld.serial_number, tcpld.product_category, 
						tcpld.quantity , tcpld.metal_touch , tcpld.gross_weight, tcpld.gold_weight , tcpld.wastage , tcpld.gold_wastage,
						tcpld.total_weight, tcpld.gold_rate_in_usd, tcpld.gold_value_in_usd , 
					   	tcpld.diamond_shape, tcpld.diamond_quality, tcpld.total_diamond_pcs,  tcpld.total_diamond_in_carat, 
					   	tcpld.diamond_rate_in_usd, tcpld.total_diamond_value_in_usd,
						tcpld.total_cubic_zirconia_in_carat , tcpld.cubic_zirconia_rate_in_usd , tcpld.total_amount_in_usd , 
					   	tcpld.value_addition, tcpld.total_value_addition_in_usd, tcpld.fob_value ,					   
						tcpl.sales_order,tcpl.customer_name, tcpl.customer_address, tcpl.date
						from `tabCustom Packing List` tcpl 
						RIGHT JOIN `tabCustom Packing List Detail` tcpld 
						ON tcpl.name = tcpld.parent  {conditions}""",as_dict=1)
	else:
		data = frappe.db.sql(f"""select tcpld.serial_number, tcpld.product_category, 
						tcpld.quantity , tcpld.metal_touch ,tcpld.gross_weight, tcpld.gold_weight , tcpld.wastage , tcpld.gold_wastage,
						tcpld.total_weight, tcpld.gold_rate_in_usd, tcpld.gold_value_in_usd , 
					   	tcpld.diamond_shape, tcpld.diamond_quality, tcpld.total_diamond_pcs, tcpld.total_diamond_in_carat, 
					   	tcpld.diamond_rate_in_usd, tcpld.total_diamond_value_in_usd,
						tcpld.total_cubic_zirconia_in_carat , tcpld.cubic_zirconia_rate_in_usd , tcpld.total_amount_in_usd , 
					   	tcpld.value_addition, tcpld.total_value_addition_in_usd, tcpld.fob_value ,					   
						tcpl.sales_order,tcpl.customer_name, tcpl.customer_address, tcpl.date
						from `tabCustom Packing List` tcpl 
						RIGHT JOIN `tabCustom Packing List Detail` tcpld 
						ON tcpl.name = tcpld.parent""",as_dict=1)
		
	if not data:

		return
	
	data = indian_format(data)
	totals = get_totals(data)	
	data += totals	

	return data

def get_totals(data):	
	
	totals = {
		"serial_number": "",
	}
	
	keys_to_total = [
		"quantity", "gross_weight", "gold_weight",
		"wastage", "gold_wastage", "total_weight",
		"gold_rate_in_usd", "gold_value_in_usd", 
		"total_diamond_pcs", "total_diamond_in_carat", "diamond_rate_in_usd",
		"total_diamond_value_in_usd", "total_cubic_zirconia_in_carat", 
		"cubic_zirconia_rate_in_usd", "total_amount_in_usd", "value_addition",
		"total_value_addition_in_usd", "fob_value"
	]
	
	total_days = {key: 0 for key in keys_to_total}
	for row in data:
		for key in keys_to_total:
			if row.get(key):
				total_days[key] += float(row[key].replace(',',''))

	total_days["serial_number"] = "Total"
	
	for j in keys_to_total:
		total_days[j] = '{:,}'.format(total_days[j])

	return [totals, total_days]

def get_columns(filters=None):
	columns = [
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Data"
		},
		{
			"label": _("Item Category"),
			"fieldname": "serial_number",
			"fieldtype": "Data"
		},
		{
			"label": _("Item Category"),
			"fieldname": "product_category",
			"fieldtype": "Data",
		},
		{
			"label": _("Quantity"),
			"fieldname": "quantity",
			"fieldtype": "Data"
		},		
		{
			"label": _("Metal Touch"),
			"fieldname": "metal_touch",
			"fieldtype": "Data"
		},		
		{
			"label": _("Gross Weight"),
			"fieldname": "gross_weight",
			"fieldtype": "Data"
		},		
		{
			"label": _("Gold Weight"),
			"fieldname": "gold_weight",
			"fieldtype": "Data"
		},
		{
			"label": _("Wastage %"),
			"fieldname": "wastage",
			"fieldtype": "Data"
		},
		{
			"label": _("Gold Wastage"),
			"fieldname": "gold_wastage",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Weight"),
			"fieldname": "total_weight",
			"fieldtype": "Data"
		},		
		{
			"label": _("Gold Rate (in USD)"),
			"fieldname": "gold_rate_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Gold Value (in USD)"),
			"fieldname": "gold_value_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("Diamond Shape"),
			"fieldname": "diamond_shape",
			"fieldtype": "Data"
		},
		{
			"label": _("Diamond Quality"),
			"fieldname": "diamond_quality",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Diamond Pcs"),
			"fieldname": "total_diamond_pcs",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Diamond (in Carat)"),
			"fieldname": "total_diamond_in_carat",
			"fieldtype": "Data"
		},
		{
			"label": _("Diamond Rate (in USD)"),
			"fieldname": "diamond_rate_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Diamond Value (in USD)"),
			"fieldname": "total_diamond_value_in_usd",
			"fieldtype": "Data"
		},				
		{
			"label": _("Total Cubic Zirconia (in Carat)"),
			"fieldname": "total_cubic_zirconia_in_carat",
			"fieldtype": "Data"
		},
		{
			"label": _("Cubic Zirconia Rate (in USD)"),
			"fieldname": "cubic_zirconia_rate_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Amount (in USD)"),
			"fieldname": "total_amount_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("Value Addition (%)"),
			"fieldname": "value_addition",
			"fieldtype": "Data"
		},
		{
			"label": _("Total Value Addition (in USD)"),
			"fieldname": "total_value_addition_in_usd",
			"fieldtype": "Data"
		},
		{
			"label": _("FOB Value (in USD)"),
			"fieldname": "fob_value",
			"fieldtype": "Data"
		}, 
	]

	return columns

def get_conditions(filters):

	filter_list = []

	if filters.get("cur_sales_order"):
		filter_list.append(f'tcpl.sales_order = "{filters.get("cur_sales_order")}"')

	if filters.get("date"):
		filter_list.append(f'''tcpl.date = "{filters.get("date")}"''')
	
	# if filters.get("customer_name"):
	# 	filter_list.append(f'''tpl.customer_name = "{filters.get("customer")}"''')

	conditions = "where " + " and ".join(filter_list)
	if conditions!='where ':
		return conditions


def indian_format(data):
	new_data = []

	keys_to_total = ["sales_order","serial_number","product_category",
		"quantity", "gross_weight", "gold_weight",
		"wastage", "gold_wastage", "total_weight",
		"gold_rate_in_usd", "gold_value_in_usd", 
		"total_diamond_pcs", "total_diamond_in_carat", "diamond_rate_in_usd",
		"total_diamond_value_in_usd", "total_cubic_zirconia_in_carat", 
		"cubic_zirconia_rate_in_usd", "total_amount_in_usd", "value_addition",
		"total_value_addition_in_usd", "fob_value",
	]	
	
	for i in data:
		new_dict = {}
		for j in keys_to_total:
			if j in ["sales_order","serial_number","product_category"]:
				new_dict[j] = i[j]
			else:	
				# new_dict[j] = '{:,}'.format(i[j])
				if isinstance(i[j], (int, float)):
					new_dict[j] = '{:,}'.format(i[j])
				else:
					new_dict[j] = i[j]
		
		new_data.append(new_dict)

	return new_data
