# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import json
import time

import frappe
import requests

# The report fetches Jewelex order tally data from a live API on the EC2
# bench instead of connecting to Jewelex directly or reading a cached JSON
# file. So no pyodbc, no per-site config, and no extra setup is needed on the
# live site.
JEWELEX_ORDER_TALLY_API_URL = "http://3.108.219.130:8003/order-tally"

# The API above may occasionally be unreachable -- keep a local copy of the
# last successful fetch here so a transient/permanent network failure
# degrades to stale data instead of a hard error.
JEWELEX_LOCAL_FALLBACK_FILENAME = "jewelex_order_tally_local_fallback.json"
JEWELEX_FETCH_RETRIES = 3
JEWELEX_FETCH_RETRY_DELAY = 2


def execute(filters=None):
	filters = filters or {}
	if frappe.utils.cint(filters.get("compare_mode")):
		return get_compare_columns(), get_compare_data(filters)

	columns = get_columns()
	data = apply_jewelex_filters(get_jewelex_data(filters), filters)
	return columns, data


def apply_jewelex_filters(rows, filters=None):
	filters = filters or {}
	order_no = filters.get("jewelex_order_no")
	batch_no = filters.get("jewelex_batch_no")

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	from_date = frappe.utils.getdate(from_date) if from_date else None
	to_date = frappe.utils.getdate(to_date) if to_date else None

	filtered = []
	for row in rows:
		if order_no and str(row.get("Order_No") or "").strip() != str(order_no).strip():
			continue
		if batch_no and str(row.get("Batch_No") or "").strip() != str(batch_no).strip():
			continue
		if from_date or to_date:
			row_date = row.get("Order_Date")
			if not row_date:
				continue
			row_date = frappe.utils.getdate(row_date)
			if from_date and row_date < from_date:
				continue
			if to_date and row_date > to_date:
				continue
		filtered.append(row)
	return filtered


def get_columns():
	# ERP-side columns will be added in a later pass.
	return [
		{"label": "Batch No", "fieldname": "Batch_No", "fieldtype": "Data", "width": 110},
		{"label": "Category", "fieldname": "Category", "fieldtype": "Data", "width": 100},
		{"label": "Sub Category", "fieldname": "Sub_Category", "fieldtype": "Data", "width": 110},
		{"label": "Setting", "fieldname": "Setting", "fieldtype": "Data", "width": 100},
		{"label": "Style Bio", "fieldname": "StyleBio", "fieldtype": "Data", "width": 100},
		{"label": "Party Code", "fieldname": "Party_Code", "fieldtype": "Data", "width": 100},
		{"label": "Gold Wt", "fieldname": "Gold_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Dia Wt", "fieldname": "Dia_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Metal Type", "fieldname": "Metal_Type", "fieldtype": "Data", "width": 100},
		{"label": "Stone Wt", "fieldname": "Stone_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Other Wt", "fieldname": "Other_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Net Gross Wt", "fieldname": "NetGross_Wt", "fieldtype": "Float", "width": 100},
		{"label": "Current Dept", "fieldname": "Current_Dept", "fieldtype": "Data", "width": 110},
		{"label": "Current Process", "fieldname": "Current_Process", "fieldtype": "Data", "width": 120},
		{"label": "Bulk Order No", "fieldname": "Bulk_Order_No", "fieldtype": "Data", "width": 110},
		{"label": "Order No", "fieldname": "Order_No", "fieldtype": "Data", "width": 110},
		{"label": "Order Date", "fieldname": "Order_Date", "fieldtype": "Date", "width": 100},
		{"label": "Due Date", "fieldname": "Due_date", "fieldtype": "Date", "width": 100},
		{"label": "Order Type", "fieldname": "Order_Type", "fieldtype": "Data", "width": 100},
	]


def _local_fallback_path():
	return frappe.get_site_path("private", "files", JEWELEX_LOCAL_FALLBACK_FILENAME)


def _read_local_fallback():
	path = _local_fallback_path()
	try:
		with open(path) as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return None


def _write_local_fallback(rows):
	with open(_local_fallback_path(), "w") as f:
		json.dump(rows, f)


def get_jewelex_data(filters=None):
	last_error = None
	for attempt in range(1, JEWELEX_FETCH_RETRIES + 1):
		try:
			response = requests.get(JEWELEX_ORDER_TALLY_API_URL, timeout=15)
			response.raise_for_status()
			payload = response.json()

			if not isinstance(payload, dict) or payload.get("status") != "success":
				raise ValueError(f"Unexpected Jewelex API response: {payload!r}")

			rows = payload.get("data")
			if rows is None:
				raise ValueError("Jewelex API response missing 'data' field")

			_write_local_fallback(rows)
			return rows
		except (requests.RequestException, ValueError) as e:
			last_error = e
			if attempt < JEWELEX_FETCH_RETRIES:
				time.sleep(JEWELEX_FETCH_RETRY_DELAY)

	frappe.log_error(
		title="Jewelex order tally API fetch failed",
		message=f"Could not reach {JEWELEX_ORDER_TALLY_API_URL} after {JEWELEX_FETCH_RETRIES} attempts: {last_error}",
	)

	fallback = _read_local_fallback()
	if fallback is not None:
		frappe.msgprint(
			"Could not reach the Jewelex order tally API right now -- showing the last "
			"successfully loaded data instead. It may be out of date.",
			indicator="orange",
			alert=True,
		)
		return fallback

	frappe.throw(
		f"Could not load Jewelex data from the API ({JEWELEX_ORDER_TALLY_API_URL}): {last_error}. "
		"No previously loaded data is available on this site to fall back to."
	)

ERP_COMPARE_QUERY = """
SELECT  pmo.jewelex_order_no AS jewelex_order_no,
        COUNT(DISTINCT pmo.name) AS erp_order_count,
        GROUP_CONCAT(DISTINCT pmo.sales_order SEPARATOR ', ') AS erp_order_no
FROM `tabParent Manufacturing Order` pmo
WHERE EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
      AND mwo.docstatus = 0
)
GROUP BY pmo.jewelex_order_no
"""

ERP_COMPLETE_QUERY = """
SELECT  pmo.jewelex_order_no AS jewelex_order_no,
        COUNT(DISTINCT pmo.name) AS erp_complete_count,
        GROUP_CONCAT(DISTINCT pmo.sales_order SEPARATOR ', ') AS erp_complete_order_no
FROM `tabParent Manufacturing Order` pmo
WHERE EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
)
AND NOT EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
      AND mwo.docstatus != 1
)
GROUP BY pmo.jewelex_order_no
"""


def get_compare_columns():
	return [
		{"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 100},
		{"label": "Order No", "fieldname": "order_no", "fieldtype": "Data", "width": 110},
		{"label": "Jewelex Batch Count", "fieldname": "jewelex_batch_count", "fieldtype": "Int", "width": 140},
		{"label": "ERP Order No", "fieldname": "erp_order_no", "fieldtype": "Data", "width": 160},
		{"label": "ERP Order Count", "fieldname": "erp_order_count", "fieldtype": "Int", "width": 130},
		{"label": "ERP Order Complete", "fieldname": "erp_order_complete", "fieldtype": "Int", "width": 160},
	]


def get_jewelex_compare_data(filters=None):
	# Derived from the same cached rows as the main report, replicating what
	# JEWELEX_COMPARE_QUERY used to compute in SQL (distinct bulk order count
	# per Order_No/Order_Date), so no separate Jewelex query is needed.
	rows = apply_jewelex_filters(get_jewelex_data(), filters)
	batch_sets = {}
	for row in rows:
		key = (row.get("Order_No"), row.get("Order_Date"))
		batch_sets.setdefault(key, set()).add(row.get("Bulk_Order_No"))

	return [
		{"Order_No": order_no, "Order_Date": order_date, "Jewelex_Batch_Count": len(batches)}
		for (order_no, order_date), batches in batch_sets.items()
	]


NOT_FOUND = "Not Found"


def get_compare_data(filters=None):
	jewelex_rows = get_jewelex_compare_data(filters)
	erp_rows = frappe.db.sql(ERP_COMPARE_QUERY, as_dict=True)
	erp_complete_rows = frappe.db.sql(ERP_COMPLETE_QUERY, as_dict=True)

	erp_by_order_no = {row.jewelex_order_no: row for row in erp_rows if row.jewelex_order_no}
	erp_complete_by_order_no = {
		row.jewelex_order_no: row for row in erp_complete_rows if row.jewelex_order_no
	}

	combined = []
	for row in jewelex_rows:
		order_no = row.get("Order_No")
		erp_row = erp_by_order_no.get(order_no)
		erp_complete_row = erp_complete_by_order_no.get(order_no)
		combined.append(
			{
				"order_date": row.get("Order_Date"),
				"order_no": order_no,
				"jewelex_batch_count": row.get("Jewelex_Batch_Count"),
				"erp_order_no": erp_row.erp_order_no if erp_row else NOT_FOUND,
				"erp_order_count": erp_row.erp_order_count if erp_row else NOT_FOUND,
				"erp_order_complete": erp_complete_row.erp_complete_count if erp_complete_row else 0,
			}
		)

	return sorted(
		combined,
		key=lambda r: (r["order_date"] is None, r["order_date"], r["order_no"] or ""),
	)
