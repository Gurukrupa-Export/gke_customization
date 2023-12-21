# Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TitanDesignInformationSheet(Document):
    # pass
	def before_save(self):
            if self.design_code:
                bom = frappe.get_doc("BOM", {"item": self.design_code})
                if bom:
                    if len(self.diamond_detail) == len(bom.get("diamond_detail")):
                        return
                    if len(self.gemstone_detail) == len(bom.get("gemstone_detail")):
                        return
                    self.set("diamond_detail", [])
                    self.set("gemstone_detail", [])
                    
                    for bom_detail in bom.get("diamond_detail"):
                        titan_detail = self.append("diamond_detail", {})
                        
                        if bom_detail.get("diamond_type"):
                            titan_detail.diamond_type = bom_detail.diamond_type

                        if bom_detail.get("stone_shape"):
                            titan_detail.stone_shape = bom_detail.stone_shape

                        if bom_detail.get("sub_setting_type"):
                            titan_detail.sub_setting_type = bom_detail.sub_setting_type

                        if bom_detail.get("diamond_sieve_size"):
                            titan_detail.diamond_sieve_size = bom_detail.diamond_sieve_size

                        if bom_detail.get("pcs"):
                            titan_detail.pcs = bom_detail.pcs

                        if bom_detail.get("weight_per_pcs"):
                            titan_detail.weight_per_pcs = bom_detail.weight_per_pcs

                        if bom_detail.get("quality"):
                            titan_detail.quality = bom_detail.quality

                        if bom_detail.get("stock_uom"):
                            titan_detail.stock_uom = bom_detail.stock_uom

                        if bom_detail.get("quantity"):
                            titan_detail.quantity = bom_detail.quantity

                        if bom_detail.get("size_in_mm"):
                            titan_detail.size_in_mm = bom_detail.size_in_mm

                    for bom_gemstone in bom.get("gemstone_detail"):
                        titan_gemstone = self.append("gemstone_detail", {})
                        
                        if bom_gemstone.get("gemstone_type"):
                            titan_gemstone.gemstone_type = bom_gemstone.gemstone_type
                        if bom_gemstone.get("cut_or_cab"):
                            titan_gemstone.cut_or_cab = bom_gemstone.cut_or_cab

                        if bom_gemstone.get("stone_shape"):
                            titan_gemstone.stone_shape = bom_gemstone.stone_shape

                        if bom_gemstone.get("gemstone_size"):
                            titan_gemstone.gemstone_size = bom_gemstone.gemstone_size

                        if bom_gemstone.get("sub_setting_type"):
                            titan_gemstone.sub_setting_type = bom_gemstone.sub_setting_type

                        if bom_gemstone.get("pcs"):
                            titan_gemstone.pcs = bom_gemstone.pcs

                        if bom_gemstone.get("gemstone_quality"):
                            titan_gemstone.gemstone_quality = bom_gemstone.gemstone_quality

                        if bom_gemstone.get("stock_uom"):
                            titan_gemstone.stock_uom = bom_gemstone.stock_uom

                        if bom_gemstone.get("quantity"):
                            titan_gemstone.quantity = bom_gemstone.quantity
                else:
                    frappe.msgprint("BOM is Not Found!")



@frappe.whitelist()
def get_table_details(design_code):
    if design_code:
                bom = frappe.get_doc("BOM", {"item": design_code})
                if bom:
                    diamond_detail = bom.get("diamond_detail")
                    gemstone_detail = bom.get("gemstone_detail")
                    return diamond_detail,gemstone_detail