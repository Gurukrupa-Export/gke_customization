# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
import datetime
from datetime import date


SYSTEM_FIELDS = {
	"name", "parent", "parentfield", "parenttype",
	"doctype", "idx", "owner", "creation",
	"modified", "modified_by", "docstatus"
}


def copy_row(new_bom, table, src):
	"""Raw-copy one child row's non-system fields onto a fresh row in new_bom[table]."""
	dest = new_bom.append(table, {})
	for key, value in src.as_dict().items():
		if key not in SYSTEM_FIELDS:
			dest.set(key, value)
	return dest


def build_metal_detail(doc, new_bom):
	new_bom.set("metal_detail", [])
	for src in doc.metal_detail:
		dest = copy_row(new_bom, "metal_detail", src)

		customer_metal_purity = frappe.db.get_value(
				"Metal Criteria",
				{"parent": doc.customer, "metal_type": dest.metal_type, "metal_touch": dest.metal_touch},
				"metal_purity",
			)
		if doc.credit_note_rate_type=='Current Rate':
			dest.rate=float(doc.gold_rate or 0) * float(customer_metal_purity) /100
		if doc.making_charges=='Without':
			dest.making_rate=0
		elif doc.making_charges=='Half':
			dest.making_rate=dest.making_rate/2
		elif doc.making_charges=='Custom':
			dest.making_rate=doc.custom_making_charges
		if doc.wastage_charges=='Without':
			dest.wastage_amount=0
		elif doc.wastage_charges=='Half':
			dest.wastage_amount=dest.wastage_amount/2
		elif doc.wastage_charges=='Custom':
			dest.wastage_amount=doc.custom_wastage_charges
		dest.customer_metal_purity=customer_metal_purity
		dest.customer_metal_purity=customer_metal_purity
		dest.amount = dest.quantity * dest.rate
		dest.making_amount = dest.making_rate*dest.quantity


def build_finding_detail(doc, new_bom):
	new_bom.set("finding_detail", [])
	for src in doc.finding_detail:
		dest = copy_row(new_bom, "finding_detail", src)

		customer_metal_purity = frappe.db.get_value(
				"Metal Criteria",
				{"parent": doc.customer, "metal_type": dest.metal_type, "metal_touch": dest.metal_touch},
				"metal_purity",
			)
		if doc.credit_note_rate_type=='Current Rate':
			dest.rate=float(doc.gold_rate or 0) * float(customer_metal_purity)/100
		if doc.making_charges=='Without':
			dest.making_rate=0
		elif doc.making_charges=='Half':
			dest.making_rate=dest.making_rate/2
		elif doc.making_charges=='Custom':
			dest.making_rate=doc.custom_making_charges
		dest.amount = dest.quantity * dest.rate
		dest.making_amount = dest.making_rate*dest.quantity



def get_current_diamond_rate(doc, dest):
	"""Look up rate/handling for one diamond row from the customer's Diamond Price List."""
	price_list_type = frappe.db.get_value(
		"Diamond Price List Table",
		{"parent": doc.customer, "diamond_shape": dest.stone_shape},
		"diamond_price_list",
	)
	if not price_list_type:
		return 0, 0

	common_filters = {
		"price_list": "Standard Selling",
		"price_list_type": price_list_type,
		"customer": doc.customer,
		"diamond_type": dest.diamond_type,
		"stone_shape": dest.stone_shape,
		"diamond_quality": dest.quality,
	}
	fields = [
		"rate", "outright_handling_charges_rate",
		"outright_handling_charges_in_percentage",
		"outwork_handling_charges_rate",
		"outwork_handling_charges_in_percentage",
	]

	if price_list_type == "Sieve Size Range":
		latest = frappe.db.get_value(
			"Diamond Price List",
			{**common_filters, "sieve_size_range": dest.sieve_size_range},
			fields, as_dict=True,
		)
	elif price_list_type == "Weight (in cts)":
		weight_per_pcs = dest.quantity / dest.pcs if dest.pcs else dest.quantity
		conds = " AND ".join(f"{k} = %s" for k in common_filters)
		rows = frappe.db.sql(
			f"""SELECT {", ".join(fields)} FROM `tabDiamond Price List`
				WHERE {conds} AND %s BETWEEN from_weight AND to_weight LIMIT 1""",
			list(common_filters.values()) + [weight_per_pcs], as_dict=True,
		)
		latest = rows[0] if rows else None
	elif price_list_type == "Size (in mm)":
		latest = frappe.db.get_value(
			"Diamond Price List",
			{**common_filters, "diamond_size_in_mm": dest.diamond_sieve_size},
			fields, as_dict=True,
		)
	else:
		latest = None

	if not latest:
		return 0, 0

	base_rate = latest.get("rate", 0)
	out_rate  = latest.get("outright_handling_charges_rate", 0)
	out_pct   = latest.get("outright_handling_charges_in_percentage", 0)
	work_rate = latest.get("outwork_handling_charges_rate", 0)
	work_pct  = latest.get("outwork_handling_charges_in_percentage", 0)
	is_cust   = dest.is_customer_item

	total_diamond_rate = 0 if is_cust else round(base_rate, 2)
	handling_rate = (
		work_rate or (base_rate * (work_pct / 100))
		if is_cust
		else out_rate or (base_rate + base_rate * (out_pct / 100)) if out_pct else 0
	)
	return total_diamond_rate, handling_rate


def build_diamond_detail(doc, new_bom):
	new_bom.set("diamond_detail", [])
	for src in doc.diamond_detail:
		dest = copy_row(new_bom, "diamond_detail", src)
		customer_group=frappe.db.get_value('Customer',doc.customer,'customer_group')
		if not(doc.company == "KG GK Jewellers Private Limited" or customer_group == "Internal"):
			if doc.diamond_rate_type == 'Current Rate':
				dest.total_diamond_rate, dest.handling_rate = get_current_diamond_rate(doc, dest)

		dest.diamond_rate_for_specified_quantity=dest.quantity *( dest.total_diamond_rate + dest.handling_rate)
		if doc.handling_charges=='Without':
			dest.handling_rate=0
		elif doc.handling_charges=='Half':
			dest.handling_rate=dest.handling_rate/2
		elif doc.handling_charges=='Custom':
			dest.handling_rate=doc.custom_handling_charges
			# frappe.msgprint(f"poiuyhg{doc.diamond_bom_amount}")


def build_gemstone_detail(doc, new_bom):
	new_bom.set("gemstone_detail", [])
	for src in doc.gemstone_detail:
		dest = copy_row(new_bom, "gemstone_detail", src)

		dest.gemstone_rate_for_specified_quantity=dest.quantity * dest.total_gemstone_rate
		if doc.gemstone_charges=='Without':
			dest.gemstone_rate_for_specified_quantity=0
		elif doc.gemstone_charges=='Half':
			dest.gemstone_rate_for_specified_quantity=dest.gemstone_rate_for_specified_quantity/2
		elif doc.gemstone_charges=='Custom':
			dest.gemstone_rate_for_specified_quantity=doc.custom_gemstones_charges


def build_other_detail(doc, new_bom):
	new_bom.set("other_detail", [])
	for src in doc.other_detail:
		copy_row(new_bom, "other_detail", src)


class ProductReturnOrder(Document):
    pass
	# def validate(self):
	# 	if self.workflow_state=='BOM Calculated':
	# 		if self.bom:
	# 			bom_doc = frappe.get_doc("BOM", self.bom)
	# 			new_bom = frappe.copy_doc(bom_doc)
	# 		else:
	# 			# Jewelex-tag rows have no source BOM to copy from - build a fresh one.
	# 			new_bom = frappe.new_doc("BOM")
	# 			new_bom.company = self.company
	# 			new_bom.currency = frappe.get_cached_value("Company", self.company, "default_currency")
	# 			new_bom.append("items", {
	# 				"item_code": self.item_code,
	# 				"qty": 1,
	# 				"uom": self.uom,
	# 				"rate": 0,
	# 			})
	
	# 		# Comment out any line below to skip that table's rebuild/calculation
	# 		# (the table then keeps whatever rows copy_doc pulled from the source BOM).
	# 		build_metal_detail(self, new_bom)
	# 		build_finding_detail(self, new_bom)
	# 		build_diamond_detail(self, new_bom)
	# 		build_gemstone_detail(self, new_bom)
	# 		build_other_detail(self, new_bom)
	
	# 		new_bom.total_metal_weight = sum(row.quantity for row in new_bom.metal_detail)
	# 		new_bom.total_metal_amount = sum(row.amount for row in new_bom.metal_detail)
	# 		new_bom.total_making_amount = sum(row.making_amount for row in new_bom.metal_detail)
	# 		new_bom.total_wastage_amount = sum(row.wastage_amount for row in new_bom.metal_detail)
	# 		new_bom.total_finding_amount = sum(row.amount for row in new_bom.finding_detail)
	# 		new_bom.total_diamond_amount = sum(row.diamond_rate_for_specified_quantity for row in new_bom.diamond_detail)
	# 		new_bom.total_gemstone_amount = sum(row.gemstone_rate_for_specified_quantity for row in new_bom.gemstone_detail)
	# 		new_bom.gemstone_bom_amount = new_bom.total_gemstone_amount
	# 		new_bom.diamond_bom_amount = new_bom.total_diamond_amount
	# 		new_bom.gold_bom_amount=new_bom.total_metal_amount 
	# 		new_bom.finding_bom_amount=new_bom.total_finding_amount
	# 		new_bom.total_bom_amount = (new_bom.diamond_bom_amount+ new_bom.gold_bom_amount+ new_bom.gemstone_bom_amount+ new_bom.finding_bom_amount)
	# 		new_bom.making_charge = (sum(r.making_amount for r in new_bom.metal_detail)+ sum(r.making_amount for r in new_bom.finding_detail) )
	# 		new_bom.finding_pcs = self.total_finding_pcs
	# 		new_bom.finding_weight = sum(row.quantity for row in new_bom.finding_detail)
	# 		new_bom.total_gemstone_pcs = self.total_gemstone_pcs
	# 		new_bom.total_gemstone_weight_per_gram = self.total_gemstone_weightin_gms
	# 		# new_bom.total_gemstone_amount = self.total_gemstone_amount
	# 		# new_bom.total_diamond_amount = self.total_diamond_amount
	# 		new_bom.total_diamond_pcs = self.total_diamond_pcs
	# 		new_bom.total_diamond_weight_in_gms = self.total_diamond_weight_in_gram
	# 		new_bom.bom_type = "Finish Goods"
	# 		new_bom.item = self.item_code
	# 		new_bom.insert(ignore_permissions=True)
	# 		# new_bom.save()
	# 		self.db_set("new_bom", new_bom.name, update_modified=False)
	# def on_submit(self):
		
	# 	if not self.serial_no:
	# 		serial = frappe.new_doc('Serial No')
	# 		serial.item_code = self.item_code
	# 		serial.customer = self.customer
	# 		serial.company=self.company
	# 		serial.purchase_document_no = self.name
	# 		serial.description=self.description
	# 		self.item_name=self.item_name
	# 		serial.custom_jwelex_tag_no = self.jewelex_tag
	# 		serial.custom_bom_no=self.new_bom
	# 		serial.status = 'Delivered'
	# 		serial.custom_manufacturer='Labh'
	# 		compose_series = self.genrate_serial_no(self.new_bom)
	# 		sr_no = make_autoname(compose_series)
	# 		serial.serial_no=sr_no
	# 		# frappe.throw(f"Serial No = {serial.serial_no}")
	# 		serial.insert(ignore_permissions=True)
	# 		# serial.save()
	# 		self.db_set("serial_no", serial.name, update_modified=False)
	


	# def genrate_serial_no(self, new_bom):
	# 	new_bom = frappe.get_doc("BOM",new_bom)
	# 		# series_start = frappe.db.get_value("Manufacturing Setting", doc.company, ["series_start"])
	# 	series_start = frappe.db.get_value("Manufacturing Setting", {"manufacturer":'Labh'}, ["series_start"])
	# 	# metal_type, manufacturer, posting_date = frappe.db.get_value(
	# 	# 	"Manufacturing Work Order",
	# 	# 	mwo_no,
	# 	# 	["metal_type", "manufacturer", "posting_date"],
	# 	# )
	# 	manufacturer='Labh'
	# 	metal_type = new_bom.metal_detail[0].metal_type if new_bom.metal_detail else None
	# 	diamond_grade_data=new_bom.diamond_detail[0].diamond_grade if new_bom.metal_detail else None
	# 	m_abbr = frappe.db.get_value("Attribute Value", metal_type, "abbreviation")
	# 	mnf_abbr = frappe.db.get_value("Manufacturer", manufacturer, ["custom_abbreviation"])
	# 	# diamond_grade = max(diamond_grade_data, key=diamond_grade_data.get) 
	# 	posting_date = datetime.date.today()
	# 	dg_abbr = frappe.db.get_value("Attribute Value", diamond_grade_data, ["abbreviation"])
	# 	date = f"{posting_date.year %100:02d}"
	# 	date_to_letter = {0: "J", 1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F", 7: "G", 8: "H", 9: "I"}
	# 	final_date = date[0] + date_to_letter[int(date[1])]
	# 	if not series_start:
	# 		errors.append(
	# 			f"Please set value <b>Series Start</b> on Manufacturing Setting for <strong>{doc.company}</strong>"
	# 		)
	# 	if not mnf_abbr:
	# 		errors.append(
	# 			f"Please set value <b>Abbreviation</b> on Manufacturer doctype for <strong>{doc.company}</strong>"
	# 		)
	# 	if not dg_abbr:
	# 		errors.append(
	# 			f"Please set value <b>Abbreviation</b> on Attribute Value doctype respective Diamond Grade:<b>{diamond_grade}</b>"
	# 		)
	# 	if not m_abbr:
	# 		errors.append(
	# 			f"Please set value <b>Abbreviation</b> on Attribute Value doctype respective Metal Type:<b>{diamond_grade}</b>"
	# 		)
	

	# 	compose_series = str(series_start + mnf_abbr + m_abbr + dg_abbr + final_date + ".1244")
	# 	return compose_series

