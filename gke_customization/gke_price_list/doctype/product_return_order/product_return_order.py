# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
import datetime
from datetime import date
import requests,json


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
	def validate(self):
		if self.workflow_state=='BOM Calculated':
			if self.bom:
				bom_doc = frappe.get_doc("BOM", self.bom)
				new_bom = frappe.copy_doc(bom_doc)
			else:
				# Jewelex-tag rows have no source BOM to copy from - build a fresh one.
				new_bom = frappe.new_doc("BOM")
				new_bom.company = self.company
				new_bom.currency = frappe.get_cached_value("Company", self.company, "default_currency")
				new_bom.append("items", {
					"item_code": self.item_code,
					"qty": 1,
					"uom": self.uom,
					"rate": 0,
				})
	
			# Comment out any line below to skip that table's rebuild/calculation
			# (the table then keeps whatever rows copy_doc pulled from the source BOM).
			build_metal_detail(self, new_bom)
			build_finding_detail(self, new_bom)
			build_diamond_detail(self, new_bom)
			build_gemstone_detail(self, new_bom)
			build_other_detail(self, new_bom)
	
			new_bom.total_metal_weight = sum(row.quantity for row in new_bom.metal_detail)
			new_bom.total_metal_amount = sum(row.amount for row in new_bom.metal_detail)
			new_bom.total_making_amount = sum(row.making_amount for row in new_bom.metal_detail)
			new_bom.total_wastage_amount = sum(row.wastage_amount for row in new_bom.metal_detail)
			new_bom.total_finding_amount = sum(row.amount for row in new_bom.finding_detail)
			new_bom.total_diamond_amount = sum(row.diamond_rate_for_specified_quantity for row in new_bom.diamond_detail)
			new_bom.total_gemstone_amount = sum(row.gemstone_rate_for_specified_quantity for row in new_bom.gemstone_detail)
			new_bom.gemstone_bom_amount = new_bom.total_gemstone_amount
			new_bom.diamond_bom_amount = new_bom.total_diamond_amount
			new_bom.gold_bom_amount=new_bom.total_metal_amount 
			new_bom.finding_bom_amount=new_bom.total_finding_amount
			new_bom.total_bom_amount = (new_bom.diamond_bom_amount+ new_bom.gold_bom_amount+ new_bom.gemstone_bom_amount+ new_bom.finding_bom_amount)
			new_bom.making_charge = (sum(r.making_amount for r in new_bom.metal_detail)+ sum(r.making_amount for r in new_bom.finding_detail) )
			new_bom.finding_pcs = self.total_finding_pcs
			new_bom.finding_weight = sum(row.quantity for row in new_bom.finding_detail)
			new_bom.total_gemstone_pcs = self.total_gemstone_pcs
			new_bom.total_gemstone_weight_per_gram = self.total_gemstone_weightin_gms
			# new_bom.total_gemstone_amount = self.total_gemstone_amount
			# new_bom.total_diamond_amount = self.total_diamond_amount
			new_bom.total_diamond_pcs = self.total_diamond_pcs
			new_bom.total_diamond_weight_in_gms = self.total_diamond_weight_in_gram
			new_bom.bom_type = "Finish Goods"
			new_bom.item = self.item_code
			new_bom.insert(ignore_permissions=True)
			# new_bom.save()
			self.db_set("new_bom", new_bom.name, update_modified=False)

	def on_update(self):
		sync_product_return_order_to_gk(self)
	def on_submit(self):
		
		if not self.serial_no:
			serial = frappe.new_doc('Serial No')
			serial.item_code = self.item_code
			serial.customer = self.customer
			serial.company=self.company
			serial.purchase_document_no = self.name
			serial.description=self.description
			self.item_name=self.item_name
			serial.custom_jwelex_tag_no = self.jewelex_tag
			serial.custom_bom_no=self.new_bom
			serial.status = 'Delivered'
			serial.custom_manufacturer='Labh'
			compose_series = self.genrate_serial_no(self.new_bom)
			sr_no = make_autoname(compose_series)
			serial.serial_no=sr_no
			# frappe.throw(f"Serial No = {serial.serial_no}")
			serial.insert(ignore_permissions=True)
			# serial.save()
			self.db_set("serial_no", serial.name, update_modified=False)
			# self.serial_no = serial.name
			if serial.name:
				remote_url = (
					"https://gkexport-dummy-v16.m.frappe.cloud"
					"/api/method/serial_product_return_order"
				)

				headers = {
				"Authorization": "token 94efdb20934f180:5418ee1e0b4a5e3",
					"Content-Type": "application/json",
					"Accept": "application/json"
				}

				payload = {
					"name": self.name,
					"serial_no": serial.name
				}

				try:

					response = requests.post(
						remote_url,
						headers=headers,
						json=payload,
						timeout=30
					)

					# Check HTTP status
					response.raise_for_status()

					# Try to read JSON response
					try:
						response_data = response.json()
					except Exception:
						response_data = response.text

					frappe.log_error(
						title="Serial No Synced Successfully",
						message=json.dumps({
							"document": self.name,
							"serial_no": serial.name,
							"status_code": response.status_code,
							"response": response_data
						}, default=str, indent=2)
					)

				except requests.exceptions.Timeout:

					frappe.log_error(
						title="Remote Serial No API Timeout",
						message=json.dumps({
							"document": self.name,
							"serial_no": serial.name,
							"url": remote_url
						}, indent=2)
					)

					frappe.throw(
						"Remote Serial No synchronization timed out."
					)

				except requests.exceptions.RequestException as e:

					frappe.log_error(
						title="Remote Serial No API Failed",
						message=json.dumps({
							"document": self.name,
							"serial_no": serial.name,
							"error": str(e),
							"response": getattr(e.response, "text", None)
							if getattr(e, "response", None)
							else None
						}, default=str, indent=2)
					)

					frappe.throw(
						"Remote Serial No synchronization failed:\n\n" + str(e)
					)

				except Exception as e:

					frappe.log_error(
						title="Remote Serial No Sync Unexpected Error",
						message=frappe.get_traceback()
					)

					frappe.throw(
						"Unexpected error during Serial No synchronization:\n\n"
						+ str(e)
					)
					


	def genrate_serial_no(self, new_bom):
		errors = []
		new_bom = frappe.get_doc("BOM",new_bom)
			# series_start = frappe.db.get_value("Manufacturing Setting", doc.company, ["series_start"])
		series_start = frappe.db.get_value("Manufacturing Setting", {"manufacturer":'Labh'}, ["series_start"])
		# metal_type, manufacturer, posting_date = frappe.db.get_value(
		# 	"Manufacturing Work Order",
		# 	mwo_no,
		# 	["metal_type", "manufacturer", "posting_date"],
		# )
		manufacturer='Labh'
		metal_type = new_bom.metal_detail[0].metal_type if new_bom.metal_detail else None
		diamond_grade_data=new_bom.diamond_detail[0].diamond_grade if new_bom.metal_detail else None
		m_abbr = frappe.db.get_value("Attribute Value", metal_type, "abbreviation")
		mnf_abbr = frappe.db.get_value("Manufacturer", manufacturer, ["custom_abbreviation"])
		# diamond_grade = max(diamond_grade_data, key=diamond_grade_data.get) 
		posting_date = datetime.date.today()
		dg_abbr = frappe.db.get_value("Attribute Value", diamond_grade_data, ["abbreviation"])
		date = f"{posting_date.year %100:02d}"
		date_to_letter = {0: "J", 1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F", 7: "G", 8: "H", 9: "I"}
		final_date = date[0] + date_to_letter[int(date[1])]
		if not series_start:
			errors.append(
				f"Please set value <b>Series Start</b> on Manufacturing Setting for <strong>{self.company}</strong>"
			)
		if not mnf_abbr:
			errors.append(
				f"Please set value <b>Abbreviation</b> on Manufacturer doctype for <strong>{self.company}</strong>"
			)
		if not dg_abbr:
			errors.append(
				f"Please set value <b>Abbreviation</b> on Attribute Value doctype respective Diamond Grade:<b>{diamond_grade_data}</b>"
			)
		if not m_abbr:
			errors.append(
				f"Please set value <b>Abbreviation</b> on Attribute Value doctype respective Metal Type:<b>{metal_type}</b>"
			)
		# frappe.throw(
		# 	f"""
		# 	series_start = {series_start}<br>
		# 	mnf_abbr = {mnf_abbr}<br>
		# 	m_abbr = {m_abbr}<br>
		# 	dg_abbr = {dg_abbr}<br>
		# 	final_date = {final_date}
		# 	"""
		# )
			

		compose_series = str(series_start + mnf_abbr + m_abbr + dg_abbr + final_date + ".1244")
		return compose_series





import json
import requests


def sync_product_return_order_to_gk(doc):

    # =========================================================
    # PREVENT REMOTE DOCUMENT FROM SYNCING BACK
    # =========================================================

    # if not doc.custom_auto_created_product_return_order:

	# =====================================================
	# GET OLD DOCUMENT
	# =====================================================

	old_doc = doc.get_doc_before_save()

	workflow_changed = False
	local_old_state = None
	local_new_state = doc.workflow_state

	if old_doc:
		local_old_state = old_doc.workflow_state

		if local_old_state != local_new_state:
			workflow_changed = True

	# =====================================================
	# DEBUG WORKFLOW CHANGE
	# =====================================================

	frappe.log_error(
		title="Product Return Workflow Debug",
		message=json.dumps({
			"document": doc.name,
			"old_state": local_old_state,
			"new_state": local_new_state,
			"workflow_changed": workflow_changed
		}, default=str, indent=2)
	)

	# =====================================================
	# ONLY SYNC WHEN WORKFLOW CHANGED
	# =====================================================

	if workflow_changed:

		# =================================================
		# METAL DETAIL
		# =================================================

		metal_detail = []

		for row in (doc.metal_detail or []):

			metal_detail.append({
				"item": row.item,
				"metal_type": row.metal_type,
				"metal_touch": row.metal_touch,
				"metal_purity": row.metal_purity,
				"metal_colour": row.metal_colour,
				"cad_weight": row.cad_weight,
				"purity_percentage": row.purity_percentage,
				"wastage_rate": row.wastage_rate,
				"wastage_amount": row.wastage_amount,
				"se_rate": row.se_rate,
				"cad_to_finish_ratio": row.cad_to_finish_ratio,
				"quantity": row.quantity,
				"actual_quantity": row.actual_quantity,
				"difference_qty": row.difference_qty,
				"additional_net_weight": row.additional_net_weight,
				"is_customer_item": row.is_customer_item,
				"rate": row.rate,
				"difference": row.difference,
				"amount": row.amount,
				"making_rate": row.making_rate,
				"making_amount": row.making_amount,
				"stock_uom": row.stock_uom,
				"item_variant": row.item_variant,
				"fg_purchase_rate": row.fg_purchase_rate,
				"fg_purchase_amount": row.fg_purchase_amount,
				"cam_weight": row.cam_weight,
				"wax_weight": row.wax_weight,
				"casting_weight": row.casting_weight,
				"finish_product_weight": row.finish_product_weight,
				"finish_loss_percentage": row.finish_loss_percentage,
				"finish_loss_grams": row.finish_loss_grams,
				"custom_rate": row.custom_rate,
				"custom_making_rate": row.custom_making_rate,
				"custom_wastage_rate": row.custom_wastage_rate
			})

		# =================================================
		# FINDING DETAIL
		# =================================================

		finding_detail = []

		for row in (doc.finding_detail or []):

			finding_detail.append({
				"item": row.item,
				"finding_category": row.finding_category,
				"finding_type": row.finding_type,
				"metal_type": row.metal_type,
				"metal_touch": row.metal_touch,
				"metal_purity": row.metal_purity,
				"metal_colour": row.metal_colour,
				"customer_metal_purity": row.customer_metal_purity,
				"purity_percentage": row.purity_percentage,
				"qty": row.qty,
				"quantity": row.quantity,
				"actual_quantity": row.actual_quantity,
				"difference_qty": row.difference_qty,
				"rate": row.rate,
				"amount": row.amount,
				"making_rate": row.making_rate,
				"making_amount": row.making_amount,
				"wastage_rate": row.wastage_rate,
				"wastage_amount": row.wastage_amount,
				"fg_purchase_rate": row.fg_purchase_rate,
				"fg_purchase_amount": row.fg_purchase_amount,
				"is_customer_item": row.is_customer_item,
				"is_manufacturing_item": row.is_manufacturing_item,
				"ignore_work_order": row.ignore_work_order,
				"not_finding_rate": row.not_finding_rate,
				"difference": row.difference,
				"stock_uom": row.stock_uom
			})

		# =================================================
		# GEMSTONE DETAIL
		# =================================================

		gemstone_detail = []

		for row in (doc.gemstone_detail or []):

			gemstone_detail.append({
				"item": row.item,
				"gemstone_type": row.gemstone_type,
				"gemstone_code": row.gemstone_code,
				"gemstone_grade": row.gemstone_grade,
				"gemstone_quality": row.gemstone_quality,
				"gemstone_pr": row.gemstone_pr,
				"cut_or_cab": row.cut_or_cab,
				"gemstone_size": row.gemstone_size,
				"stone_shape": row.stone_shape,
				"size_height": row.size_height,
				"size_weight": row.size_weight,
				"pcs": row.pcs,
				"quantity": row.quantity,
				"quantity_3": row.quantity_3,
				"stock_uom": row.stock_uom,
				"per_pc_or_per_carat": row.per_pc_or_per_carat,
				"price_list_type": row.price_list_type,
				"rate": row.rate,
				"amount": row.amount,
				"fg_purchase_rate": row.fg_purchase_rate,
				"gemstone_rate_for_specified_quantity":
					row.gemstone_rate_for_specified_quantity,
				"total_gemstone_rate": row.total_gemstone_rate,
				"is_customer_item": row.is_customer_item
			})

		# =================================================
		# DIAMOND DETAIL
		# =================================================

		diamond_detail = []

		for row in (doc.diamond_detail or []):

			diamond_detail.append({
				"item": row.item,
				"diamond_type": row.diamond_type,
				"stone_shape": row.stone_shape,
				"sieve_size_color": row.sieve_size_color,
				"diamond_sieve_size": row.diamond_sieve_size,
				"sieve_size_range": row.sieve_size_range,
				"size_in_mm": row.size_in_mm,
				"is_customer_item": row.is_customer_item,
				"total_diamond_rate": row.total_diamond_rate,
				"fg_purchase_rate": row.fg_purchase_rate,
				"se_rate": row.se_rate,
				"handling_rate": row.handling_rate,
				"size_type": row.size_type,
				"pcs": row.pcs,
				"weight_per_pcs": row.weight_per_pcs,
				"std_wt": row.std_wt,
				"quantity": row.quantity,
				"quantity_3": row.quantity_3,
				"actual_quantity": row.actual_quantity,
				"weight_in_gms": row.weight_in_gms,
				"difference": row.difference,
				"diamond_grade": row.diamond_grade,
				"stock_uom": row.stock_uom,
				"item_variant": row.item_variant,
				"diamond_rate_for_specified_quantity":
					row.diamond_rate_for_specified_quantity,
				"fg_purchase_amount": row.fg_purchase_amount
			})

		# =================================================
		# OTHER DETAIL
		# =================================================

		other_detail = []

		for row in (doc.other_detail or []):

			other_detail.append({
				"item_code": row.item_code,
				"qty": row.qty,
				"quantity": row.quantity,
				"rate": row.rate,
				"amount": row.amount,
				"uom": row.uom
			})

		# =================================================
		# MAIN PAYLOAD
		# =================================================

		payload = {

			# -------------------------------------------------
			# BASIC
			# -------------------------------------------------

			"name": doc.name,
			"index": doc.index,

			"customer": "GJCU0009",
			"customer_name": "Gurukrupa Export Private Limited - Factory",

			"item_code": doc.item_code,
			"new_bom": doc.new_bom,
			"serial_no": doc.serial_no,

			# "branch": doc.branch,

			"is_jewlex_credit_note": doc.is_jewlex_credit_note,
			"is_jewelex_tag": doc.is_jewelex_tag,

			"product_return_order_form":
				doc.product_return_order_form,

			"company": "KG GK Jewellers Private Limited",
			"sales_type": doc.sales_type,
			"ref_company": doc.ref_company,

			"date": doc.date,
			"posting_time": doc.posting_time,

			"status": doc.status,

			# -------------------------------------------------
			# WORKFLOW
			#
			# IMPORTANT:
			# workflow_state is removed before PUT.
			# -------------------------------------------------

			"workflow_state": doc.workflow_state,

			# -------------------------------------------------
			# RETURN / CREDIT NOTE
			# -------------------------------------------------

			"making_charges": doc.making_charges,
			"custom_making_charges": doc.custom_making_charges,

			"credit_note_rate_type": doc.credit_note_rate_type,

			"return_material_type": doc.return_material_type,

			"gemstone_charges": doc.gemstone_charges,
			"custom_gemstone_charges": doc.custom_gemstone_charges,

			"diamond_rate_type": doc.diamond_rate_type,

			"handling_charges": doc.handling_charges,
			"wastage_charges": doc.wastage_charges,

			# -------------------------------------------------
			# GOLD RATE
			# -------------------------------------------------

			"gold_rate_with_gst": doc.gold_rate_with_gst,
			"gold_rate": doc.gold_rate,

			# -------------------------------------------------
			# ITEM
			# -------------------------------------------------

			"serial_no": doc.serial_no,
			"hsn_sac": doc.hsn_sac,
			"item_group": doc.item_group,
			"item_name": doc.item_name,

			"bom": doc.bom,

			"metal_touch": doc.metal_touch,
			"metal_purity": doc.metal_purity,
			"metal_colour": doc.metal_colour,
			"setting_type": doc.setting_type,

			# -------------------------------------------------
			# WEIGHT
			# -------------------------------------------------

			"net_weight": doc.net_weight,
			"gross_weight": doc.gross_weight,

			"gold_weight": doc.gold_weight,
			"diamond_weight": doc.diamond_weight,

			"physical_net_weight": doc.physical_net_weight,
			"physical_gross_weight": doc.physical_gross_weight,

			# -------------------------------------------------
			# CATEGORY
			# -------------------------------------------------

			"item_category": doc.item_category,
			"item_subcategory": doc.item_subcategory,

			# -------------------------------------------------
			# DESCRIPTION / IMAGE
			# -------------------------------------------------

			"description": doc.description,
			"image": doc.image,

			# -------------------------------------------------
			# QUANTITY
			# -------------------------------------------------

			"qty": doc.qty,
			"uom": doc.uom,

			# -------------------------------------------------
			# AMOUNTS
			# -------------------------------------------------

			"rate": doc.rate,
			"amount": doc.amount,

			"base_rate": doc.base_rate,
			"base_amount": doc.base_amount,

			"metal_amount": doc.metal_amount,
			"diamond_amount": doc.diamond_amount,
			"finding_amount": doc.finding_amount,
			"making_amount": doc.making_amount,

			"certification_amount": doc.certification_amount,
			"freight_amount": doc.freight_amount,
			"gemstone_amount": doc.gemstone_amount,
			"other_material_amount": doc.other_material_amount,
			"hallmarking_amount": doc.hallmarking_amount,
			"custom_duty_amount": doc.custom_duty_amount,
			"other_amount": doc.other_amount,

			"total_weight": doc.total_weight,

			# -------------------------------------------------
			# WAREHOUSE / INVOICE
			# -------------------------------------------------

			"warehouse": doc.warehouse,

			"sales_invoice": doc.sales_invoice,
			"sales_invoice_item": doc.sales_invoice_item,

			# -------------------------------------------------
			# COUNTS
			# -------------------------------------------------

			"total_finding_pcs": doc.total_finding_pcs,
			"total_gemstone_pcs": doc.total_gemstone_pcs,
			"total_diamond_pcs": doc.total_diamond_pcs,

			# -------------------------------------------------
			# CHILD TABLES
			# -------------------------------------------------

			"metal_detail": metal_detail,
			"finding_detail": finding_detail,
			"gemstone_detail": gemstone_detail,
			"diamond_detail": diamond_detail,
			"other_detail": other_detail,

			# -------------------------------------------------
			# PREVENT REMOTE SYNC BACK
			# -------------------------------------------------

			# "custom_auto_created_product_return_order": 1
		}

		# =====================================================
		# REMOTE API
		# =====================================================

		# base_url = (
		#     "https://gkexport-dummy-v16.m.frappe.cloud"
		#     "/api/resource/Product%20Return%20Order"
		# )
		base_url = (
			"https://gkexport-dummy-v16.m.frappe.cloud/"
			"/api/resource/Product%20Return%20Order"
		)

		remote_url = base_url + "/" + str(doc.name)

		# =====================================================
		# API TOKEN
		#
		# IMPORTANT:
		# Replace these with your NEW rotated credentials.
		# =====================================================

		headers = {
			"Authorization": "token 94efdb20934f180:5418ee1e0b4a5e3",
			"Content-Type": "application/json",
			"Accept": "application/json"
		}

		# =====================================================
		# WORKFLOW API
		# =====================================================

		workflow_url = (
			"https://gkexport-dummy-v16.m.frappe.cloud/"
			"/api/method/frappe.model.workflow.apply_workflow"
		)

		# =====================================================
		# GET REMOTE DOCUMENT
		# =====================================================

		remote_exists = False
		remote_response = None
		remote_data = {}

		try:

			get_resp = requests.get(
				remote_url,
				headers=headers
			)
			get_resp.raise_for_status()

			remote_response = get_resp.json()

			remote_exists = True

			remote_data = remote_response.get(
				"data",
				{}
			)

		except Exception as get_error:

			error_text = str(get_error)

			is_404 = False

			if "404" in error_text:
				is_404 = True

			try:
				if (
					hasattr(get_error, "response")
					and get_error.response
					and get_error.response.status_code == 404
				):
					is_404 = True
			except Exception:
				pass

			if not is_404:

				frappe.log_error(
					title="Remote Product Return GET Failed",
					message=(
						"Document: "
						+ str(doc.name)
						+ "\n\n"
						+ error_text
					)
				)

				frappe.throw(
					"Unable to check Product Return Order on GK:\n\n"
					+ error_text
				)

		# =====================================================
		# CREATE REMOTE DOCUMENT
		# =====================================================

		if not remote_exists:

			# ---------------------------------------------
			# DO NOT SEND workflow_state DURING CREATE
			# ---------------------------------------------

			create_payload = payload.copy()

			create_payload.pop(
				"workflow_state",
				None
			)

			try:

				create_resp = requests.post(
					base_url,
					headers=headers,
					data=json.dumps(
						create_payload,
						default=str
					)
				)
				create_resp.raise_for_status()

				create_response = create_resp.json()

				frappe.log_error(
					title="Remote Product Return Order Created",
					message=json.dumps({
						"document": doc.name,
						"local_old_state": local_old_state,
						"local_new_state": local_new_state,
						"response": create_response
					}, default=str, indent=2)
				)

			except Exception as create_error:

				error_detail = str(create_error)

				try:

					if (
						hasattr(create_error, "response")
						and create_error.response
					):

						error_detail += (
							"\nHTTP Status: "
							+ str(
								create_error.response.status_code
							)
						)

						error_detail += (
							"\nGK Response: "
							+ str(
								create_error.response.text
							)
						)

				except Exception:
					pass

				frappe.log_error(
					title="Remote Product Return Order Creation Failed",
					message=(
						"Document: "
						+ str(doc.name)
						+ "\n\n"
						+ error_detail
					)
				)

				frappe.throw(
					"Remote Product Return Order creation failed:\n\n"
					+ error_detail
				)

			# ---------------------------------------------
			# GET NEW REMOTE DOCUMENT
			# ---------------------------------------------

			try:

				get_resp = requests.get(
					remote_url,
					headers=headers
				)
				get_resp.raise_for_status()

				remote_response = get_resp.json()

				remote_data = remote_response.get(
					"data",
					{}
				)

				remote_workflow_state = remote_data.get(
					"workflow_state"
				)

			except Exception as e:

				frappe.throw(
					"Remote document was created but could "
					"not be fetched afterward.\n\n"
					+ str(e)
				)

		else:

			remote_workflow_state = remote_data.get(
				"workflow_state"
			)

		# =====================================================
		# LOG REMOTE STATE
		# =====================================================

		frappe.log_error(
			title="Remote Workflow State Before Sync",
			message=json.dumps({
				"document": doc.name,
				"local_old_state": local_old_state,
				"local_new_state": local_new_state,
				"remote_state": remote_workflow_state
			}, default=str, indent=2)
		)

		# =====================================================
		# UPDATE REMOTE DOCUMENT DATA
		#
		# IMPORTANT:
		# NEVER PUT workflow_state
		# =====================================================

		update_payload = payload.copy()

		update_payload.pop(
			"workflow_state",
			None
		)

		try:

			update_resp = requests.put(
				remote_url,
				headers=headers,
				data=json.dumps(
					update_payload,
					default=str
				)
			)
			update_resp.raise_for_status()

			update_response = update_resp.json()

			frappe.log_error(
				title="Remote Product Return Order Data Updated",
				message=json.dumps({
					"document": doc.name,
					"response": update_response
				}, default=str, indent=2)
			)

		except Exception as update_error:

			error_detail = str(update_error)

			try:

				if (
					hasattr(update_error, "response")
					and update_error.response
				):

					error_detail += (
						"\nHTTP Status: "
						+ str(
							update_error.response.status_code
						)
					)

					error_detail += (
						"\nGK Response: "
						+ str(
							update_error.response.text
						)
					)

			except Exception:
				pass

			frappe.log_error(
				title="Remote Product Return Order Update Failed",
				message=(
					"Document: "
					+ str(doc.name)
					+ "\n\n"
					+ error_detail
				)
			)

			frappe.throw(
				"Remote Product Return Order update failed:\n\n"
				+ error_detail
			)

		# =====================================================
		# DETERMINE REMOTE WORKFLOW ACTION
		#
		# Mapping:
		#
		# Draft
		#   -> Create Item
		#   Action = Send to IBM
		#
		# Create Item
		#   -> Send For Approval
		#   Action = Send For Approval
		#
		# Draft
		#   -> BOM Calculated
		#   Action = Calculate Bom
		#
		# BOM Calculated
		#   -> Send For Approval
		#   Action = Send For Approval
		#
		# Send For Approval
		#   -> BOM Calculated
		#   Action = BOM Recalculation
		#
		# Send For Approval
		#   -> Approved
		#   Action = Approve
		#
		# =====================================================

		workflow_action = None
		expected_remote_state = local_new_state

		# =====================================================
		# DRAFT -> CREATE ITEM
		# =====================================================

		if (
			local_old_state == "Draft"
			and local_new_state == "Create Item"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Local transition:\n"
					"Draft -> Create Item\n\n"
					"is_jewelex_tag is not enabled."
				)

			workflow_action = "Send to IBM"

		# =====================================================
		# CREATE ITEM -> SEND FOR APPROVAL
		# =====================================================

		elif (
			local_old_state == "Create Item"
			and local_new_state == "Send For Approval"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Create Item -> Send For Approval\n\n"
					"is_jewelex_tag is not enabled."
				)

			if not doc.item_code:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Create Item -> Send For Approval\n\n"
					"item_code is missing."
				)

			workflow_action = "Send For Approval"

		# =====================================================
		# DRAFT -> BOM CALCULATED
		# =====================================================

		elif (
			local_old_state == "Draft"
			and local_new_state == "BOM Calculated"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Draft -> BOM Calculated\n\n"
					"is_jewelex_tag is not enabled."
				)

			workflow_action = "Calculate Bom"

		# =====================================================
		# BOM CALCULATED -> SEND FOR APPROVAL
		# =====================================================

		elif (
			local_old_state == "BOM Calculated"
			and local_new_state == "Send For Approval"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"BOM Calculated -> Send For Approval\n\n"
					"is_jewelex_tag is not enabled."
				)

			if not doc.item_code:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"BOM Calculated -> Send For Approval\n\n"
					"item_code is missing."
				)

			workflow_action = "Send For Approval"

		# =====================================================
		# SEND FOR APPROVAL -> BOM CALCULATED
		#
		# IMPORTANT:
		#
		# GK workflow:
		#
		# Send For Approval
		#       |
		#       | BOM Recalculation
		#       v
		# BOM Calculated
		#
		# Therefore action MUST be:
		# "BOM Recalculation"
		# =====================================================

		elif (
			local_old_state == "Send For Approval"
			and local_new_state == "BOM Calculated"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Send For Approval -> BOM Calculated\n\n"
					"is_jewelex_tag is not enabled."
				)

			if not doc.item_code:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Send For Approval -> BOM Calculated\n\n"
					"item_code is missing."
				)

			workflow_action = "BOM Recalculation"

		# =====================================================
		# SEND FOR APPROVAL -> APPROVED
		# =====================================================

		elif (
			local_old_state == "Send For Approval"
			and local_new_state == "Approved"
		):

			if not doc.is_jewelex_tag:

				frappe.throw(
					"Cannot synchronize workflow to GK.\n\n"
					"Send For Approval -> Approved\n\n"
					"is_jewelex_tag is not enabled."
				)

			workflow_action = "Approve"

		# =====================================================
		# NO MAPPING
		# =====================================================

		else:

			frappe.log_error(
				title="No Remote Workflow Mapping",
				message=json.dumps({
					"document": doc.name,
					"local_old_state": local_old_state,
					"local_new_state": local_new_state,
					"remote_state": remote_workflow_state
				}, default=str, indent=2)
			)

			frappe.throw(
				"No remote workflow mapping configured.\n\n"
				"Document: "
				+ str(doc.name)
				+ "\n\n"
				"Local Old State: "
				+ str(local_old_state)
				+ "\n"
				"Local New State: "
				+ str(local_new_state)
				+ "\n"
				"Remote State: "
				+ str(remote_workflow_state)
			)

		# =====================================================
		# LOG SELECTED WORKFLOW MAPPING
		# =====================================================

		frappe.log_error(
			title="Remote Workflow Mapping Selected",
			message=json.dumps({
				"document": doc.name,
				"local_old_state": local_old_state,
				"local_new_state": local_new_state,
				"remote_current_state": remote_workflow_state,
				"workflow_action": workflow_action,
				"expected_remote_state": expected_remote_state
			}, default=str, indent=2)
		)

		# =====================================================
		# CHECK REMOTE STATE BEFORE APPLYING ACTION
		#
		# Remote should currently be at LOCAL OLD STATE.
		# =====================================================

		if remote_workflow_state != local_old_state:

			# -------------------------------------------------
			# SPECIAL CASE:
			# Remote is already at LOCAL NEW STATE.
			# -------------------------------------------------

			if remote_workflow_state == local_new_state:

				frappe.log_error(
					title="Remote Workflow Already Synchronized",
					message=json.dumps({
						"document": doc.name,
						"local_old_state": local_old_state,
						"local_new_state": local_new_state,
						"remote_state": remote_workflow_state
					}, default=str, indent=2)
				)

			else:

				frappe.throw(
					"Remote workflow is not in the expected state.\n\n"
					"Document: "
					+ str(doc.name)
					+ "\n\n"
					"Local Old State: "
					+ str(local_old_state)
					+ "\n"
					"Local New State: "
					+ str(local_new_state)
					+ "\n"
					"Remote Current State: "
					+ str(remote_workflow_state)
					+ "\n"
					"Expected Remote State: "
					+ str(local_old_state)
					+ "\n"
					"Action Required: "
					+ str(workflow_action)
				)

		# =====================================================
		# APPLY WORKFLOW
		# =====================================================

		if (
			remote_workflow_state == local_old_state
			and workflow_action
		):

			workflow_payload = {
				"doc": json.dumps({
					"doctype": "Product Return Order",
					"name": doc.name
				}),
				"action": workflow_action
			}

			# -------------------------------------------------
			# LOG REQUEST
			# -------------------------------------------------

			frappe.log_error(
				title="Remote Workflow Request",
				message=json.dumps({
					"document": doc.name,
					"local_old_state": local_old_state,
					"local_new_state": local_new_state,
					"remote_state": remote_workflow_state,
					"workflow_action": workflow_action,
					"expected_remote_state":
						expected_remote_state,
					"workflow_payload": workflow_payload
				}, default=str, indent=2)
			)

			# -------------------------------------------------
			# CALL APPLY WORKFLOW
			# -------------------------------------------------

			try:

				workflow_resp = requests.post(
					workflow_url,
					headers=headers,
					data=json.dumps(
						workflow_payload,
						default=str
					)
				)
				workflow_resp.raise_for_status()

				workflow_response = workflow_resp.json()

			except Exception as workflow_error:

				error_detail = str(workflow_error)

				try:

					if (
						hasattr(workflow_error, "response")
						and workflow_error.response
					):

						error_detail += (
							"\n\nHTTP Status: "
							+ str(
								workflow_error.response.status_code
							)
						)

						error_detail += (
							"\n\nGK Response:\n"
							+ str(
								workflow_error.response.text
							)
						)

				except Exception:
					pass

				frappe.log_error(
					title="GK Apply Workflow Failed",
					message=(
						"Document: "
						+ str(doc.name)
						+ "\n\n"
						"Local Old State: "
						+ str(local_old_state)
						+ "\n"
						"Local New State: "
						+ str(local_new_state)
						+ "\n"
						"Remote State: "
						+ str(remote_workflow_state)
						+ "\n"
						"Action: "
						+ str(workflow_action)
						+ "\n\n"
						"Payload:\n"
						+ json.dumps(
							workflow_payload,
							indent=2,
							default=str
						)
						+ "\n\n"
						"Error:\n"
						+ error_detail
					)
				)

				frappe.throw(
					"Remote Product Return Order Workflow "
					"Sync Failed:\n\n"
					+ error_detail
				)

			# =================================================
			# GET FINAL REMOTE DOCUMENT
			# =================================================

			try:

				final_resp = requests.get(
					remote_url,
					headers=headers
				)
				final_resp.raise_for_status()

				final_response = final_resp.json()

				final_data = final_response.get(
					"data",
					{}
				)

				final_workflow_state = final_data.get(
					"workflow_state"
				)

			except Exception as final_error:

				frappe.throw(
					"Workflow action was sent to GK, "
					"but final remote state could not be checked.\n\n"
					+ str(final_error)
				)

			# =================================================
			# LOG FINAL RESULT
			# =================================================

			frappe.log_error(
				title="Remote Product Return Workflow Result",
				message=json.dumps({
					"document": doc.name,
					"local_old_state": local_old_state,
					"local_new_state": local_new_state,
					"remote_state_before":
						remote_workflow_state,
					"workflow_action": workflow_action,
					"expected_remote_state":
						expected_remote_state,
					"actual_remote_state":
						final_workflow_state,
					"workflow_response":
						workflow_response
				}, default=str, indent=2)
			)

			# =================================================
			# FINAL VALIDATION
			#
			# Compare remote final state with local new state.
			# =================================================

			if final_workflow_state != local_new_state:

				frappe.throw(
					"Remote workflow action was executed, "
					"but remote workflow did not reach "
					"the local workflow state.\n\n"
					"Document: "
					+ str(doc.name)
					+ "\n\n"
					"Local Old State: "
					+ str(local_old_state)
					+ "\n"
					"Local New State: "
					+ str(local_new_state)
					+ "\n"
					"Remote State Before: "
					+ str(remote_workflow_state)
					+ "\n"
					"Remote State After: "
					+ str(final_workflow_state)
					+ "\n"
					"Workflow Action: "
					+ str(workflow_action)
				)

			# =================================================
			# SUCCESS LOG
			# =================================================

			frappe.log_error(
				title="Remote Product Return Workflow Synchronized",
				message=json.dumps({
					"document": doc.name,
					"local_old_state": local_old_state,
					"local_new_state": local_new_state,
					"remote_old_state":
						remote_workflow_state,
					"remote_new_state":
						final_workflow_state,
					"action":
						workflow_action
				}, default=str, indent=2)
			)

