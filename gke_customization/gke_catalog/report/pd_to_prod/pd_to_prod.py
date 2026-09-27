# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import requests

JWELEX_API_BASE_URL = "http://3.108.219.130:8003"


def _get_pd_to_prod_data():
	return _call_jwelex_api(f"{JWELEX_API_BASE_URL}/pd-to-prod")


def _get_pd_to_prod_tag_summary():
	return _call_jwelex_api(f"{JWELEX_API_BASE_URL}/pd-to-prod-tag-summary")


def _call_jwelex_api(url):
	try:
		response = requests.get(url, timeout=180)
		response.raise_for_status()
		return response.json().get("data")
	except requests.RequestException:
		frappe.log_error(
			title="PD to Prod Jwelex API call failed",
			message=frappe.get_traceback()
		)
		frappe.throw(f"Failed to fetch data from Jwelex API at {url}")


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": "Item Code",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": "Variant Of",
			"fieldname": "variant_of",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": "Item Category",
			"fieldname": "item_category",
			"fieldtype": "Link",
			"options": "Attribute Value",
			"width": 150,
		},
		{
			"label": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"label": "Sketch Order No",
			"fieldname": "sketch_order_no",
			"fieldtype": "Link",
			"options": "Sketch Order",
			"width": 150,
		},
		
		{
			"label": "CAD Order No",
			"fieldname": "cad_order_no",
			"fieldtype": "Link",
			"options": "Order",
			"width": 150,
		},
		{
			"label": "Sketch Order Date",
			"fieldname": "sketch_order_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": "CAD Order Date",
			"fieldname": "cad_order_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": "StyleBio",
			"fieldname": "stylebio",
			"fieldtype": "Data",
			"width": 150,
		},
		# {
		# 	"label": "Catelog Info Id",
		# 	"fieldname": "catelog_info_ids",
		# 	"fieldtype": "Data",
		# 	"width": 120,
		# },
		# {
		# 	"label": "StyleBio Id (Jwelex)",
		# 	"fieldname": "stylebio_ids",
		# 	"fieldtype": "Data",
		# 	"width": 150,
		# },
		{
			"label": "Date",
			"fieldname": "entry_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": "Category",
			"fieldname": "category_name",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": "Sub-Category",
			"fieldname": "sub_category_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": "Setting",
			"fieldname": "designsetting_name",
			"fieldtype": "Data",
			"width": 150,
		},
		# {
		# 	"label": "Tag No",
		# 	"fieldname": "tagno",
		# 	"fieldtype": "Data",
		# 	"width": 120,
		# },
		# {
		# 	"label": "Tag Date",
		# 	"fieldname": "tagdate",
		# 	"fieldtype": "Date",
		# 	"width": 100,
		# },
		# {
		# 	"label": "Total Tag No",
		# 	"fieldname": "total_tag_no",
		# 	"fieldtype": "Int",
		# 	"width": 110,
		# },
		{
			"label": "Tag Nos",
			"fieldname": "tag_nos",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "First-Tag Date",
			"fieldname": "first_tag_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": "Total Sold",
			"fieldname": "total_sold",
			"fieldtype": "Int",
			"width": 100,
		},
	]


def get_data(filters=None):
	query = """
		SELECT
			fsac.item                                      AS "item_code",
			COALESCE(so.customer_code, ord.customer_code)  AS "customer",
			so.name                                        AS "sketch_order_no",
			it.variant_of                                  AS "variant_of",
			it.item_category                               AS "item_category",
			ord.name                                        AS "cad_order_no",
			so.order_date                                  AS "sketch_order_date",
			ord.order_date                                 AS "cad_order_date",
			it.stylebio                                    AS "stylebio"
		FROM `tabSketch Order` so
		INNER JOIN `tabFinal Sketch Approval CMO` fsac
			ON fsac.parent = so.name
			AND fsac.parenttype = 'Sketch Order'
			AND fsac.parentfield = 'final_sketch_approval_cmo'
		LEFT JOIN `tabItem` it
			ON it.name = fsac.item
		LEFT JOIN `tabOrder` ord
			ON ord.design_id = fsac.item
		WHERE fsac.item IS NOT NULL
			{conditions}
		ORDER BY so.name
	""".format(conditions=get_conditions(filters))

	data = frappe.db.sql(query, filters, as_dict=True)

	jwelex_data = _get_pd_to_prod_data() or []
	jwelex_by_stylebio = {}
	for row in jwelex_data:
		jwelex_by_stylebio.setdefault(row.get("StyleBio_Ids"), row)

	blank_jwelex_row = {
		"catelog_info_ids": None,
		"stylebio_ids": None,
		"entry_date": None,
		"category_name": None,
		"sub_category_name": None,
		"designsetting_name": None,
		"tagno": None,
		"tagdate": None,
	}

	tag_summary_data = _get_pd_to_prod_tag_summary() or []
	tag_summary_by_stylebio = {}
	for row in tag_summary_data:
		tag_summary_by_stylebio.setdefault(row.get("StyleBio"), row)

	blank_tag_summary_row = {
		"total_tag_no": None,
		"first_tag_date": None,
		"tag_nos": None,
		"total_sold": None,
	}

	for row in data:
		jwelex_row = jwelex_by_stylebio.get(row.get("stylebio"))
		if jwelex_row:
			row.update({
				"catelog_info_ids": jwelex_row.get("Catelog_Info_Ids"),
				"stylebio_ids": jwelex_row.get("StyleBio_Ids"),
				"entry_date": jwelex_row.get("Entry_Date"),
				"category_name": jwelex_row.get("Category_Name"),
				"sub_category_name": jwelex_row.get("Sub_Category_Name"),
				"designsetting_name": jwelex_row.get("DesignSetting_Name"),
				"tagno": jwelex_row.get("TagNo"),
				"tagdate": jwelex_row.get("TagDate"),
			})
		else:
			row.update(blank_jwelex_row)

		tag_summary_row = tag_summary_by_stylebio.get(row.get("stylebio"))
		if tag_summary_row:
			row.update({
				"total_tag_no": tag_summary_row.get("TotalTagNo"),
				"first_tag_date": tag_summary_row.get("FirstTagDate"),
				"tag_nos": tag_summary_row.get("TagNos"),
				"total_sold": tag_summary_row.get("TotalSold"),
			})
		else:
			row.update(blank_tag_summary_row)

	return data


def get_conditions(filters=None):
	filters = filters or {}
	conditions = ""

	if filters.get("from_date"):
		conditions += " AND so.order_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND so.order_date <= %(to_date)s"

	return conditions
