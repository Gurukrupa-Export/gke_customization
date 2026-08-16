# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	if filters.get("summary_view"):
		columns = get_summary_columns()
		data = get_summary_data(filters)
	else:
		columns = get_columns()
		data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Invoice No"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Entry Date"), "fieldname": "entry_date", "fieldtype": "Date", "width": 100},
		{"label": _("Customer Code"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("Item Category"), "fieldname": "item_category", "fieldtype": "Data", "width": 100},
		{"label": _("Sub Category"), "fieldname": "subcategory", "fieldtype": "Data", "width": 100},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 120},
		{"label": _("BOM No"), "fieldname": "bom_no", "fieldtype": "Link", "options": "BOM", "width": 120},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		
		{"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Taxes and Charges"), "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 160},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounded Total"), "fieldname": "rounded_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounding Adjustment"), "fieldname": "rounding_adjustment", "fieldtype": "Currency", "width": 140},
		
		{"label": _("Material"), "fieldname": "material", "fieldtype": "Data", "width": 100},
		{"label": _("Metal Colour"), "fieldname": "metal_colour", "fieldtype": "Data", "width": 100},
		{"label": _("Shape"), "fieldname": "shape", "fieldtype": "Data", "width": 100},
		{"label": _("KT/Quality"), "fieldname": "purity", "fieldtype": "Data", "width": 120},
		{"label": _("Size"), "fieldname": "size", "fieldtype": "Data", "width": 100},
		{"label": _("Code"), "fieldname": "code", "fieldtype": "Data", "width": 100},
		{"label": _("Pcs"), "fieldname": "pcs", "fieldtype": "Int", "width": 80},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Making Rate"), "fieldname": "making_rate", "fieldtype": "Currency", "width": 110},
		{"label": _("Making Amount"), "fieldname": "making_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Weight"), "fieldname": "weight", "fieldtype": "Float", "width": 100},
		{"label": _("Pure Weight"), "fieldname": "pure_weight", "fieldtype": "Float", "width": 110},
		{"label": _("Metal Ratio"), "fieldname": "metal_ratio", "fieldtype": "Float", "width": 100},
		{"label": _("Certificate Amount"), "fieldname": "custom_certification_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Hallmarking Amount"), "fieldname": "custom_hallmarking_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Wastage Amount"), "fieldname": "wastage_amount", "fieldtype": "Currency", "width": 120},
	]


def get_conditions(filters):
	conditions = ""
	values = {}

	if filters.get("company"):
		conditions += " and si.company = %(company)s"
		values["company"] = filters.get("company")

	if filters.get("from_date"):
		conditions += " and si.posting_date >= %(from_date)s"
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions += " and si.posting_date <= %(to_date)s"
		values["to_date"] = filters.get("to_date")

	if filters.get("customer"):
		conditions += " and si.customer = %(customer)s"
		values["customer"] = filters.get("customer")

	if filters.get("item_code"):
		conditions += " and sii.item_code = %(item_code)s"
		values["item_code"] = filters.get("item_code")

	if filters.get("invoice_no"):
		conditions += " and si.name = %(invoice_no)s"
		values["invoice_no"] = filters.get("invoice_no")

	if filters.get("sales_type"):
		conditions += " and si.sales_type = %(sales_type)s"
		values["sales_type"] = filters.get("sales_type")

	if filters.get("invoice_type") == "Sales Invoice":
		conditions += " and si.is_return = 0"
	elif filters.get("invoice_type") == "Credit Note":
		conditions += " and si.is_return = 1"

	return conditions, values


def get_raw_data(filters):
	conditions, values = get_conditions(filters)

	query = """
		select
			si.name as name,
			si.posting_date as posting_date,
			date(si.creation) as entry_date,
			si.customer as customer,
			si.customer_name as customer_name,
			si.due_date as due_date,
			sii.item_code as item_code,
			sii.item_name as item_name,
			sii.item_category as item_category,
			coalesce(sii.custom_item_sub_category, i.subcategory) as subcategory,
			sii.serial_no as serial_no,
			sii.serial_and_batch_bundle as serial_and_batch_bundle,
			sii.bom as bom_no,

			sii.qty as qty,
			sii.stock_uom as uom,
			sii.net_rate as net_rate,
			sii.net_amount as net_amount,
			si.base_grand_total as grand_total,
			si.base_net_total as net_total,
			si.base_rounded_total as rounded_total,
			si.base_rounding_adjustment as rounding_adjustment,
			si.base_total_taxes_and_charges as total_taxes_and_charges,
			iva.metal_colour as metal_colour,
			sii.custom_certification_amount as custom_certification_amount,
			sii.custom_hallmarking_amount as custom_hallmarking_amount,
			sii.metal_amount as metal_amount,
			sii.diamond_amount as diamond_amount,
			sii.gemstone_amount as gemstone_amount,
			sii.finding_amount as finding_amount,
			sii.wastage_amount as wastage_amount
		from `tabSales Invoice` si
		right join `tabSales Invoice Item` sii
			on si.name = sii.parent
		Join
		`tabItem` i
			on sii.item_code = i.name
		left join (
			select
				parent,
				max(case when attribute like %(metal_colour_pattern)s then attribute_value end) as metal_colour
			from `tabItem Variant Attribute`
			group by parent
		) iva on iva.parent = sii.item_code
		where si.docstatus = 1 {conditions}

		order by si.posting_date desc
	""".format(conditions=conditions)

	values["metal_colour_pattern"] = "%Colour%"

	return frappe.db.sql(query, values, as_dict=1)


def get_data(filters):
	data = get_raw_data(filters)
	rows = split_by_serial_no(data)
	return expand_with_material_details(rows)


def split_by_serial_no(data):
	bundles = {row.serial_and_batch_bundle for row in data if row.serial_and_batch_bundle}
	bundle_serials = {}
	if bundles:
		for entry in frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": ("in", list(bundles)), "serial_no": ("is", "set")},
			fields=["parent", "serial_no"],
		):
			bundle_serials.setdefault(entry.parent, []).append(entry.serial_no)

	rows = []
	for row in data:
		serial_nos = []
		if row.serial_no:
			serial_nos = [s.strip() for s in row.serial_no.split("\n") if s.strip()]
		elif row.serial_and_batch_bundle:
			serial_nos = bundle_serials.get(row.serial_and_batch_bundle, [])

		row.pop("serial_and_batch_bundle", None)

		if not serial_nos:
			row.serial_no = None
			rows.append(row)
			continue

		for serial_no in serial_nos:
			new_row = row.copy()
			new_row.serial_no = serial_no
			rows.append(new_row)

	return rows


def get_bom_material_details(bom_nos):
	"""
	Fetch Metal / Diamond / Finding / Gemstone / Other component rows for the
	given BOMs, in the same shape Finish Good Item Details uses.
	"""
	if not bom_nos:
		return {}

	sql = """
	SELECT * FROM (

		SELECT
			bom.name AS bom_no,
			'Metal' AS material,
			'' AS shape,
			bmd.metal_purity AS purity,
			'' AS size,
			'' AS code,
			1 AS pcs,
			IFNULL(bmd.quantity,0) AS weight,
			ROUND(IFNULL(bmd.quantity,0) * (IFNULL(bmd.metal_purity,0) / 100), 3) AS pure_weight,
			ROUND(IFNULL(bmd.metal_purity,0) / 100, 3) AS metal_ratio,
			IFNULL(bmd.rate,0) AS rate,
			IFNULL(bmd.amount,0) AS amount,
			IFNULL(bmd.making_rate,0) AS making_rate,
			IFNULL(bmd.making_amount,0) AS making_amount,
			1 AS sort_order
		FROM `tabBOM` bom
		INNER JOIN `tabBOM Metal Detail` bmd ON bmd.parent = bom.name
		WHERE bom.name IN %(bom_nos)s

		UNION ALL

		SELECT
			bom.name,
			'Diamond',
			IFNULL(bdd.stone_shape,''),
			IFNULL(bdd.quality,''),
			IFNULL(bdd.diamond_sieve_size,''),
			'',
			CAST(IFNULL(bdd.pcs,0) AS SIGNED),
			IFNULL(bdd.quantity,0),
			ROUND(IFNULL(bdd.quantity,0) / 5, 3),
			0,
			IFNULL(bdd.total_diamond_rate,0),
			IFNULL(bdd.diamond_rate_for_specified_quantity,0),
			0,
			0,
			2
		FROM `tabBOM` bom
		INNER JOIN `tabBOM Diamond Detail` bdd ON bdd.parent = bom.name
		WHERE bom.name IN %(bom_nos)s

		UNION ALL

		SELECT
			bom.name,
			'Finding',
			IFNULL(bfd.finding_type,''),
			IFNULL(bfd.metal_purity,''),
			IFNULL(bfd.finding_size,''),
			IFNULL(bfd.item,''),
			CAST(IFNULL(bfd.qty,0) AS SIGNED),
			IFNULL(bfd.quantity,0),
			ROUND(IFNULL(bfd.quantity,0) * (IFNULL(bfd.metal_purity,0) / 100), 3),
			ROUND(IFNULL(bfd.metal_purity,0) / 100, 3),
			IFNULL(bfd.rate,0),
			IFNULL(bfd.amount,0),
			IFNULL(bfd.making_rate,0),
			IFNULL(bfd.making_amount,0),
			3
		FROM `tabBOM` bom
		INNER JOIN `tabBOM Finding Detail` bfd ON bfd.parent = bom.name
		WHERE bom.name IN %(bom_nos)s

		UNION ALL

		SELECT
			bom.name,
			'Gemstone',
			IFNULL(bgd.stone_shape,''),
			IFNULL(bgd.gemstone_quality,''),
			IFNULL(bgd.gemstone_size,''),
			IFNULL(bgd.gemstone_code,''),
			CAST(IFNULL(bgd.pcs,0) AS SIGNED),
			IFNULL(bgd.quantity,0),
			ROUND(IFNULL(bgd.quantity,0) / 5, 3),
			0,
			IFNULL(bgd.total_gemstone_rate,0),
			IFNULL(bgd.gemstone_rate_for_specified_quantity,0),
			0,
			0,
			4
		FROM `tabBOM` bom
		INNER JOIN `tabBOM Gemstone Detail` bgd ON bgd.parent = bom.name
		WHERE bom.name IN %(bom_nos)s

		UNION ALL

		SELECT
			bom.name,
			'Other',
			'',
			'',
			'',
			IFNULL(bod.item_code,''),
			CAST(IFNULL(bod.qty,0) AS SIGNED),
			IFNULL(bod.quantity,0),
			IFNULL(bod.quantity,0),
			0,
			IFNULL(bod.rate,0),
			IFNULL(bod.amount,0),
			0,
			0,
			5
		FROM `tabBOM` bom
		INNER JOIN `tabBOM Other Detail` bod ON bod.parent = bom.name
		WHERE bom.name IN %(bom_nos)s

	) t
	ORDER BY bom_no, sort_order, shape, size
	"""

	rows = frappe.db.sql(sql, {"bom_nos": tuple(bom_nos)}, as_dict=True)

	material_map = {}
	for row in rows:
		# Skip empty metal rows
		if row["material"] == "Metal" and not row.get("weight") and not row.get("pure_weight"):
			continue
		# Skip empty diamond rows
		if row["material"] == "Diamond" and not row.get("weight") and not row.get("pcs"):
			continue

		material_map.setdefault(row["bom_no"], []).append(row)

	return material_map


INVOICE_LEVEL_FIELDS = [
	"name", "posting_date", "entry_date", "customer", "customer_name", "due_date",
	"item_code", "item_name", "item_category", "subcategory", "serial_no", "bom_no",
	"qty", "uom", "grand_total", "net_total", "rounded_total",
	"rounding_adjustment", "total_taxes_and_charges", "metal_colour",
	"custom_certification_amount", "custom_hallmarking_amount", "metal_amount",
	"diamond_amount", "gemstone_amount", "finding_amount", "wastage_amount",
]

MATERIAL_FIELDS = [
	"material", "shape", "purity", "size", "code", "pcs", "weight", "pure_weight",
	"metal_ratio", "rate", "amount", "making_rate", "making_amount",
]

TOTAL_FIELDS = [
	"grand_total", "net_total", "rounded_total",
	"rounding_adjustment", "total_taxes_and_charges",
]


def expand_with_material_details(rows):
	"""
	Expand each invoice/serial no row into one row per BOM component
	(Metal, Diamond, Finding, Gemstone, Other), the same way Finish Good
	Item Details lists a serial no's components, and blank out the
	repeated invoice-level columns on the follow-up rows.
	"""
	bom_nos = {row.get("bom_no") for row in rows if row.get("bom_no")}
	material_map = get_bom_material_details(bom_nos)

	final_rows = []
	invoices_with_totals = set()
	for row in rows:
		materials = material_map.get(row.get("bom_no")) or []

		is_subcontracting = row.get("item_name") == "Subcontracting Charges"
		keep_totals = False
		if not is_subcontracting and row.get("name") not in invoices_with_totals:
			keep_totals = True
			invoices_with_totals.add(row.get("name"))

		if not materials:
			new_row = dict(row)
			for field in MATERIAL_FIELDS:
				new_row[field] = 0 if field in ("rate", "amount", "making_rate", "making_amount") else ""

			if is_subcontracting:
				new_row["rate"] = row.get("net_rate") or 0
				new_row["amount"] = row.get("net_amount") or 0

			if not keep_totals:
				for field in TOTAL_FIELDS:
					new_row[field] = 0

			new_row.pop("net_rate", None)
			new_row.pop("net_amount", None)
			final_rows.append(new_row)
			continue

		for i, material in enumerate(materials):
			if i == 0:
				new_row = dict(row)
				if not keep_totals:
					for field in TOTAL_FIELDS:
						new_row[field] = 0
			else:
				new_row = {field: "" for field in INVOICE_LEVEL_FIELDS}
				new_row["name"] = row.get("name")
				new_row["serial_no"] = row.get("serial_no")

			try:
				pcs = int(material.get("pcs") or 0)
			except (TypeError, ValueError):
				pcs = 0

			new_row["material"] = material.get("material") or ""
			new_row["shape"] = material.get("shape") or ""
			new_row["purity"] = material.get("purity") or ""
			new_row["size"] = material.get("size") or ""
			new_row["code"] = material.get("code") or ""
			new_row["pcs"] = pcs
			new_row["weight"] = material.get("weight") or 0
			new_row["pure_weight"] = material.get("pure_weight") or 0
			new_row["metal_ratio"] = material.get("metal_ratio") or 0
			new_row["rate"] = material.get("rate") or 0
			new_row["amount"] = material.get("amount") or 0
			new_row["making_rate"] = material.get("making_rate") or 0
			new_row["making_amount"] = material.get("making_amount") or 0

			new_row.pop("net_rate", None)
			new_row.pop("net_amount", None)
			final_rows.append(new_row)

	return final_rows


def get_summary_columns():
	return [
		{"label": _("Invoice No"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Customer Code"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Tax"), "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 120},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounded Total"), "fieldname": "rounded_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounding Adjustment"), "fieldname": "rounding_adjustment", "fieldtype": "Currency", "width": 140},
		{"label": _("Making Amount"), "fieldname": "making_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Gross Weight"), "fieldname": "total_gross_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Metal Weight"), "fieldname": "total_metal_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Finding Weight"), "fieldname": "total_finding_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Diamond Weight"), "fieldname": "total_diamond_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Gemstone Weight"), "fieldname": "total_gemstone_weight", "fieldtype": "Float", "width": 140},
		{"label": _("Certificate Amount"), "fieldname": "custom_certification_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Hallmarking Amount"), "fieldname": "custom_hallmarking_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Wastage Amount"), "fieldname": "wastage_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Metal Total"), "fieldname": "metal_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Diamond Total"), "fieldname": "diamond_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Gemstone Total"), "fieldname": "gemstone_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Finding Total"), "fieldname": "finding_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Other Total"), "fieldname": "other_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Subcontracting Amount"), "fieldname": "subcontracting_amount", "fieldtype": "Currency", "width": 150},
	]


def new_summary_row(row):
	return {
		"name": row.get("name"),
		"posting_date": row.get("posting_date"),
		"customer": row.get("customer"),
		"customer_name": row.get("customer_name"),
		"due_date": row.get("due_date"),
		"net_total": row.get("net_total") or 0,
		"total_taxes_and_charges": row.get("total_taxes_and_charges") or 0,
		"grand_total": row.get("grand_total") or 0,
		"rounded_total": row.get("rounded_total") or 0,
		"rounding_adjustment": row.get("rounding_adjustment") or 0,
		"qty": 0,
		"making_amount": 0,
		"total_gross_weight": 0,
		"total_metal_weight": 0,
		"total_finding_weight": 0,
		"total_diamond_weight": 0,
		"total_gemstone_weight": 0,
		"custom_certification_amount": 0,
		"custom_hallmarking_amount": 0,
		"wastage_amount": 0,
		"metal_total": 0,
		"diamond_total": 0,
		"gemstone_total": 0,
		"finding_total": 0,
		"other_total": 0,
		"subcontracting_amount": 0,
	}


def get_summary_data(filters):
	"""
	Invoice no wise summary: one row per invoice, materials rolled up into
	Metal / Diamond / Gemstone / Finding / Other / Subcontracting totals
	instead of listing them material wise.
	"""
	data = get_raw_data(filters)

	summary = {}
	order = []

	for row in data:
		name = row.get("name")
		inv = summary.get(name)
		if not inv:
			inv = new_summary_row(row)
			summary[name] = inv
			order.append(name)

		inv["custom_certification_amount"] += row.get("custom_certification_amount") or 0
		inv["custom_hallmarking_amount"] += row.get("custom_hallmarking_amount") or 0
		inv["wastage_amount"] += row.get("wastage_amount") or 0

		if row.get("item_name") == "Subcontracting Charges":
			inv["subcontracting_amount"] += row.get("net_amount") or 0
			continue

		inv["qty"] += row.get("qty") or 0

	rows = split_by_serial_no(data)
	bom_nos = {row.get("bom_no") for row in rows if row.get("bom_no")}
	material_map = get_bom_material_details(bom_nos)

	for row in rows:
		if row.get("item_name") == "Subcontracting Charges":
			continue

		inv = summary.get(row.get("name"))
		if not inv:
			continue

		for material in material_map.get(row.get("bom_no")) or []:
			amount = material.get("amount") or 0
			mat_type = material.get("material")

			inv["making_amount"] += material.get("making_amount") or 0

			if mat_type == "Metal":
				inv["metal_total"] += amount
				inv["total_metal_weight"] += material.get("weight") or 0
				inv["total_gross_weight"] += material.get("weight") or 0
			elif mat_type == "Finding":
				inv["finding_total"] += amount
				inv["total_finding_weight"] += material.get("weight") or 0
				inv["total_gross_weight"] += material.get("weight") or 0
			elif mat_type == "Diamond":
				inv["diamond_total"] += amount
				inv["total_diamond_weight"] += material.get("pure_weight") or 0
				inv["total_gross_weight"] += material.get("pure_weight") or 0
			elif mat_type == "Gemstone":
				inv["gemstone_total"] += amount
				inv["total_gemstone_weight"] += material.get("pure_weight") or 0
				inv["total_gross_weight"] += material.get("pure_weight") or 0
			elif mat_type == "Other":
				inv["other_total"] += amount

	return [summary[name] for name in order]
