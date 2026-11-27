# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from concurrent.futures import ThreadPoolExecutor

import frappe
import requests

JWELEX_API_BASE_URL = "http://3.108.219.130:8003"


def _get_pd_to_prod_data():
	return _call_jwelex_api(f"{JWELEX_API_BASE_URL}/pd-to-prod")


def _get_pd_to_prod_tag_summary():
	return _call_jwelex_api(f"{JWELEX_API_BASE_URL}/pd-to-prod-tag-summary")


def _fetch_json(url):
	"""Plain HTTP fetch with no `frappe.*` calls, so it is safe to run in a worker
	thread (frappe.local is not available there). Returns (data, error)."""
	try:
		response = requests.get(url, timeout=180)
		response.raise_for_status()
		return response.json().get("data"), None
	except requests.RequestException:
		return None, url


def _call_jwelex_api(url):
	data, failed_url = _fetch_json(url)
	if failed_url:
		frappe.log_error(
			title="PD to Prod Jwelex API call failed",
			message=f"Failed to fetch {failed_url}",
		)
		frappe.throw(f"Failed to fetch data from Jwelex API at {failed_url}")
	return data


def _call_jwelex_apis_parallel(*urls):
	"""Fetch several Jwelex endpoints concurrently (total time = slowest call
	instead of the sum). Errors are logged/raised here in the main thread."""
	with ThreadPoolExecutor(max_workers=len(urls)) as pool:
		results = list(pool.map(_fetch_json, urls))
	for _data, failed_url in results:
		if failed_url:
			frappe.log_error(
				title="PD to Prod Jwelex API call failed",
				message=f"Failed to fetch {failed_url}",
			)
			frappe.throw(f"Failed to fetch data from Jwelex API at {failed_url}")
	return [data for data, _ in results]


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
			"label": "Setting (ERP)",
			"fieldname": "setting_type",
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
			"label": "Customer Name",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 150,
			"hidden": 1,
		},
		{
			"label": "Sketch Order No",
			"fieldname": "sketch_order_no",
			"fieldtype": "Link",
			"options": "Sketch Order",
			"width": 150,
		},
		{
			"label": "Order Type",
			"fieldname": "order_type",
			"fieldtype": "Data",
			"width": 100,
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
			"label": "Setting (Jwelex)",
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
	conditions = get_conditions(filters)

	# `tabOrder.design_id` has no index, so joining `tabOrder` inside this query
	# forced a full table scan per Sketch Order row (~75s+). The Sketch Order /
	# Item part is cheap, so it is queried alone; `tabOrder` is read once and
	# matched in Python below (same LEFT JOIN semantics, one scan instead of many).
	query = """
		SELECT
			fsac.item                AS item_code,
			so.customer_code         AS so_customer,
			so.name                  AS sketch_order_no,
			so.order_type            AS order_type,
			it.variant_of            AS variant_of,
			it.item_category         AS item_category,
			it.setting_type          AS setting_type,
			so.order_date            AS sketch_order_date,
			it.stylebio              AS stylebio
		FROM `tabSketch Order` so
		INNER JOIN `tabFinal Sketch Approval CMO` fsac
			ON fsac.parent = so.name
			AND fsac.parenttype = 'Sketch Order'
			AND fsac.parentfield = 'final_sketch_approval_cmo'
		LEFT JOIN `tabItem` it
			ON it.name = fsac.item
		WHERE fsac.item IS NOT NULL
			AND TRIM(fsac.item) != ''
			{conditions}

		UNION ALL

		SELECT
			so.item_code             AS item_code,
			so.customer_code         AS so_customer,
			so.name                  AS sketch_order_no,
			so.order_type            AS order_type,
			it.variant_of            AS variant_of,
			it.item_category         AS item_category,
			it.setting_type          AS setting_type,
			so.order_date            AS sketch_order_date,
			it.stylebio              AS stylebio
		FROM `tabSketch Order` so
		LEFT JOIN `tabItem` it
			ON it.name = so.item_code
		WHERE so.item_code IS NOT NULL
			AND TRIM(so.item_code) != ''
			AND NOT EXISTS (
				SELECT 1 FROM `tabFinal Sketch Approval CMO` fsac2
				WHERE fsac2.parent = so.name
					AND fsac2.parenttype = 'Sketch Order'
					AND fsac2.parentfield = 'final_sketch_approval_cmo'
					AND fsac2.item = so.item_code
			)
			{conditions}
	""".format(conditions=conditions)

	base_rows = frappe.db.sql(query, filters, as_dict=True)

	item_codes = list({r["item_code"] for r in base_rows if r.get("item_code")})
	orders_by_design = {}
	if item_codes:
		# One pass over tabOrder for all designs at once.
		for o in frappe.db.sql(
			"""
			SELECT name, design_id, order_date, customer_code
			FROM `tabOrder`
			WHERE design_id IN %(codes)s
			""",
			{"codes": tuple(item_codes)},
			as_dict=True,
		):
			orders_by_design.setdefault((o["design_id"] or "").lower(), []).append(o)

	# Rebuild the old (LEFT JOIN tabOrder + UNION) rows: one row per
	# (sketch order, item, CAD order), duplicates removed like UNION did.
	data, seen = [], set()
	for r in base_rows:
		orders = orders_by_design.get((r["item_code"] or "").lower()) or [None]
		for o in orders:
			if r["so_customer"] is not None:
				customer = r["so_customer"]
			else:
				customer = o["customer_code"] if o else None
			row = {
				"item_code": r["item_code"],
				"customer": customer,
				"sketch_order_no": r["sketch_order_no"],
				"order_type": r["order_type"],
				"variant_of": r["variant_of"],
				"item_category": r["item_category"],
				"setting_type": r["setting_type"],
				"cad_order_no": o["name"] if o else None,
				"sketch_order_date": r["sketch_order_date"],
				"cad_order_date": o["order_date"] if o else None,
				"stylebio": r["stylebio"],
			}
			key = tuple(row.values())
			if key in seen:
				continue
			seen.add(key)
			data.append(row)
	data.sort(key=lambda x: x["sketch_order_no"] or "")

	# Customer names are looked up once here instead of joining `tabCustomer`
	# inside the (already heavy) query above.
	customer_codes = list({row["customer"] for row in data if row.get("customer")})
	customer_name_by_code = {}
	if customer_codes:
		customer_name_by_code = {
			c.name: c.customer_name
			for c in frappe.db.get_all(
				"Customer",
				filters={"name": ["in", customer_codes]},
				fields=["name", "customer_name"],
			)
		}
	for row in data:
		row["customer_name"] = customer_name_by_code.get(row.get("customer"))

	jwelex_data, tag_summary_data = _call_jwelex_apis_parallel(
		f"{JWELEX_API_BASE_URL}/pd-to-prod",
		f"{JWELEX_API_BASE_URL}/pd-to-prod-tag-summary",
	)
	jwelex_data = jwelex_data or []
	tag_summary_data = tag_summary_data or []
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
