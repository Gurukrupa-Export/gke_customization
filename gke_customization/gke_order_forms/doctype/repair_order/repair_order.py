# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document,json
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.utils.data import now_datetime
from frappe.utils import get_datetime, now_datetime
from datetime import datetime
from frappe.model.naming import make_autoname


class RepairOrder(Document):
	def before_insert(self):
		if self.bom:
			fetch_bom_details(self)
		if self.required_design in  ["No","CAD"] and self.product_type in ["Company Goods - Branch Sales , Unsold & Undelivered","Customer Goods (Company Manufactured) - Sold & Delivered"]:
			fetch_bom_details(self)
		if self.tag_no1:
					fetch_jwelex_bom_details(self)

	def on_submit(self):
		if self.required_design == 'Manual':
			if self.workflow_state == 'Create Sketch' and not self.sketch_order_form:
				order_form_id = create_sketch(self)
				frappe.msgprint("New Sketch Order Form Created: {0}".format(get_link_to_form("Sketch Order Form",order_form_id)))

		# if self.required_design == 'CAD':
		# 	if self.workflow_state == 'Create CAD' and not self.sketch_order_form:
		# 		order_form_id = create_cad(self,sketch_item_code=self.item)
		# 		frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		
		if self.required_design == 'No':
			if self.product_type in ['Customer Goods (Company Manufactured) - Sold & Delivered','Company Goods - Branch Sales , Unsold & Undelivered']:
				# frappe.db.set_value('Item',self.item,'custom_repair_order',self.name)
				# frappe.db.set_value('Item',self.item,'custom_repair_order_form',self.serial_and_design_code_order_form)
				frappe.db.set_value(self.doctype, self.name, "new_item_code", self.item)
				if self.workflow_state == 'Update Item':
					new_bom_doc = create_bom(self,self.item)
					frappe.db.set_value(self.doctype, self.name, "new_bom", new_bom_doc)
				
			# else:
				# item_template = create_item_template_from_order(self)
				# updatet_item_template(item_template)
				# item_variant = create_variant_of_template_from_order(item_template,self.name)
				# update_item_variant(item_variant,item_template)
				# frappe.msgprint(("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
				# frappe.db.set_value(self.doctype, self.name, "new_item_code", item_variant)
				# frappe.db.set_value(self.doctype, self.name, "item", item_variant)	
		if self.workflow_state == "BOM Created" and self.product_type in ["Company Goods - Branch Sales , Unsold & Undelivered","Customer Goods (Company Manufactured) - Sold & Delivered"]:
					bom_creation(self)

	def on_update_after_submit(self):
		if self.required_design == 'Manual':
			if self.workflow_state == 'Create CAD' and not self.order_form:
				sketch_items = frappe.db.get_list('Item', filters={'custom_sketch_order_form_id': self.sketch_order_form}, fields=['name'])
				if not sketch_items:
					frappe.throw(
						f"Cannot create CAD: Sketch Order Form {frappe.bold(self.sketch_order_form)} "
						"is not yet approved or no item has been created from it. "
						"Please approve the Sketch Order Form first."
					)
				sketch_item_code = sketch_items[0]['name']
				order_form_id = create_cad(self, sketch_item_code)
				frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form", order_form_id)))
		# if self.product_type not in ['Customer Goods (Company Manufactured) - Sold & Delivered','Company Goods - Branch Sales , Unsold & Undelivered'] and self.required_design == 'No':
		# 	cerate_bom_timesheet(self)
  
		if self.workflow_state == "Creating BOM":
			bom_creation(self)
		if self.workflow_state == "BOM QC" and self.product_type == "Customer Goods (Other Company Manufactured)":
			create_serial_no(self)
		if self.workflow_state == "Create Serial No" and self.product_type == "Customer Goods (Other Company Manufactured)":
			create_serial_no(self)
		if self.workflow_state == "BOM QC" and self.tag_no1:
			# frappe.throw("HI")
			create_serial_no(self)
		if self.required_design == 'CAD':
					if self.workflow_state == 'Create CAD' and not self.sketch_order_form:
						order_form_id = create_cad(self,sketch_item_code=self.item)
						frappe.msgprint("New Order Form Created: {0}".format(get_link_to_form("Order Form",order_form_id)))
		if self.workflow_state == 'Update BOM' and self.is_jewelex_tag:
			new_bom_doc = bom_creation(self)
			self.db_set("item", self.new_item_code)
			# frappe.db.set_value(self.doctype, self.name, "new_bom", new_bom_doc)
		


		
# def fetch_bom_details(self):
# 	source_bom = None
# 	if self.bom:
# 		source_bom = frappe.get_doc("BOM", self.bom)
# 	if self.required_design in ["No",'CAD'] and self.product_type in ["Company Goods - Branch Sales , Unsold & Undelivered","Customer Goods (Company Manufactured) - Sold & Delivered"]:
# 		source_bom = frappe.get_doc("BOM", self.serial_no_bom)

# 	self.set("metal_detail", [])
# 	total_metal_weight = 0
# 	for row in source_bom.metal_detail:
# 		self.append("metal_detail", {
# 			"metal_type": row.metal_type,
# 			"metal_touch": row.metal_touch,
# 			"metal_colour": row.metal_colour,
# 			"metal_purity": row.metal_purity,
# 			"quantity": row.quantity,
# 			"difference": row.difference,
# 			"cad_weight": row.cad_weight,
# 			"cam_weight": row.cam_weight,
# 			"wax_weight": row.wax_weight,
# 			"casting_weight": row.casting_weight,
# 			"finish_loss_grams": row.finish_loss_grams,
# 			"finish_loss_percentage": row.finish_loss_percentage,
# 			"finish_product_weight": row.finish_product_weight,
# 		})
# 		total_metal_weight += row.quantity or 0

# 	self.set("finding_detail", [])
# 	for row in source_bom.finding_detail:
# 		self.append("finding_detail", {
# 			"metal_type": row.metal_type,
# 			"metal_touch": row.metal_touch,
# 			"metal_colour": row.metal_colour,
# 			"metal_purity": row.metal_purity,
# 			"quantity": row.quantity,
# 			"qty": row.qty,
# 			"finding_size": row.finding_size,
# 			"finding_type": row.finding_type,
# 			"finding_category": row.finding_category,
# 		})

# 	self.set("diamond_detail", [])
# 	for row in source_bom.diamond_detail:
# 		self.append("diamond_detail", {
# 			"sieve_size_range": row.sieve_size_range,
# 			"diamond_sieve_size": row.diamond_sieve_size,
# 			"size_in_mm": row.size_in_mm,
# 			"sub_setting_type": row.sub_setting_type,
# 			"stone_shape": row.stone_shape,
# 			"diamond_type": row.diamond_type,
# 			"quality": row.quality,
# 			"diamond_grade": row.diamond_grade,
# 			"weight_in_gms": row.weight_in_gms,
# 			"quantity": row.quantity,
# 			"weight_per_pcs": row.weight_per_pcs,
# 			"pcs": row.pcs,
# 		})

# 	self.set("gemstone_detail", [])
# 	for row in source_bom.gemstone_detail:
# 		self.append("gemstone_detail", {
# 			"gemstone_quality": row.gemstone_quality,
# 			"stone_shape": row.stone_shape,
# 			"cut_or_cab": row.cut_or_cab,
# 			"gemstone_type": row.gemstone_type,
# 			"gemstone_size": row.gemstone_size,
# 			"gemstone_code": row.gemstone_code,
# 			"sub_setting_type": row.sub_setting_type,
# 			"pcs": row.pcs,
# 			"quantity": row.quantity,
# 			"weight_in_gms": row.weight_in_gms,
# 			"is_customer_item": row.is_customer_item,
# 		})

# 	self.set("other_detail", [])
# 	for row in source_bom.other_detail:
# 		self.append("other_detail", {
# 			"quantity": row.quantity,
# 			"qty": row.qty,
# 			"item_code": row.item_code,
# 		})

# 	# Per-category totals (BOM field -> Repair Order field)
# 	self.total_metal_weight = total_metal_weight

# 	self.total_finding_pcs = source_bom.finding_pcs
# 	self.total_finding_weightin_gms = source_bom.total_finding_weight_per_gram

# 	self.total_diamond_pcs = source_bom.total_diamond_pcs
# 	self.total_diamond_weight = source_bom.total_diamond_weight
# 	self.total_diamond_weightin_gms = source_bom.total_diamond_weight_in_gms

# 	self.total_gemstone_pcs = source_bom.total_gemstone_pcs
# 	self.total_gemstone_weight = source_bom.total_gemstone_weight
# 	self.total_gemstone_weightin_gms = source_bom.total_gemstone_weight_in_gms

# 	self.total_other_pcs = source_bom.total_other_pcs
# 	self.total_other_weight = source_bom.total_other_weight

# 	# Product Weight section
# 	self.metal_weight_in_gram = source_bom.metal_weight
# 	self.gross_weight_in_gram = source_bom.gross_weight
# 	self.net_weight_in_gram = source_bom.metal_and_finding_weight
# 	self.net_wt_add_on = source_bom.net_wt_add_on
# 	self.diamond_weight_in_carat = source_bom.diamond_weight
# 	self.gemstone_weight_in_carat = source_bom.gemstone_weight
# 	self.other_weight_in_gram = source_bom.other_weight
# 	self.finding_weight_in_gram = source_bom.finding_weight_
# 	self.total_diamond_weight_in_gram = source_bom.total_diamond_weight_in_gms
# 	self.total_gemstone_weight_in_gram = source_bom.total_gemstone_weight_in_gms

# 	# Product Ratio section
# 	self.metal_to_diamond_ratioincl_of_finding = source_bom.gold_to_diamond_ratio
# 	self.metal_to_diamond_ratioexcl_of_finding = source_bom.metal_to_diamond_ratio_excl_of_finding
# 	self.avg_diamond_weightin_carat = source_bom.diamond_ratio
# 	self.rating = source_bom.custom_rating




		
def fetch_bom_details(self):
	source_bom = None
	if self.bom:
		source_bom = frappe.get_doc("BOM", self.bom)
	if self.required_design in ["No",'CAD'] and self.product_type in ["Company Goods - Branch Sales , Unsold & Undelivered","Customer Goods (Company Manufactured) - Sold & Delivered"] and self.serial_no_bom:
		source_bom = frappe.get_doc("BOM", self.serial_no_bom)

	if not source_bom:
		return

	self.set("metal_detail", [])
	total_metal_weight = 0
	for row in source_bom.metal_detail:
		self.append("metal_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"difference": row.difference,
			"cad_weight": row.cad_weight,
			"cam_weight": row.cam_weight,
			"wax_weight": row.wax_weight,
			"casting_weight": row.casting_weight,
			"finish_loss_grams": row.finish_loss_grams,
			"finish_loss_percentage": row.finish_loss_percentage,
			"finish_product_weight": row.finish_product_weight,
		})
		total_metal_weight += row.quantity or 0

	self.set("finding_detail", [])
	for row in source_bom.finding_detail:
		self.append("finding_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"qty": row.qty,
			"finding_size": row.finding_size,
			"finding_type": row.finding_type,
			"finding_category": row.finding_category,
		})

	self.set("diamond_detail", [])
	for row in source_bom.diamond_detail:
		self.append("diamond_detail", {
			"sieve_size_range": row.sieve_size_range,
			"diamond_sieve_size": row.diamond_sieve_size,
			"size_in_mm": row.size_in_mm,
			"sub_setting_type": row.sub_setting_type,
			"stone_shape": row.stone_shape,
			"diamond_type": row.diamond_type,
			"quality": row.quality,
			"diamond_grade": row.diamond_grade,
			"weight_in_gms": row.weight_in_gms,
			"quantity": row.quantity,
			"weight_per_pcs": row.weight_per_pcs,
			"pcs": row.pcs,
		})

	self.set("gemstone_detail", [])
	for row in source_bom.gemstone_detail:
		self.append("gemstone_detail", {
			"gemstone_quality": row.gemstone_quality,
			"stone_shape": row.stone_shape,
			"cut_or_cab": row.cut_or_cab,
			"gemstone_type": row.gemstone_type,
			"gemstone_size": row.gemstone_size,
			"gemstone_code": row.gemstone_code,
			"sub_setting_type": row.sub_setting_type,
			"pcs": row.pcs,
			"quantity": row.quantity,
			"weight_in_gms": row.weight_in_gms,
			"is_customer_item": row.is_customer_item,
		})

	self.set("other_detail", [])
	for row in source_bom.other_detail:
		self.append("other_detail", {
			"quantity": row.quantity,
			"qty": row.qty,
			"item_code": row.item_code,
		})

	# Per-category totals (BOM field -> Repair Order field)
	self.total_metal_weight = total_metal_weight

	self.total_finding_pcs = source_bom.finding_pcs
	self.total_finding_weightin_gms = source_bom.total_finding_weight_per_gram

	self.total_diamond_pcs = source_bom.total_diamond_pcs
	self.total_diamond_weight = source_bom.total_diamond_weight
	self.total_diamond_weightin_gms = source_bom.total_diamond_weight_in_gms

	self.total_gemstone_pcs = source_bom.total_gemstone_pcs
	self.total_gemstone_weight = source_bom.total_gemstone_weight
	self.total_gemstone_weightin_gms = source_bom.total_gemstone_weight_in_gms

	self.total_other_pcs = source_bom.total_other_pcs
	self.total_other_weight = source_bom.total_other_weight

	# Product Weight section
	self.metal_weight_in_gram = source_bom.metal_weight
	self.gross_weight_in_gram = source_bom.gross_weight
	self.net_weight_in_gram = source_bom.metal_and_finding_weight
	self.net_wt_add_on = source_bom.net_wt_add_on
	self.diamond_weight_in_carat = source_bom.diamond_weight
	self.gemstone_weight_in_carat = source_bom.gemstone_weight
	self.other_weight_in_gram = source_bom.other_weight
	self.finding_weight_in_gram = source_bom.finding_weight_
	self.total_diamond_weight_in_gram = source_bom.total_diamond_weight_in_gms
	self.total_gemstone_weight_in_gram = source_bom.total_gemstone_weight_in_gms

	# Product Ratio section
	self.metal_to_diamond_ratioincl_of_finding = source_bom.gold_to_diamond_ratio
	self.metal_to_diamond_ratioexcl_of_finding = source_bom.metal_to_diamond_ratio_excl_of_finding
	self.avg_diamond_weightin_carat = source_bom.diamond_ratio
	self.rating = source_bom.custom_rating

def fetch_jwelex_bom_details(self):
	company_code = "GEPL" if self.company == "Gurukrupa Export Private Limited" else "KGPL"
	data = get_data_from_jwelex(self.tag_no1, company_code)
	materials = data.get("materials", {})

	self.set("metal_detail", [])
	for row in materials.get("metal_details", []):
		self.append("metal_detail", {
			"metal_type": row.get("Meterial"),
			"metal_touch": row.get("Purity_Name"),
			"metal_purity": row.get("Size_Name"),
			"metal_colour": "Yellow",
			"quantity": row.get("Weight"),
		})

	self.set("finding_detail", [])
	for row in materials.get("finding_details", []):
		self.append("finding_detail", {
			"metal_type": row.get("Meterial"),
			"metal_touch": row.get("Purity_Name"),
			"finding_type": row.get("Shape_Name"),
			"finding_size": row.get("Size_Name"),
			"finding_category": row.get("Code_Name"),
			"quantity": row.get("Weight"),
			"qty": row.get("Pcs"),
		})

	self.set("diamond_detail", [])
	for row in materials.get("diamond_details", []):
		pcs = row.get("Pcs") or 0
		weight = row.get("Weight") or 0
		self.append("diamond_detail", {
			"diamond_type": row.get("Meterial"),
			"stone_shape": row.get("Shape_Name"),
			"diamond_grade": row.get("Purity_Name"),
			"diamond_sieve_size": row.get("Size_Name"),
			"size_in_mm": row.get("Code_Name"),
			"pcs": pcs,
			"quantity": weight,
			"weight_in_gms": row.get("Gross_Wt"),
			"weight_per_pcs": (weight / pcs) if pcs else weight,
		})

	self.set("gemstone_detail", [])
	for row in materials.get("stone_details", []):
		self.append("gemstone_detail", {
			"gemstone_type": row.get("Meterial"),
			"stone_shape": row.get("Shape_Name"),
			"gemstone_quality": row.get("Purity_Name"),
			"gemstone_size": row.get("Size_Name"),
			"gemstone_code": row.get("Code_Name"),
			"pcs": row.get("Pcs"),
			"quantity": row.get("Weight"),
			"weight_in_gms": row.get("Gross_Wt"),
		})

	self.set("other_detail", [])
	for row in materials.get("other_details", []):
		self.append("other_detail", {
			"item_code": row.get("Meterial"),
			"quantity": row.get("Weight"),
			"qty": row.get("Pcs"),
		})


def bom_creation(self):
	# if not self.item:
	# 	frappe.throw("Item is not specified in the Order.")
	if not self.qty:
		frappe.throw("Quantity is not specified in the Order.")

	# Check if BOM already exists for this item and design_type is NOT Mod
	if self.required_design not in ["No","CAD"]:
		existing_boms = frappe.get_all("BOM", filters={"item": self.item, "docstatus": 1}, fields=["name"])
		if existing_boms:
			frappe.throw(f"BOM already exists for item {self.item}. Multiple BOMs are allowed only for 'Mod' design type.")

	# Create new BOM document
	bom = frappe.new_doc("BOM")
	if self.is_jewelex_tag:
		bom.item = self.new_item_code
	else:
		bom.item = self.item
	bom.is_active = 1
	bom.is_default = 0

	total_diamond_pcs = 0
	total_finding_pcs = 0
	total_gemstone_pcs = 0
	finding_quantity = 0
	gemstone_quantity = 0
	metal_quantity_total = 0
	diamond_weight = 0 
	gemstone_weight = 0
	finding_weight = 0

	# Set naming series
	bom.naming_series = f"BOM-{self.item}.-"
	bom.product_size = self.product_size
	if self.required_design == 'CAD':
		bom.bom_type = "Finish Goods"
		bom.is_active = 0
	else:
		bom.bom_type = "Template"
	bom.detachable = self.detachable
	bom.metal_type = self.metal_type
	bom.metal_touch = self.metal_touch
	bom.metal_colour = self.metal_colour
	# bom.diamond_type = self.diamond_type
	bom.metal_target = self.metal_target
	bom.diamond_target = self.diamond_target
	bom.stone_changeable = self.stone_changeable
	bom.capganthan = self.capganthan
	bom.chain_weight = self.chain_weight
	bom.feature = self.feature
	bom.rhodium = self.rhodium
	bom.back_chain_size = self.back_chain_size
	bom.two_in_one = self.two_in_one
	bom.enamal = self.enamal
	bom.chain_type = self.chain_type
	bom.gemstone_type1 = self.gemstone_type
	bom.gemstone_quality = self.gemstone_quality
	bom.setting_type = self.setting_type
	bom.sub_setting_type1 = self.sub_setting_type1
	bom.lock_type = self.lock_type
	bom.distance_between_kadi_to_mugappu = self.distance_between_kadi_to_mugappu
	bom.number_of_ant = self.number_of_ant
	bom.space_between_mugappu = self.space_between_mugappu
	bom.count_of_spiral_turns = self.count_of_spiral_turns
	bom.black_bead_line = self.black_bead_line
	bom.chain_length = self.chain_length

	# Append item in BOM Items table (Raw Materials)
	bom.append("items", {
    "item_code": self.new_item_code if self.is_jewelex_tag else self.item,
    "qty": self.qty,
    "do_not_explode": 1
	})

	# Copy metal_detail and set BOM's metal_purity from first row
	first_metal_purity = None

	for row in self.metal_detail:
		bom.append("metal_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"difference":row.difference,
			"cad_weight":row.cad_weight,
			"cam_weight":row.cam_weight,
			"wax_weight":row.wax_weight,
			"casting_weight":row.casting_weight,
			"finish_loss_grams":row.finish_loss_grams,
			"finish_loss_percentage":row.finish_loss_percentage,
			"finish_product_weight":row.finish_product_weight,
			# Add any other fields present in the child table
		})
	for row in self.finding_detail:
		bom.append("finding_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"qty":row.qty,
			"finding_size":row.finding_size,
			"finding_type":row.finding_type,
			"finding_category":row.finding_category,
		})
	for row in self.diamond_detail:
		bom.append("diamond_detail", {
			"sieve_size_range": row.sieve_size_range,
			"diamond_sieve_size": row.diamond_sieve_size,
			"size_in_mm": row.size_in_mm,
			"sub_setting_type": row.sub_setting_type,
			"stone_shape": row.stone_shape,
			"diamond_type":row.diamond_type,
			"quality":row.quality,
			"diamond_grade":row.diamond_grade,
			"weight_in_gms":row.weight_in_gms,
			"quantity":row.quantity,
			"weight_per_pcs":row.weight_per_pcs,
			"pcs":row.pcs,
		})
	for row in self.gemstone_detail:
		bom.append("gemstone_detail", {
			"gemstone_quality": row.gemstone_quality,
			"stone_shape": row.stone_shape,
			"cut_or_cab": row.cut_or_cab,
			"gemstone_type": row.gemstone_type,
			"gemstone_size": row.gemstone_size,
			"gemstone_code":row.gemstone_code,
			"sub_setting_type":row.sub_setting_type,
			"pcs":row.pcs,
			"quantity":row.quantity,
			"weight_in_gms":row.weight_in_gms,
			"is_customer_item":row.is_customer_item,
		})
	for row in self.other_detail:
		bom.append("other_detail", {
			"quantity": row.quantity,
			"qty": row.qty,
			"item_code": row.item_code,
		})
	
	bom.total_metal_weight = metal_quantity_total
	bom.metal_weight = bom.total_metal_weight
	if first_metal_purity:
		bom.metal_purity = first_metal_purity

	# Copy finding_detail
	
	bom.finding_pcs = total_finding_pcs
	bom.total_finding_weight_per_gram = finding_quantity
	bom.finding_weight = finding_weight

	# Copy diamond_detail
	
	bom.total_diamond_pcs = total_diamond_pcs
	bom.diamond_weight = diamond_weight

	# Copy gemstone_details
	
	bom.total_gemstone_pcs = total_gemstone_pcs
	bom.total_gemstone_weight_per_gram = gemstone_quantity
	bom.gemstone_weight = gemstone_weight

	# Final calculated fields
	bom.metal_and_finding_weight = (bom.metal_weight or 0) + (bom.finding_weight or 0)
	bom.gold_to_diamond_ratio = (
		float(bom.metal_and_finding_weight) / float(bom.diamond_weight) if bom.diamond_weight else 0
	)

	# Save and submit the BOM
	bom.insert()
	bom.save(ignore_permissions=True)

	# Update Order with created BOM name
	if self.product_type in ["Company Goods - Branch Sales , Unsold & Undelivered","Customer Goods (Company Manufactured) - Sold & Delivered"] and self.required_design =="CAD":
		self.db_set("product_bom", bom.name)  # Assuming 'new_bom' field exists
	else:
		self.db_set("new_bom", bom.name)  # Assuming 'new_bom' field exists

	frappe.msgprint(f"BOM {bom.name} created successfully.")



		
def create_cad(self,sketch_item_code):
	
	order_form_doc = frappe.new_doc("Order Form")
	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.branch = self.branch
	order_form_doc.flow_type = self.flow_type
	order_form_doc.salesman_name = self.salesman_name
	order_form_doc.customer_code = self.customer_code
	order_form_doc.order_date = self.order_date
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.project = self.project
	order_form_doc.parcel_place = self.parcel_place
	order_form_doc.po_no = self.po_no
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.diamond_quality = self.diamond_quality
	order_form_doc.service_type = self.service_type
	order_form_doc.repair_order = self.name
	order_form_doc.total_rows = 1
	set_value_in_cad_child_table(order_form_doc,self,sketch_item_code)
	
	
	order_form_doc.save()
	frappe.db.set_value('Repair Order',self.name,'order_form',order_form_doc.name)
	return order_form_doc.name

def create_sketch(self):
	order_form_doc = frappe.new_doc("Sketch Order Form")

	order_form_doc.company = self.company
	order_form_doc.department = self.department
	order_form_doc.branch = self.branch
	order_form_doc.salesman_name = self.salesman_name

	order_form_doc.customer_code = self.customer_code
	order_date = get_datetime(self.order_date).date()
	current_time = now_datetime().time()

	order_form_doc.order_date = datetime.combine(order_date, current_time)
	# order_form_doc.order_date = self.order_date
	order_form_doc.delivery_date = self.delivery_date
	order_form_doc.project = self.project
	order_form_doc.design_by = "Customer Design"
	order_form_doc.po_no = self.po_no
	order_form_doc.order_type = self.order_type
	order_form_doc.due_days = self.due_days
	order_form_doc.repair_order = self.name
	set_value_in_sketch_child_table(order_form_doc,self)
	order_form_doc.save()
	frappe.db.set_value('Repair Order',self.name,'sketch_order_form',order_form_doc.name)
	return order_form_doc.name

def set_value_in_cad_child_table(order_form_doc,self,sketch_item_code):
	order_details = order_form_doc.append("order_details", {})
	if self.required_design == 'Manual':
		# order_details.design_type = 'Mod'
		order_details.design_type = 'Sketch Design'
	elif self.required_design == 'CAD':
		if self.tag_no or self.serial_no:
			if self.mod_reason == "Category Change":
				order_details.design_type = 'New Design'
				order_details.reference_serial_no = self.tag_no
				order_details.reference_design_code = self.item

			else:
				order_details.design_type = 'Mod - Old Stylebio & Tag No'
				
		else:
			order_details.design_type = 'New Design'

	if self.product_type == 'Company Goods - Branch Sales , Unsold & Undelivered':
		order_details.design_by = 'Our Design'
		
	else:
		order_details.design_by = 'Customer Design'
	

	# frappe.throw(f"{sketch_item_code}")
	order_details.bom_or_cad = workflow_state_maker(self)
	order_details.item_type = set_item_type(self)
	order_details.is_repairing = 1
	order_details.tag__design_id = self.item
	if self.mod_reason == "Category Change":
		order_details.tag_no = ""
		order_details.bom = ""
		order_details.design_id = ""
		image = frappe.db.get_value("Item", self.item, "image")
		order_details.design_image_1 =  image
	elif (self.is_jewelex_tag and self.serial_no) and self.required_design == 'CAD':
		order_details.tag_no = self.serial_no
		order_details.bom = self.new_bom
		order_details.design_id = self.new_item_code
	else:
		order_details.tag_no = self.tag_no
		order_details.bom = self.bom
		order_details.design_id = sketch_item_code

	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.metal_target = self.metal_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1
	order_details.design_image_1 = self.design_image1
	order_details.stone_changeable = self.stone_changeable
	order_details.metal_colour = self.metal_colour
	subcategory_attributes = frappe.db.sql(f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{self.subcategory}' and in_cad = 1""",as_dict=1)
	for i in subcategory_attributes:
		a = getattr(self, i['item_attribute'].replace(' ','_').lower().replace('item_subcategory','subcategory').replace('item_category','category').replace('custom_metal_target','metal_target').replace('/',''))
		setattr(order_details, i['item_attribute'].replace(' ','_').lower(), a)

def set_value_in_sketch_child_table(order_form_doc,self):
	order_details = order_form_doc.append("order_details", {})
	order_details.design_type = 'New Design'
	# order_details.item_type = 'Only Variant'
	order_details.is_repairing = 1
	order_details.tag__design_id = self.item
	order_details.tag_id = self.tag_no
	order_details.master_bom_no = self.bom
	order_details.delivery_date = self.delivery_date
	order_details.category = self.category
	order_details.subcategory = self.subcategory
	order_details.qty = self.qty
	order_details.setting_type = self.setting_type
	order_details.sub_setting_type1 = self.sub_setting_type1
	order_details.sub_setting_type2 = self.sub_setting_type2
	order_details.metal_target = self.metal_target
	order_details.diamond_target = self.diamond_target
	order_details.product_size = self.product_size
	order_details.gemstone_type1 = self.gemstone_type1
	order_details.budget = 0
	order_details.stone_changeable = self.stone_changeable
	subcategory_attributes = frappe.db.sql(f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{self.subcategory}' and in_cad = 1""",as_dict=1)
	for i in subcategory_attributes:
		a = getattr(self, i['item_attribute'].replace(' ','_').lower().replace('item_subcategory','subcategory').replace('item_category','category').replace('custom_metal_target','metal_target').replace("/",""))
		setattr(order_details, i['item_attribute'].replace(' ','_').lower(), a)
		# try:
		# except:
		# 	pass
	
def workflow_state_maker(self):
	if self.product_type in ['Company Goods - Branch Sales , Unsold & Undelivered','Customer Goods (Company Manufactured) - Sold & Delivered']:
		bom_or_cad = 'Duplicate BOM'
	else:
		bom_or_cad = 'CAD'
	return bom_or_cad

def set_item_type(self):
	item_type = ''
	if self.product_type == 'Customer Goods (Other Company Manufactured)':
		item_type = 'Template and Variant'
	elif self.product_type in ['Company Goods - Branch Sales , Unsold & Undelivered','Customer Goods (Company Manufactured) - Sold & Delivered'] and self.repair_type =='Modified Raw Material':
		item_type = 'Only Variant'
	elif self.product_type in ['Company Goods - Branch Sales , Unsold & Undelivered','Customer Goods (Company Manufactured) - Sold & Delivered'] and self.repair_type =='Modified Product':
		item_type = 'Template and Variant'
	return item_type

def create_item_template_from_order(source_name, target_doc=None):
	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1
		# target.subcategory = source.subcategory
		# target.item_category = source.category
	
		try:
		# if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		except:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		target.item_group = source.subcategory + " - T",

		
	doc = get_mapped_doc(
		"Repair Order",
		source_name.name,
		{
			"Repair Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					
				} 
			}
		},target_doc, post_process
	)
	# frappe.throw(f"{doc.item_category}")

	doc.save()
	return doc.name

def create_variant_of_template_from_order(item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Repair Order'
		target.item_group = frappe.db.get_value('Repair Order',source_name,'subcategory') + " - V",
		target.custom_repair_order = source_name
		target.custom_repair_order_form = frappe.db.get_value('Repair Order',source_name,'order_form')
		target.item_code = f'{item_template}-001'
		target.sequence = item_template[2:7]
		subcateogy = frappe.db.get_value('Item',item_template,'item_subcategory')
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': subcateogy,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			try:
				attribute_value = frappe.db.get_value('Repair Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':attribute_value
			})

		try:
		# if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		except:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')

	doc = get_mapped_doc(
		"Repair Order",
		source_name,
		{
			"Repair Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					# "india":"india",
					# "india_states":"india_states",
					# "usa":"usa",
					# "usa_states":"usa_states",
					# "age_group":"custom_age_group",
					# "alphabetnumber":"custom_alphabetnumber",
					# "animalbirds":"custom_animalbirds",
					# "collection":"custom_collection",
					# "design_style":"custom_design_style",
					# "gender":"custom_gender",
					# "lines_rows":"custom_lines__rows",
					# "language":"custom_language",
					# "occasion":"custom_occasion",
					# "rhodium":"custom_rhodium",
					# "shapes":"custom_religious",
					# "religious":"custom_shapes",
					# "zodiac":"custom_zodiac",
				} 
			}
		},target_doc, post_process
	)
	
	doc.save()
	return doc.name


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)
		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)
		quotation.conversion_rate = exchange_rate
		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")

		quotation.quotation_to = "Customer"
		field_map = {
 			# target : source
			"company": "company",
			"party_name": "customer_code",
			"order_type": "order_type",
			"diamond_quality": "diamond_quality"
		}
		for target_field, source_field in field_map.items():
			quotation.set(target_field,source.get(source_field))
		service_types = frappe.db.get_values("Service Type 2", {"parent": source.name},"service_type1")
		for service_type in service_types:
			quotation.append("service_type",{"service_type1": service_type[0]})

	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	snd_order = frappe.db.get_value("Repair Order", source_name, "*")
	if snd_order.get("new_item_code"):
		item = snd_order.get("new_item_code")
	else:
		item = snd_order.get("item")
	target_doc.append("items", {
		"branch": snd_order.get("branch"),
		"project": snd_order.get("project"),
		"item_code": item,
		"serial_no": snd_order.get("tag_no"),
		"metal_colour": snd_order.get("metal_colour"),
		"metal_purity": snd_order.get("metal_purity"),
		"metal_touch": snd_order.get("metal_touch"),
		"gemstone_quality": snd_order.get("gemstone_quality"),
		"item_category" : snd_order.get("category"),
		"diamond_quality": snd_order.get("diamond_quality"),
		"item_subcategory": snd_order.get("subcategory"),
		"setting_type": snd_order.get("setting_type"),
		"delivery_date": snd_order.get("delivery_date"),
		"order_form_type": "Repair Order",
		"order_form_id": snd_order.get("name"),
		"salesman_name": snd_order.get("salesman_name"),
		"order_form_date": snd_order.get("order_date"),
		"custom_customer_sample": snd_order.get("customer_sample"),
		"custom_customer_voucher_no": snd_order.get("customer_sample_voucher_no"),
		"custom_customer_gold": snd_order.get("customer_gold"),
		"custom_customer_diamond": snd_order.get("customer_diamond"),
		"custom_customer_stone": snd_order.get("customer_stone"),
		"custom_customer_good": snd_order.get("customer_good"),
		"po_no": snd_order.get("po_no"),
		"custom_repair_type": snd_order.get("repair_type"),
		"custom_product_type": snd_order.get("product_type"),
		"custom_serial_id_bom": snd_order.get("bom"),
		"custom_bom_weight": snd_order.get("bom_weight"),
		"custom_customer_weight": snd_order.get("customer_weight"),
		"custom_required_design":snd_order.get("required_design"),
		"custom_new_item_code":snd_order.get("new_item_code"),
		"custom_new_bom":snd_order.get("new_bom"),

	})
	set_missing_values(snd_order, target_doc)

	return target_doc

def updatet_item_template(item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template,
		"custom_repair_order":"",
		"custom_repair_order_form":"",
	})

def update_item_variant(item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})


# def create_bom(self,item_variant):
# 	if self.serial_no_bom:
# 		bom_doc = frappe.get_doc("BOM",self.serial_no_bom)
# 	# elif self.bom:
# 	else:
# 		bom_doc = frappe.get_doc("BOM",self.bom)
# 	new_bom_doc = frappe.new_doc("BOM")
# 	new_bom_doc = bom_doc
# 	new_bom_doc.docstatus = 0
# 	new_bom_doc.name = ''
# 	new_bom_doc.is_active = 1
# 	new_bom_doc.is_default = 1
# 	new_bom_doc.bom_type = 'Template'
# 	new_bom_doc.item = item_variant
# 	new_bom_doc.custom_order_form_type = 'Repair Order'
# 	new_bom_doc.custom_cad_order_form_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_form_id")
# 	new_bom_doc.custom_order_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_id")
# 	new_bom_doc.custom_repair_order_form_id = frappe.db.get_value("Item",item_variant,"custom_repair_order_form")
# 	new_bom_doc.custom_repair_order_id = frappe.db.get_value("Item",item_variant,"custom_repair_order")
# 	new_bom_doc.save()
# 	return new_bom_doc.name



def create_bom(self,item_variant):
	if self.serial_no_bom:
		bom_doc = frappe.get_doc("BOM",self.serial_no_bom)
	# elif self.bom:
	else:
		bom_doc = frappe.get_doc("BOM",self.bom)
	new_bom_doc = frappe.new_doc("BOM")
	new_bom_doc = bom_doc
	new_bom_doc.docstatus = 0
	new_bom_doc.name = ''
	new_bom_doc.is_active = 1
	new_bom_doc.is_default = 1
	new_bom_doc.bom_type = 'Template'
	new_bom_doc.item = item_variant
	new_bom_doc.custom_order_form_type = 'Repair Order'
	new_bom_doc.custom_cad_order_form_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_form_id")
	new_bom_doc.custom_order_id = frappe.db.get_value("Item",item_variant,"custom_cad_order_id")
	new_bom_doc.custom_repair_order_form_id = frappe.db.get_value("Item",item_variant,"custom_repair_order_form")
	new_bom_doc.custom_repair_order_id = frappe.db.get_value("Item",item_variant,"custom_repair_order")

	metal_quantity_total = 0
	first_metal_purity = None

	new_bom_doc.set("metal_detail", [])
	for row in self.metal_detail:
		new_bom_doc.append("metal_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"difference":row.difference,
			"cad_weight":row.cad_weight,
			"cam_weight":row.cam_weight,
			"wax_weight":row.wax_weight,
			"casting_weight":row.casting_weight,
			"finish_loss_grams":row.finish_loss_grams,
			"finish_loss_percentage":row.finish_loss_percentage,
			"finish_product_weight":row.finish_product_weight,
			# Add any other fields present in the child table
		})
	new_bom_doc.set("finding_detail", [])
	for row in self.finding_detail:
		new_bom_doc.append("finding_detail", {
			"metal_type": row.metal_type,
			"metal_touch": row.metal_touch,
			"metal_colour": row.metal_colour,
			"metal_purity": row.metal_purity,
			"quantity": row.quantity,
			"qty":row.qty,
			"finding_size":row.finding_size,
			"finding_type":row.finding_type,
			"finding_category":row.finding_category,
		})
	new_bom_doc.set("diamond_detail", [])
	for row in self.diamond_detail:
		new_bom_doc.append("diamond_detail", {
			"sieve_size_range": row.sieve_size_range,
			"diamond_sieve_size": row.diamond_sieve_size,
			"size_in_mm": row.size_in_mm,
			"sub_setting_type": row.sub_setting_type,
			"stone_shape": row.stone_shape,
			"diamond_type":row.diamond_type,
			"quality":row.quality,
			"diamond_grade":row.diamond_grade,
			"weight_in_gms":row.weight_in_gms,
			"quantity":row.quantity,
			"weight_per_pcs":row.weight_per_pcs,
			"pcs":row.pcs,
		})
	new_bom_doc.set("gemstone_detail", [])
	for row in self.gemstone_detail:
		new_bom_doc.append("gemstone_detail", {
			"gemstone_quality": row.gemstone_quality,
			"stone_shape": row.stone_shape,
			"cut_or_cab": row.cut_or_cab,
			"gemstone_type": row.gemstone_type,
			"gemstone_size": row.gemstone_size,
			"gemstone_code":row.gemstone_code,
			"sub_setting_type":row.sub_setting_type,
			"pcs":row.pcs,
			"quantity":row.quantity,
			"weight_in_gms":row.weight_in_gms,
			"is_customer_item":row.is_customer_item,
		})
	new_bom_doc.set("other_detail", [])
	for row in self.other_detail:
		new_bom_doc.append("other_detail", {
			"quantity": row.quantity,
			"qty": row.qty,
			"item_code": row.item_code,
		})

	new_bom_doc.total_metal_weight = metal_quantity_total
	new_bom_doc.metal_weight = new_bom_doc.total_metal_weight
	if first_metal_purity:
		new_bom_doc.metal_purity = first_metal_purity

	new_bom_doc.save()
	return new_bom_doc.name



def cerate_bom_timesheet(self):
	if self.workflow_state == "Creating BOM":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')

		designer_value = self.bom_assignment[-1].designer		
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
		else:
			timesheet_doc = frappe.new_doc("Timesheet")
			timesheet_doc.employee = designer_value
		
		if (timesheet_doc.time_logs and 
			timesheet_doc.time_logs[-1].activity_type in ['BOM QC','BOM QC - On-Hold']) :
			timesheet_doc.time_logs[-1].to_time = now_datetime()
			timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600

		time_log = timesheet_doc.append("time_logs", {})
		time_log.activity_type = "Create BOM"
		time_log.from_time = now_datetime()
		timesheet_doc.repair_order = self.name	
		if self.new_bom:
			timesheet_doc.save()
			frappe.msgprint("Timesheets Created for BOM each designer assignment")

	elif self.workflow_state == "Creating BOM - On-Hold":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')


		designer_value = self.bom_assignment[-1].designer
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			if timesheet_doc.time_logs:	
				time_log = timesheet_doc.time_logs[-1]					
				time_log.to_time = now_datetime()
				time_log.completed = 1
				time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

			if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "Create BOM - On Hold":
				qc_time_log = timesheet_doc.append("time_logs", {})
				qc_time_log.activity_type = "Create BOM - On Hold"
				qc_time_log.from_time = now_datetime()
				qc_time_log.custom_cad_order_id = self.name
				timesheet_doc.save()

		else:
			frappe.throw("Timesheets is not created for each designer assignment")		
			

	elif self.workflow_state == "BOM QC":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')

		designer_value = self.bom_assignment[-1].designer

		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			if timesheet_doc.time_logs:	
				time_log = timesheet_doc.time_logs[-1]					
				time_log.to_time = now_datetime()
				time_log.completed = 1
				time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

			qc_time_log = timesheet_doc.append("time_logs", {})
			qc_time_log.activity_type = "BOM QC"
			qc_time_log.from_time = now_datetime()
			qc_time_log.custom_cad_order_id = self.name				
			timesheet_doc.save()
		else:
			frappe.throw("Timesheets is not created for each designer assignment")		

	elif self.workflow_state == "BOM QC - On-Hold":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')

		designer_value = self.bom_assignment[-1].designer
		
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			if timesheet_doc.time_logs:	
				time_log = timesheet_doc.time_logs[-1]					
				time_log.to_time = now_datetime()
				time_log.completed = 1
				time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

			if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "BOM QC - On Hold":
				qc_time_log = timesheet_doc.append("time_logs", {})
				qc_time_log.activity_type = "BOM QC - On Hold"
				qc_time_log.from_time = now_datetime()
				qc_time_log.custom_cad_order_id = self.name
				timesheet_doc.save()
		else:
			frappe.throw("Timesheets is not created for each designer assignment")		

	elif self.workflow_state == "Updating BOM":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')

		designer_value = self.bom_assignment[-1].designer
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			if timesheet_doc.time_logs:	
				time_log = timesheet_doc.time_logs[-1]					
				time_log.to_time = now_datetime()
				time_log.completed = 1
				time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
			
			update_time_log = timesheet_doc.append("time_logs", {})
			update_time_log.activity_type = "Updating BOM"
			update_time_log.from_time = now_datetime()
			update_time_log.custom_cad_order_id = self.name	
			timesheet_doc.save()
		else:
			frappe.throw("Timesheets is not created for each designer assignment")
			
		frappe.msgprint("Timesheets Updating BOM for each designer assignment")

	elif self.workflow_state == "Updating BOM - On-Hold":
		if len(self.bom_assignment)>1:
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')


		designer_value = self.bom_assignment[-1].designer
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			if timesheet_doc.time_logs:	
				time_log = timesheet_doc.time_logs[-1]					
				time_log.to_time = now_datetime()
				time_log.completed = 1
				time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

			if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "Updating BOM - On Hold":
				qc_time_log = timesheet_doc.append("time_logs", {})
				qc_time_log.activity_type = "Updating BOM - On Hold"
				qc_time_log.from_time = now_datetime()
				qc_time_log.custom_cad_order_id = self.name
				timesheet_doc.save()
		else:
			frappe.throw("Timesheets is not created for each designer assignment")		
			

	elif self.workflow_state == "Approved":		
		if len(self.bom_assignment)>1:				
			for i in self.bom_assignment[:-1]:
				timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"repair_order":self.name}, ["name","docstatus"])
				if docstatus == 0:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet)
					if (timesheet_doc.time_logs):
						timesheet_doc.time_logs[-1].to_time = now_datetime()
						timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
						timesheet_doc.save()
					timesheet_doc.run_method('submit')

		
		designer_value = self.bom_assignment[-1].designer
		# Check if a timesheet document already exists for the employee
		timesheet = frappe.get_all(
			"Timesheet", filters={"employee": designer_value,"repair_order":self.name}, fields=["name"],
		)
		if timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

			time_log = timesheet_doc.time_logs[-1]					
			time_log.to_time = now_datetime()
			time_log.completed = 1
			time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600				
			timesheet_doc.save()
			timesheet_doc.run_method('submit')				
		else:
			frappe.throw("Timesheets is not created for each designer assignment")




def create_serial_no(self):
	serial = frappe.new_doc('Serial No')
	if self.is_jewelex_tag:
		serial.item_code = self.new_item_code
	else:
		serial.item_code = self.item
	serial.customer = self.customer_code
	serial.company=self.company
	serial.purchase_document_no = self.name
	# serial.description=self.description
	# self.item_name=self.item_name
	# serial.custom_jwelex_tag_no = self.jewelex_tag
	serial.custom_bom_no=self.new_bom
	serial.status = 'Delivered'
	# serial.custom_manufacturer='Labh'
	if self.is_jewelex_tag:
		compose_series = genrate_serial_no(self, self.product_bom)
	else:
		compose_series = genrate_serial_no(self, self.new_bom)
	sr_no = make_autoname(compose_series)
	serial.serial_no=sr_no
	# frappe.throw(f"Serial No = {serial.serial_no}")
	serial.insert(ignore_permissions=True)
	# serial.save()
	self.db_set("serial_no", serial.name, update_modified=False)


def genrate_serial_no(self, new_bom):
	new_bom = frappe.get_doc("BOM", new_bom)
	# series_start = frappe.db.get_value("Manufacturing Setting", doc.company, ["series_start"])
	series_start = frappe.db.get_value("Manufacturing Setting", {"manufacturer":'Labh'}, ["series_start"])
	# metal_type, manufacturer, posting_date = frappe.db.get_value(
	# 	"Manufacturing Work Order",
	# 	mwo_no,
	# 	["metal_type", "manufacturer", "posting_date"],
	# )
	manufacturer='Labh'
	errors = []
	metal_type = new_bom.metal_detail[0].metal_type if new_bom.metal_detail else None
	diamond_grade_data=new_bom.diamond_detail[0].diamond_grade if new_bom.metal_detail else None
	m_abbr = frappe.db.get_value("Attribute Value", metal_type, "abbreviation")
	mnf_abbr = frappe.db.get_value("Manufacturer", manufacturer, ["custom_abbreviation"])
	posting_date = datetime.today().date()
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

	if errors:
		frappe.throw("<br>".join(errors))

	compose_series = str(series_start + mnf_abbr + m_abbr + dg_abbr + final_date + ".####")
	return compose_series





@frappe.whitelist()
def get_data_from_jwelex(tag_no, company):
    url = "http://3.108.219.130:8001/credit-note"

    response = requests.get(
        url,
        params={
            "tag_no": tag_no,
            "company": company
        },
        timeout=30
    )

    response.raise_for_status()
    return response.json()
