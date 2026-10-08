# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	tab_view = filters.get("tab_view") or "Transaction"

	tab_handlers = {
		"Transaction": (get_transaction_columns, get_transaction_data),
		"Serial No Detail": (get_serial_no_detail_columns, get_serial_no_detail_data),
		"Material Detail": (get_material_detail_columns, get_material_detail_data),
		"Serial No Wise Detail": (get_serial_no_wise_detail_columns, get_serial_no_wise_detail_data),
	}

	get_columns_fn, get_data_fn = tab_handlers[tab_view]

	columns = get_columns_fn()
	data = get_data_fn(filters)
	return columns, data


def get_transaction_columns():
	return [
		{
			"label": "Refining ID",
			"fieldname": "refining_id",
			"fieldtype": "Link",
			"options": "Refining Entry",
			"width": 150,
		},
		{
			"label": "Date",
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": "Department",
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"label": "Stock Entry",
			"fieldname": "stock_entry",
			"fieldtype": "Link",
			"options": "Stock Entry",
			"width": 150,
		},
		{
			"label": "Created By",
			"fieldname": "created_by",
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_transaction_data(filters=None):
	filters = filters or {}

	conditions = get_conditions(filters)

	return frappe.db.sql(
		"""
		SELECT
			re.name AS refining_id,
			DATE(re.creation) AS date,
			re.department AS department,
			re.material_transfer_se AS stock_entry,
			re.owner AS created_by
		FROM
			`tabRefining Entry` re
		WHERE
			re.refining_type IN ('Work Order Refining', 'Serial Number Refining')
			{conditions}
		ORDER BY
			re.creation DESC
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)


def get_serial_no_detail_columns():
	return [
		{
			"label": "Refining ID",
			"fieldname": "refining_id",
			"fieldtype": "Link",
			"options": "Refining Entry",
			"width": 150,
		},
		{
			"label": "Serial No",
			"fieldname": "serial_no",
			"fieldtype": "Link",
			"options": "Serial No",
			"width": 150,
		},
		{
			"label": "Design ID",
			"fieldname": "design_id",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": "Pcs",
			"fieldname": "pcs",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": "Gross Weight",
			"fieldname": "gross_weight",
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"label": "Net Weight",
			"fieldname": "net_weight",
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"label": "Pure Weight",
			"fieldname": "pure_weight",
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
	]


def get_serial_no_detail_data(filters=None):
	filters = filters or {}

	conditions = get_conditions(filters)

	return frappe.db.sql(
		"""
		SELECT
			re.name AS refining_id,
			sn.serial_number AS serial_no,
			sn.item_code AS design_id,
			sn.pcs AS pcs,
			sn.gross_weight AS gross_weight,
			sn.net_weight AS net_weight,
			sn.pure_weight AS pure_weight
		FROM
			`tabRefining Serial No Detail` sn
		INNER JOIN
			`tabRefining Entry` re ON re.name = sn.parent
		WHERE
			re.refining_type IN ('Work Order Refining', 'Serial Number Refining')
			{conditions}
		ORDER BY
			re.creation DESC, sn.idx
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)


def get_material_detail_columns():
	return [
		{
			"label": "Item Code",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": "Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 150,
		},
		{
			"label": "UOM",
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"label": "Total Qty",
			"fieldname": "total_qty",
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
	]


def get_material_detail_data(filters=None):
	filters = filters or {}

	conditions = get_conditions(filters)

	return frappe.db.sql(
		"""
		SELECT
			mi.item_code AS item_code,
			mi.item_group AS item_group,
			mi.uom AS uom,
			SUM(mi.qty) AS total_qty
		FROM
			`tabRefining Material Line` mi
		INNER JOIN
			`tabRefining Entry` re ON re.name = mi.parent
		WHERE
			re.refining_type IN ('Work Order Refining', 'Serial Number Refining')
			AND mi.source_type != 'Serial Number'
			AND (
				mi.item_group LIKE '%%Metal%%'
				OR mi.item_group LIKE '%%Diamond%%'
				OR mi.item_group LIKE '%%Gemstone%%'
				OR mi.item_group LIKE '%%Other%%'
				OR mi.item_group LIKE '%%Finding%%'
				OR mi.item_group IS NULL
				OR mi.item_group = ''
			)
			{conditions}
		GROUP BY
			mi.item_code, mi.item_group, mi.uom
		ORDER BY
			mi.item_code
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)


def get_serial_no_wise_detail_columns():
	return []


def get_serial_no_wise_detail_data(filters=None):
	return []


def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"):
		conditions += " AND DATE(re.creation) >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND DATE(re.creation) <= %(to_date)s"

	if filters.get("department"):
		conditions += " AND re.department = %(department)s"

	if filters.get("refining_id"):
		conditions += " AND re.name = %(refining_id)s"

	if filters.get("status"):
		conditions += " AND re.status = %(status)s"

	return conditions
