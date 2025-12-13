# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReviseSupplierServicesPrice(Document):
	def before_save(self):
		if self.supplier and self.purchase_type and self.metal_type and self.type_of_subcontracting:
			filters = {"supplier":self.supplier,
		 					"purchase_type":self.purchase_type,
							"metal_type":self.metal_type,
							"type_of_subcontracting":self.type_of_subcontracting}
			price_list_id = frappe.db.get_value("Supplier Services Price",filters)
			if not price_list_id:
				return
			doc = frappe.get_doc("Supplier Services Price",price_list_id)
			if len(self.revise_subcategory) != len(doc.subcategory):
				if self.revise_subcategory==[]:
					self.set("revise_subcategory", [])
					old_supplier_price_list = doc.subcategory
					data = []
					for i in old_supplier_price_list:
						data.append(
                                {
                                    "sub_category":i.sub_category,
                                    "rate_per_gm":i.rate_per_gm,
                                    "rate_per_pc":i.rate_per_pc,
                                    "rate_per_diamond":i.rate_per_diamond,
                                    "wastage":i.wastage,
									"rate_per_gm_threshold":i.rate_per_gm_threshold,
									"supplier_fg_purchase_rate":i.supplier_fg_purchase_rate,
                                    "name":i.name,
                                }
                            )
					sorted_data = sorted(data, key=lambda x: x['sub_category'])
					for j in sorted_data:
						rate_details = self.append("revise_subcategory", {})
						rate_details.sub_category = j['sub_category']
						
						rate_details.rate_per_gm = j['rate_per_gm']
						rate_details.new_rate_per_gm = j['rate_per_gm']
						
						rate_details.rate_per_diamond = j['rate_per_diamond']
						rate_details.new_rate_per_diamond = j['rate_per_diamond']
						
						rate_details.rate_per_pc = j['rate_per_pc']
						rate_details.new_rate_per_pc = j['rate_per_pc']
						
						rate_details.wastage = j['wastage']
						rate_details.new_wastage = j['wastage']
						
						rate_details.name = j['name']
				else:
					old_supplier_price_list = [d.name for d in self.revise_subcategory]
					sorted_data = []
					old_supplier_serive_price_list = frappe.get_all("Supplier Services Price Item Subcategory", filters={"parent":price_list_id}, fields=["name"],)
					for j in old_supplier_serive_price_list:
						j = j['name']
						if j not in old_supplier_price_list:
							sorted_data.append(
							{
								"sub_category":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"sub_category"),
								"rate_per_gm":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"rate_per_gm"),
								"rate_per_pc":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"rate_per_pc"),
								"rate_per_diamond":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"rate_per_diamond"),
								"wastage":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"wastage"),
								"name":frappe.db.get_value("Supplier Services Price Item Subcategory",{"name":j},"name"),
							}
						)
                            
					for k in sorted_data:
						rate_details = self.append("revise_subcategory", {})
						rate_details.sub_category = k['sub_category']
						
						rate_details.rate_per_gm = k['rate_per_gm']
						rate_details.new_rate_per_gm = k['rate_per_gm']
						
						rate_details.rate_per_pc = k['rate_per_pc']
						rate_details.new_rate_per_pc = k['rate_per_pc']
						
						rate_details.rate_per_diamond = k['rate_per_diamond']
						rate_details.new_rate_per_diamond = k['rate_per_diamond']
						
						rate_details.wastage = k['wastage']
						rate_details.new_wastage = k['wastage']
						
						rate_details.name = k['name']

		return


	def on_submit(self):
		filters = {"supplier":self.supplier,
					"purchase_type":self.purchase_type,
					"metal_type":self.metal_type,
					"type_of_subcontracting":self.type_of_subcontracting}
		price_list_id = frappe.db.get_value("Supplier Services Price",filters,"name")
		if price_list_id:
			if self.revise_subcategory:
				for i in self.revise_subcategory:
						if i.name:
							subcategory_doc = frappe.get_doc('Supplier Services Price Item Subcategory',i.name)
							subcategory_doc.rate_per_gm = i.revise_rate_per_gm
							subcategory_doc.rate_per_pc = i.revise_rate_per_pc
							subcategory_doc.rate_per_diamond = i.revise_rate_per_diamond
							subcategory_doc.wastage = i.revise_wastage
							subcategory_doc.rate_per_gm_threshold = i.revise_rate_per_gm_threshold
							subcategory_doc.supplier_fg_purchase_rate = i.revise_supplier_fg_purchase_rate
							subcategory_doc.save()

						else:
							supplier_services_price_doc = frappe.get_doc("Making Charge Price", price_list_id)
							subcategory = supplier_services_price_doc.append("subcategory", {})
							subcategory.sub_category = i.sub_category
							subcategory.rate_per_gm = i.new_rate_per_gm
							subcategory.rate_per_pc = i.new_rate_per_pc
							subcategory.rate_per_diamond = i.new_rate_per_diamond
							subcategory.wastage = i.new_wastage
							supplier_services_price_doc.save()

		else:
			supplier_services_price_doc = frappe.new_doc("Supplier Services Price")
			supplier_services_price_doc.supplier = self.supplier
			supplier_services_price_doc.purchase_type = self.purchase_type
			supplier_services_price_doc.metal_type = self.metal_type
			supplier_services_price_doc.type_of_subcontracting = self.type_of_subcontracting
			for i in self.revise_making_charge_price_item_subcategory:
				
				row = supplier_services_price_doc.append("subcategory", {})
				row.sub_category = i.sub_category
				row.rate_per_gm = i.new_rate_per_gm
				row.rate_per_pc = i.new_rate_per_pc
				row.rate_per_diamond = i.new_rate_per_diamond
				row.wastage = i.new_wastage

			supplier_services_price_doc.save()
		frappe.msgprint("Price List Updated")


