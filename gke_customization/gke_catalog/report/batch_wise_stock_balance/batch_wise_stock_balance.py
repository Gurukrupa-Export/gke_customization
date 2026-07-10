# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
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
				"fieldtype": "Link",
				"options": "Item",
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
				"label": _("Source Document Type"),
				"fieldname": "reference_doctype",
				"fieldtype": "Data",
				"width": 180,	
			},
			{
				"label": _("Source Document Name"),
				"fieldname": "reference_name",
				"fieldtype": "Dynamic Link",
				"options": "reference_doctype",
				"width": 200,
			},
			{
				"label": _("Expiry Date"),
				"fieldname": "expiry_date",
				"fieldtype": "Date",
				"width": 120,
			},
			{	"label": _("Balance Qty"), 
    			"fieldname": "balance_qty", 
       			"fieldtype": "Float", 
          		"width": 150
            },
			{
				"label": _("Rate"),
				"fieldname": "incoming_rate",
				"fieldtype": "Currency",
				"width": 120,
        	},
			{
				"label": _("Value"),
				"fieldname": "value",
				"fieldtype": "Currency",
				"width": 150,
			},
			{
				"label": _("Invoice Done"),
				"fieldname": "invoice_done",
				"fieldtype": "Check",
				"width": 100,
			},
		]
	)

	return columns


def get_data(filters):
	data = []
	batchwise_data = get_batchwise_data_from_stock_ledger(filters)
	batchwise_data = get_batchwise_data_from_serial_batch_bundle(batchwise_data, filters)

	data = parse_batchwise_data(batchwise_data)

	return data


def parse_batchwise_data(batchwise_data):
	data = []
	for key in batchwise_data:
		d = batchwise_data[key]

		if flt(d.balance_qty) == 0:
			continue

		d.value = flt(d.balance_qty) * flt(d.get("incoming_rate", 0))

		data.append(d)

	invoiced_batches = get_invoiced_batches({d.batch_no for d in data if d.batch_no})
	for d in data:
		d.invoice_done = 1 if d.batch_no in invoiced_batches else 0

	return data


def get_invoiced_batches(batch_nos):
	if not batch_nos:
		return set()

	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(pi_item)
		.inner_join(pi)
		.on(pi_item.parent == pi.name)
		.select(pi_item.batch_no)
		.distinct()
		.where((pi.docstatus == 1) & (pi_item.batch_no.isin(list(batch_nos))))
	)

	return {d.batch_no for d in query.run(as_dict=True)}


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
			batch.reference_doctype,
    		batch.reference_name,
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
			batch.reference_doctype,
    		batch.reference_name,
			ch_table.incoming_rate.as_("incoming_rate"),
			Sum(ch_table.qty).as_("balance_qty"),
		)
		.where((table.is_cancelled == 0) & (table.docstatus == 1))
		.groupby(ch_table.batch_no, table.item_code, ch_table.warehouse,ch_table.incoming_rate)
	)

	query = get_query_based_on_filters(query, batch, table, filters)

	for d in query.run(as_dict=True):
		key = (d.item_code, d.warehouse, d.batch_no)

		if key in batchwise_data:
			batchwise_data[key].balance_qty += flt(d.balance_qty)
			batchwise_data[key].incoming_rate = d.incoming_rate
		else:
			batchwise_data.setdefault(key, d)

	return batchwise_data

def _as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            import json
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [v.strip() for v in value.split(",") if v.strip()]
    return [value]

def get_query_based_on_filters(query, batch, table, filters):
	item_codes = _as_list(getattr(filters, "item_code", None))
	if item_codes:
		query = query.where(table.item_code.isin(item_codes))

	if filters.batch_no:
		query = query.where(batch.name == filters.batch_no)

	if filters.to_date == today():
		if not filters.include_expired_batches:
			query = query.where(
				(batch.expiry_date >= today()) | (batch.expiry_date.isnull())
			)

		query = query.where(batch.batch_qty > 0)

	else:
		to_date = get_datetime(str(filters.to_date) + " 23:59:59")
		query = query.where(table.posting_datetime <= to_date)

	warehouses_selected = _as_list(getattr(filters, "warehouse", None))
	if warehouses_selected:
		query = query.where(table.warehouse.isin(warehouses_selected))

		warehouses = frappe.get_all(
			"Warehouse",
			filters={
				"lft": (">=", lft),
				"rgt": ("<=", rgt),
				"is_group": 0,
			},
			pluck="name",
		)

		query = query.where(table.warehouse.isin(warehouses))

	elif filters.warehouse_type:
		warehouses = frappe.get_all(
			"Warehouse",
			filters={
				"warehouse_type": filters.warehouse_type,
				"is_group": 0,
			},
			pluck="name",
		)

		query = query.where(table.warehouse.isin(warehouses))

	# Company Filter
	if filters.company:
		company_warehouses = frappe.get_all(
			"Warehouse",
			filters={
				"company": filters.company,
				"is_group": 0,
			},
			pluck="name",
		)

		query = query.where(table.warehouse.isin(company_warehouses))

	if filters.show_item_name:
		query = query.select(batch.item_name)

	return query