# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document

class ReviseMakingChargePrice(Document):
    def before_insert(self):
        filters = {
				"customer": self.customer,
				"setting_type": self.setting_type,
				"metal_type": self.metal_type,
                "metal_touch":self.metal_touch,
                "from_gold_rate":self.from_gold_rate,
                "to_gold_rate":self.to_gold_rate
			}
                   
        name = frappe.db.get_value("Making Charge Price",filters,"name")
        if name:
            if len(self.revise_making_charge_price_item_subcategory) != len(frappe.get_doc("Making Charge Price",name).subcategory):
                if self.revise_making_charge_price_item_subcategory==[]:
                    self.set("revise_making_charge_price_item_subcategory", [])
                    old_making_charge_price_list = frappe.get_doc("Making Charge Price",name).subcategory
                    making_data = []                
                    for i in old_making_charge_price_list:
                        making_data.append(
                                {
                                    "subcategory":i.subcategory,
                                    "rate_per_gm":i.rate_per_gm,
                                    # "new_rate_per_gm":i.rate_per_gm,
                                    "rate_per_pc":i.rate_per_pc,
                                    # "new_rate_per_pc":i.rate_per_pc,
                                    "rate_per_diamond":i.rate_per_diamond,
                                    # "new_rate_per_diamond":i.rate_per_diamond,
                                    "wastage":i.wastage,
                                    # "new_wastage":i.wastage,
                                    "name":i.name,
                                }
                            )
                    sorted_data = sorted(making_data, key=lambda x: x['subcategory'])
                    for j in sorted_data:
                        rate_details = self.append("revise_making_charge_price_item_subcategory", {})
                        rate_details.subcategory = j['subcategory']
                        
                        rate_details.rate_per_gm = j['rate_per_gm']
                        rate_details.new_rate_per_gm = j['rate_per_gm']
                        
                        rate_details.rate_per_diamond = j['rate_per_diamond']
                        rate_details.new_rate_per_diamond = j['rate_per_diamond']
                        
                        rate_details.rate_per_pc = j['rate_per_pc']
                        rate_details.new_rate_per_pc = j['rate_per_pc']
                        
                        rate_details.wastage = j['wastage']
                        rate_details.new_wastage = j['wastage']
                        
                        rate_details.making_charge_price_item_subcategory = j['name']                
                else:
                    old_making_charge_price_item_subcategory = [d.making_charge_price_item_subcategory for d in self.revise_making_charge_price_item_subcategory]
                    sorted_data = []
                    old_making_charge_price_list = frappe.get_all("Making Charge Price Item Subcategory", filters={"parent":name}, fields=["name"],)
                    for j in old_making_charge_price_list:
                        j = j['name']
                        if j not in old_making_charge_price_item_subcategory:
                            sorted_data.append(
                            {
                                "subcategory":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"subcategory"),
                                "rate_per_gm":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_gm"),
                                "rate_per_pc":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_pc"),
                                "rate_per_diamond":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_diamond"),
                                "wastage":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"wastage"),
                                # "new_rate_per_gm":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_gm"),
                                # "new_rate_per_pc":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_pc"),
                                # "new_rate_per_diamond":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"rate_per_diamond"),
                                # "new_wastage":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"wastage"),
                                "name":frappe.db.get_value("Making Charge Price Item Subcategory",{"name":j},"name"),
                            }
                        )
                            
                    for k in sorted_data:
                        rate_details = self.append("revise_making_charge_price_item_subcategory", {})
                        rate_details.subcategory = k['subcategory']
                        
                        rate_details.rate_per_gm = k['rate_per_gm']
                        rate_details.new_rate_per_gm = k['rate_per_gm']
                        
                        rate_details.rate_per_pc = k['rate_per_pc']
                        rate_details.new_rate_per_pc = k['rate_per_pc']
                        
                        rate_details.rate_per_diamond = k['rate_per_diamond']
                        rate_details.new_rate_per_diamond = k['rate_per_diamond']
                        
                        rate_details.wastage = k['wastage']
                        rate_details.new_wastage = k['wastage']
                        
                        rate_details.making_charge_price_item_subcategory = k['name']
                        
            if len(self.revise_making_charge_price_finding_subcategory) != len(frappe.get_doc("Making Charge Price",name).finding_subcategory):
                if self.revise_making_charge_price_finding_subcategory==[]:
                    
                    self.set("revise_making_charge_price_finding_subcategory", [])
                    old_making_charge_price_list = frappe.get_doc("Making Charge Price",name).finding_subcategory
                    making_data = []                
                    for i in old_making_charge_price_list:
                        making_data.append(
								{
									"subcategory":i.subcategory,
									"rate_per_gm":i.rate_per_gm,
                                    # "new_rate_per_gm":i.rate_per_gm,
									"rate_per_pc":i.rate_per_pc,
									# "new_rate_per_pc":i.rate_per_pc,
									"rate_per_diamond":i.rate_per_diamond,
									# "new_rate_per_diamond":i.rate_per_diamond,
									"wastage":i.wastage,
                                    # "new_wastage":i.wastage,
									"name":i.name,
								}
							)
                    sorted_data = sorted(making_data, key=lambda x: x['subcategory'])
                    for j in sorted_data:
                        rate_details = self.append("revise_making_charge_price_finding_subcategory", {})
                        rate_details.subcategory = j['subcategory']
                        
                        rate_details.rate_per_gm = j['rate_per_gm']
                        rate_details.new_rate_per_gm = j['rate_per_gm']
                        
                        rate_details.rate_per_pc = j['rate_per_pc']
                        rate_details.new_rate_per_pc = j['rate_per_pc']
                        
                        rate_details.rate_per_diamond = j['rate_per_diamond']
                        rate_details.new_rate_per_diamond = j['rate_per_diamond']
                        
                        rate_details.wastage = j['wastage']
                        rate_details.new_wastage = j['wastage']
                        
                        rate_details.making_charge_price_finding_subcategory = j['name']
                else:
                    old_making_charge_price_item_subcategory = [d.making_charge_price_finding_subcategory for d in self.revise_making_charge_price_finding_subcategory]
                    sorted_data = []
                    for j in frappe.db.get_list("Making Charge Price Finding Subcategory",filters={'parent':name},pluck="name"):
                        if j not in old_making_charge_price_item_subcategory:
                            sorted_data.append(
							{
								"subcategory":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"subcategory"),
								"rate_per_gm":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_gm"),
								"rate_per_pc":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_pc"),
								"rate_per_diamond":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_diamond"),
								"wastage":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"wastage"),
                                # "new_rate_per_gm":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_gm"),
								# "new_rate_per_pc":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_pc"),
								# "new_rate_per_diamond":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"rate_per_diamond"),
								# "new_wastage":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"wastage"),
								"name":frappe.db.get_value("Making Charge Price Finding Subcategory",{"name":j},"name"),
							}
						)
                            
                    for k in sorted_data:
                        rate_details = self.append("revise_making_charge_price_finding_subcategory", {})
                        rate_details.subcategory = k['subcategory']
                        
                        rate_details.rate_per_gm = k['rate_per_gm']
                        rate_details.new_rate_per_gm = k['rate_per_gm']
                        
                        rate_details.rate_per_pc = k['rate_per_pc']
                        rate_details.new_rate_per_pc = k['rate_per_pc']
                        
                        rate_details.rate_per_diamond = k['rate_per_diamond']
                        rate_details.new_rate_per_diamond = k['rate_per_diamond']
                        
                        rate_details.wastage = k['wastage']
                        rate_details.new_wastage = k['wastage']
                        
                        rate_details.making_charge_price_item_subcategory = k['name']                
		

                        
    def on_submit(self):
        filters = {
				"customer": self.customer,
				"setting_type": self.setting_type,
				"metal_type": self.metal_type,
                "metal_touch":self.metal_touch,
                "from_gold_rate":self.from_gold_rate,
                "to_gold_rate":self.to_gold_rate
			}
        name = frappe.db.get_value("Making Charge Price",filters,"name")
        if name:
            if self.revise_making_charge_price_item_subcategory:
                for i in self.revise_making_charge_price_item_subcategory:
                        if i.making_charge_price_item_subcategory:
                            # frappe.db.set_value('Making Charge Price Item Subcategory',i.making_charge_price_item_subcategory,{
                            #     'rate_per_gm':i.new_rate_per_gm,
                            #     'rate_per_pc':i.new_rate_per_pc,
                            #     'rate_per_diamond':i.new_rate_per_diamond,
                            #     'wastage':i.new_wastage,
                            #     'rate_per_gm_threshold':i.new_rate_per_gm_threshold,
                            #     })
                            subcategory_doc = frappe.get_doc('Making Charge Price Item Subcategory',i.making_charge_price_item_subcategory)
                            subcategory_doc.rate_per_gm = i.new_rate_per_gm
                            subcategory_doc.rate_per_pc = i.new_rate_per_pc
                            subcategory_doc.rate_per_diamond = i.new_rate_per_diamond
                            subcategory_doc.wastage = i.new_wastage
                            subcategory_doc.to_diamond = i.to_diamond
                            subcategory_doc.from_diamond = i.from_diamond
                            # subcategory_doc.rate_per_gm_threshold = i.new_rate_per_gm_threshold
                            subcategory_doc.save()
                        else:
                            making_charge_price_doc = frappe.get_doc("Making Charge Price", name)

                            existing_row = None
                            for row in making_charge_price_doc.subcategory:
                                if row.subcategory == i.subcategory:
                                    existing_row = row
                                    break

                            if existing_row:
                                existing_row.rate_per_gm = i.new_rate_per_gm
                                existing_row.rate_per_pc = i.new_rate_per_pc
                                existing_row.rate_per_diamond = i.new_rate_per_diamond
                                existing_row.wastage = i.new_wastage
                                existing_row.to_diamond = i.to_diamond
                                existing_row.from_diamond = i.from_diamond
                            else:
                                subcategory = making_charge_price_doc.append("subcategory", {})
                                subcategory.subcategory = i.subcategory
                                subcategory.rate_per_gm = i.new_rate_per_gm
                                subcategory.rate_per_pc = i.new_rate_per_pc
                                subcategory.rate_per_diamond = i.new_rate_per_diamond
                                subcategory.wastage = i.new_wastage
                                subcategory_doc.to_diamond = i.to_diamond
                                subcategory_doc.from_diamond = i.from_diamond
                                # subcategory.rate_per_gm_threshold = self.new_rate_per_gm_threshold
                            making_charge_price_doc.save()

            if self.revise_making_charge_price_finding_subcategory:
                for i in self.revise_making_charge_price_finding_subcategory:
                        if i.making_charge_price_finding_subcategory:
                            frappe.db.set_value('Making Charge Price Finding Subcategory',i.making_charge_price_finding_subcategory,{
                                'rate_per_gm':i.new_rate_per_gm,
                                'rate_per_pc':i.new_rate_per_pc,
                                'rate_per_diamond':i.new_rate_per_diamond,
                                'wastage':i.new_wastage,
                                })
                            
                        else:
                            existing_row = None
                            for row in making_charge_price_doc.finding_subcategory:
                                if row.subcategory == i.subcategory:
                                    existing_row = row
                                    break

                            if existing_row:
                                existing_row.rate_per_gm = i.new_rate_per_gm
                                existing_row.rate_per_pc = i.new_rate_per_pc
                                existing_row.rate_per_diamond = i.new_rate_per_diamond
                                existing_row.wastage = i.new_wastage
                            else:
                                a = ''
                            making_charge_price_doc.save()
        else:
            making_charge_price_doc = frappe.new_doc("Making Charge Price")
            making_charge_price_doc.customer = self.customer
            making_charge_price_doc.setting_type = self.setting_type
            making_charge_price_doc.metal_type = self.metal_type
            making_charge_price_doc.metal_type = self.metal_touch
            for i in self.revise_making_charge_price_item_subcategory:
               
               time_log = making_charge_price_doc.append("subcategory", {})
               time_log.subcategory = i.subcategory
               time_log.rate_per_gm = i.new_rate_per_gm
               time_log.rate_per_pc = i.new_rate_per_pc
               time_log.rate_per_diamond = i.new_rate_per_diamond
               time_log.wastage = i.new_wastage
               time_log.to_diamond = i.to_diamond
               time_log.from_diamond = i.from_diamond

            making_charge_price_doc.save()
        frappe.msgprint("Price List Updated")



