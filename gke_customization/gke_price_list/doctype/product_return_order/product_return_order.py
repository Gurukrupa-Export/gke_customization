# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProductReturnOrder(Document):
	def on_submit(self):
		bom_doc = frappe.get_doc("BOM", self.bom)
		new_bom = frappe.copy_doc(bom_doc)
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
		for table in child_tables:
		# clear existing copied BOM rows if required
			new_bom.set(table, [])

			for src in getattr(self, table):
				dest = new_bom.append(table, {})

				for key, value in src.as_dict().items():
					if key not in system_fields:
						dest.set(key, value)
				
				if table == "metal_detail":
					customer_metal_purity = frappe.db.get_value(
							"Metal Criteria",
							{"parent": self.customer, "metal_type": dest.metal_type, "metal_touch": dest.metal_touch},
							"metal_purity",
						)
					if self.credit_note_rate_type=='Current Rate':
						dest.rate=float(self.gold_rate or 0) * float(customer_metal_purity) /100
					if self.making_charges=='Without':
						dest.making_rate=0
					elif self.making_charges=='Half':
						dest.making_rate=dest.making_rate/2
					elif self.making_charges=='Custom':
						dest.making_rate=self.custom_making_charges
					dest.customer_metal_purity=customer_metal_purity
					dest.amount = dest.quantity * dest.rate
					dest.making_amount = dest.making_rate*dest.quantity
				if table == "finding_detail":
					customer_metal_purity = frappe.db.get_value(
							"Metal Criteria",
							{"parent": self.customer, "metal_type": dest.metal_type, "metal_touch": dest.metal_touch},
							"metal_purity",
						)
					if self.credit_note_rate_type=='Current Rate':
						dest.rate=float(self.gold_rate or 0) * float(customer_metal_purity)/100
					if self.making_charges=='Without':
						dest.making_rate=0
					elif self.making_charges=='Half':
						dest.making_rate=dest.making_rate/2
					elif self.making_charges=='Custom':
						dest.making_rate=self.custom_making_charges
					dest.amount = dest.quantity * dest.rate
					dest.making_amount = dest.making_rate*dest.quantity
				if table == "diamond_detail":
					dest.diamond_rate_for_specified_quantity=dest.quantity * dest.total_diamond_rate
				if table == "gemstone_detail":
					dest.gemstone_rate_for_specified_quantity=dest.quantity * dest.total_gemstone_rate
					if self.gemstone_charges=='Without':
						dest.gemstone_rate_for_specified_quantity=0
					elif self.gemstone_charges=='Half':
						dest.gemstone_rate_for_specified_quantity=dest.gemstone_rate_for_specified_quantity/2
					elif self.gemstone_charges=='Custom':
						dest.gemstone_rate_for_specified_quantity=self.custom_gemstones_charges
		
		new_bom.total_metal_weight = self.total_metal_weight
		new_bom.total_metal_amount = sum(row.amount for row in new_bom.metal_detail)
		new_bom.total_making_amount = sum(row.making_amount for row in new_bom.metal_detail)
		new_bom.total_finding_amount = sum(row.amount for row in new_bom.finding_detail)
		new_bom.total_diamond_amount = sum(row.diamond_rate_for_specified_quantity for row in new_bom.diamond_detail)
		new_bom.total_gemstone_amount = sum(row.gemstone_rate_for_specified_quantity for row in new_bom.gemstone_detail)
		new_bom.gemstone_bom_amount = new_bom.total_gemstone_amount
		new_bom.diamond_bom_amount = new_bom.diamond_bom_amount
		new_bom.gold_bom_amount=new_bom.total_metal_amount 
		new_bom.finding_bom_amount=new_bom.total_finding_amount
		new_bom.total_bom_amount = (new_bom.diamond_bom_amount+ new_bom.gold_bom_amount+ new_bom.gemstone_bom_amount+ new_bom.finding_bom_amount)
		new_bom.making_charge = (sum(r.making_amount for r in new_bom.metal_detail)+ sum(r.making_amount for r in new_bom.finding_detail) )
		total_amount = (new_bom.total_bom_amount+ new_bom.making_charge+ float(new_bom.certification_amount)
        + float(new_bom.custom_duty_amount)+ float(new_bom.hallmarking_amount)+ float(new_bom.freight_amount)
        + float(new_bom.sale_amount)
    )
		new_bom.finding_pcs = self.total_finding_pcs
		new_bom.finding_weight = self.finding_weight
		new_bom.total_gemstone_pcs = self.total_gemstone_pcs
		new_bom.total_gemstone_weight_per_gram = self.total_gemstone_weightin_gms
		new_bom.total_gemstone_amount = self.total_gemstone_amount
		new_bom.total_diamond_amount = self.total_diamond_amount
		new_bom.total_diamond_pcs = self.total_diamond_pcs
		new_bom.total_diamond_weight_in_gms = self.total_diamond_weight_in_gram
		new_bom.insert(ignore_permissions=True)
		# new_bom.save()
		self.db_set("new_bom", new_bom.name, update_modified=False)