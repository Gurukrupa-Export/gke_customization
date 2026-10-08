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
		{"label": _("Invoice No"), "fieldname": "name", "fieldtype": "Link", "options": "Purchase Invoice", "width": 130},
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Entry Date"), "fieldname": "entry_date", "fieldtype": "Date", "width": 100},
		{"label": _("Purchase Type"), "fieldname": "purchase_type", "fieldtype": "Link", "options": "Purchase Type", "width": 120},
		{"label": _("Supplier Code"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 120},
		{"label": _("Supplier"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 150},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
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
		{"label": _("Weight"), "fieldname": "weight", "fieldtype": "Float", "width": 100},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
	]


def get_conditions(filters):
	conditions = ""
	values = {}

	if filters.get("company"):
		conditions += " and pi.company = %(company)s"
		values["company"] = filters.get("company")

	if filters.get("from_date"):
		conditions += " and pi.posting_date >= %(from_date)s"
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions += " and pi.posting_date <= %(to_date)s"
		values["to_date"] = filters.get("to_date")

	if filters.get("supplier"):
		conditions += " and pi.supplier = %(supplier)s"
		values["supplier"] = filters.get("supplier")

	if filters.get("purchase_type"):
		conditions += " and pi.purchase_type = %(purchase_type)s"
		values["purchase_type"] = filters.get("purchase_type")

	if filters.get("item_code"):
		conditions += " and pii.item_code = %(item_code)s"
		values["item_code"] = filters.get("item_code")

	if filters.get("invoice_no"):
		conditions += " and pi.name = %(invoice_no)s"
		values["invoice_no"] = filters.get("invoice_no")

	return conditions, values


SUBCONTRACTING_ITEM_GROUP = "Subcontracting"
MATERIAL_ITEM_GROUP_ROOT = "Raw Material"

# Purchase Invoice lines are never linked to a BOM (there's nothing to
# explode into components the way Sales Invoice lines are) - the line
# itself already IS one material purchase, so the Item Group tells us
# what bucket it belongs to.
MATERIAL_GROUP_MAP = {
	"Metal - V": "Metal",
	"Alloy": "Metal",
	"Diamond - V": "Diamond",
	"Gemstone - V": "Gemstone",
	"Finding - V": "Finding",
	"Other Material - V": "Other",
	SUBCONTRACTING_ITEM_GROUP: "Subcontracting",
}


def get_material_item_groups():
	"""
	Resolve every Item Group under "Raw Material" (Alloy, Diamond - V,
	Finding - V, Gemstone - V, Metal - V, Other Material - V, ...), plus the
	"Subcontracting" group, so the report only pulls jewellery material and
	job-work purchase lines and not unrelated expense purchases (Utility
	Expense, Dine & Stay Expense, Office Supplies, etc).

	Walked via parent_item_group rather than the lft/rgt nested set values,
	since the nested set values on this site are stale.
	"""
	groups = frappe.get_all("Item Group", fields=["name", "parent_item_group"])
	children_map = {}
	for group in groups:
		children_map.setdefault(group.parent_item_group, []).append(group.name)

	resolved = set()
	queue = [MATERIAL_ITEM_GROUP_ROOT]
	while queue:
		current = queue.pop()
		if current in resolved:
			continue
		resolved.add(current)
		queue.extend(children_map.get(current, []))

	resolved.add(SUBCONTRACTING_ITEM_GROUP)
	return resolved


def get_raw_data(filters):
	conditions, values = get_conditions(filters)

	query = """
		select
			pi.name as name,
			pi.posting_date as posting_date,
			date(pi.creation) as entry_date,
			pi.purchase_type as purchase_type,
			pi.supplier as supplier,
			pi.supplier_name as supplier_name,
			pi.due_date as due_date,
			pii.item_code as item_code,
			pii.item_name as item_name,
			i.item_group as item_group,

			pii.qty as qty,
			pii.stock_uom as uom,
			pii.rate as rate,
			pii.net_rate as net_rate,
			pii.net_amount as net_amount,
			pi.base_grand_total as grand_total,
			pi.base_net_total as net_total,
			pi.base_rounded_total as rounded_total,
			pi.base_rounding_adjustment as rounding_adjustment,
			pi.base_total_taxes_and_charges as total_taxes_and_charges,

			iva.metal_colour as metal_colour,
			iva.metal_purity as metal_purity,
			iva.stone_shape as stone_shape,
			iva.diamond_grade as diamond_grade,
			iva.diamond_sieve_size as diamond_sieve_size,
			iva.gemstone_quality as gemstone_quality,
			iva.gemstone_size as gemstone_size,
			iva.finding_category as finding_category,
			iva.finding_size as finding_size
		from `tabPurchase Invoice` pi
		right join `tabPurchase Invoice Item` pii
			on pi.name = pii.parent
		Join
		`tabItem` i
			on pii.item_code = i.name
		left join (
			select
				parent,
				max(case when attribute like %(metal_colour_pattern)s then attribute_value end) as metal_colour,
				max(case when attribute = 'Metal Purity' then attribute_value end) as metal_purity,
				max(case when attribute = 'Stone Shape' then attribute_value end) as stone_shape,
				max(case when attribute = 'Diamond Grade' then attribute_value end) as diamond_grade,
				max(case when attribute = 'Diamond Sieve Size' then attribute_value end) as diamond_sieve_size,
				max(case when attribute = 'Gemstone Quality' then attribute_value end) as gemstone_quality,
				max(case when attribute = 'Gemstone Size' then attribute_value end) as gemstone_size,
				max(case when attribute = 'Finding Category' then attribute_value end) as finding_category,
				max(case when attribute = 'Finding Size' then attribute_value end) as finding_size
			from `tabItem Variant Attribute`
			group by parent
		) iva on iva.parent = pii.item_code
		where pi.docstatus = 1 and i.item_group in %(material_item_groups)s {conditions}

		order by pi.posting_date desc
	""".format(conditions=conditions)

	values["metal_colour_pattern"] = "%Colour%"
	values["material_item_groups"] = tuple(get_material_item_groups())

	return frappe.db.sql(query, values, as_dict=1)


def as_material_row(row):
	"""
	Turn one Purchase Invoice Item row into a material row. Unlike Sales
	Invoice lines, a purchase line already IS the material (Diamond - V,
	Metal - V, Finding - V, Gemstone - V are the item groups themselves),
	so there's no BOM to expand into components - the material type comes
	straight from the Item Group, and Shape/Purity/Size come from the
	Item's own Variant Attributes.
	"""
	material = MATERIAL_GROUP_MAP.get(row.get("item_group"), "")
	new_row = dict(row)
	new_row["material"] = material

	if material == "Subcontracting":
		new_row["shape"] = ""
		new_row["purity"] = ""
		new_row["size"] = ""
		new_row["weight"] = 0
		new_row["rate"] = row.get("net_rate") or 0
		new_row["amount"] = row.get("net_amount") or 0
	elif material == "Diamond":
		new_row["shape"] = row.get("stone_shape") or ""
		new_row["purity"] = row.get("diamond_grade") or ""
		new_row["size"] = row.get("diamond_sieve_size") or ""
		new_row["weight"] = row.get("qty") or 0
		new_row["amount"] = row.get("net_amount") or 0
	elif material == "Gemstone":
		new_row["shape"] = row.get("stone_shape") or ""
		new_row["purity"] = row.get("gemstone_quality") or ""
		new_row["size"] = row.get("gemstone_size") or ""
		new_row["weight"] = row.get("qty") or 0
		new_row["amount"] = row.get("net_amount") or 0
	elif material == "Finding":
		new_row["shape"] = row.get("finding_category") or ""
		new_row["purity"] = row.get("metal_purity") or ""
		new_row["size"] = row.get("finding_size") or ""
		new_row["weight"] = row.get("qty") or 0
		new_row["amount"] = row.get("net_amount") or 0
	elif material == "Metal":
		new_row["shape"] = ""
		new_row["purity"] = row.get("metal_purity") or ""
		new_row["size"] = ""
		new_row["weight"] = row.get("qty") or 0
		new_row["amount"] = row.get("net_amount") or 0
	else:
		new_row["shape"] = ""
		new_row["purity"] = ""
		new_row["size"] = ""
		new_row["weight"] = row.get("qty") or 0
		new_row["amount"] = row.get("net_amount") or 0

	for field in (
		"item_group", "net_rate", "net_amount", "metal_purity", "stone_shape",
		"diamond_grade", "diamond_sieve_size", "gemstone_quality", "gemstone_size",
		"finding_category", "finding_size",
	):
		new_row.pop(field, None)

	return new_row


TOTAL_FIELDS = [
	"grand_total", "net_total", "rounded_total",
	"rounding_adjustment", "total_taxes_and_charges",
]


def get_data(filters):
	"""
	One row per Purchase Invoice Item line (already material-level - see
	as_material_row). Invoice-level totals are only kept on the first line
	of each invoice so a blind column sum in the report doesn't double
	count them across an invoice's other material lines.
	"""
	data = get_raw_data(filters)

	final_rows = []
	invoices_with_totals = set()
	for row in data:
		new_row = as_material_row(row)

		if row.get("name") not in invoices_with_totals:
			invoices_with_totals.add(row.get("name"))
		else:
			for field in TOTAL_FIELDS:
				new_row[field] = 0

		final_rows.append(new_row)

	return final_rows


def get_summary_columns():
	return [
		{"label": _("Invoice No"), "fieldname": "name", "fieldtype": "Link", "options": "Purchase Invoice", "width": 130},
		{"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Purchase Type"), "fieldname": "purchase_type", "fieldtype": "Link", "options": "Purchase Type", "width": 120},
		{"label": _("Supplier Code"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 120},
		{"label": _("Supplier"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 150},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Total Tax"), "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 120},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounded Total"), "fieldname": "rounded_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Rounding Adjustment"), "fieldname": "rounding_adjustment", "fieldtype": "Currency", "width": 140},
		{"label": _("Total Gross Weight"), "fieldname": "total_gross_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Metal Weight"), "fieldname": "total_metal_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Finding Weight"), "fieldname": "total_finding_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Diamond Weight"), "fieldname": "total_diamond_weight", "fieldtype": "Float", "width": 130},
		{"label": _("Total Gemstone Weight"), "fieldname": "total_gemstone_weight", "fieldtype": "Float", "width": 140},
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
		"purchase_type": row.get("purchase_type"),
		"supplier": row.get("supplier"),
		"supplier_name": row.get("supplier_name"),
		"due_date": row.get("due_date"),
		"net_total": row.get("net_total") or 0,
		"total_taxes_and_charges": row.get("total_taxes_and_charges") or 0,
		"grand_total": row.get("grand_total") or 0,
		"rounded_total": row.get("rounded_total") or 0,
		"rounding_adjustment": row.get("rounding_adjustment") or 0,
		"qty": 0,
		"total_gross_weight": 0,
		"total_metal_weight": 0,
		"total_finding_weight": 0,
		"total_diamond_weight": 0,
		"total_gemstone_weight": 0,
		"metal_total": 0,
		"diamond_total": 0,
		"gemstone_total": 0,
		"finding_total": 0,
		"other_total": 0,
		"subcontracting_amount": 0,
	}


def get_summary_data(filters):
	"""
	Invoice no wise summary: one row per invoice, material purchase lines
	rolled up into Metal / Diamond / Gemstone / Finding / Other /
	Subcontracting totals instead of listing them line by line.
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

		material_row = as_material_row(row)
		material = material_row["material"]

		if material == "Subcontracting":
			inv["subcontracting_amount"] += material_row.get("amount") or 0
			continue

		inv["qty"] += row.get("qty") or 0
		amount = material_row.get("amount") or 0
		weight = material_row.get("weight") or 0

		if material == "Metal":
			inv["metal_total"] += amount
			inv["total_metal_weight"] += weight
			inv["total_gross_weight"] += weight
		elif material == "Finding":
			inv["finding_total"] += amount
			inv["total_finding_weight"] += weight
			inv["total_gross_weight"] += weight
		elif material == "Diamond":
			inv["diamond_total"] += amount
			inv["total_diamond_weight"] += weight
			inv["total_gross_weight"] += weight
		elif material == "Gemstone":
			inv["gemstone_total"] += amount
			inv["total_gemstone_weight"] += weight
			inv["total_gross_weight"] += weight
		elif material == "Other":
			inv["other_total"] += amount

	return [summary[name] for name in order]
