# Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document,json

class CustomerDesignInformationSheet(Document):
    def before_save(self):
        # if self.serial_no:
        #     # frappe.db.get_value
        #     frappe.throw("HFEF")

        if self.design_code:
            master_bom = frappe.db.get_value("BOM",
                            {
                                "item":self.design_code,
                                "bom_type":"Finish Goods", 
                                "is_default": 1,
                                "is_active": 1
                            }, "name")
            if not master_bom:
                master_bom = frappe.db.get_value("Item",self.design_code,'master_bom','name')
                item_bom = frappe.db.get_value("BOM", {"name": master_bom,"item": self.design_code,"bom_type": "Template"}, 'name')
                if item_bom == None:
                    frappe.throw(f"{self.design_code} has master_bom {master_bom}" )
                
            bom = frappe.get_doc('BOM',master_bom)
            if bom:
                self.bom = master_bom
                self.set("diamond_detail", [])
                self.set("gemstone_detail", [])
                if len(self.diamond_detail) != len(bom.get("diamond_detail")):
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
                        
                        if bom_detail.get("sieve_size_range"):
                            titan_detail.sieve_size_range = bom_detail.sieve_size_range

                        if bom_detail.get("quantity"):
                            titan_detail.quantity = bom_detail.quantity

                        if bom_detail.get("size_in_mm"):
                            titan_detail.size_in_mm = bom_detail.size_in_mm

                if len(self.gemstone_detail) != len(bom.get("gemstone_detail")):
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
                
                # if self.customer_name in ("Caratlane"):
                #     frappe.throw(f"{self.diamond_weight}")
                #     if self.diamond_weight:
                #         dia_wgt = self.diamond_weight
                #         tolerance = (dia_wgt * 3) / 100
                        
                #         self.max_diamond = dia_wgt + tolerance
                #         self.min_diamond = dia_wgt - tolerance

                #     if self.metal_and_finding_weight:
                #         net_wgt = self.metal_and_finding_weight
                #         tolerance = (net_wgt * 3) / 100
                        
                #         self.max_net = net_wgt + tolerance
                #         self.min_net = net_wgt - tolerance
            else:
                frappe.msgprint("BOM is Not Found!")
        
        if self.name:
            if self.is_set == 0:
                design_code_2 = frappe.db.get_value('Titan Design Information Sheet',self.name,'design_code_2')
                similar_doc = frappe.db.get_value('Titan Design Information Sheet',{'design_code':design_code_2,'design_code_2':self.design_code},'name')
                
                frappe.db.set_value('Titan Design Information Sheet',similar_doc,'is_set',0)
                frappe.db.set_value('Titan Design Information Sheet',similar_doc,'design_code_2','')
                frappe.db.set_value('Titan Design Information Sheet',similar_doc,'fourteen_digit_set_code','')


            if self.is_set == 1:
                design_code_2 = frappe.db.get_value('Titan Design Information Sheet',self.name,'design_code_2')
                if not design_code_2:
                    design_code_2 = self.design_code_2

                similar_doc_name = frappe.db.get_value('Titan Design Information Sheet',{'design_code':design_code_2},'name')
                if not similar_doc_name:
                    similar_doc = frappe.get_doc('Titan Design Information Sheet',similar_doc_name)
                    doc = frappe.get_doc({
                        'doctype':'Titan Design Information Sheet',
                        'design_code':design_code_2,
                        'design_code_2':self.design_code,
                        'is_set':1,
                        'designer':self.designer,
                        'order_date':self.order_date,
                        'launch_month':self.launch_month,
                        'fourteen_digit_set_code':self.fourteen_digit_set_code,
                        })
                    doc.insert()
                else:
                    frappe.db.set_value('Titan Design Information Sheet',similar_doc_name,{
                                            'is_set':1,
                                            'design_code_2':self.design_code,
                                            'fourteen_digit_set_code':self.fourteen_digit_set_code
                                            })
                    
                    


    # def validate(self):
    #     if self.is_set == 0:
    #         self.design_code_2 = ''
    #         self.fourteen_digit_set_code = ''

        # if self.is_set == 1:
        #         design_code_2 = frappe.db.get_value('Titan Design Information Sheet',self.name,'design_code_2')
        #         frappe.msgprint(design_code_2)
        #         similar_doc = frappe.get_doc('Titan Design Information Sheet',{'design_code':design_code_2})
                # if not similar_doc:
                #     doc = frappe.get_doc({
                #         'doctype':'Titan Design Information Sheet',
                #         'design_code':design_code_2,
                #         'design_code_2':self.design_code
                #         })
                #     doc.insert()
                # else:
                #     frappe.db.set_value('Titan Design Information Sheet',similar_doc.name,{'is_set':1,'design_code_2':self.design_code})


@frappe.whitelist()
def get_table_details(design_code):
    if design_code:
        bom = frappe.get_doc("BOM", {"item": design_code})
        if bom:
            diamond_detail = bom.get("diamond_detail")
            gemstone_detail = bom.get("gemstone_detail")
            return diamond_detail,gemstone_detail
                


