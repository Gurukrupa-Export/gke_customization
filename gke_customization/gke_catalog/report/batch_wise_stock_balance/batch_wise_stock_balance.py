# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, get_datetime, today


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		}
	]

	if filters.show_item_name:
		columns.append(
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Data",
				"width": 200,
			}
		)

	columns.extend(
		[
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 200,
			},
			{
				"label": _("Batch No"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"width": 150,
				"options": "Batch",
			},
			{
				"label": _("Expiry Date"),
				"fieldname": "expiry_date",
				"fieldtype": "Date",
				"width": 120,
			},
			{
				"label": _("Balance Qty"),
				"fieldname": "balance_qty",
				"fieldtype": "Float",
				"width": 150,
			},
			{
				"label": _("Rate"),
				"fieldname": "rate",
				"fieldtype": "Currency",
				"width": 150,
			},
			{
				"label": _("Rate Type"),
				"fieldname": "rate_type",
				"fieldtype": "Data",
				"width": 100,
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"width": 150,
			},
		]
	)

	return columns


def get_data(filters):
	batchwise_data = get_batchwise_data_from_stock_ledger(filters)
	batchwise_data = get_batchwise_data_from_serial_batch_bundle(batchwise_data, filters)

	# Collect all unique batch_nos to fetch rates in bulk
	all_batches = list({key[2] for key in batchwise_data})
	batch_rates = get_batch_rates(all_batches)

	# Attach rate, rate_type, and amount to each row
	for key, d in batchwise_data.items():
		item_code = d.item_code
		batch_no = d.batch_no
		rate_info = batch_rates.get((item_code, batch_no)) or batch_rates.get(batch_no)
		if rate_info:
			d.rate = flt(rate_info.get("rate"))
			d.rate_type = rate_info.get("rate_type")
		else:
			d.rate = 0.0
			d.rate_type = ""
		d.amount = flt(d.balance_qty) * flt(d.rate)

	data = parse_batchwise_data(batchwise_data)
	return data


def parse_batchwise_data(batchwise_data):
	data = []
	for key in batchwise_data:
		d = batchwise_data[key]
		if d.balance_qty == 0:
			continue
		data.append(d)
	return data


def get_batch_rates(batches):
	"""
	Returns rate per (item_code, batch_no):
	  - PI rate  if a submitted Purchase Invoice line exists for that batch
	  - PR rate  otherwise
	"""
	batch_rates = {}

	if not batches:
		return batch_rates

	# ── 1. Purchase Invoice rates (higher priority) ──────────────────────────
	pi_data = frappe.db.sql(
		"""
		SELECT
			pii.item_code,
			pii.batch_no,
			pii.rate
		FROM `tabPurchase Invoice Item` pii
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
		WHERE pii.batch_no IN %(batches)s
		  AND pi.docstatus = 1
		ORDER BY pi.posting_date DESC, pi.creation DESC
		""",
		{"batches": tuple(batches)},
		as_dict=True,
	)

	for row in pi_data:
		key = (row.item_code, row.batch_no)
		# Keep only the most-recent PI rate (first row wins due to ORDER BY)
		if key not in batch_rates:
			batch_rates[key] = {"rate": row.rate, "rate_type": "PI Rate"}

	# ── 2. Purchase Receipt rates (fallback) ──────────────────────────────────
	pr_data = frappe.db.sql(
		"""
		SELECT
			pri.item_code,
			pri.batch_no,
			pri.rate
		FROM `tabPurchase Receipt Item` pri
		INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pri.batch_no IN %(batches)s
		  AND pr.docstatus = 1
		ORDER BY pr.posting_date DESC, pr.creation DESC
		""",
		{"batches": tuple(batches)},
		as_dict=True,
	)

	for row in pr_data:
		key = (row.item_code, row.batch_no)
		if key not in batch_rates:
			batch_rates[key] = {"rate": row.rate, "rate_type": "PR Rate"}

	# ── 3. Delivery Note rates (fallback) ──────────────────────────
	dn_data = frappe.db.sql(
		"""
		SELECT
			dni.item_code,
			dni.batch_no,
			dni.rate
		FROM `tabDelivery Note Item` dni
		INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
		WHERE dni.batch_no IN %(batches)s
		  AND dn.docstatus = 1
		ORDER BY dn.posting_date DESC, dn.creation DESC
		""",
		{"batches": tuple(batches)},
		as_dict=True,
	)

	for row in dn_data:
		key = (row.item_code, row.batch_no)

		# Only use DN rate if PI and PR rate are not available
		if key not in batch_rates:
			batch_rates[key] = {"rate": row.rate, "rate_type": "DN Rate"}

	# ── 4. Credit Note rates (fallback) ──────────────────────────
	cn_data = frappe.db.sql(
		"""
		SELECT
			sii.item_code,
			sii.batch_no,
			sii.rate
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE sii.batch_no IN %(batches)s
		AND si.docstatus = 1
		AND si.is_return = 1
		ORDER BY si.posting_date DESC, si.creation DESC
		""",
		{"batches": tuple(batches)},
		as_dict=True,
	)

	for row in cn_data:
		key = (row.item_code, row.batch_no)

		# Only use CN rate if PI, PR and DN rates are not available
		if key not in batch_rates:
			batch_rates[key] = {"rate": row.rate,"rate_type": "CN Rate"}
   	# ── 5. Repack rates (fallback) ──────────────────────────
	repack_data = frappe.db.sql(
		"""
		SELECT
			sed.item_code,
			sed.batch_no,
			sed.basic_rate AS rate
		FROM `tabStock Entry Detail` sed
		INNER JOIN `tabStock Entry` se
			ON se.name = sed.parent
		WHERE sed.batch_no IN %(batches)s
		AND se.docstatus = 1
		AND se.purpose = 'Repack'
		ORDER BY se.posting_date DESC, se.creation DESC
		""",
		{"batches": tuple(batches)},
		as_dict=True,
	)

	for row in repack_data:
		key = (row.item_code, row.batch_no)

		if key not in batch_rates:
			batch_rates[key] = {"rate": row.rate,"rate_type": "Repack Rate"}
	return batch_rates

def get_batchwise_data_from_stock_ledger(filters):
	batchwise_data = frappe._dict({})

	table = frappe.qb.DocType("Stock Ledger Entry")
	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(table)
		.inner_join(batch)
		.on(table.batch_no == batch.name)
		.select(
			table.item_code,
			table.batch_no,
			table.warehouse,
			batch.expiry_date,
			Sum(table.actual_qty).as_("balance_qty"),
		)
		.where(table.is_cancelled == 0)
		.groupby(table.batch_no, table.item_code, table.warehouse)
	)

	query = get_query_based_on_filters(query, batch, table, filters)

	for d in query.run(as_dict=True):
		key = (d.item_code, d.warehouse, d.batch_no)
		batchwise_data.setdefault(key, d)

	return batchwise_data


def get_batchwise_data_from_serial_batch_bundle(batchwise_data, filters):
	table = frappe.qb.DocType("Stock Ledger Entry")
	ch_table = frappe.qb.DocType("Serial and Batch Entry")
	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(table)
		.inner_join(ch_table)
		.on(table.serial_and_batch_bundle == ch_table.parent)
		.inner_join(batch)
		.on(ch_table.batch_no == batch.name)
		.select(
			table.item_code,
			ch_table.batch_no,
			table.warehouse,
			batch.expiry_date,
			Sum(ch_table.qty).as_("balance_qty"),
		)
		.where((table.is_cancelled == 0) & (table.docstatus == 1))
		.groupby(ch_table.batch_no, table.item_code, table.warehouse)
	)

	query = get_query_based_on_filters(query, batch, table, filters)

	for d in query.run(as_dict=True):
		key = (d.item_code, d.warehouse, d.batch_no)
		if key in batchwise_data:
			batchwise_data[key].balance_qty += flt(d.balance_qty)
		else:
			batchwise_data.setdefault(key, d)

	return batchwise_data


def get_query_based_on_filters(query, batch, table, filters):
	if filters.get("item_code"):
		query = query.where(table.item_code == filters.item_code)

	if filters.get("batch_no"):
		query = query.where(batch.name == filters.batch_no)

	if filters.get("company"):
		query = query.where(table.company == filters.company)

	if filters.get("to_date") == today():
		if not filters.get("include_expired_batches"):
			query = query.where((batch.expiry_date >= today()) | (batch.expiry_date.isnull()))

		query = query.where(batch.batch_qty > 0)

	else:
		to_date = get_datetime(str(filters.to_date) + " 23:59:59")
		query = query.where(table.posting_datetime <= to_date)

	if filters.get("warehouse"):
		lft, rgt = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"])
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"lft": (">=", lft), "rgt": ("<=", rgt), "is_group": 0},
			pluck="name",
		)
		query = query.where(table.warehouse.isin(warehouses))

	elif filters.get("warehouse_type"):
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"warehouse_type": filters.warehouse_type, "is_group": 0},
			pluck="name",
		)
		query = query.where(table.warehouse.isin(warehouses))

	if filters.get("show_item_name"):
		query = query.select(batch.item_name)

	return query