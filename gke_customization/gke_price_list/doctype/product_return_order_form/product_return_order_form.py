# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import copy
from collections import defaultdict
import json
import re
import frappe
import time
import requests
from pypika import Order
from frappe.query_builder import DocType
from frappe.model.document import Document
from frappe.utils import flt
from gke_customization.gke_price_list.doctype.product_return_order_form.e_invoice_logic import validate_e_invoice_items
from gke_customization.gke_price_list.doctype.product_return_order_form.product_return_order_form_api import trigger_pricing_calculation


def resolve_attribute_value(text, flag_field):
	"""Resolve a raw Jwelex label to an Attribute Value name. Returns None if not found."""
	if not text:
		return None
	return frappe.db.get_value("Attribute Value", {"name": text.strip(), flag_field: 1}, "name")


# Known Jwelex Purity_Name -> (metal_touch, metal_colour, metal_purity) overrides
JWELEX_METAL_PURITY_MAP = {
	"92 %": {"metal_touch": "22KT", "metal_colour": "Yellow", "metal_purity": "92.0"},
}


def append_metal_detail_from_jwelex(product_order, metal_details):
	for m in metal_details:
		dest = product_order.append("metal_detail", {})

		metal_type = resolve_attribute_value(m.get("Meterial"), "is_metal_type")
		if metal_type:
			dest.metal_type = metal_type

		purity_name = (m.get("Purity_Name") or "").strip()
		purity_map = JWELEX_METAL_PURITY_MAP.get(purity_name)
		if purity_map:
			dest.metal_touch = purity_map["metal_touch"]
			dest.metal_colour = purity_map["metal_colour"]
			dest.metal_purity = purity_map["metal_purity"]
		else:
			metal_purity = resolve_attribute_value(purity_name, "is_metal_purity")
			if metal_purity:
				dest.metal_purity = metal_purity

		dest.quantity = m.get("Weight")
		dest.rate = m.get("Rate")
		dest.amount = m.get("Amount")
		dest.se_rate = m.get("Costing_Rate")


def parse_float(text):
	"""Extract the first number out of a raw Jwelex value like '2.20 MM'."""
	if text is None or text == "":
		return None
	if isinstance(text, (int, float)):
		return text
	match = re.search(r"[-+]?\d*\.?\d+", str(text))
	return float(match.group()) if match else None


def append_diamond_detail_from_jwelex(product_order, diamond_details):
	for d in diamond_details:
		dest = product_order.append("diamond_detail", {})

		dest.diamond_type = "Natural"

		stone_shape = resolve_attribute_value(d.get("Shape_Name"), "is_stone_shape")
		if stone_shape:
			dest.stone_shape = stone_shape

		dest.size_in_mm = parse_float(d.get("Code_Name"))
		dest.pcs = d.get("Pcs")
		dest.quantity = d.get("Weight")
		dest.total_diamond_rate = d.get("Rate")
		dest.diamond_rate_for_specified_quantity = d.get("Amount")
		dest.se_rate = d.get("Costing_Amt")


def append_finding_detail_from_jwelex(product_order, finding_details):
	for f in finding_details:
		dest = product_order.append("finding_detail", {})

		metal_type = resolve_attribute_value(f.get("Meterial"), "is_metal_type")
		if metal_type:
			dest.metal_type = metal_type

		finding_category = resolve_attribute_value(f.get("Shape_Name"), "is_finding_category")
		if finding_category:
			dest.finding_category = finding_category

		metal_purity = resolve_attribute_value(f.get("Purity_Name"), "is_metal_purity")
		if metal_purity:
			dest.metal_purity = metal_purity

		dest.quantity = f.get("Weight")
		dest.rate = f.get("Rate")
		dest.amount = f.get("Amount")
		dest.se_rate = f.get("Costing_Rate")


def append_gemstone_detail_from_jwelex(product_order, stone_details):
	for s in stone_details:
		dest = product_order.append("gemstone_detail", {})

		stone_shape = resolve_attribute_value(s.get("Shape_Name"), "is_stone_shape")
		if stone_shape:
			dest.stone_shape = stone_shape

		gemstone_size = resolve_attribute_value(s.get("Size_Name"), "is_gemstone_size")
		if gemstone_size:
			dest.gemstone_size = gemstone_size

		dest.pcs = s.get("Pcs")
		dest.quantity = s.get("Weight")
		dest.total_gemstone_rate = s.get("Rate")
		dest.gemstone_rate_for_specified_quantity = s.get("Amount")
		dest.se_rate = s.get("Costing_Rate")


class ProductReturnOrderForm(Document):
	def get_data_from_jwelex(self,tag_no,company,is_sale):
		url = "http://3.108.219.130:8001/credit-note"

		response = requests.get(
			url,
			params={"tag_no": tag_no, "company": company, "is_sale": is_sale},
			timeout=30
		)

		if not response.ok:
			frappe.throw(
				f"Jwelex API rejected Tag No {frappe.bold(tag_no)} "
				f"({response.status_code}): {response.text}"
			)
		return response.json()
		
	def before_validate(self):
		
		gold_gst_rate = frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate")
		for row in self.items:
			if flt(row.physical_gross_weight) >flt(row.gross_weight):
				frappe.throw("Physical  GrossWeight should not be greater than Gross weight ")
			if flt(row.physical_net_weight) >flt(row.net_weight):
				frappe.throw("Physical Net Weight should not be greater than Net weight ")
		# 	row.rate = row.rate
		# 	row.amount = row.amount
		# 	row.base_rate=row.rate
		# 	row.base_amount = row.amount
		# for row in self.items:
		# for row in self.items:
		# 	bom_d = frappe.db.get_value("BOM", row.bom, "hallmarking_amount") or 0
		# 	bom_c = frappe.db.get_value("BOM", row.bom, "certification_amount") or 0
		# 	row.base_rate = row.rate
		# 	row.rate = row.base_rate
		# 	frappe.msgprint(f"{row.rate}")
		# 	hall_rate= row.rate-bom_d
		# 	certi_rate=row.rate-bom_c
		# 	frappe.msgprint(f"{row.rate},{certi_rate}")
		# 	if not self.product_hallmarking:
		# 		row.rate = hall_rate
		# 	else:
		# 		row.rate += hall_rate

		# 	if not self.product_certification:
		# 		row.rate = certi_rate
		# 	else:
		# 		row.rate += certi_rate
		for row in self.items:
			hallmarking_amount = frappe.db.get_value(
				"BOM", row.bom, "hallmarking_amount"
			) or 0

			certification_amount = frappe.db.get_value(
				"BOM", row.bom, "certification_amount"
			) or 0
			# frappe.throw(f"{certification_amount}")
			# Store original values only once
			if not row.base_rate:
				row.base_rate = row.rate
			else:
				row.rate=row.base_rate

			if not row.base_amount:
				row.base_amount = row.amount

			rate = row.base_rate
			amount = row.base_amount

			# Remove unchecked charges
			if not self.product_hallmarking:
				rate -= hallmarking_amount
				amount -= hallmarking_amount * row.qty

			if not self.product_certification:
				rate -= certification_amount
				amount -= certification_amount * row.qty

			row.rate = rate
			row.amount = amount
			# row.rate = rate
			# row.amount = rate
			# frappe.throw(f"{row.amount}")
		# for row in self.items:
			# # frappe.throw(f"fii{self.gold_rate_with_gst}")
			# if not row.metal_purity:
			# 	frappe.throw("Add Metal Purity")
			# if row.metal_purity:
			# 	row.rate=float(self.gold_rate_with_gst) *float( row.metal_purity)/((100 + int(gold_gst_rate)))
			# 	row.amount= row.rate
	def set_missing_tax_category_and_template(self):
		 
		# if self.sales_type not in ("Outright", "Outwork", "Branch Sales", "Hybrid"):
		# 	return
		# if self.tax_category and self.taxes_and_charges and self.get("taxes"):
		# 	return

		# customer_state = frappe.db.get_value("Address", self.customer_address, "gst_state_number")
		# company_state = frappe.db.get_value("Address", self.company_address, "gst_state_number")
		# if not customer_state or not company_state:
		# 	return

		# if not self.tax_category:
		# 	self.tax_category = "In-State" if customer_state == company_state else "Out-State"
		self.tax_category = "In-State"
		if not self.taxes_and_charges:
			taxes_and_charges = frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"company": self.company, "tax_category": self.tax_category, "disabled": 0},
				"name",
			)
			if not taxes_and_charges:
				frappe.log_error(
					f"No Sales Taxes and Charges Template found for "
					f"Company: {self.company}, Tax Category: {self.tax_category}",
					"set_missing_tax_category_and_template",
				)
				return
			self.taxes_and_charges = taxes_and_charges

		if not self.get("taxes"):
			tax_rows = frappe.get_all(
				"Sales Taxes and Charges",
				filters={"parent": self.taxes_and_charges},
				fields=["charge_type", "account_head", "description", "rate", "cost_center"],
				order_by="idx asc",
			)
			for t in tax_rows:
				self.append("taxes", {
					"charge_type": t.charge_type,
					"account_head": t.account_head,
					"description": t.description,
					"rate": t.rate,
					"cost_center": t.cost_center,
				})

	def calculate_sales_taxes_and_charges(self):
		"""
		Handle Outright / Outwork / Branch Sales / Hybrid GST for the
		credit note, mirroring the Sales Order pattern
		(sales_order/doc_events.set_gst_details / _set_hybrid_gst_details).
		"""
		# if self.sales_type not in ("Outright", "Outwork", "Branch Sales", "Hybrid"):
		# 	return
		# frappe.throw("hiii")
		if not self.items:
			return

		# Row rate/amount (including the hallmarking/certification toggle)
		# are already finalized by validate() before this runs — see the
		# row-finalization loop there. Nothing to reapply here.

		# --- tax category from customer/company state ---
		# customer_state = frappe.db.get_value("Address", self.customer_address, "gst_state_number")
		# company_state = frappe.db.get_value("Address", self.company_address, "gst_state_number")
		# if not customer_state or not company_state:
		# 	return

		self.tax_category = "In-State" 
		SALES_TYPE_ITEM_TAX_TEMPLATE = {
					"Finished Goods Return": {
						"Gurukrupa Export Private Limited": "GST 3% - GEPL",
						"KG GK Jewellers Private Limited": "GST 3% - KGJPL",
					},
					"Outright": {
											"Gurukrupa Export Private Limited": "GST 3% - GEPL",
											"KG GK Jewellers Private Limited": "GST 3% - KGJPL",
										},
					"Outwork": {
						"Gurukrupa Export Private Limited": "GST 5% - GEPL",
						"KG GK Jewellers Private Limited": "GST 5% - KGJPL",
					},
				}
		item_template_map = {
			**SALES_TYPE_ITEM_TAX_TEMPLATE,
			"Branch Sales": {"Gurukrupa Export Private Limited": "GST 3% - GEPL"},
		}
		# Hybrid borrows the Outright template for account-head selection only;
		# the real 3%/5% split is done in _set_hybrid_gst_details below.
		item_template_map["Hybrid"] = item_template_map["Outwork"]

		item_tax_template = item_template_map.get(self.invoice_sales_type, {}).get(self.company)
		# frappe.throw(f"{item_tax_template}")
		if not item_tax_template:
			return

		exempted_templates = ["Exempted - GEPL", "Exempted - KGJPL", "Exempted - SHC", "Exempted - SD"]
		if item_tax_template in exempted_templates:
			return

		taxes_and_charges = frappe.db.get_value(
			"Sales Taxes and Charges Template",
			{"company": self.company, "tax_category": self.tax_category, "disabled": 0},
			"name",
		)
		if not taxes_and_charges:
			frappe.log_error(
				f"No Sales Taxes and Charges Template found for "
				f"Company: {self.company}, Tax Category: {self.tax_category}",
				"calculate_sales_taxes_and_charges",
			)
			return

		self.taxes_and_charges = taxes_and_charges

		if self.invoice_sales_type == "Hybrid":
			self._set_hybrid_gst_details(item_tax_template)
			return

		# --- standard single-rate path (Outright / Outwork / Branch Sales) ---
		net_total = sum(flt(item.amount) for item in self.items)

		template_rates = frappe.get_all(
			"Item Tax Template Detail",
			filters={"parent": item_tax_template},
			fields=["tax_type", "tax_rate"],
		)

		self.sales_taxes_and_charges = []
		cumulative_total = net_total
		processed = []

		for r in template_rates:
			tax_type = r.tax_type or ""
			if "Output" not in tax_type or "RCM" in tax_type:
				continue
			if self.tax_category == "In-State" and "IGST" in tax_type:
				continue
			if self.tax_category != "In-State" and ("CGST" in tax_type or "SGST" in tax_type):
				continue
			if tax_type in processed:
				continue
			processed.append(tax_type)

			tax_rate = flt(r.tax_rate)
			tax_amount = net_total * (tax_rate / 100)
			cumulative_total += tax_amount

			self.append("sales_taxes_and_charges", {
				"charge_type": "On Net Total",
				"account_head": tax_type,
				"description": tax_type.split(" - ")[0] if " - " in tax_type else tax_type,
				"rate": tax_rate,
				"tax_amount": tax_amount,
				"total": cumulative_total,
			})

		self.total_taxes_and_charges = sum(flt(d.tax_amount) for d in self.sales_taxes_and_charges)
		self.grand_total = net_total + self.total_taxes_and_charges
		self.rounded_total = round(self.grand_total)
		self.rounding_adjustment = abs(self.rounded_total - self.grand_total)

	def _set_hybrid_gst_details(self, item_tax_template):
		HYBRID_ENABLED_COMPANIES=("KG GK Jewellers Private Limited",)
		if self.company not in HYBRID_ENABLED_COMPANIES:
			frappe.throw(_("Hybrid Sales Type is not yet enabled for company {0}").format(self.company))

		fg_rate = flt(frappe.db.get_value(
			"Sales Type Multiselect", {"parent": self.customer, "sales_type": "Outright"}, "tax_rate",
		))
		sc_rate = flt(frappe.db.get_value(
			"Sales Type Multiselect", {"parent": self.customer, "sales_type": "Outwork"}, "tax_rate",
		))

		total_owned = 0.0
		total_supplied = 0.0
		for item in self.items:
			owned = (
				flt(item.metal_amount) + flt(item.diamond_amount)
				+ flt(item.gemstone_amount) + flt(item.finding_amount)
				+ flt(item.hallmarking_amount) + flt(item.certification_amount)
			)
			supplied = flt(item.making_amount)
			# frappe.throw(f"{supplied}")
			item.custom_company_owned_amount = owned
			item.custom_customer_supplied_amount = supplied
			total_owned += owned
			total_supplied += supplied

		self.sales_taxes_and_charges = []
		tax_rows = frappe.get_all(
			"Sales Taxes and Charges",
			filters={"parent": self.taxes_and_charges},
			fields=["charge_type", "account_head", "description", "rate", "cost_center"],
			order_by="idx asc",
		)

		account_by_type = {}
		for t in tax_rows:
			head = t.account_head or ""
			if "IGST" in head:
				account_by_type.setdefault("IGST", t)
			elif "CGST" in head:
				account_by_type.setdefault("CGST", t)
			elif "SGST" in head:
				account_by_type.setdefault("SGST", t)

		# Accumulate Outright + Outwork portions per account head first, so
		# each account head (CGST/SGST/IGST) ends up as exactly one row —
		# same as a standard, non-Hybrid tax table — instead of one row per
		# Outright/Outwork portion. The rupee tax_amount is the exact,
		# correct combined total; the row's own "rate" is left at 0 rather
		# than a blended figure — same convention Sales Order's Hybrid
		# handling uses (clear_hybrid_header_tax_rate): a single row can't
		# truthfully state two different real rates, and a blended number
		# would just be a different kind of wrong one.
		merged_tax = {}

		def _add_tax_amount(account_key, amount):
			if not amount:
				return
			merged_tax.setdefault(account_key, 0.0)
			merged_tax[account_key] += amount

		if self.tax_category == "In-State":
			_add_tax_amount("CGST", round(total_owned * fg_rate / 2 / 100, 2))
			_add_tax_amount("SGST", round(total_owned * fg_rate / 2 / 100, 2))
			_add_tax_amount("CGST", round(total_supplied * sc_rate / 2 / 100, 2))
			_add_tax_amount("SGST", round(total_supplied * sc_rate / 2 / 100, 2))
		else:
			_add_tax_amount("IGST", round(total_owned * fg_rate / 100, 2))
			_add_tax_amount("IGST", round(total_supplied * sc_rate / 100, 2))

		net_total = total_owned + total_supplied
		for account_key, amount in merged_tax.items():
			template = account_by_type.get(account_key)
			if not template:
				continue
			self.append("sales_taxes_and_charges", {
				"charge_type": template.charge_type,
				"account_head": template.account_head,
				"description": template.description,
				"rate": 0,
				"cost_center": template.cost_center,
				"tax_amount": amount,
			})
		self.total_taxes_and_charges = sum(flt(d.tax_amount) for d in self.sales_taxes_and_charges)
		self.grand_total = net_total + self.total_taxes_and_charges
		self.rounded_total = round(self.grand_total)
		self.rounding_adjustment = abs(self.rounded_total - self.grand_total)

		# Blended per-item rate, same reasoning as the SO version: a single
		# credit-note row can't carry two distinct legal GST rates, so the
		# item shows a weighted-average rate while the header taxes table
		# carries the clean real-rate breakdown.
		for item in self.items:
			item.item_tax_template = item_tax_template
			owned = flt(item.custom_company_owned_amount)
			supplied = flt(item.custom_customer_supplied_amount)
			if self.tax_category == "In-State":
				cgst_amount = round(owned * fg_rate / 2 / 100 + supplied * sc_rate / 2 / 100, 2)
				item.cgst_amount = cgst_amount
				item.sgst_amount = cgst_amount
				item.igst_amount = 0.0
			else:
				igst_amount = round(owned * fg_rate / 100 + supplied * sc_rate / 100, 2)
				item.igst_amount = igst_amount
				item.cgst_amount = 0.0
				item.sgst_amount = 0.0

	# def calculate_taxes_and_totals(self):
	# 	self.calculate_sales_taxes_and_charges()
	def validate(self):
		# frappe.throw("hiii")
		# self.calculate_taxes_and_totals()
		gold_gst_rate = frappe.db.get_single_value(
			"Jewellery Settings", "gold_gst_rate"
		)

		SALES_TYPE_ITEM_TAX_TEMPLATE = {
			"Finished Goods Return": {
				"Gurukrupa Export Private Limited": "GST 3% - GEPL",
				"KG GK Jewellers Private Limited": "GST 3% - KGJPL",
			},
			"Outwork": {
				"Gurukrupa Export Private Limited": "GST 5% - GEPL",
				"KG GK Jewellers Private Limited": "GST 5% - KGJPL",
			},
		}

		HYBRID_OUTWORK_ITEM = "Subcontracting Charges"
		sc_template = SALES_TYPE_ITEM_TAX_TEMPLATE["Outwork"].get(self.company)

		# self.items = [
		# 	d for d in self.items
		# 	if not d.custom_is_subcontracting_charge_row
		# ]
		# for row in self.items:
		# 	row.rate = row.rate
		# 	row.amount = row.amount
		# 	frappe.throw(f"{row.amount}")
		# for row in self.items:
		# 	if not row.metal_purity:
		# 		frappe.throw("Add Metal Purity")
		# 	if row.metal_purity:
		# 		row.rate=float(self.gold_rate_with_gst) *float( row.metal_purity)/((100 + int(gold_gst_rate)))
		# 		row.amount= row.rate
		# if not self.is_jewlex_credit_note:
		# self.set_gst_details
		if self.credit_note_rate_type == "Current Rate":
			if not self.gold_rate_with_gst or not self.gold_rate:
				frappe.throw(
					"Gold rate with GST and Gold rate are mandatory for Current Rate calculation"
				)

		if not self.items: return

		# credit_note_mapping = {
		# 	("Return", "Sale Without Payment-Return"): self.apply_pcpm_manual_calculation,
		# 	("Return", "Sale With Payment-Return"): self.apply_bbpm_manual_calculation,
		# 	("Repair", "QC Fail-Repair"): self.apply_pcpm_manual_calculation,
		# 	("Repair", "Physical-Repair"): self.apply_physical_repair_manual_calculation,
		# 	("Consignment", "Finish Goods-Consignment"): self.apply_pcpm_manual_calculation,
		# 	("Consignment", "Raw Material-Consignment"): self.apply_consignment_raw_material_manual_calculation,
		# }

		self.return_material_type = '' # set only raw material-Consignment while calculation
		# calculation_function = credit_note_mapping.get((self.credit_note_type, self.return_subtype))

		# if calculation_function:
		# 	calculation_function()
		# else:
		# 	frappe.throw(
		# 		f"Invalid credit note type: {self.credit_note_type} / {self.return_subtype}"
		# 	)

		# else:
		trigger_pricing_calculation(self)

		# Backfill weight/pcs fields from the BOM for rows saved before these
		# fields existed on the row (e.g. serial_no was set before this
		# fetch was added) — only touches fields still at 0 on the row, and
		# only when the BOM actually has a non-zero value for it.
		for row in self.items:
			if not row.bom:
				continue
			bom_weights = None
			for field, bom_field in (
				("metal_weight", "metal_weight"),
				("finding_weight", "finding_weight"),
				("gemstone_weight", "gemstone_weight"),
				("diamond_pcs", "total_diamond_pcs"),
				("gemstone_pcs", "total_gemstone_pcs"),
			):
				if flt(row.get(field)):
					continue
				if bom_weights is None:
					bom_weights = frappe.db.get_value(
						"BOM", row.bom,
						["metal_weight", "finding_weight", "gemstone_weight", "total_diamond_pcs", "total_gemstone_pcs"],
						as_dict=True,
					) or {}
				if flt(bom_weights.get(bom_field)):
					row.set(field, bom_weights.get(bom_field))

		self.metal_weight = sum(flt(row.metal_weight) for row in self.items)
		self.diamond_weight = sum(flt(row.diamond_weight) for row in self.items)
		self.finding_weight = sum(flt(row.finding_weight) for row in self.items)
		self.gemstone_weight = sum(flt(row.gemstone_weight) for row in self.items)
		self.diamond_pcs = sum(flt(row.diamond_pcs) for row in self.items)
		self.gemstone_pcs = sum(flt(row.gemstone_pcs) for row in self.items)

		if self.invoice_sales_type == "Hybrid":
			gst_hsn_code = frappe.db.get_value("Item", HYBRID_OUTWORK_ITEM, "gst_hsn_code")

			total_making_charge = 0
			for row in self.items:
				if row.item_code == HYBRID_OUTWORK_ITEM:
					continue
				total_making_charge += frappe.db.get_value("BOM", row.bom, "making_charge") or 0
				# The making charge moves onto the Subcontracting Charges row
				# below — zero it here so it isn't also counted a second time
				# inside this row's own rate/amount (row finalization below
				# sums row.making_amount into rate/amount for every row).
				row.making_amount = 0

			if self.making_charges_type == "Without":
				total_making_charge = 0
			elif self.making_charges_type == "Half":
				total_making_charge = total_making_charge * 0.5

			sc_row = next((d for d in self.items if d.item_code == HYBRID_OUTWORK_ITEM), None)
			if not sc_row:
				sc_row = self.append("items", {
					"item_code": HYBRID_OUTWORK_ITEM,
					"item_name": HYBRID_OUTWORK_ITEM,
					"description": HYBRID_OUTWORK_ITEM,
					"qty": 1,
					"uom": "Nos",
					"gst_hsn_code": gst_hsn_code,
					"item_tax_template": sc_template,
					"custom_is_subcontracting_charge_row": 1,
				})

			# Own making_amount (not just rate/amount) so _set_hybrid_gst_details
			# picks this row up as the "supplied" (Outwork) portion — it sums
			# item.making_amount across all rows, and this row is otherwise
			# invisible to that total.
			sc_row.rate = total_making_charge
			sc_row.amount = total_making_charge
			sc_row.making_amount = total_making_charge

		# Finalize each row's rate/amount from its own component fields —
		# metal/diamond/finding/gemstone/making are already set by
		# trigger_pricing_calculation() above (or by the Hybrid block just
		# above for the Subcontracting Charges row). Hallmarking/certification
		# are pulled from BOM here (the one place they're set for BOM-based
		# rows) and folded in only if the corresponding toggle is on. This
		# runs BEFORE total_amount/e-invoice/tax so those are always computed
		# from each row's final number, not a stale one.
		for row in self.items:
			if row.bom:
				row.hallmarking_amount = frappe.db.get_value("BOM", row.bom, "hallmarking_amount") or 0
				row.certification_amount = frappe.db.get_value("BOM", row.bom, "certification_amount") or 0

			rate = (
				flt(row.metal_amount)
				+ flt(row.diamond_amount)
				+ flt(row.finding_amount)
				+ flt(row.gemstone_amount)
				+ flt(row.making_amount)
				+ (flt(row.hallmarking_amount) if self.product_hallmarking else 0)
				+ (flt(row.certification_amount) if self.product_certification else 0)
			)
			row.rate = rate
			row.amount = rate * flt(row.qty or 1)
			row.base_rate = rate
			row.base_amount = row.amount

		self.total_amount = sum(flt(row.amount) for row in self.items)

		validate_e_invoice_items(self)

		self.calculate_taxes_and_totals()
		self.set_total_in_words()
		# for row in self.items:
		# 	bom_d = frappe.db.get_value("BOM", row.bom, "hallmarking_amount") or 0
		# 	bom_c = frappe.db.get_value("BOM", row.bom, "certification_amount") or 0

		# 	rate = row.base_rate

		# 	if not self.product_hallmarking:
		# 		rate -= bom_d
		# 	else:
		# 		rate += bom_d

		# 	if not self.product_certification:
		# 		rate -= bom_c
		# 	else:
		# 		rate += bom_c

		# 	row.rate = rate
		# 	row.amount = rate
			# frappe.throw(f"{row.amount}")
		# ===================================================================
		# for row in self.items:
		
		# 	data = self.get_data_from_jwelex(row.tag_no)

		# 	customer = data["customer_info"]["customer_name"]
		# 	frappe.throw(f"{customer}")
	

	def update_einvoice_items(self, invoice_data, payment_terms_data,allowed_item_types):
		frappe.throw("hii")
		if not self.get("invoice_item"):
			self.invoice_item = []
		else:
			self.set("invoice_item", [])
		precision = frappe.db.get_value('Customer',self.customer,"custom_precision_variable")
		for row in invoice_data:
			if row not in allowed_item_types:
				continue
			if invoice_data[row]["amount"] >= 0:
				if payment_terms_data.get(row):
					payment_terms_data[row] += round(invoice_data[row]["amount"], precision)
				else:
					payment_terms_data[row] = round(invoice_data[row]["amount"], precision)
				self.append(
					"invoice_item",
					{
						"item_code": row,
						"item_name": row,
						"uom": invoice_data[row]["uom"] or "Nos",
						"gst_hsn_code": invoice_data[row]["hsn_code"],
						"conversion_factor": 1,
						"qty": invoice_data[row]["qty"],
						"rate": invoice_data[row].get("rate", 0),
						"base_rate": invoice_data[row].get("rate", 0),
						"amount": flt(invoice_data[row]["amount"], 3),
						"base_amount": invoice_data[row]["amount"],
						"income_account": invoice_data[row]["income_account"],
						"cost_center": invoice_data[row]["cost_center"],
					},
				)

	def update_bom_details(self, row, bom_doc, is_branch_customer, invoice_data, gold_rate_changed=True):
		gold_item = None
		gold_making_item = None
		bom_doc.customer = self.customer
		precision = frappe.db.get_value("Customer", self.customer, "custom_precision_variable")
		so_doc = frappe.get_doc("Sales Order", row.sales_order)
		so_item_map = {}
		for item in so_doc.custom_invoice_item:
			# frappe.throw("hiii")
			so_item_map[item.item_code] = item

		def add_to_invoice(item_code, so_item, fallback_amount=0, fallback_qty=0,fallback_rate=0, hsn=None, uom=None):

			if so_item:
				amount = so_item.amount
				qty = so_item.qty
				rate = so_item.rate
			else:
				amount = fallback_amount
				qty = fallback_qty
				rate = fallback_rate

			if item_code in invoice_data:
				if so_item:
					frappe.throw(f"{qty}")
					invoice_data[item_code]["amount"] = amount
					invoice_data[item_code]["qty"] = qty
					invoice_data[item_code]["rate"] = rate
				else:
					# fallback case → can accumulate
					invoice_data[item_code]["amount"] += amount
					invoice_data[item_code]["qty"] += qty
					invoice_data[item_code]["rate"] = rate
			else:
				invoice_data[item_code] = {
					"amount": amount,
					"qty": qty,
					"rate": rate,
					"hsn_code": hsn,
					"uom": uom,
					"income_account": row.income_account,
					"cost_center": row.cost_center,
				}
		for i in bom_doc.metal_detail:
			update_making_charges(row, bom_doc, i, self.gold_rate_with_gst) 
			einvoice_item, hsn_code, uom = frappe.db.get_value(
				"E Invoice Item",
				{
					"is_for_metal": 1,
					"metal_type": i.metal_type,
					"metal_purity": i.metal_touch,
				},
				["name", "hsn_code", "uom"],
			) or (None, None, None)

			# Hybrid: making charge is always job-work value (Outwork rate),
			# regardless of is_customer_item — same rule as validate_item_dharm()
			# in sales_order.py.
			filter_value = (
				"is_for_labour"
				if (i.is_customer_item or self.sales_type == "Hybrid")
				else "is_for_making"
			)

			making_item, making_hsn, making_uom = frappe.db.get_value(
				"E Invoice Item",
				{
					filter_value: 1,
					"metal_type": i.metal_type,
					"metal_purity": i.metal_touch,
				},
				["name", "hsn_code", "uom"],
			) or (None, None, None)

			so_metal = so_item_map.get(einvoice_item)
			so_making = so_item_map.get(making_item)

			if einvoice_item and not i.is_customer_item:
				add_to_invoice(
					einvoice_item,
					so_metal,
					fallback_amount=round(i.amount,precision),
					fallback_qty=i.quantity,

					fallback_rate=i.rate,
					hsn=hsn_code,
					uom=uom,
				)

			if making_item and not is_branch_customer:
				is_metal_per_pc = (
					flt(i.making_rate) > 0
					and abs(flt(i.making_amount) - flt(i.making_rate)) < 0.01
				)
				making_amount_with_wastage = flt(i.making_amount) + flt(i.wastage_amount)
				# metal_making_qty = 1 if is_metal_per_pc else i.quantity
				add_to_invoice(
					making_item,
					so_making,
					fallback_amount=round(making_amount_with_wastage,precision),
					fallback_qty=i.quantity,
					fallback_rate=i.making_rate,
					hsn=making_hsn,
					uom=making_uom,
				)

			if i.is_customer_item:
				self.is_customer_metal = True


		for i in bom_doc.finding_detail:
			update_making_charges(row, bom_doc, i, self.gold_rate_with_gst)
			einvoice_item = hsn_code = uom = None

			# ---------------- Finding amount: category-specific match ----------------
			result = frappe.db.get_value(
				"E Invoice Item",
				{
					"is_for_finding": 1,
					"metal_type": i.metal_type,
					"metal_purity": i.metal_touch,
					"finding_category": i.finding_category,
				},
				["name", "hsn_code", "uom"],
			)
			if result:
				einvoice_item, hsn_code, uom = result
			else:
				# FIXED: fallback must only match a genuinely generic record
				# (finding_category is unset) — not just any record sharing
				# metal_type/metal_purity, which could accidentally be a
				# different category's record.
				result = frappe.db.get_value(
					"E Invoice Item",
					{
						"is_for_metal": 1,
						"metal_type": i.metal_type,
						"metal_purity": i.metal_touch,
						"finding_category": ["is", "not set"],
					},
					["name", "hsn_code", "uom"],
				)
				if result:
					einvoice_item, hsn_code, uom = result

			# Hybrid: making charge is always job-work value (Outwork rate),
			# regardless of is_customer_item — same rule as validate_item_dharm()
			# in sales_order.py.
			filter_value = (
				"is_for_labour"
				if (i.is_customer_item or self.sales_type == "Hybrid")
				else "is_for_finding_making"
			)

			making_item = making_hsn = making_uom = None

			# ---------------- Making charge: category-specific match ----------------
			result = frappe.db.get_value(
				"E Invoice Item",
				{
					# "is_for_metal": 1,
					filter_value:1,
					"metal_type": i.metal_type,
					"metal_purity": i.metal_touch,
					"finding_category": i.finding_category,
				},
				["name", "hsn_code", "uom"],
			)
			if result:
				making_item, making_hsn, making_uom = result
			else:
				# Fallback mirrors the SO's behavior — drop into the generic
				# metal bucket for whichever filter_value we resolved above
				# (is_for_labour for Hybrid/customer-supplied, is_for_making
				# otherwise), not hardcoded to is_for_making, so Hybrid making
				# charges don't fall back into the Outright-taxed bucket.
				fallback_filter_value = (
					"is_for_labour"
					if (i.is_customer_item or self.sales_type == "Hybrid")
					else "is_for_making"
				)
				result = frappe.db.get_value(
					"E Invoice Item",
					{
						fallback_filter_value: 1,
						"metal_type": i.metal_type,
						"metal_purity": i.metal_touch,
					},
					["name", "hsn_code", "uom"],
				)
				if result:
					making_item, making_hsn, making_uom = result

			so_finding = so_item_map.get(einvoice_item)
			so_making = so_item_map.get(making_item)

			if einvoice_item and not i.is_customer_item:
				add_to_invoice(
					einvoice_item,
					so_finding,
					fallback_amount=round(i.amount,precision),
					fallback_qty=i.quantity,
					fallback_rate=i.rate,
					hsn=hsn_code,
					uom=uom,
				)

			if making_item:
				making_amount_with_wastage = flt(i.making_amount) + flt(i.wastage_amount)
				add_to_invoice(
					making_item,
					so_making,
					fallback_amount=round(making_amount_with_wastage,precision),
					fallback_qty=i.quantity,
					fallback_rate=i.making_rate,
					hsn=making_hsn,
					uom=making_uom,
				)
			if i.is_customer_item:
				self.is_customer_metal = True

		for i in bom_doc.diamond_detail:		
			einvoice_item = hsn_code = uom = None
			result = frappe.db.get_value(
				"E Invoice Item",
				{
					"is_for_diamond": 1,
					"diamond_type": i.diamond_type
				},
				["name", "hsn_code", "uom"],
			)

			if result:
				einvoice_item, hsn_code, uom = result
			else:
				continue  

			so_item = so_item_map.get(einvoice_item)

			if so_item:
				amount = so_item.amount
				qty = so_item.qty
				rate = so_item.rate

			else:
				amount = _calculate_diamond_amount(bom_doc, i, {}, {})
				if is_branch_customer:
					amount = i.se_rate * i.quantity

				qty = i.quantity
				rate = 0

			if not i.is_customer_item:
				if einvoice_item in invoice_data:
					invoice_data[einvoice_item]["amount"] = round(amount , precision)
					invoice_data[einvoice_item]["qty"] = qty
				else:
					invoice_data[einvoice_item] = {
						"amount": amount,
						"qty": qty,
						"rate": rate,
						"hsn_code": hsn_code,
						"uom": uom,
						"income_account": row.income_account,
						"cost_center": row.cost_center,
					}

			if self.sales_type == "Hybrid":
				# Handling charge is always job-work value, whether the stone
				# is company-owned or customer-supplied — route it to the same
				# labour/Subcontracting bucket used for metal/finding making
				# above (mirrors the diamond handling split added to
				# validate_item_dharm() in sales_order.py). Not filtered by uom —
				# "Subcontracting Income" is Gram-based even though diamonds
				# are Carat, matching the existing is_for_labour convention
				# elsewhere in this function.
				labour_item, labour_hsn, labour_uom = frappe.db.get_value(
					"E Invoice Item",
					{"is_for_labour": 1},
					["name", "hsn_code", "uom"],
				) or (None, None, None)
				if labour_item:
					so_labour = so_item_map.get(labour_item)
					handling_amount = round(flt(i.quantity) * flt(i.handling_rate), precision)
					add_to_invoice(
						labour_item,
						so_labour,
						fallback_amount=handling_amount,
						fallback_qty=i.quantity,
						fallback_rate=i.handling_rate,
						hsn=labour_hsn,
						uom=labour_uom,
					)

			if i.is_customer_item:
				self.is_customer_diamond = True
		for i in bom_doc.gemstone_detail:

			einvoice_item, hsn_code, uom = frappe.db.get_value(
				"E Invoice Item",
				{"is_for_gemstone": 1},
				["name", "hsn_code", "uom"],
			) or (None, None, None)

			if not einvoice_item:
				continue

			so_item = so_item_map.get(einvoice_item)

			if so_item:
				amount = so_item.amount
				qty = so_item.qty
				rate = so_item.rate
			else:
			
				amount = i.gemstone_rate_for_specified_quantity
				qty = i.quantity
				rate = i.total_gemstone_rate

				if is_branch_customer:
					amount = i.se_rate * i.quantity
					rate = i.se_rate

		
			if einvoice_item and not i.is_customer_item:
				if so_item_map.get(einvoice_item):
					invoice_data[f"{einvoice_item}"] = {
						"amount": so_item_map[einvoice_item].amount,
						"qty": so_item_map[einvoice_item].qty,
						"rate": so_item_map[einvoice_item].rate,
						"hsn_code": hsn_code,
						"uom": uom,
						"income_account": row.income_account,
						"cost_center": row.cost_center,
					}
				else:
					invoice_data[f"{einvoice_item}"] = {
						"amount": amount,
						"qty": i.quantity,
						"rate": i.rate,
						"hsn_code": hsn_code,
						"uom": uom,
						"income_account": row.income_account,
						"cost_center": row.cost_center,
					}

			if i.is_customer_item:
				self.is_customer_gemstone = True
	
		bom_doc.gold_rate_with_gst = self.gold_rate_with_gst
		customer_group=frappe.db.get_value('Customer',self.customer,'customer_group')
		if not (self.company == "KG GK Jewellers Private Limited" or customer_group == "Internal"):
			bom_doc.validate()
			bom_doc.save()
			# update_totals("BOM", bom_doc.name)

	def on_submit(self):

		# if self.yu: return

		# items reqd
		if not self.items:
			frappe.throw("Items are mandatory for credit note")
		index = self.idx + 1
		
		for item_row in self.items:
			jewelex_data = None
			bom = None
			if item_row.item_code == 'Subcontracting Charges':
				continue
			jewelex_company = "KGPL" if self.ref_company == "KG" else "GEPL"
			if item_row.jewelex_tag and item_row.is_sale:
				jewelex_data = self.get_data_from_jwelex(item_row.jewelex_tag,jewelex_company,1)
			elif item_row.jewelex_tag and not item_row.is_sale:
				jewelex_data = self.get_data_from_jwelex(item_row.jewelex_tag,jewelex_company,0)
			elif item_row.serial_no:
				bom_name = frappe.db.get_value("Serial No", item_row.serial_no, "custom_bom_no")
				if not bom_name:
					frappe.throw(f"BOM not found against Serial No {frappe.bold(item_row.serial_no)}")
				# bom = frappe.get_doc("BOM", bom_name)
			# else:
				bom = frappe.get_doc("BOM", item_row.bom)

			product_order = frappe.new_doc("Product Return Order")
			product_order.customer = self.customer
			product_order.company = self.company
			product_order.branch = self.branch
			product_order.return_subtype = self.return_subtype
			product_order.return_type = self.credit_note_type
			product_order.sales_type = self.sales_type
			product_order.credit_note_rate_type=self.credit_note_rate_type
			product_order.product_return_order_form = self.name
			product_order.gold_rate_with_gst = self.gold_rate_with_gst
			product_order.gold_rate = self.gold_rate
			product_order.making_charges = self.making_charges_type
			product_order.making_charges=self.making_charges_type
			product_order.custom_making_charges = self.custom_making_charges
			product_order.gemstone_charges=self.gemstone_charges
			product_order.custom_gemstones_charges = self.custom_gemstones_charges

			product_order.custom_wastage_charges = self.custom_wastage_charges
			product_order.wastage_charges = self.wastage_charges
			product_order.custom_handling_charges = self.custom_handling_charges
			product_order.handling_charges = self.handling_charges
			product_order.diamond_rate_type=self.diamond_rate_type

			product_order.index =index
			index += 1

			product_order.item_code = item_row.item_code
			product_order.item_name = item_row.item_name
			product_order.is_jewelex_tag = item_row.is_jewelex_tag
			product_order.jewelex_tag = item_row.jewelex_tag
			# product_order.bom = bom.name if bom else item_row.bom
			product_order.bom = item_row.bom
			product_order.serial_no = item_row.serial_no
			product_order.hsn_sac = item_row.hsn_sac
			product_order.item_group = item_row.item_group
			product_order.item_category = item_row.item_category
			product_order.description = item_row.description
			product_order.uom = item_row.uom
			product_order.physical_net_weight = item_row.physical_net_weight
			product_order.physical_gross_weight = item_row.physical_gross_weight
			product_order.sales_invoice = item_row.sales_invoice
			product_order.sales_invoice_item = item_row.sales_invoice_item
			product_order.warehouse = item_row.warehouse
			product_order.rate = item_row.rate
			product_order.making_amount = item_row.making_amount
			product_order.metal_amount = item_row.metal_amount
			product_order.diamond_amount = item_row.diamond_amount
			product_order.finding_amount = item_row.finding_amount
			product_order.gemstone_amount = item_row.gemstone_amount
			product_order.hallmarking_amount = item_row.hallmarking_amount
			product_order.certification_amount = item_row.certification_amount
			product_order.net_weight = item_row.net_weight
			product_order.gross_weight = item_row.gross_weight
			product_order.physical_gross_weight = item_row.physical_gross_weight
			product_order.physical_net_weight = item_row.physical_net_weight
			product_order.diamond_weight = item_row.diamond_weight
			product_order.metal_touch = item_row.metal_touch
			product_order.metal_colour = item_row.metal_colour
			product_order.item_subcategory = item_row.item_subcategory
			product_order.metal_purity = item_row.metal_purity
			product_order.setting_type = item_row.setting_type
			product_order.amount = item_row.amount

			system_fields = {
				"name", "parent", "parentfield", "parenttype",
				"doctype", "idx", "owner", "creation",
				"modified", "modified_by", "docstatus"
			}
			child_tables = [
				"metal_detail",
				"finding_detail",
				"diamond_detail",
				"gemstone_detail",
				"other_detail"
			]

			if bom:
				for table in child_tables:
					for src in getattr(bom, table):
						dest = product_order.append(table, {})

						for key, value in src.as_dict().items():
							if key not in system_fields:
								dest.set(key, value)

			if jewelex_data:
				materials = jewelex_data.get("materials", {})
				summary_totals = jewelex_data.get("summary_totals", {})
				totals = jewelex_data.get("totals", {})
				charges_info = jewelex_data.get("charges_info", {})

				if summary_totals.get("gross_wt") is not None:
					product_order.gross_weight = summary_totals.get("gross_wt")

				product_order.metal_amount = totals.get("metal_totals", {}).get("total_amount")
				product_order.diamond_amount = totals.get("diamond_totals", {}).get("total_amount")
				product_order.gemstone_amount = totals.get("stone_totals", {}).get("total_amount")
				product_order.finding_amount = totals.get("finding_totals", {}).get("total_amount")
				product_order.other_material_amount = totals.get("other_totals", {}).get("total_amount")

				product_order.making_amount = flt(charges_info.get("metal_making_amount")) + flt(charges_info.get("chain_making_amount"))
				product_order.certification_amount = charges_info.get("certificate_charges")
				product_order.hallmarking_amount = charges_info.get("hm_charges")

				product_order.set("metal_detail", [])
				append_metal_detail_from_jwelex(product_order, materials.get("metal_details", []))

				product_order.set("diamond_detail", [])
				append_diamond_detail_from_jwelex(product_order, materials.get("diamond_details", []))

				product_order.set("finding_detail", [])
				append_finding_detail_from_jwelex(product_order, materials.get("finding_details", []))

				product_order.set("gemstone_detail", [])
				append_gemstone_detail_from_jwelex(product_order, materials.get("stone_details", []))

				product_order.total_finding_pcs = len(materials.get("finding_details", []))
				product_order.total_gemstone_pcs = len(materials.get("stone_details", []))
				product_order.total_diamond_pcs = sum(
					(d.get("Pcs") or 0) for d in materials.get("diamond_details", [])
				)
			else:
				product_order.total_finding_pcs = bom.finding_pcs
				product_order.total_finding_pcs = 1
				product_order.total_gemstone_pcs = bom.total_gemstone_pcs
				product_order.total_diamond_pcs = bom.total_diamond_pcs


			product_order.insert(ignore_permissions=True)
			product_order.save()
			# If Tag No then Skip
			if item_row.tag_no:
				continue

			if not item_row.is_jewelex_tag and not item_row.jewelex_tag:
				if not item_row.sales_invoice_item or not item_row.sales_invoice:
					frappe.throw(f"Sales Invoice Item or Sales Invoice is mandatory for item {frappe.bold(item_row.item_code)}")

				if not item_row.qty:
					frappe.throw(f"Quantity is mandatory for item {frappe.bold(item_row.item_code)}")

				if not item_row.rate:
					frappe.throw(f"Rate is mandatory for item {frappe.bold(item_row.item_code)}")

				sales_invoice_item = frappe.db.get_value("Sales Invoice Item", item_row.sales_invoice_item, ["warehouse"], as_dict=1)
				warehouse = sales_invoice_item.get("warehouse")

				if not warehouse: # warning msg : Warehouse not found from Sales invoice so we can't create active BOM and serial no
					frappe.throw(f"Ware house not found for item {frappe.bold(item_row.item_code)}")

				serial_no_doc = frappe.get_doc("Serial No", item_row.get("serial_no"))
				bom_doc = frappe.get_doc("BOM", item_row.get("bom"))

				if not serial_no_doc:
					frappe.throw(f"Serial No not found for item {frappe.bold(item_row.item_code)}")

			# # Active Serial No
			# # frappe.db.set_value("Serial No", item_row.get("serial_no"), {"status": "Active","warehouse": warehouse})

			# # Update BOM
			# frappe.db.set_value("BOM", item_row.get("bom"), "is_active", 1)

		self.db_set("status", "Approved")
		# self.create_return_sales_invoices()

	@frappe.whitelist()
	def create_return_sales_invoices(self):
		"""Create Return Sales Invoices (Credit Notes) grouped by Sales Invoice.

		Builds return invoices from scratch using frappe.new_doc with all
		item data sourced from the Product Return Form. Does NOT use
		ERPNext's make_return_doc.
		"""

		# Group child table rows by sales_invoice
		si_items_map = defaultdict(list)
		for row in self.items:
			if row.tag_no: # skip jwelex 
				continue
			if row.sales_invoice and row.sales_invoice_item:
				si_items_map[row.sales_invoice].append(row)

		if not si_items_map:
			return

		created_invoices = []

		return_sales_invoices_map = {}

		try:
			for si_name, return_rows in si_items_map.items():
				# Validate the source Sales Invoice exists and is submitted
				if not frappe.db.exists("Sales Invoice", si_name):
					frappe.throw(f"Sales Invoice {frappe.bold(si_name)} not found")

				# Fetch original invoice header fields
				original_si = frappe.get_doc("Sales Invoice", si_name)

				if original_si.docstatus != 1:
					frappe.throw(f"Sales Invoice {frappe.bold(si_name)} is not submitted")

				# Create return Sales Invoice
				return_doc = frappe.new_doc("Sales Invoice")

				# Copy header fields from original invoice
				return_doc.customer = original_si.customer
				return_doc.company = original_si.company
				return_doc.posting_date = self.date or original_si.posting_date
				return_doc.posting_time = self.posting_time or original_si.posting_time
				return_doc.set_posting_time = 1

				# Return / Credit Note flags
				return_doc.is_return = 1
				return_doc.update_stock = 0
				return_doc.update_billed_amount_in_sales_order = 0
				return_doc.update_billed_amount_in_delivery_note = 0
				return_doc.update_outstanding_for_self = 0

				# Copy key fields from original invoice
				return_doc.currency = original_si.currency
				return_doc.conversion_rate = original_si.conversion_rate
				return_doc.selling_price_list = original_si.selling_price_list
				return_doc.price_list_currency = original_si.price_list_currency
				return_doc.plc_conversion_rate = original_si.plc_conversion_rate
				return_doc.debit_to = original_si.debit_to
				return_doc.customer_address = original_si.customer_address
				return_doc.company_address = original_si.company_address
				return_doc.shipping_address_name = original_si.shipping_address_name
				return_doc.cost_center = original_si.cost_center
				return_doc.tax_category = original_si.tax_category
				return_doc.taxes_and_charges = original_si.taxes_and_charges
				return_doc.ignore_pricing_rule = 1

				# Copy custom fields from original invoice if they exist
				for field in ["sales_type", "branch", "gold_rate", "gold_rate_with_gst"]:
					if hasattr(self, field) and hasattr(return_doc, field):
						return_doc.set(field, self.get(field))

				# Add items from Product Return Form
				for prf_row in return_rows:
					# Validate return qty does not exceed original qty
					original_qty = frappe.db.get_value(
						"Sales Invoice Item", prf_row.sales_invoice_item, "qty"
					)
					if flt(prf_row.qty) > flt(original_qty):
						frappe.throw(
							f"Return qty ({prf_row.qty}) exceeds original invoice qty "
							f"({original_qty}) for item {frappe.bold(prf_row.item_code)} "
							f"in Sales Invoice {frappe.bold(si_name)}"
						)

					# Get original SI item for fields not in PRF
					original_item = frappe.db.get_value(
						"Sales Invoice Item", prf_row.sales_invoice_item,
						["income_account", "cost_center", "warehouse",
						"expense_account", "conversion_factor", "uom",
						"stock_uom", "description", "item_name",
						"item_group", "gst_hsn_code", "serial_no","sales_order"],
						as_dict=True
					)
					si_item = frappe.get_doc("Sales Invoice Item", prf_row.sales_invoice_item)
					# print(si_item.as_dict())
					# frappe.throw(f"{si_item.as_dict()}")
					# Populate and set accounting fields explicitly for GL entries
					amount = flt(-1 * abs(flt(prf_row.amount)), return_doc.precision("amount", "items"))
					rate = flt(prf_row.rate, return_doc.precision("rate", "items"))
					base_amount = flt(-1 * abs(flt(prf_row.base_amount or prf_row.amount)), return_doc.precision("base_amount", "items"))
					base_rate = flt(prf_row.base_rate or prf_row.rate, return_doc.precision("base_rate", "items"))

					return_doc.append("items", {
						"item_code": prf_row.item_code,
						"item_name": original_item.get("item_name") or prf_row.get("item_name"),
						"description": original_item.get("description") or prf_row.get("description"),
						"gst_hsn_code": original_item.get("gst_hsn_code") or prf_row.get("hsn_sac"),
						"uom": prf_row.get("uom") or original_item.get("uom") or "Nos",
						"stock_uom": original_item.get("stock_uom") or prf_row.get("uom") or "Nos",
						"conversion_factor": original_item.get("conversion_factor") or 1,
						"qty": -1 * abs(flt(prf_row.qty)),
						"stock_qty": -1 * abs(flt(prf_row.qty)) * flt(original_item.get("conversion_factor") or 1),
						"rate": rate,
						"amount": amount,
						"base_rate": base_rate,
						"base_amount": base_amount,
						"net_rate": rate,
						"net_amount": amount,
						"base_net_rate": base_rate,
						"base_net_amount": base_amount,
						"income_account": original_item.get("income_account"),
						"expense_account": original_item.get("expense_account"),
						"cost_center": original_item.get("cost_center"),
						"sales_order": original_item.get("sales_order"),
						"warehouse": original_item.get("warehouse") or prf_row.get("warehouse"),
						"serial_no": prf_row.serial_no,
						"bom": prf_row.bom,
						"metal_amount": flt(prf_row.metal_amount, return_doc.precision("metal_amount", "items")),
						"diamond_amount": flt(prf_row.diamond_amount, return_doc.precision("diamond_amount", "items")),
						"finding_amount": flt(prf_row.finding_amount, return_doc.precision("finding_amount", "items")),
						"making_amount": flt(prf_row.making_amount, return_doc.precision("making_amount", "items")),
						"gemstone_amount": flt(prf_row.gemstone_amount, return_doc.precision("gemstone_amount", "items")),
						"certification_amount": flt(prf_row.certification_amount, return_doc.precision("certification_amount", "items")),
						"freight_amount": flt(prf_row.freight_amount, return_doc.precision("freight_amount", "items")),
						"other_material_amount": flt(prf_row.other_material_amount, return_doc.precision("other_material_amount", "items")),
						"hallmarking_amount": flt(prf_row.hallmarking_amount, return_doc.precision("hallmarking_amount", "items")),
						"custom_duty_amount": flt(prf_row.custom_duty_amount, return_doc.precision("custom_duty_amount", "items")),
						"other_amount": flt(prf_row.other_amount, return_doc.precision("other_amount", "items")),
					})

				# Add taxes from Product Return Form
				for tax_row in self.sales_taxes_and_charges:
					tax_amount = flt(-1 * abs(flt(tax_row.tax_amount)), return_doc.precision("tax_amount", "taxes"))
					base_tax_amount = flt(tax_amount * (return_doc.conversion_rate or 1.0), return_doc.precision("base_tax_amount", "taxes"))
					
					return_doc.append("taxes", {
						"charge_type": tax_row.charge_type or "Actual",
						"account_head": tax_row.account_head,
						"rate": tax_row.rate,
						"tax_amount": tax_amount,
						"base_tax_amount": base_tax_amount,
						"tax_amount_after_discount_amount": tax_amount,
						"base_tax_amount_after_discount_amount": base_tax_amount,
						"description": tax_row.description,
						"cost_center": tax_row.get("cost_center"),
						"included_in_print_rate": tax_row.get("included_in_print_rate"),
					})

				# Calculate and set totals manually to satisfy MandatoryError
				# (Since we skip validate() which would normally calculate these)
				net_total = flt(sum(flt(item.amount) for item in return_doc.items), return_doc.precision("net_total"))
				base_net_total = flt(sum(flt(item.base_amount) for item in return_doc.items), return_doc.precision("base_net_total"))
				
				# Ensure conversion_rate matches the ratio of base_net_total to net_total
				# to prevent precision loss GL entries which cause imbalance
				if abs(net_total) > 0.001:
					return_doc.conversion_rate = flt(abs(base_net_total / net_total), 9)
				
				total_taxes = flt(sum(flt(tax.tax_amount) for tax in return_doc.taxes), return_doc.precision("total_taxes_and_charges"))
				base_total_taxes = flt(sum(flt(tax.base_tax_amount) for tax in return_doc.taxes), return_doc.precision("base_total_taxes_and_charges"))
				
				grand_total = flt(net_total + total_taxes, return_doc.precision("grand_total"))
				base_grand_total = flt(base_net_total + base_total_taxes, return_doc.precision("base_grand_total"))
				total_qty = sum(flt(item.qty) for item in return_doc.items)

				return_doc.total = net_total
				return_doc.base_total = base_net_total
				return_doc.net_total = net_total
				return_doc.base_net_total = base_net_total
				return_doc.total_qty = total_qty
				
				return_doc.total_taxes_and_charges = total_taxes
				return_doc.base_total_taxes_and_charges = base_total_taxes
				
				return_doc.grand_total = grand_total
				return_doc.base_grand_total = base_grand_total
				
				# Explicitly set rounding to 0 to avoid balancing issues
				return_doc.rounding_adjustment = 0
				return_doc.base_rounding_adjustment = 0
				return_doc.rounded_total = 0
				return_doc.base_rounded_total = 0

				# Set against_income_account manually for GL entries
				income_accounts = list(set([item.income_account for item in return_doc.items if item.income_account]))
				return_doc.against_income_account = ", ".join(income_accounts)

				# Ensure party account currency is available for GL entries
				if original_si.get("party_account_currency"):
					return_doc.party_account_currency = original_si.party_account_currency
				else:
					# Fallback to company currency if not found
					from erpnext.accounts.utils import get_account_currency
					return_doc.party_account_currency = get_account_currency(return_doc.debit_to) or return_doc.currency
				
				# Set custom field to link back to PRF
				return_doc.custom_product_return_order_form_ref = self.name

				# Skip ERPNext standard validate (rate check in validate_returned_items
				# doesn't allow PRF rates that differ from original SI rates)
				return_doc.flags.ignore_validate = True
				return_doc.insert(ignore_permissions=True)
				# return_doc.submit()
				return_doc.flags.ignore_validate = False

				# Add comment linking back to Product Return Form
				return_doc.add_comment(
					"Comment",
					f"Return invoice created from Product Return Form: {self.name}"
				)

				return_doc = frappe.get_doc("Sales Invoice", return_doc.name)
				return_doc.submit()

				# Add reference to original sales invoice
				frappe.db.set_value(return_doc.doctype, return_doc.name, "sales_invoice", si_name)

				created_invoices.append(return_doc.name)

				return_sales_invoices_map[si_name] = return_doc.name

			# add return refrence
			for item_row in self.items:
				if item_row.get("sales_invoice") and return_sales_invoices_map.get(item_row.sales_invoice):
					frappe.db.set_value("Product Return Form Item", item_row.name, "return_sales_invoice", return_sales_invoices_map.get(item_row.sales_invoice))

		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(f"Error creating return invoice: {str(e)}")
			frappe.throw(f"Error creating return invoice: {str(e)}")
		if created_invoices:
			invoice_links = ", ".join(
				[frappe.utils.get_link_to_form("Sales Invoice", inv) for inv in created_invoices]
			)
			frappe.msgprint(
				f"Return Sales Invoice(s) created: {invoice_links}",
				title="Credit Notes Created",
				indicator="green",
				alert=True
			)


	def set_total_in_words(self):
		from frappe.utils import money_in_words
		self.in_words = money_in_words(flt(self.rounded_total))

	def apply_pcpm_manual_calculation(self):
		"""
		Manual calculation for Sale Without Payment (PCPM) credit notes.
		Reverses invoice amounts proportionally based on return quantity.

		Cross Check Example:
		- Invoice: 10 items, total = 1000
		- Return: 7 items
		- Formula : 7/10 * 1000 = 700
		- Expected: 700 

		"""
		total_taxable = 0
		total_gst = 0

		# Clear existing tax rows
		self.sales_taxes_and_charges = []

		for row in self.items:
			if not row.sales_invoice_item:
				continue

			invoice_item = frappe.get_doc("Sales Invoice Item", row.sales_invoice_item)

			if not invoice_item.qty:
				frappe.throw(
					f"Invoice quantity missing for item {frappe.bold(row.item_code)}"
				)

			if flt(row.qty) > flt(invoice_item.qty):
				frappe.throw(
					f"Return quantity cannot exceed invoice quantity for item {frappe.bold(row.item_code)}"
				)

			factor = flt(row.qty) / flt(invoice_item.qty)

			# Lock invoice rates
			# row.rate = invoice_item.rate
			row.base_rate = invoice_item.base_rate

			# Proportional reversal of amounts
			proportional_fields = [
				"amount",
				"base_amount",
				"metal_amount",
				"diamond_amount",
				"finding_amount",
				"making_amount",
				"certification_amount",
				"freight_amount",
				"gemstone_amount",
				"other_material_amount",
				"hallmarking_amount",
				"custom_duty_amount",
				"other_amount",
			]

			for field in proportional_fields:
				invoice_val = flt(invoice_item.get(field, 0))
				row.set(field, invoice_val * factor)


			# Making charges Type
			if self.making_charges_type == "Without":
				row.making_amount = 0
			elif self.making_charges_type == "With":
				row.making_amount = row.making_amount
			elif self.making_charges_type == "Half":
				row.making_amount = row.making_amount * 0.5
			else:
				row.making_amount = 0

			row.rate = row.metal_amount + row.finding_amount + row.diamond_amount + row.gemstone_amount + row.making_amount
			row.amount = row.rate * row.qty

			total_taxable += flt(row.amount)

			# -------------------------------------------------
			# GST PROPORTIONAL REVERSAL (FROM SALES INVOICE)
			# -------------------------------------------------
			invoice = frappe.get_doc("Sales Invoice", invoice_item.parent)

		# Apply proportional GST from invoice tax rows
		for tax in invoice.taxes:
			if not tax.tax_amount:
				continue

			gst_amount = flt(tax.tax_amount) * factor
			total_gst += gst_amount

			self.append("sales_taxes_and_charges", {
				"charge_type": "Actual",
				"account_head": tax.account_head,
				"rate": tax.rate,
				"tax_amount": gst_amount,
				"description": tax.description,
			})

		# -------------------------------------------------
		# SET TOTALS MANUALLY
		# -------------------------------------------------
		self.total_taxes_and_charges = total_gst
		self.grand_total = total_taxable + total_gst
		self.rounded_total=round(self.grand_total)
		self.rounding_adjustment=abs(self.rounded_total - self.grand_total)
	def apply_bbpm_manual_calculation(self):
		"""
		Apply BBPM (Sale with Payment) manual calculation.

		Calculates Metal, Making, Wastage, and Finding amounts
		based on BOM configuration and customer-specific rules.

		- Gold rate should be taken as the current day rate. (on the date of the credit note).
		- Diamond and gemstone rates should be applied as per the updated live price list.
		- Making charges must be applied exactly as per the original invoice rate or as selected in the form.
		"""

		total_taxable = 0
		total_gst = 0
		self.sales_taxes_and_charges = []

		gold_gst_rate = flt(frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate") or 0)

		# precision = frappe.db.get_value("Customer", self.customer, "custom_precision_variable") or 3
		precision = 3
		customer_group = frappe.db.get_value("Customer", self.customer, "customer_group")

		gemstone_price_list_type = frappe.db.get_value("Customer", self.customer, "custom_gemstone_price_list_type")

		for row in self.items:
			if not row.bom:
				frappe.throw(
					f"BOM is mandatory for calculation for item "
					f"{frappe.bold(row.item_code)}"
				)

			bom_doc = frappe.get_doc("BOM", row.bom)

			# ------------------------------------------------
			# METAL / MAKING / WASTAGE TOTALS
			# ------------------------------------------------
			row_metal_amt_total = 0
			row_making_amt_total = 0
			row_wastage_amt_total = 0
			row_finding_amt_total = 0
			row_diamond_amt_total = 0
			row_gemstone_amt_total = 0

			mc = frappe.get_all(
				"Making Charge Price",
				filters={
					"customer": self.customer,
					"metal_type": bom_doc.metal_type,
					"setting_type": bom_doc.setting_type,
					"from_gold_rate": ["<=", self.gold_rate_with_gst],
					"to_gold_rate": [">=", self.gold_rate_with_gst],
					"metal_touch": bom_doc.metal_touch,
				},
				fields=["name"],
				limit=1,
			)
			# if not mc:
			# 		frappe.throw(
			# 			f"Create a valid Making Charge Price for "
			# 			f"{bom_doc.metal_type} / {bom_doc.metal_touch},{self.gold_rate_with_gst}"
			# 		)
			# customer_metal_purity = frappe.db.get_value(
			# 	"Metal Criteria",
			# 	{
			# 		"parent": self.customer,
			# 		"metal_type": md_row.metal_type,
			# 		"metal_touch": md_row.metal_touch,
			# 	},
			# 	"metal_purity",
			# )

			# if not customer_metal_purity:
			# 	frappe.throw("Metal Purity not found for Customer")

			# calculated_gold_rate = (
			# 	flt(customer_metal_purity) * self.gold_rate_with_gst
			# ) / (100 + gold_gst_rate)

			# line_gold_amt = round(calculated_gold_rate * md_row.quantity, 2)
			
			if not mc:
				frappe.throw(
					f"Create a valid Making Charge Price for "
					f"{bom_doc.metal_type} / {bom_doc.metal_touch},{self.gold_rate_with_gst}"
				)

			mc_name = mc[0]["name"]

			# =================================================
			# METAL, MAKING & WASTAGE CALCULATION
			# =================================================
			if hasattr(bom_doc, "metal_detail"):
				for md_row in bom_doc.metal_detail:

					sub_info = frappe.db.get_value(
						"Making Charge Price Item Subcategory",
						{
							"parent": mc_name,
							"subcategory": bom_doc.item_subcategory,
						},
						[
							"rate_per_gm",
							"rate_per_pc",
							"wastage",
							"rate_per_gm_threshold",
						],
						as_dict=True,
					)
					
					if not sub_info:
						frappe.throw(
							f"Making Charge Subcategory {bom_doc.item_subcategory} not found"
						)

					threshold = flt(sub_info.rate_per_gm_threshold) or 2
					weight_for_calc = flt(bom_doc.metal_and_finding_weight)

					if weight_for_calc < threshold:
						making_rate = flt(sub_info.rate_per_pc)
						wastage_rate = 0
					else:
						making_rate = flt(sub_info.rate_per_gm)
						wastage_rate = flt(sub_info.wastage) / 100

				

					line_making_amt = (
						making_rate
						if weight_for_calc < threshold
						else making_rate * md_row.quantity
					)
					customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": self.customer,
							"metal_type": md_row.metal_type,
							"metal_touch": md_row.metal_touch,
						},
						"metal_purity",
					)

					if not customer_metal_purity:
						frappe.throw("Metal Purity not found for Customer")

					calculated_gold_rate = (
						flt(customer_metal_purity) * self.gold_rate_with_gst
					) / (100 + gold_gst_rate)

					line_gold_amt = round(calculated_gold_rate * md_row.quantity, 2)
					if (
						self.company == "KG GK Jewellers Private Limited"
						and customer_group == "Internal"
					):
						line_gold_amt = md_row.amount
						
					line_wastage_amt = line_gold_amt * wastage_rate

					row_metal_amt_total += line_gold_amt
					# row_making_amt_total += line_making_amt
					row_wastage_amt_total += line_wastage_amt

			# =================================================
			# FINDING AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "finding_detail"):
				for fd_row in bom_doc.finding_detail:

					find = frappe.db.get_all(
						"Making Charge Price Finding Subcategory",
						filters={
							"parent": mc_name,
							"subcategory": fd_row.finding_type,
						},
						fields=["rate_per_gm", "rate_per_pc"],
						limit=1,
					)

					# Fallback to Item Subcategory
					if not find:
						find = frappe.db.get_all(
							"Making Charge Price Item Subcategory",
							filters={
								"parent": mc_name,
								"subcategory": bom_doc.item_subcategory,
							},
							fields=["rate_per_gm", "rate_per_pc"],
							limit=1,
						)

					if not find:
						frappe.throw(
							f"Finding rate not found for {fd_row.finding_type}"
						)

					find_info = find[0]

					customer_metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` where parent = '{self.customer}' and metal_type = '{fd_row.metal_type}' and metal_touch = '{fd_row.metal_touch}'""",as_dict=True)[0]['metal_purity']
					calculated_gold_rate = (float(customer_metal_purity) * self.gold_rate_with_gst) / (100 + int(gold_gst_rate))


					# Same metal rate logic
					line_finding_rate = round(calculated_gold_rate, 2)
					line_finding_amt = round(line_finding_rate * fd_row.quantity, 2)
					finding_weight = getattr(bom_doc, "metal_and_finding_weight", None)

					if finding_weight is not None and finding_weight < 2:
						making_rate = find_info.get("rate_per_pc", 0)
						wastage_rate = 0 
						line_making_amt = making_rate 
					else:
						making_rate = find_info.get("rate_per_gm", 0)
						wastage_rate = find_info.get("wastage", 0) / 100.0
						line_making_amt = making_rate * fd_row.quantity

					row_finding_amt_total += line_finding_amt
					# row_making_amt_total += line_making_amt
					row_wastage_amt_total += wastage_rate * line_finding_amt

			# =================================================
			# DIAMOND AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "diamond_detail"):
				

				for diamond_row in bom_doc.diamond_detail:

					# -------------------------------
					# CUSTOMER DIAMOND PRICE LIST
					# -------------------------------
					customer_price_list = frappe.db.sql(
						"""
						SELECT diamond_price_list
						FROM `tabDiamond Price List Table`
						WHERE parent = %s AND diamond_shape = %s
						""",
						(self.customer, diamond_row.stone_shape),
						as_dict=True,
					)

					if not customer_price_list:
						continue
					# frappe.throw("Diamond Detail Found")
					diamond_price_list = customer_price_list[0].diamond_price_list

					common_filters = {
						"price_list": "Standard Selling",
						"price_list_type": diamond_price_list,
						"customer": self.customer,
						"diamond_type": diamond_row.diamond_type,
						"stone_shape": diamond_row.stone_shape,
						"diamond_quality": diamond_row.quality,
					}

					# -------------------------------
					# WEIGHT PER PCS
					# -------------------------------
					weight_per_piece = (
						diamond_row.quantity / diamond_row.pcs
						if diamond_row.pcs else 0
					)
 

					# if 0.001 < weight_per_piece > 0.005:
					# 	weight_per_piece = round(weight_per_piece, 2)
					
					weight_per_piece = round(weight_per_piece, 3)
					
					# frappe.msgprint(f"Diamond type: {diamond_row.diamond_type} <br> Shape: {diamond_row.stone_shape} <br> Quality: {diamond_row.quality} <br> Quantity: {diamond_row.quantity} <br> Pcs: {diamond_row.pcs} <br> Weight per Piece: {weight_per_piece}")
					# if (
					# 	self.company == "KG GK Jewellers Private Limited"
					# 	and customer_group == "Internal"
					# ):
					# 	diamond_rate = diamond_row.total_diamond_rate
					# 	quantity = round(diamond_row.quantity, 3)
					# 	diamond_amount = round(quantity * diamond_rate, 2)
					# row_diamond_amt_total += diamond_amount
					# diamond_price_row = None
					# frappe.throw(f"{diamond_price_list}Diamond Detail Found")
					# -------------------------------
					# PRICE LIST TYPE LOGIC
					# -------------------------------
					if diamond_price_list == "Sieve Size Range":
						diamond_price_row = frappe.db.get_value(
							"Diamond Price List",
							{**common_filters, "sieve_size_range": diamond_row.sieve_size_range},
							[
								"rate",
								"outright_handling_charges_rate",
								"outwork_handling_charges_rate",
								"outright_handling_charges_in_percentage",
								"outwork_handling_charges_in_percentage",
								"supplier_fg_purchase_rate",
							],
							as_dict=True,
						)

					elif diamond_price_list == "Weight (in cts)":
						filter_conditions = " AND ".join(
							[f"{key} = %s" for key in common_filters]
						)

						rate_result = frappe.db.sql(
							f"""
							SELECT
							name,
								rate,
								outright_handling_charges_rate,
								outright_handling_charges_in_percentage,
								outwork_handling_charges_rate,
								outwork_handling_charges_in_percentage,
								supplier_fg_purchase_rate
							FROM `tabDiamond Price List`
							WHERE {filter_conditions}
							AND %s BETWEEN from_weight AND to_weight
							LIMIT 1
							""",
							list(common_filters.values()) + [weight_per_piece],
							as_dict=True,
						)
						# frappe.msgprint(frappe.as_json(rate_result))

						diamond_price_row = rate_result[0] if rate_result else None

					elif diamond_price_list == "Size (in mm)":
						diamond_price_row = frappe.db.get_value(
							"Diamond Price List",
							{**common_filters, "diamond_size_in_mm": diamond_row.diamond_sieve_size},
							[
								"rate",
								"outright_handling_charges_rate",
								"outwork_handling_charges_rate",
								"outright_handling_charges_in_percentage",
								"outwork_handling_charges_in_percentage",
								"supplier_fg_purchase_rate",
							],
							as_dict=True,
						)

					if not diamond_price_row:
						# frappe.msgprint("Diamond Price Row Not Found")
						continue
					# frappe.throw("Diamond Detail Found")
					# -------------------------------
					# RATE CALCULATION
					# -------------------------------
					base_rate = diamond_price_row.get("rate", 0)
					outright_rate = diamond_price_row.get("outright_handling_charges_rate", 0)
					outright_pct = diamond_price_row.get("outright_handling_charges_in_percentage", 0)
					outwork_rate = diamond_price_row.get("outwork_handling_charges_rate", 0)
					outwork_pct = diamond_price_row.get("outwork_handling_charges_in_percentage", 0)

					is_customer_item = getattr(diamond_row, "is_customer_item", False)

					# if is_customer_item:
					# 	total_rate = outright_rate or (base_rate * (outright_pct / 100))
					# else:
						# if outright_rate:
						# 	total_rate = base_rate + outright_rate
						# else:
							# total_rate = base_rate + (base_rate * (outright_pct / 100))
					total_rate = base_rate
					# -------------------------------
					# COMPANY & CUSTOMER GROUP LOGIC
					# -------------------------------
					if (
						self.company == "KG GK Jewellers Private Limited"
						and customer_group == "Internal"
					):
						diamond_rate = diamond_row.total_diamond_rate
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)

					elif (
						self.company == "Gurukrupa Export Private Limited"
						and customer_group == "Internal"
					):
						diamond_rate = diamond_price_row.get("supplier_fg_purchase_rate", 0)
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)

					else:
						diamond_rate = round(total_rate, 2)
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)
					
					# frappe.msgprint(f"""Diamond Rate: {diamond_rate} <br>
					# Diamond Quantity: {quantity} <br>
					# Diamond Total Rate: {total_rate} <br>
					# Diamond Amount: {diamond_amount}""")
					row_diamond_amt_total += diamond_amount


			# =================================================
			# GEMSTONE AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "gemstone_detail") and bom_doc.gemstone_detail:

				def calculate_percentage_amount(rate, base_value):
					return round((flt(rate) / 100) * flt(base_value), 2)

				for gs_row in bom_doc.gemstone_detail:

					# ---------------------------------------------
					# INTERNAL CUSTOMER – COMPANY SPECIFIC
					# ---------------------------------------------
					if self.company == "Gurukrupa Export Private Limited" and customer_group == "Internal":
						rate = gs_row.fg_purchase_rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					if self.company == "KG GK Jewellers Private Limited" and customer_group == "Internal":
						rate = gs_row.se_rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# FIXED PRICE LIST – NON-RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Fixed" and customer_group != "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"customer": self.customer,
								"price_list_type": gemstone_price_list_type,
								"gemstone_grade": gs_row.gemstone_grade,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_type": gs_row.gemstone_type,
								"stone_shape": gs_row.stone_shape,
							},
							fields=["rate", "handling_rate"],
							limit=1,
						)

						if not price_list:
							
							# frappe.throw("No Gemstone Price List found")
							return

						rate = price_list[0].rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# RETAIL CUSTOMER – FIXED PRICE
					# ---------------------------------------------
					if customer_group == "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"is_retail_customer": 1,
								"price_list_type": gemstone_price_list_type,
								"gemstone_grade": gs_row.gemstone_grade,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_type": gs_row.gemstone_type,
								"stone_shape": gs_row.stone_shape,
							},
							fields=["rate", "outwork_handling_charges_rate"],
							limit=1,
						)

						if not price_list:
							frappe.throw("No Retail Gemstone Price List found")

						rate = (
							price_list[0].outwork_handling_charges_rate
							if gs_row.is_customer_item
							else price_list[0].rate
						)

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# DIAMOND RANGE – NON-RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Diamond Range" and customer_group != "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"customer": self.customer,
								"price_list_type": gemstone_price_list_type,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_grade": gs_row.gemstone_grade,
								"from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
								"to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
							},
							fields=["name"],
							limit=1,
						)

						if not price_list:
							return
							# frappe.throw("Gemstone Diamond Range price list not found")

						price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

						rate = 0.0
						for mul in price_list_doc.gemstone_multiplier:
							if (
								mul.gemstone_type == gs_row.gemstone_type
								and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
							):
								if gs_row.is_customer_item:
									rate = {
										"Precious": mul.outwork_precious_percentage,
										"Semi-Precious": mul.outwork_semi_precious_percentage,
										"Synthetic": mul.outwork_synthetic_percentage,
									}.get(gs_row.gemstone_quality, 0)
								else:
									rate = {
										"Precious": mul.precious_percentage,
										"Semi-Precious": mul.semi_precious_percentage,
										"Synthetic": mul.synthetic_percentage,
									}.get(gs_row.gemstone_quality, 0)
								break

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)
						continue

					# ---------------------------------------------
					# DIAMOND RANGE – RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Diamond Range" and customer_group == "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"is_retail_customer": 1,
								"price_list_type": gemstone_price_list_type,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_grade": gs_row.gemstone_grade,
								"from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
								"to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
							},
							fields=["name"],
							limit=1,
						)

						if not price_list:
							frappe.throw("Retail Gemstone Diamond Range price list not found")

						price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

						rate = 0.0
						for mul in price_list_doc.get("gemstone_multiplier", []):
							if (
								mul.gemstone_type == gs_row.gemstone_type
								and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
							):
								rate = {
									"Precious": mul.precious_percentage,
									"Semi-Precious": mul.semi_precious_percentage,
									"Synthetic": mul.synthetic_percentage,
								}.get(gs_row.gemstone_quality, 0)
								break

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)


			# ------------------------------------------------
			# APPLY TOTALS TO ITEM
			# ------------------------------------------------
			row.metal_amount = row_metal_amt_total
			row.finding_amount = row_finding_amt_total
			row.diamond_amount = row_diamond_amt_total
			# row.diamond_amount= bom_doc.total_diamond_amount
			row.gemstone_amount = row_gemstone_amt_total

			# Making charges must be applied exactly as per the original invoice rate or as selected in the form
			if row.sales_invoice and row.sales_invoice_item:
				row_making_amt_total = frappe.db.get_value("Sales Invoice Item", row.sales_invoice_item, "making_amount")

			row_making_amt_total = row_making_amt_total
			
			# Making charges Type
			if self.making_charges_type == "Without":
				row.making_amount = 0
			elif self.making_charges_type == "With":
				row.making_amount = row_making_amt_total
			elif self.making_charges_type == "Half":
				row.making_amount = row_making_amt_total * 0.5
			else:
				row.making_amount = 0

			row.rate = row.metal_amount + row.finding_amount + row.diamond_amount + row.gemstone_amount + row.making_amount + row.hallmarking_amount + row.certification_amount
			row.amount = row.rate * row.qty
			# frappe.throw(f"{row.amount},{row.diamond_amount},{row.metal_amount}")

			total_taxable += row.amount

		self.total_taxes_and_charges = total_gst
		self.grand_total = total_taxable + total_gst
		self.rounded_total=round(self.grand_total)
		self.rounding_adjustment=abs(self.rounded_total - self.grand_total)

	def apply_physical_repair_manual_calculation(self):
		"""
		Apply Physical Repair manual calculation.

		Calculates Metal, Making, Wastage, and Finding amounts
		based on BOM configuration and customer-specific rules.
		"""

		total_taxable = 0
		total_gst = 0
		self.sales_taxes_and_charges = []

		gold_gst_rate = flt(frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate") or 0)

		# precision = frappe.db.get_value("Customer", self.customer, "custom_precision_variable") or 3
		precision = 3
		customer_group = frappe.db.get_value("Customer", self.customer, "customer_group")

		gemstone_price_list_type = frappe.db.get_value("Customer", self.customer, "custom_gemstone_price_list_type")

		for row in self.items:
			if not row.bom:
				frappe.throw(
					f"BOM is mandatory for calculation for item "
					f"{frappe.bold(row.item_code)}"
				)

			bom_doc = frappe.get_doc("BOM", row.bom)

			# ------------------------------------------------
			# METAL / MAKING / WASTAGE TOTALS
			# ------------------------------------------------
			row_metal_amt_total = 0
			row_making_amt_total = 0
			row_wastage_amt_total = 0
			row_finding_amt_total = 0
			row_diamond_amt_total = 0
			row_gemstone_amt_total = 0

			mc = frappe.get_all(
				"Making Charge Price",
				filters={
					"customer": self.customer,
					"metal_type": bom_doc.metal_type,
					"setting_type": bom_doc.setting_type,
					"from_gold_rate": ["<=", self.gold_rate_with_gst],
					"to_gold_rate": [">=", self.gold_rate_with_gst],
					"metal_touch": bom_doc.metal_touch,
				},
				fields=["name"],
				limit=1,
			)

			if not mc:
				frappe.throw(
					f"Create a valid Making Charge Price for "
					f"{bom_doc.metal_type} / {bom_doc.metal_touch}"
				)

			mc_name = mc[0]["name"]

			# =================================================
			# METAL, MAKING & WASTAGE CALCULATION
			# =================================================
			if hasattr(bom_doc, "metal_detail"):
				for md_row in bom_doc.metal_detail:

					sub_info = frappe.db.get_value(
						"Making Charge Price Item Subcategory",
						{
							"parent": mc_name,
							"subcategory": bom_doc.item_subcategory,
						},
						[
							"rate_per_gm",
							"rate_per_pc",
							"wastage",
							"rate_per_gm_threshold",
						],
						as_dict=True,
					)

					if not sub_info:
						frappe.throw(
							f"Making Charge Subcategory {bom_doc.item_subcategory} not found"
						)

					threshold = flt(sub_info.rate_per_gm_threshold) or 2
					weight_for_calc = flt(bom_doc.metal_and_finding_weight)

					if weight_for_calc < threshold:
						making_rate = flt(sub_info.rate_per_pc)
						wastage_rate = 0
					else:
						making_rate = flt(sub_info.rate_per_gm)
						wastage_rate = flt(sub_info.wastage) / 100

					customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": self.customer,
							"metal_type": md_row.metal_type,
							"metal_touch": md_row.metal_touch,
						},
						"metal_purity",
					)

					if not customer_metal_purity:
						frappe.throw("Metal Purity not found for Customer")
					
					calculated_gold_rate = (
						flt(customer_metal_purity) * self.gold_rate_with_gst
					) / (100 + gold_gst_rate)


					line_gold_amt = round(calculated_gold_rate * md_row.quantity, 2)

					line_making_amt = (
						making_rate
						if weight_for_calc < threshold
						else making_rate * md_row.quantity
					)

					# frappe.msgprint(f"metal type: {md_row.metal_type} <br> metal touch: {md_row.metal_touch} <br> customer: {self.customer} <br> Customer Metal Purity: {customer_metal_purity} <br> Gold Rate: {self.gold_rate_with_gst} <br> Gold GST Rate: {gold_gst_rate} <br> Calculated Gold Rate: {calculated_gold_rate} <br> Line Gold Amount: {round(calculated_gold_rate * md_row.quantity, 2)} <br> Making Rate {making_rate} <br> Making Amount {line_making_amt}")
     
					line_wastage_amt = line_gold_amt * wastage_rate

					row_metal_amt_total += line_gold_amt
					row_making_amt_total += line_making_amt
					row_wastage_amt_total += line_wastage_amt

			# =================================================
			# FINDING AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "finding_detail"):
				for fd_row in bom_doc.finding_detail:

					find = frappe.db.get_all(
						"Making Charge Price Finding Subcategory",
						filters={
							"parent": mc_name,
							"subcategory": fd_row.finding_type,
						},
						fields=["rate_per_gm", "rate_per_pc"],
						limit=1,
					)

					# Fallback to Item Subcategory
					if not find:
						find = frappe.db.get_all(
							"Making Charge Price Item Subcategory",
							filters={
								"parent": mc_name,
								"subcategory": bom_doc.item_subcategory,
							},
							fields=["rate_per_gm", "rate_per_pc"],
							limit=1,
						)

					if not find:
						frappe.throw(
							f"Finding rate not found for {fd_row.finding_type}"
						)

					find_info = find[0]

					customer_metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` where parent = '{self.customer}' and metal_type = '{fd_row.metal_type}' and metal_touch = '{fd_row.metal_touch}'""",as_dict=True)[0]['metal_purity']
					calculated_gold_rate = (float(customer_metal_purity) * self.gold_rate_with_gst) / (100 + int(gold_gst_rate))


					# Same metal rate logic
					line_finding_rate = round(calculated_gold_rate, 2)
					line_finding_amt = round(line_finding_rate * fd_row.quantity, 2)
					finding_weight = getattr(bom_doc, "metal_and_finding_weight", None)

					if finding_weight is not None and finding_weight < 2:
						making_rate = find_info.get("rate_per_pc", 0)
						wastage_rate = 0 
						line_making_amt = making_rate 
					else:
						making_rate = find_info.get("rate_per_gm", 0)
						wastage_rate = find_info.get("wastage", 0) / 100.0
						line_making_amt = making_rate * fd_row.quantity

					row_finding_amt_total += line_finding_amt
					row_making_amt_total += line_making_amt
					row_wastage_amt_total += wastage_rate * line_finding_amt

			# =================================================
			# DIAMOND AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "diamond_detail"):
				# frappe.msgprint("Diamond Detail Found")

				for diamond_row in bom_doc.diamond_detail:

					# -------------------------------
					# CUSTOMER DIAMOND PRICE LIST
					# -------------------------------
					customer_price_list = frappe.db.sql(
						"""
						SELECT diamond_price_list
						FROM `tabDiamond Price List Table`
						WHERE parent = %s AND diamond_shape = %s
						""",
						(self.customer, diamond_row.stone_shape),
						as_dict=True,
					)

					if not customer_price_list:
						continue
					
					diamond_price_list = customer_price_list[0].diamond_price_list

					common_filters = {
						"price_list": "Standard Selling",
						"price_list_type": diamond_price_list,
						"customer": self.customer,
						"diamond_type": diamond_row.diamond_type,
						"stone_shape": diamond_row.stone_shape,
						"diamond_quality": diamond_row.quality,
					}

					# -------------------------------
					# WEIGHT PER PCS
					# -------------------------------
					weight_per_piece = (
						diamond_row.quantity / diamond_row.pcs
						if diamond_row.pcs else 0
					)

					if 0.001 < weight_per_piece > 0.005:
						weight_per_piece = round(weight_per_piece, 3)

					diamond_price_row = None

					# -------------------------------
					# PRICE LIST TYPE LOGIC
					# -------------------------------
					if diamond_price_list == "Sieve Size Range":
						diamond_price_row = frappe.db.get_value(
							"Diamond Price List",
							{**common_filters, "sieve_size_range": diamond_row.sieve_size_range},
							[
								"name",
								"rate",
								"outright_handling_charges_rate",
								"outwork_handling_charges_rate",
								"outright_handling_charges_in_percentage",
								"outwork_handling_charges_in_percentage",
								"supplier_fg_purchase_rate",
							],
							as_dict=True,
						)

					elif diamond_price_list == "Weight (in cts)":
						filter_conditions = " AND ".join(
							[f"{key} = %s" for key in common_filters]
						)

						rate_result = frappe.db.sql(
							f"""
							SELECT
								name,
								rate,
								outright_handling_charges_rate,
								outright_handling_charges_in_percentage,
								outwork_handling_charges_rate,
								outwork_handling_charges_in_percentage,
								supplier_fg_purchase_rate
							FROM `tabDiamond Price List`
							WHERE {filter_conditions}
							AND %s BETWEEN from_weight AND to_weight
							LIMIT 1
							""",
							list(common_filters.values()) + [weight_per_piece],
							as_dict=True,
						)

						diamond_price_row = rate_result[0] if rate_result else None

					elif diamond_price_list == "Size (in mm)":
						diamond_price_row = frappe.db.get_value(
							"Diamond Price List",
							{**common_filters, "diamond_size_in_mm": diamond_row.diamond_sieve_size},
							[
								"name",
								"rate",
								"outright_handling_charges_rate",
								"outwork_handling_charges_rate",
								"outright_handling_charges_in_percentage",
								"outwork_handling_charges_in_percentage",
								"supplier_fg_purchase_rate",
							],
							as_dict=True,
						)

					if not diamond_price_row:
						# frappe.msgprint("Diamond Price Row Not Found")
						continue

					# -------------------------------
					# RATE CALCULATION
					# -------------------------------
					base_rate = diamond_price_row.get("rate", 0)
					outright_rate = diamond_price_row.get("outright_handling_charges_rate", 0)
					outright_pct = diamond_price_row.get("outright_handling_charges_in_percentage", 0)
					outwork_rate = diamond_price_row.get("outwork_handling_charges_rate", 0)
					outwork_pct = diamond_price_row.get("outwork_handling_charges_in_percentage", 0)

					is_customer_item = getattr(diamond_row, "is_customer_item", False)

					if is_customer_item:
						total_rate = outright_rate or (base_rate * (outright_pct / 100))
					else:
						if outright_rate:
							total_rate = base_rate + outright_rate
						else:
							total_rate = base_rate + (base_rate * (outright_pct / 100))

					# total_rate = base_rate
					
					# -------------------------------
					# COMPANY & CUSTOMER GROUP LOGIC
					# -------------------------------
					if (
						self.company == "KG GK Jewellers Private Limited"
						and customer_group == "Internal"
					):
						diamond_rate = diamond_row.se_rate
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)

					elif (
						self.company == "Gurukrupa Export Private Limited"
						and customer_group == "Internal"
					):
						diamond_rate = diamond_price_row.get("supplier_fg_purchase_rate", 0)
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)

					else:
						diamond_rate = round(total_rate, 2)
						quantity = round(diamond_row.quantity, 3)
						diamond_amount = round(quantity * diamond_rate, 2)
					
					# frappe.msgprint(f"""
					# Diamond Price List: {diamond_price_list} <br>
					# Diamond Price Row: {frappe.as_json(diamond_price_row)} <br>
					# Diamond Rate: {diamond_rate} <br>
					# Quantity: {quantity} <br>
					# Diamond Amount: {diamond_amount}
					# """)
					row_diamond_amt_total += diamond_amount


			# =================================================
			# GEMSTONE AMOUNT CALCULATION
			# =================================================
			if hasattr(bom_doc, "gemstone_detail") and bom_doc.gemstone_detail:

				def calculate_percentage_amount(rate, base_value):
					return round((flt(rate) / 100) * flt(base_value), 2)

				for gs_row in bom_doc.gemstone_detail:

					# ---------------------------------------------
					# INTERNAL CUSTOMER – COMPANY SPECIFIC
					# ---------------------------------------------
					if self.company == "Gurukrupa Export Private Limited" and customer_group == "Internal":
						rate = gs_row.fg_purchase_rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					if self.company == "KG GK Jewellers Private Limited" and customer_group == "Internal":
						rate = gs_row.se_rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# FIXED PRICE LIST – NON-RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Fixed" and customer_group != "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"customer": self.customer,
								"price_list_type": gemstone_price_list_type,
								"gemstone_grade": gs_row.gemstone_grade,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_type": gs_row.gemstone_type,
								"stone_shape": gs_row.stone_shape,
							},
							fields=["rate", "handling_rate"],
							limit=1,
						)

						if not price_list:
							frappe.throw("No Gemstone Price List found")

						rate = price_list[0].rate
						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# RETAIL CUSTOMER – FIXED PRICE
					# ---------------------------------------------
					if customer_group == "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"is_retail_customer": 1,
								"price_list_type": gemstone_price_list_type,
								"gemstone_grade": gs_row.gemstone_grade,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_type": gs_row.gemstone_type,
								"stone_shape": gs_row.stone_shape,
							},
							fields=["rate", "outwork_handling_charges_rate"],
							limit=1,
						)

						if not price_list:
							frappe.throw("No Retail Gemstone Price List found")

						rate = (
							price_list[0].outwork_handling_charges_rate
							if gs_row.is_customer_item
							else price_list[0].rate
						)

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
						continue

					# ---------------------------------------------
					# DIAMOND RANGE – NON-RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Diamond Range" and customer_group != "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"customer": self.customer,
								"price_list_type": gemstone_price_list_type,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_grade": gs_row.gemstone_grade,
								"from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
								"to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
							},
							fields=["name"],
							limit=1,
						)

						if not price_list:
							frappe.throw("Gemstone Diamond Range price list not found")

						price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

						rate = 0.0
						for mul in price_list_doc.gemstone_multiplier:
							if (
								mul.gemstone_type == gs_row.gemstone_type
								and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
							):
								if gs_row.is_customer_item:
									rate = {
										"Precious": mul.outwork_precious_percentage,
										"Semi-Precious": mul.outwork_semi_precious_percentage,
										"Synthetic": mul.outwork_synthetic_percentage,
									}.get(gs_row.gemstone_quality, 0)
								else:
									rate = {
										"Precious": mul.precious_percentage,
										"Semi-Precious": mul.semi_precious_percentage,
										"Synthetic": mul.synthetic_percentage,
									}.get(gs_row.gemstone_quality, 0)
								break

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)
						continue

					# ---------------------------------------------
					# DIAMOND RANGE – RETAIL
					# ---------------------------------------------
					if gemstone_price_list_type == "Diamond Range" and customer_group == "Retail":
						price_list = frappe.get_all(
							"Gemstone Price List",
							filters={
								"is_retail_customer": 1,
								"price_list_type": gemstone_price_list_type,
								"cut_or_cab": gs_row.cut_or_cab,
								"gemstone_grade": gs_row.gemstone_grade,
								"from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
								"to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
							},
							fields=["name"],
							limit=1,
						)

						if not price_list:
							frappe.throw("Retail Gemstone Diamond Range price list not found")

						price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

						rate = 0.0
						for mul in price_list_doc.get("gemstone_multiplier", []):
							if (
								mul.gemstone_type == gs_row.gemstone_type
								and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
							):
								rate = {
									"Precious": mul.precious_percentage,
									"Semi-Precious": mul.semi_precious_percentage,
									"Synthetic": mul.synthetic_percentage,
								}.get(gs_row.gemstone_quality, 0)
								break

						row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)


			# ------------------------------------------------
			# APPLY TOTALS TO ITEM
			# ------------------------------------------------
			row.metal_amount = row_metal_amt_total
			row.finding_amount = row_finding_amt_total
			row.diamond_amount = row_diamond_amt_total
			row.gemstone_amount = row_gemstone_amt_total

			# Making charges Type
			if self.making_charges_type == "Without":
				row.making_amount = 0
			elif self.making_charges_type == "With":
				row.making_amount = row_making_amt_total
			elif self.making_charges_type == "Half":
				row.making_amount = row_making_amt_total * 0.5
			else:
				row.making_amount = 0

			row.rate = row.metal_amount + row.finding_amount + row.diamond_amount + row.gemstone_amount + row.making_amount
			row.amount = row.rate * row.qty

			total_taxable += row.amount

		self.total_taxes_and_charges = total_gst
		self.grand_total = total_taxable + total_gst
		self.rounded_total=round(self.grand_total)
		self.rounding_adjustment=abs(self.rounded_total - self.grand_total)
	def apply_consignment_raw_material_manual_calculation(self):
		"""
		Apply manual calculation for Consignment: Raw Material credit notes.
		"""

		self.making_charges_type = "With"
		self.return_material_type = "Diamond-Gemstone"

		total_taxable = 0
		total_gst = 0

		# Clear existing tax rows
		self.sales_taxes_and_charges = []

		for row in self.items:
			if not row.sales_invoice_item:
				continue

			invoice_item = frappe.get_doc("Sales Invoice Item", row.sales_invoice_item)

			if not invoice_item.qty:
				frappe.throw(
					f"Invoice quantity missing for item {frappe.bold(row.item_code)}"
				)

			if flt(row.qty) > flt(invoice_item.qty):
				frappe.throw(
					f"Return quantity cannot exceed invoice quantity for item {frappe.bold(row.item_code)}"
				)

			factor = flt(row.qty) / flt(invoice_item.qty)

			# invoice rates
			row.rate = invoice_item.rate
			row.base_rate = invoice_item.base_rate

			# Proportional reversal of amounts
			proportional_fields = [
				"amount",
				"base_amount",
				"metal_amount",
				"diamond_amount",
				"finding_amount",
				"making_amount",
				"certification_amount",
				"freight_amount",
				"gemstone_amount",
				"other_material_amount",
				"hallmarking_amount",
				"custom_duty_amount",
				"other_amount",
			]

			for field in proportional_fields:
				row.set(field, 0)
			
			raw_material_fields = [
				"making_amount",
				"diamond_amount",
				"gemstone_amount",
			]
		
			for field in raw_material_fields:
				row.set(field, invoice_item.get(field) * factor)

			# makeing charge: 50% labour charges
			row.set("making_amount", invoice_item.get("making_amount") * factor * 0.5)
			
			# diamond and gemstone amount as invoice item amount
			row.set("diamond_amount", invoice_item.get("diamond_amount") * factor)
			row.set("gemstone_amount", invoice_item.get("gemstone_amount") * factor)

			if self.return_material_type == "Metal-Finding":
				row.set("diamond_amount", 0)
				row.set("gemstone_amount", 0)
			elif self.return_material_type == "Diamond-Gemstone":
				row.set("metal_amount", 0)
				row.set("finding_amount", 0)
			

			# Custom Duty: (making + diamond + gemstone amount) * 6% * 50%
			custom_duty_rate = (row.get("making_amount") + row.get("diamond_amount") + row.get("gemstone_amount")) * factor * 0.06 * 0.5
			row.set("custom_duty_amount", flt(custom_duty_rate))

			# Rate = (making + diamond + gemstone amount) - custom duty amount
			row.rate = (row.get("making_amount") + row.get("diamond_amount") + row.get("gemstone_amount")) - row.get("custom_duty_amount")
			row.amount = row.rate * row.qty

			total_taxable += flt(row.amount)

			# -------------------------------------------------
			# GST PROPORTIONAL REVERSAL (FROM SALES INVOICE)
			# -------------------------------------------------
			# invoice = frappe.get_doc("Sales Invoice", invoice_item.parent)

		# -------------------------------------------------
		# SET TOTALS MANUALLY
		# -------------------------------------------------
		self.total_taxes_and_charges = total_gst
		self.grand_total = total_taxable + total_gst
		self.rounded_total=round(self.grand_total)
		self.rounding_adjustment=abs(self.rounded_total - self.grand_total)
	
	def _get_customer_state(self):
		"""
		Fetch customer state from Address linked via Dynamic Link.
		Prefers primary address (is_primary_address=1), falls back to any available.
		
		Returns:
			str or None: Customer state name, or None if not found
		"""
		if not self.customer:
			return None

		# Try to get primary address first
		primary_address = frappe.db.sql(
			"""
			SELECT addr.state
			FROM `tabAddress` AS addr
			INNER JOIN `tabDynamic Link` AS dl ON dl.parent = addr.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			AND dl.parenttype = 'Address'
			AND addr.is_primary_address = 1
			LIMIT 1
			""",
			(self.customer,),
			as_dict=True,
		)

		if primary_address and primary_address[0].get("state"):
			return primary_address[0]["state"]

		# Fallback to any available address
		any_address = frappe.db.sql(
			"""
			SELECT addr.state
			FROM `tabAddress` AS addr
			INNER JOIN `tabDynamic Link` AS dl ON dl.parent = addr.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			AND dl.parenttype = 'Address'
			AND addr.state IS NOT NULL
			AND addr.state != ''
			LIMIT 1
			""",
			(self.customer,),
			as_dict=True,
		)

		if any_address:
			return any_address[0].get("state")

		return None

	def _set_tax_category_from_states(self):
		"""
		Auto-set tax_category based on state comparison between
		customer address state and branch state.
		
		- If customer_state == branch_state: tax_category = "In-State"
		- Otherwise: tax_category = "Out-State"
		
		Handles edge cases gracefully:
		- Customer has no address
		- Address has no state
		- Branch or branch state missing
		"""
		# Get customer state
		customer_state = self._get_customer_state()

		# Get branch state
		branch_state = None
		if self.branch:
			branch_state = frappe.db.get_value("Branch", self.branch, "state")
		# frappe.throw(f"{customer_state},{branch_state}hii")
		# Handle edge cases - if either state is missing, don't auto-set
		if not customer_state or not branch_state:
			return

		# frappe.msgprint(f"Customer State: {customer_state} <br> Branch State: {branch_state}")
		# Compare states and set tax category
		if customer_state == branch_state:
			# frappe.throw("hii")
			self.tax_category = "In-State"
		else:
			# frappe.throw("hiie")
			self.tax_category = "Out-State"
# //////////////////////////====================shruti///////////////////////////
	def calculate_sales_taxes_and_charges1(self):
		"""
		Handle Finished Goods Return (3%) and Subcontracting (5%) GST calculation.
		Populates the sales_taxes_and_charges child table based on
		the selected Item Tax Template.

		Explanation:
		1. Auto-set Tax Category based on customer/branch state comparison
		2. Calculate Net Total from items
		3. Skip exempted templates
		4. Determine tax category (In-State vs Out-State)
		5. Build query conditions based on tax category
		6. Fetch tax rates from Item Tax Template Detail
		7. Calculate cumulative total
		8. Clear and rebuild taxes table
		9. Add tax rows to sales_taxes_and_charges
		"""
		if self.sales_type not in ['Finished Goods Return', 'Subcontracting']:
			return
		if not self.items:
			return

		# Map Sales Type + Company to appropriate Item Tax Template
		template_map = {
			'Finished Goods Return': {
				'Gurukrupa Export Private Limited': 'GST 3% - GEPL',
				'KG GK Jewellers Private Limited': 'GST 3% - KGJPL',
			},
			'Subcontracting': {
				'Gurukrupa Export Private Limited': 'GST 5% - GEPL',
				'KG GK Jewellers Private Limited': 'GST 5% - KGJPL',
			},
		}
		item_tax_template = template_map.get(self.sales_type, {}).get(self.company, '')
		
		if not item_tax_template:
			return
		# for row in self.items:
		# 	row.rate = row.base_rate
		# 	row.amount = row.base_amount
		for row in self.items:
			hallmarking_amount = frappe.db.get_value(
				"BOM", row.bom, "hallmarking_amount"
			) or 0

			certification_amount = frappe.db.get_value(
				"BOM", row.bom, "certification_amount"
			) or 0
			# frappe.throw(f"{certification_amount}")
			# Store original values only once
			if not row.base_rate:
				row.base_rate = row.rate
			else:
				row.rate=row.base_rate

			if not row.base_amount:
				row.base_amount = row.amount

			rate = row.base_rate
			amount = row.base_amount

			# Remove unchecked charges
			if not self.product_hallmarking:
				rate -= hallmarking_amount
				amount -= hallmarking_amount * row.qty

			if not self.product_certification:
				rate -= certification_amount
				amount -= certification_amount * row.qty

			row.rate = rate
			row.amount = amount
			# frappe.throw(f"{row.amount}")
		# Calculate Net Total from items
		net_total = sum(flt(item.amount) for item in self.items)

		# Skip exempted templates
		exempted_templates = ['Exempted - GEPL', 'Exempted - KGJPL', 'Exempted - SHC', 'Exempted - SD']
		if item_tax_template in exempted_templates:
			return

		# -------------------------------------------------
		# AUTO SET TAX CATEGORY BASED ON STATE COMPARISON
		# -------------------------------------------------
		self._set_tax_category_from_states()

		# Determine tax category (In-State vs Out-State)
		# Use the tax_category field if set, otherwise default to In-State
		is_intra_state = self.tax_category in ['In-State', ''] or not self.tax_category

		# Build query conditions based on tax category
		conditions = []
		if is_intra_state:
			conditions.append("tax_type not like '%%IGST%%'")
			conditions.append("tax_type like 'Output%%'")
			conditions.append("tax_type not like '%%RCM%%'")
		else:
			conditions.append("tax_type like '%%IGST%%'")
			conditions.append("tax_type like 'Output%%'")
			conditions.append("tax_type not like '%%RCM%%'")
		
		where_clause = " AND ".join(conditions)

		tax_rows = frappe.db.sql(
			f"""SELECT tax_type, tax_rate
				FROM `tabItem Tax Template Detail`
				WHERE parent = %s AND {where_clause}""",
			(item_tax_template,),
			as_dict=1,
		)

		# Clear and rebuild taxes table
		self.sales_taxes_and_charges = []
		cumulative_total = net_total
		processed_accounts = []

		for row in tax_rows:
			tax_type = row.get("tax_type")
			if tax_type in processed_accounts:
				continue
			processed_accounts.append(tax_type)

			tax_rate = flt(row.get("tax_rate", 0))
			tax_amount = net_total * (tax_rate / 100)
			cumulative_total += tax_amount

			self.append("sales_taxes_and_charges", {
				"charge_type": "On Net Total",
				"account_head": tax_type,
				"description": tax_type.split(" - ")[0] if " - " in tax_type else tax_type,
				"rate": tax_rate,
				"tax_amount": tax_amount,
				"total": cumulative_total,
			})

		# Set totals
		self.total_taxes_and_charges = sum(flt(d.tax_amount) for d in self.sales_taxes_and_charges)
		self.grand_total = net_total + self.total_taxes_and_charges
		self.rounded_total=round(self.grand_total)
		self.rounding_adjustment=abs(self.rounded_total - self.grand_total)

	def calculate_taxes_and_totals(self):
		# frappe.throw("hii")
		self.calculate_sales_taxes_and_charges()


@frappe.whitelist()
def get_sales_bom_nd_invoice(serial_no, customer, sales_type):
	if not serial_no or not customer:
		frappe.throw("Serial No and Customer are required")

	# Validate Serial No and get Item Code
	serial_doc = frappe.db.get_value(
		"Serial No",
		serial_no,
		["item_code", "status"],
		as_dict=True
	)
	if not serial_doc:
		frappe.throw(f"Serial No {serial_no} does not exist")

	if serial_doc.status != "Delivered":
		frappe.throw(
			f"Serial No <b>{serial_no}</b> status is <b>{serial_doc.status}</b>. "
			f"It must be <b>Delivered</b> to proceed."
		)

	item_code = serial_doc.item_code if serial_doc else None

	# fetch customer name
	customer_name = frappe.db.get_value("Customer", customer, "customer_name")
	if not customer_name:
		frappe.throw(f"Customer {customer} does not exist")

	# Query Sales Invoice via Query Builder
	SalesInvoice = DocType("Sales Invoice")
	SalesInvoiceItem = DocType("Sales Invoice Item")

	result = (
		frappe.qb
		.from_(SalesInvoiceItem)
		.join(SalesInvoice)
		.on(SalesInvoice.name == SalesInvoiceItem.parent)
		.select(
			SalesInvoice.name.as_("sales_invoice"),
			SalesInvoice.customer,
			SalesInvoiceItem.name.as_("sii_name"),
			SalesInvoiceItem.qty,
			SalesInvoiceItem.uom,
			SalesInvoiceItem.custom_diamond_quality,
		)
		.where(
			(SalesInvoice.docstatus == 1)
			& (SalesInvoice.is_return == False)
			# g& (SalesInvoice.sales_type == sales_type)
			& (SalesInvoiceItem.serial_no == serial_no)
		)
		.orderby(SalesInvoice.creation, order=Order.desc)
		.limit(1)
		.run(as_dict=True)
	)
	# frappe.throw(f"{result}")
	if not result:
		frappe.throw(f"Serial No {serial_no} not found in any submitted Sales Invoice")

	if result[0].customer != customer:
		frappe.throw(
			f"Serial No {serial_no} does not belong to Customer {customer},{frappe.bold(customer_name)}. "
		)

	sales_invoice_item = frappe.db.get_value("Sales Invoice Item", {"name": result[0].sii_name}, "*",as_dict=True)
	bom_details = {}
	if sales_invoice_item.get("bom"):
		bom_details = frappe.db.get_value(
			"BOM",
			sales_invoice_item.bom,
			["metal_and_finding_weight", "gross_weight","metal_purity","metal_touch","diamond_quality","item_subcategory","metal_purity","setting_type","total_metal_weight","diamond_weight","metal_colour","total_gemstone_weight","making_charge","finding_weight","total_diamond_pcs","total_gemstone_pcs"],
			as_dict=True
		) or {}

	# frappe.throw(f"gtf{sales_invoice_item}")
	return {
		"sales_invoice": sales_invoice_item,
		"item_code": item_code,
		"bom": sales_invoice_item.get("bom",""),
		"net_weight": bom_details.get("metal_and_finding_weight"),
    	"gross_weight": bom_details.get("gross_weight"),
		"metal_purity": bom_details.get("metal_purity"),
		"metal_touch": bom_details.get("metal_touch"),
		"metal_colour": bom_details.get("metal_colour"),
		"diamond_quality": bom_details.get("diamond_quality"),
		"item_subcategory": bom_details.get("item_subcategory"),
		"metal_purity": bom_details.get("metal_purity"),
		"setting_type": bom_details.get("setting_type"),
		"making_charge":bom_details.get("making_charge"),
		"total_metal_weight": bom_details.get("total_metal_weight"),
		"total_diamond_weight_in_gms": bom_details.get("diamond_weight"),
		"total_gemstone_weight": bom_details.get("total_gemstone_weight"),
		"finding_weight": bom_details.get("finding_weight"),
		"total_diamond_pcs": bom_details.get("total_diamond_pcs"),
		"total_gemstone_pcs": bom_details.get("total_gemstone_pcs")
	}



@frappe.whitelist()
def get_credit_note_adjusted_bom(doc, invoice_item, bom_name):
	"""
	Fetch BOM and apply rate updates based on credit note type & subtype.
	For Jewelex credit notes, invoice_item may be empty — calculation
	proceeds without invoice-based data.
	"""

	if not bom_name:
		frappe.throw("BOM is required")
	
	if not isinstance(doc, dict):
		doc = frappe._dict(json.loads(doc))

	is_jewlex = doc.get("is_jewlex_credit_note")

	# For non-Jewelex, invoice_item is mandatory
	if not invoice_item and not is_jewlex:
		frappe.throw("Invoice Item is required")

	# Fetch BOM safely and prevent mutation of original document
	bom_doc = frappe.get_doc("BOM", bom_name).as_dict()
	bom_data = copy.deepcopy(bom_doc)

	# Get Invoice Item, or derive from BOM details for Jewelex credit notes
	if invoice_item:
		invoice_item_doc = frappe.get_doc("Sales Invoice Item", invoice_item).as_dict()
	else:
		# Jewelex path: build invoice_item_doc from BOM details
		making_amount = sum(
			flt(r.get("making_amount", 0)) for r in bom_data.get("metal_detail", [])
		) + sum(
			flt(r.get("making_amount", 0)) for r in bom_data.get("finding_detail", [])
		)
		diamond_amount = sum(
			flt(r.get("diamond_rate_for_specified_quantity", 0)) for r in bom_data.get("diamond_detail", [])
		)
		gemstone_amount = sum(
			flt(r.get("gemstone_rate_for_specified_quantity", 0)) for r in bom_data.get("gemstone_detail", [])
		)
		invoice_item_doc = frappe._dict({
			"making_amount": making_amount,
			"diamond_amount": diamond_amount,
			"gemstone_amount": gemstone_amount,
		})

	credit_note_type = doc.credit_note_type
	return_subtype = doc.return_subtype

	rate_update_rules = {
		# Sale without payment / QC fail repair / FG consignment
		("Return", "Sale Without Payment-Return"): apply_invoice_rate_to_bom,
		("Repair", "QC Fail-Repair"): apply_invoice_rate_to_bom,
		("Consignment", "Finish Goods-Consignment"): apply_invoice_rate_to_bom,

		# BBPM – Sale with payment
		("Return", "Sale With Payment-Return"): apply_current_bbpm_rate_to_bom,

		# Physical repair
		("Repair", "Physical-Repair"): apply_current_physical_repair_rate_to_bom,

		# Consignment – Raw material
		("Consignment", "Raw Material-Consignment"):
			apply_current_consignment_raw_material_rate_to_bom,
	}

	bom_update_fn = rate_update_rules.get(
		(credit_note_type, return_subtype)
	)

	if bom_update_fn:
		bom_data = bom_update_fn(doc, bom_data, invoice_item_doc)

	return bom_data


# ------------------------------------------------------------------
# Rate update handlers
# ------------------------------------------------------------------

def apply_invoice_rate_to_bom(doc, bom_data, invoice_item_doc):
	"""
	Apply invoice rate to BOM items.
	Used for:
	- Sale Without Payment
	- QC Fail Repair
	- Finish Goods Consignment
	"""
	metal_data = bom_data.get("metal_detail", [])
	finding_data = bom_data.get("finding_detail", [])
	diamond_data = bom_data.get("diamond_detail", [])
	gemstone_data = bom_data.get("gemstone_detail", [])

	for md_row in metal_data:
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": md_row.metal_type,
							"metal_touch": md_row.metal_touch,
						},
						"metal_purity",
					)
		metal_purity = customer_metal_purity or 0
		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amount = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amount = md_row.making_amount
			making_rate = md_row.making_rate
		elif doc.making_charges_type == "Half":
			making_amount = md_row.making_amount * 0.5
			making_rate = md_row.making_rate * 0.5
		else:
			making_amount = 0
			making_rate = 0

		md_row.update({
			"making_rate": making_rate,
			"making_amount": making_amount,
			"metal_purity": metal_purity,
		})
	
	for fd_row in finding_data:
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": fd_row.metal_type,
							"metal_touch": fd_row.metal_touch,
						},
						"metal_purity",
					)
		
		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amount = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amount = fd_row.making_amount
			making_rate = fd_row.making_rate
		elif doc.making_charges_type == "Half":
			making_amount = fd_row.making_amount * 0.5
			making_rate = fd_row.making_rate * 0.5
		else:
			making_amount = 0
			making_rate = 0

		fd_row.update({
			"customer_metal_purity": customer_metal_purity,
			"making_rate": making_rate,
			"making_amount": making_amount,
		})

	return bom_data


def apply_current_bbpm_rate_to_bom(doc, bom_data: dict, invoice_item_doc: dict):
	"""
	Apply current BBPM rate to BOM items.
	Used for Sale With Payment.
	"""
	gold_gst_rate = flt(frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate") or 0)

	customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
	gemstone_price_list_type = frappe.db.get_value("Customer", doc.customer, "custom_gemstone_price_list_type")

	metal_data = bom_data.get("metal_detail", [])
	finding_data = bom_data.get("finding_detail", [])
	diamond_data = bom_data.get("diamond_detail", [])
	gemstone_data = bom_data.get("gemstone_detail", [])

	mc = frappe.get_all(
			"Making Charge Price",
			filters={
				"customer": doc.customer,
				"metal_type": bom_data.metal_type,
				"setting_type": bom_data.setting_type,
				"from_gold_rate": ["<=", doc.gold_rate_with_gst],
				"to_gold_rate": [">=", doc.gold_rate_with_gst],
				"metal_touch": bom_data.metal_touch,
			},
			fields=["name"],
			limit=1,
		)
	mc_name = mc[0]["name"] if mc else ""
	# frappe.msgprint(f"Making Charge Price: {mc_name}")

	sub_info = frappe.db.get_value(
				"Making Charge Price Item Subcategory",
				{
					"parent": mc_name,
					"subcategory": bom_data.item_subcategory,
				},
				[
					"rate_per_gm",
					"rate_per_pc",
					"wastage",
					"rate_per_gm_threshold",
				],
				as_dict=True,
			)
	# frappe.msgprint(f"Sub Info: {sub_info}")

	for md_row in metal_data:
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": md_row.metal_type,
							"metal_touch": md_row.metal_touch,
						},
						"metal_purity",
					)
		metal_purity = customer_metal_purity or 0
		calculated_gold_rate = (flt(customer_metal_purity) * doc.gold_rate_with_gst) / (100 + gold_gst_rate)
		gold_amount = round(calculated_gold_rate * md_row.quantity, 2)

		# making_rate = invoice_item_doc.get("making_amount", 0) / md_row.quantity
		# making_amount = making_rate * md_row.quantity

		threshold = flt(sub_info.rate_per_gm_threshold) or 2
		weight_for_calc = flt(bom_data.metal_and_finding_weight)


		if weight_for_calc < threshold:
			making_rate = flt(sub_info.rate_per_pc)
			wastage_rate = 0
		else:
			making_rate = flt(sub_info.rate_per_gm)
			wastage_rate = flt(sub_info.wastage) / 100
		
		making_amount = (making_rate if weight_for_calc < threshold else making_rate * md_row.quantity)
		# frappe.msgprint(f"making amount :;;; {making_amount}")

		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amount = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amount = making_amount
		elif doc.making_charges_type == "Half":
			making_amount = making_amount * 0.5
			making_rate = making_rate * 0.5
		else:
			making_amount = 0
			making_rate = 0

		
		md_row.update({
			"metal_purity": metal_purity,
			"customer_metal_purity": customer_metal_purity,
			"rate": calculated_gold_rate,
			"amount": gold_amount,
			"making_rate": making_rate,
			"making_amount": making_amount,

		})
	
	for fd_row in finding_data:
		finding_sub_info = frappe.db.get_all(
						"Making Charge Price Finding Subcategory",
						filters={
							"parent": mc_name,
							"subcategory": fd_row.finding_type,
						},
						fields=["rate_per_gm", "rate_per_pc"],
						limit=1,
					)
		
		if not finding_sub_info:
			finding_sub_info = sub_info
		else:
			finding_sub_info = finding_sub_info[0]
		
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": fd_row.metal_type,
							"metal_touch": fd_row.metal_touch,
						},
						"metal_purity",
					)
		calculated_gold_rate = (float(customer_metal_purity) * doc.gold_rate_with_gst) / (100 + int(gold_gst_rate))
		gold_amount = round(calculated_gold_rate * fd_row.quantity, 2)

		line_finding_rate = round(calculated_gold_rate, 2)
		line_finding_amt = round(line_finding_rate * fd_row.quantity, 2)
		finding_weight = getattr(bom_data, "metal_and_finding_weight", None)

		if finding_weight is not None and finding_weight < 2:
			making_rate = finding_sub_info.get("rate_per_pc", 0)
			wastage_rate = 0 
			making_amt = making_rate 
		else:
			making_rate = finding_sub_info.get("rate_per_gm", 0)
			wastage_rate = finding_sub_info.get("wastage", 0) / 100.0
			making_amt = making_rate * fd_row.quantity

		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amt = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amt = making_amt
		elif doc.making_charges_type == "Half":
			making_amt = making_amt * 0.5
			making_rate = making_rate * 0.5
		else:
			making_amt = 0
			making_rate = 0
		
		fd_row.update({
			"metal_purity": customer_metal_purity,
			"customer_metal_purity": customer_metal_purity,
			"gold_rate": calculated_gold_rate,
			"gold_amount": gold_amount,
			"rate": line_finding_rate,
			"amount": line_finding_amt,
			"making_rate": making_rate,
			"making_amount": making_amt,
			"wastage_rate": wastage_rate,
		})
		# frappe.msgprint(f"Finding Row - CUSTOMER METAL PURITY: {fd_row.get('metal_purity')}")

	for dd_row in diamond_data:
		customer_price_list = frappe.db.get_all(
						"Diamond Price List Table",
						filters={
							"parent": doc.customer,
							"diamond_shape": dd_row.stone_shape,
						},
						fields=["diamond_price_list", "parent"],
					)
		# frappe.msgprint(f"Diamond Price List: {customer_price_list}")
		
		if not customer_price_list:
			continue

		diamond_price_list = customer_price_list[0].diamond_price_list
		diamond_price_row = None
		
		common_filters = {
			"price_list": "Standard Selling",
			"price_list_type": diamond_price_list,
			"customer": doc.customer,
			"diamond_type": dd_row.diamond_type,
			"stone_shape": dd_row.stone_shape,
			"diamond_quality": dd_row.quality,
		}

		# -------------------------------
		# WEIGHT PER PCS
		# -------------------------------
		weight_per_piece = (
			dd_row.quantity / dd_row.pcs
			if dd_row.pcs else 0
		)		
		weight_per_piece = round(weight_per_piece, 3)

		# -------------------------------
		# PRICE LIST TYPE LOGIC
		# -------------------------------
		if diamond_price_list == "Sieve Size Range":
			diamond_price_row = frappe.db.get_value(
				"Diamond Price List",
				{**common_filters, "sieve_size_range": dd_row.sieve_size_range},
				[
					"name",
					"rate",
					"outright_handling_charges_rate",
					"outwork_handling_charges_rate",
					"outright_handling_charges_in_percentage",
					"outwork_handling_charges_in_percentage",
					"supplier_fg_purchase_rate",
				],
				as_dict=True,
			)

		elif diamond_price_list == "Weight (in cts)":
			filter_conditions = " AND ".join(
				[f"{key} = %s" for key in common_filters]
			)

			rate_result = frappe.db.sql(
				f"""
				SELECT
				name,
					rate,
					outright_handling_charges_rate,
					outright_handling_charges_in_percentage,
					outwork_handling_charges_rate,
					outwork_handling_charges_in_percentage,
					supplier_fg_purchase_rate
				FROM `tabDiamond Price List`
				WHERE {filter_conditions}
				AND %s BETWEEN from_weight AND to_weight
				LIMIT 1
				""",
				list(common_filters.values()) + [weight_per_piece],
				as_dict=True,
			)

			diamond_price_row = rate_result[0] if rate_result else None
			# frappe.msgprint(f"Diamond Price Row: {frappe.as_json(diamond_price_row)}")

		elif diamond_price_list == "Size (in mm)":
			diamond_price_row = frappe.db.get_value(
				"Diamond Price List",
				{**common_filters, "diamond_size_in_mm": dd_row.diamond_sieve_size},
				[
					"name",
					"rate",
					"outright_handling_charges_rate",
					"outwork_handling_charges_rate",
					"outright_handling_charges_in_percentage",
					"outwork_handling_charges_in_percentage",
					"supplier_fg_purchase_rate",
				],
				as_dict=True,
			)

		if not diamond_price_row:
			# frappe.msgprint("Diamond Price Row Not Found")
			continue
		
		# frappe.msgprint(f"DIAOMN PRICE LIST :::: {frappe.as_json(diamond_price_row)}")

		base_rate = diamond_price_row.get("rate", 0)

		total_rate = base_rate
		# -------------------------------
		# COMPANY & CUSTOMER GROUP LOGIC
		# -------------------------------
		if (
			doc.company == "KG GK Jewellers Private Limited"
			and customer_group == "Internal"
		):
			diamond_rate = dd_row.se_rate
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)
			# frappe.throw(f"{diamond_amount}")

		elif (
			doc.company == "Gurukrupa Export Private Limited"
			and customer_group == "Internal"
		):
			diamond_rate = diamond_price_row.get("supplier_fg_purchase_rate", 0)
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)

		else:
			diamond_rate = round(total_rate, 2)
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)
		
		dd_row.update({
			"weight_per_pcs": weight_per_piece,
			"total_diamond_rate": diamond_rate,
			"diamond_rate_for_specified_quantity": diamond_amount,
		})

	for gd_row in gemstone_data:
		if doc.company == "Gurukrupa Export Private Limited" and customer_group == "Internal":
			rate = gd_row.fg_purchase_rate
			amount = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": amount,
			})
			continue

		if doc.company == "KG GK Jewellers Private Limited" and customer_group == "Internal":
			rate = gd_row.se_rate
			amount = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": amount,
			})
			continue
		
		# ---------------------------------------------
		# FIXED PRICE LIST – NON-RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Fixed" and customer_group != "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"customer": doc.customer,
					"price_list_type": gemstone_price_list_type,
					"gemstone_grade": gd_row.gemstone_grade,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_type": gd_row.gemstone_type,
					"stone_shape": gd_row.stone_shape,
				},
				fields=["rate", "handling_rate"],
				limit=1,
			)

			if not price_list:
				frappe.throw("No Gemstone Price List found")

			rate = price_list[0].rate
			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# RETAIL CUSTOMER – FIXED PRICE
		# ---------------------------------------------
		if customer_group == "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"is_retail_customer": 1,
					"price_list_type": gemstone_price_list_type,
					"gemstone_grade": gd_row.gemstone_grade,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_type": gd_row.gemstone_type,
					"stone_shape": gd_row.stone_shape,
				},
				fields=["rate", "outwork_handling_charges_rate"],
				limit=1,
			)

			if not price_list:
				frappe.throw("No Retail Gemstone Price List found")

			rate = (
				price_list[0].outwork_handling_charges_rate
				if gd_row.is_customer_item
				else price_list[0].rate
			)

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# DIAMOND RANGE – NON-RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Diamond Range" and customer_group != "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"customer": doc.customer,
					"price_list_type": gemstone_price_list_type,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_grade": gd_row.gemstone_grade,
					"from_gemstone_pr_rate": ["<=", gd_row.gemstone_pr],
					"to_gemstone_pr_rate": [">=", gd_row.gemstone_pr],
				},
				fields=["name"],
				limit=1,
			)

			if not price_list:
				frappe.throw("Gemstone Diamond Range price list not found")

			price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

			rate = 0.0
			for mul in price_list_doc.gemstone_multiplier:
				if (
					mul.gemstone_type == gd_row.gemstone_type
					and flt(mul.from_weight) <= flt(gd_row.gemstone_pr) <= flt(mul.to_weight)
				):
					if gd_row.is_customer_item:
						rate = {
							"Precious": mul.outwork_precious_percentage,
							"Semi-Precious": mul.outwork_semi_precious_percentage,
							"Synthetic": mul.outwork_synthetic_percentage,
						}.get(gd_row.gemstone_quality, 0)
					else:
						rate = {
							"Precious": mul.precious_percentage,
							"Semi-Precious": mul.semi_precious_percentage,
							"Synthetic": mul.synthetic_percentage,
						}.get(gd_row.gemstone_quality, 0)
					break

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.gemstone_pr)
			
			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# DIAMOND RANGE – RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Diamond Range" and customer_group == "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"is_retail_customer": 1,
					"price_list_type": gemstone_price_list_type,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_grade": gd_row.gemstone_grade,
					"from_gemstone_pr_rate": ["<=", gd_row.gemstone_pr],
					"to_gemstone_pr_rate": [">=", gd_row.gemstone_pr],
				},
				fields=["name"],
				limit=1,
			)

			if not price_list:
				frappe.throw("Retail Gemstone Diamond Range price list not found")

			price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

			rate = 0.0
			for mul in price_list_doc.get("gemstone_multiplier", []):
				if (
					mul.gemstone_type == gd_row.gemstone_type
					and flt(mul.from_weight) <= flt(gd_row.gemstone_pr) <= flt(mul.to_weight)
				):
					rate = {
						"Precious": mul.precious_percentage,
						"Semi-Precious": mul.semi_precious_percentage,
						"Synthetic": mul.synthetic_percentage,
					}.get(gd_row.gemstone_quality, 0)
					break

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.gemstone_pr)
			
			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue


	return bom_data

def apply_current_physical_repair_rate_to_bom(doc, bom_data: dict, invoice_item_doc: dict):
	"""
	Apply current rate for physical repair.
	"""
	gold_gst_rate = flt(frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate") or 0)

	customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
	gemstone_price_list_type = frappe.db.get_value("Customer", doc.customer, "custom_gemstone_price_list_type")
	
	metal_data = bom_data.get("metal_detail", [])
	finding_data = bom_data.get("finding_detail", [])
	diamond_data = bom_data.get("diamond_detail", [])
	gemstone_data = bom_data.get("gemstone_detail", [])


	mc = frappe.get_all(
			"Making Charge Price",
			filters={
				"customer": doc.customer,
				"metal_type": bom_data.get("metal_type"),
				"setting_type": bom_data.get("setting_type"),
				"from_gold_rate": ["<=", doc.gold_rate_with_gst],
				"to_gold_rate": [">=", doc.gold_rate_with_gst],
				"metal_touch": bom_data.get("metal_touch"),
			},
			fields=["name"],
			limit=1,
		)
	mc_name = mc[0]["name"] if mc else ""

	sub_info = frappe.db.get_value(
				"Making Charge Price Item Subcategory",
				{
					"parent": mc_name,
					"subcategory": bom_data.get("item_subcategory"),
				},
				[
					"rate_per_gm",
					"rate_per_pc",
					"wastage",
					"rate_per_gm_threshold",
				],
				as_dict=True,
			)
	if not sub_info: 
		return bom_data.update({
			"metal_detail": [], 
			"finding_detail": [], 
			"diamond_detail": [], 
			"gemstone_detail": []
			})


	for md_row in metal_data:

		# Making Rate and threshold
		threshold = flt(sub_info.rate_per_gm_threshold) or 2
		weight_for_calc = flt(bom_data.get("metal_and_finding_weight", 0))
		
		if weight_for_calc < threshold:
			making_rate = flt(sub_info.rate_per_pc)
		else:
			making_rate = flt(sub_info.rate_per_gm)

		# Get customer metal purity
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": md_row.metal_type,
							"metal_touch": md_row.metal_touch,
						},
						"metal_purity",
					)
		metal_purity = customer_metal_purity or 0
		calculated_gold_rate = (flt(customer_metal_purity) * doc.gold_rate_with_gst) / (100 + gold_gst_rate)
		gold_amount = round(calculated_gold_rate * md_row.quantity, 2)
		
		making_amount = making_rate if weight_for_calc < threshold else making_rate * md_row.quantity

		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amount = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amount = making_amount
		elif doc.making_charges_type == "Half":
			making_amount = making_amount * 0.5
			making_rate = making_rate * 0.5
		else:
			making_amount = 0
			making_rate = 0
		
		md_row.update({
			"metal_purity": metal_purity,
			"customer_metal_purity": customer_metal_purity,
			"rate": calculated_gold_rate,
			"amount": gold_amount,
			"making_rate": making_rate,
			"making_amount": making_amount,
		})

	for fd_row in finding_data:
		finding_sub_info = frappe.db.get_value(
						"Making Charge Price Finding Subcategory",
						{
							"parent": mc_name,
							"subcategory": fd_row.finding_type,
						},
						["rate_per_gm", "rate_per_pc"],
						as_dict=True,
					)
		
		if not finding_sub_info:
			finding_sub_info = sub_info
		
		customer_metal_purity = frappe.db.get_value(
						"Metal Criteria",
						{
							"parent": doc.customer,
							"metal_type": fd_row.metal_type,
							"metal_touch": fd_row.metal_touch,
						},
						"metal_purity",
					)
		calculated_gold_rate = (float(customer_metal_purity) * doc.gold_rate_with_gst) / (100 + int(gold_gst_rate))
		gold_amount = round(calculated_gold_rate * fd_row.quantity, 2)

		finding_rate = round(calculated_gold_rate, 2)
		finding_amt = round(finding_rate * fd_row.quantity, 2)
		finding_weight = getattr(bom_data, "metal_and_finding_weight", None)

		if finding_weight is not None and finding_weight < 2:
			making_rate = finding_sub_info.get("rate_per_pc", 0)
			wastage_rate = 0 
			making_amt = making_rate 
		else:
			making_rate = finding_sub_info.get("rate_per_gm", 0)
			wastage_rate = finding_sub_info.get("wastage", 0) / 100.0
			making_amt = making_rate * fd_row.quantity

		# Making charges Type
		if doc.making_charges_type == "Without":
			making_amount = 0
			making_rate = 0
		elif doc.making_charges_type == "With":
			making_amount = making_amount
		elif doc.making_charges_type == "Half":
			making_amount = making_amount * 0.5
			making_rate = making_rate * 0.5
		else:
			making_amount = 0
			making_rate = 0
					
		fd_row.update({
			"metal_purity": metal_purity,
			"customer_metal_purity": customer_metal_purity,
			"gold_rate": calculated_gold_rate,
			"gold_amount": gold_amount,
			"rate": finding_rate,
			"amount": finding_amt,
			"making_rate": making_rate,
			"making_amount": making_amt,
			"wastage_rate": wastage_rate,
		})

	for dd_row in diamond_data:
		customer_price_list = frappe.db.get_all(
						"Diamond Price List Table",
						filters={
							"parent": doc.customer,
							"diamond_shape": dd_row.stone_shape,
						},
						fields=["diamond_price_list"],
					)
		
		if not customer_price_list:
			dd_row.update({
				"total_diamond_rate": 0,
				"diamond_rate_for_specified_quantity": 0,
			})
			continue

		diamond_price_list = customer_price_list[0].diamond_price_list
		diamond_price_row = None
		
		common_filters = {
			"price_list": "Standard Selling",
			"price_list_type": diamond_price_list,
			"customer": doc.customer,
			"diamond_type": dd_row.diamond_type,
			"stone_shape": dd_row.stone_shape,
			"diamond_quality": dd_row.quality,
		}

		# -------------------------------
		# WEIGHT PER PCS
		# -------------------------------
		weight_per_piece = (
			dd_row.quantity / dd_row.pcs
			if dd_row.pcs else 0
		)		
		weight_per_piece = round(weight_per_piece, 3)

		# -------------------------------
		# PRICE LIST TYPE LOGIC
		# -------------------------------
		if diamond_price_list == "Sieve Size Range":
			diamond_price_row = frappe.db.get_value(
				"Diamond Price List",
				{**common_filters, "sieve_size_range": dd_row.sieve_size_range},
				[
					"rate",
					"outright_handling_charges_rate",
					"outwork_handling_charges_rate",
					"outright_handling_charges_in_percentage",
					"outwork_handling_charges_in_percentage",
					"supplier_fg_purchase_rate",
				],
				as_dict=True,
			)

		elif diamond_price_list == "Weight (in cts)":
			filter_conditions = " AND ".join(
				[f"{key} = %s" for key in common_filters]
			)

			rate_result = frappe.db.sql(
				f"""
				SELECT
				name,
					rate,
					outright_handling_charges_rate,
					outright_handling_charges_in_percentage,
					outwork_handling_charges_rate,
					outwork_handling_charges_in_percentage,
					supplier_fg_purchase_rate
				FROM `tabDiamond Price List`
				WHERE {filter_conditions}
				AND %s BETWEEN from_weight AND to_weight
				LIMIT 1
				""",
				list(common_filters.values()) + [weight_per_piece],
				as_dict=True,
			)

			diamond_price_row = rate_result[0] if rate_result else None

		elif diamond_price_list == "Size (in mm)":
			diamond_price_row = frappe.db.get_value(
				"Diamond Price List",
				{**common_filters, "diamond_size_in_mm": dd_row.diamond_sieve_size},
				[
					"rate",
					"outright_handling_charges_rate",
					"outwork_handling_charges_rate",
					"outright_handling_charges_in_percentage",
					"outwork_handling_charges_in_percentage",
					"supplier_fg_purchase_rate",
				],
				as_dict=True,
			)

		if not diamond_price_row:
			dd_row.update({
				"total_diamond_rate": 0,
				"diamond_rate_for_specified_quantity": 0,
			})
			continue

		base_rate = diamond_price_row.get("rate", 0)

		total_rate = base_rate
		# -------------------------------
		# COMPANY & CUSTOMER GROUP LOGIC
		# -------------------------------
		if (
			doc.company == "KG GK Jewellers Private Limited"
			and customer_group == "Internal"
		):
			diamond_rate = dd_row.se_rate
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)

		elif (
			doc.company == "Gurukrupa Export Private Limited"
			and customer_group == "Internal"
		):
			diamond_rate = diamond_price_row.get("supplier_fg_purchase_rate", 0)
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)

		else:
			diamond_rate = round(total_rate, 2)
			quantity = round(dd_row.quantity, 3)
			diamond_amount = round(quantity * diamond_rate, 2)
		
		dd_row.update({
			"weight_per_pcs": weight_per_piece,
			"total_diamond_rate": diamond_rate,
			"diamond_rate_for_specified_quantity": diamond_amount,
		})

	for gd_row in gemstone_data:
		if doc.company == "Gurukrupa Export Private Limited" and customer_group == "Internal":
			rate = gd_row.fg_purchase_rate
			amount = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": amount,
			})
			continue

		if doc.company == "KG GK Jewellers Private Limited" and customer_group == "Internal":
			rate = gd_row.se_rate
			amount = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": amount,
			})
			continue
		
		# ---------------------------------------------
		# FIXED PRICE LIST – NON-RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Fixed" and customer_group != "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"customer": doc.customer,
					"price_list_type": gemstone_price_list_type,
					"gemstone_grade": gd_row.gemstone_grade,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_type": gd_row.gemstone_type,
					"stone_shape": gd_row.stone_shape,
				},
				fields=["rate", "handling_rate"],
				limit=1,
			)

			if not price_list:
				frappe.throw("No Gemstone Price List found")

			rate = price_list[0].rate
			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# RETAIL CUSTOMER – FIXED PRICE
		# ---------------------------------------------
		if customer_group == "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"is_retail_customer": 1,
					"price_list_type": gemstone_price_list_type,
					"gemstone_grade": gd_row.gemstone_grade,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_type": gd_row.gemstone_type,
					"stone_shape": gd_row.stone_shape,
				},
				fields=["rate", "outwork_handling_charges_rate"],
				limit=1,
			)

			if not price_list:
				frappe.throw("No Retail Gemstone Price List found")

			rate = (
				price_list[0].outwork_handling_charges_rate
				if gd_row.is_customer_item
				else price_list[0].rate
			)

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.quantity)

			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# DIAMOND RANGE – NON-RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Diamond Range" and customer_group != "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"customer": doc.customer,
					"price_list_type": gemstone_price_list_type,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_grade": gd_row.gemstone_grade,
					"from_gemstone_pr_rate": ["<=", gd_row.gemstone_pr],
					"to_gemstone_pr_rate": [">=", gd_row.gemstone_pr],
				},
				fields=["name"],
				limit=1,
			)

			if not price_list:
				frappe.throw("Gemstone Diamond Range price list not found")

			price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

			rate = 0.0
			for mul in price_list_doc.gemstone_multiplier:
				if (
					mul.gemstone_type == gd_row.gemstone_type
					and flt(mul.from_weight) <= flt(gd_row.gemstone_pr) <= flt(mul.to_weight)
				):
					if gd_row.is_customer_item:
						rate = {
							"Precious": mul.outwork_precious_percentage,
							"Semi-Precious": mul.outwork_semi_precious_percentage,
							"Synthetic": mul.outwork_synthetic_percentage,
						}.get(gd_row.gemstone_quality, 0)
					else:
						rate = {
							"Precious": mul.precious_percentage,
							"Semi-Precious": mul.semi_precious_percentage,
							"Synthetic": mul.synthetic_percentage,
						}.get(gd_row.gemstone_quality, 0)
					break

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.gemstone_pr)
			
			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue

		# ---------------------------------------------
		# DIAMOND RANGE – RETAIL
		# ---------------------------------------------
		if gemstone_price_list_type == "Diamond Range" and customer_group == "Retail":
			price_list = frappe.get_all(
				"Gemstone Price List",
				filters={
					"is_retail_customer": 1,
					"price_list_type": gemstone_price_list_type,
					"cut_or_cab": gd_row.cut_or_cab,
					"gemstone_grade": gd_row.gemstone_grade,
					"from_gemstone_pr_rate": ["<=", gd_row.gemstone_pr],
					"to_gemstone_pr_rate": [">=", gd_row.gemstone_pr],
				},
				fields=["name"],
				limit=1,
			)

			if not price_list:
				frappe.throw("Retail Gemstone Diamond Range price list not found")

			price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

			rate = 0.0
			for mul in price_list_doc.get("gemstone_multiplier", []):
				if (
					mul.gemstone_type == gd_row.gemstone_type
					and flt(mul.from_weight) <= flt(gd_row.gemstone_pr) <= flt(mul.to_weight)
				):
					rate = {
						"Precious": mul.precious_percentage,
						"Semi-Precious": mul.semi_precious_percentage,
						"Synthetic": mul.synthetic_percentage,
					}.get(gd_row.gemstone_quality, 0)
					break

			gemstone_amt_total = calculate_percentage_amount(rate, gd_row.gemstone_pr)
			
			gd_row.update({
				"total_gemstone_rate": rate,
				"gemstone_rate_for_specified_quantity": gemstone_amt_total
			})
			continue
	
	return bom_data


def apply_current_consignment_raw_material_rate_to_bom(doc, bom_data: dict, invoice_item_doc: dict):
	"""
	Apply current rate for raw material consignment.
	"""
	precision = 3
	metal_data = bom_data.get("metal_detail", [])
	finding_data = bom_data.get("finding_detail", [])
	diamond_data = bom_data.get("diamond_detail", [])
	gemstone_data = bom_data.get("gemstone_detail", [])

	# factor = flt(row.qty) / flt(invoice_item.qty)
	if doc.return_material_type == "Metal-Finding":
		bom_data.update({
			"diamond_detail": [],
			"gemstone_detail": []
		})
	elif doc.return_material_type == "Diamond-Gemstone":
		bom_data.update({
			"metal_detail": [],
			"finding_detail": []
		})

	# makeing charge: 50% labour charges
	making_amount = invoice_item_doc.get("making_amount", 0) * 0.5

	# diamond and gemstone amount as invoice item amount
	diamond_amount = invoice_item_doc.get("diamond_amount", 0)
	gemstone_amount = invoice_item_doc.get("gemstone_amount", 0)

	# Custom Duty: (making + diamond + gemstone amount) * 6% * 50%
	custom_duty_amount = (making_amount + diamond_amount + gemstone_amount) * 0.06 * 0.5

	return bom_data.update({"custom_duty_amount": custom_duty_amount, "diamond_amount": diamond_amount})



def calculate_percentage_amount(rate, base_value):
	return round((flt(rate) / 100) * flt(base_value), 2)


def create_return_sales_invoice(doc):
	pass


