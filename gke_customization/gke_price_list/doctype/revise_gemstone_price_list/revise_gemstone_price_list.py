# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document

class ReviseGemstonePriceList(Document):
    def before_save(self):
        filters = {
				"customer": self.customer,
				"price_list": self.price_list,
				"price_list_type": self.price_list_type,
				"gemstone_type": self.gemstone_type,
				"cut_or_cab": self.cut_or_cab,
				"stone_shape": self.stone_shape,
                "gemstone_quality": self.gemstone_quality,
                "gemstone_grade":self.gemstone_grade
			}
                   
        if self.price_list_type == 'Fixed':
            if len(self.revise_gemstone_pricelist_detail) != len(frappe.db.get_list("Gemstone Price List",filters=filters,fields=["from_weight","to_weight"])):
                if self.revise_gemstone_pricelist_detail==[]:
                    self.set("revise_gemstone_pricelist_detail", [])
                    # old_diamond_price_list = frappe.db.get_list("Gemstone Price List",filters=filters,fields=["from_weight","to_weight"])
                    old_gemstone_price_list = frappe.db.get_list("Gemstone Price List",filters=filters,fields=["name","from_weight","to_weight","rate","outwork_handling_charges_rate","outwork_handling_charges_in_percentage","outright_handling_charges_rate","outright_handling_charges_in_percentage","supplier_fg_purchase_rate"])
                    # frappe.throw(f"{old_gemstone_price_list}")
                    gemstone_price_list = []
                    for j in old_gemstone_price_list:
                        gemstone_price_list.append({
                            "weight_range": f"{j['from_weight']}-{j['to_weight']}",
                            "name": j['name'],
                            "rate": j['rate'],
                            "outwork_handling_charges_rate": j['outwork_handling_charges_rate'],
                            "outwork_handling_charges_in_percentage": j['outwork_handling_charges_in_percentage'],
                            "outright_handling_charges_rate": j['outright_handling_charges_rate'],
                            "outright_handling_charges_in_percentage": j['outright_handling_charges_in_percentage'],
                            "supplier_fg_purchase_rate": j['supplier_fg_purchase_rate'],
                        })

                    output_list = remove_duplicate_data(gemstone_price_list)
                    sorted_data = sort_data(self,output_list)
                    set_data_in_child_table(self,sorted_data)
                else:
                    old_gemstone_price_list = [d.gemstone_price_list for d in self.revise_gemstone_pricelist_detail]
                    for j in frappe.db.get_list("Gemstone Price List",filters=filters,pluck="name"):
                        if j not in old_gemstone_price_list:
                            sorted_data = []
                            for k in frappe.db.get_list("Gemstone Price List",filters={"name":j},fields=["from_weight","to_weight"]):
                                sorted_data.append({"weight_range":f"{k['from_weight']}-{k['to_weight']}"})
                            set_data_in_child_table(self,sorted_data)
        else:
            old_rate = frappe.db.get_list("Gemstone Price List",filters=filters,fields=["rate","name"])
            self.rate_per_carat = old_rate[0]['rate']
            self.gemstone_price_list = old_rate[0]['name']
            
                            
    def on_submit(self):
        # if self.price_list_type == 'Fixed':
        if self.price_list_type == 'Fixed':
            for i in self.revise_gemstone_pricelist_detail:
                # if i.difference!=0:
                frappe.db.set_value('Gemstone Price List',i.gemstone_price_list,{'rate':i.new_rate,'supplier_fg_purchase_rate':i.new_supplier_fg_purchase_rate,'outwork_handling_charges_rate':i.new_outwork_handling_charges_rate,
                'outwork_handling_charges_in_percentage':i.new_outwork_handling_charges_in_,
                'outright_handling_charges_rate':i.new_outright_handling_charges_rate,
                'outright_handling_charges_in_percentage':i.new_outright_handling_charges_in_})
                if not i.gemstone_price_list:
                    crate_price_list(self,i)
        else:
            frappe.db.set_value('Gemstone Price List',self.gemstone_price_list,{'rate':self.revised_rate})
            if not self.gemstone_price_list:
                crate_price_list(self,self)
        frappe.msgprint("Price List Updated")
            
def crate_price_list(self,row):
    gemstone_price_list_doc = frappe.new_doc("Gemstone Price List")
    gemstone_price_list_doc.customer = self.customer
    gemstone_price_list_doc.price_list = self.price_list
    gemstone_price_list_doc.price_list_type = self.price_list_type
    gemstone_price_list_doc.gemstone_type = self.gemstone_type
    gemstone_price_list_doc.cut_or_cab = self.cut_or_cab
    gemstone_price_list_doc.stone_shape = self.stone_shape
    gemstone_price_list_doc.gemstone_quality = self.gemstone_quality
    gemstone_price_list_doc.gemstone_size = self.gemstone_size
    gemstone_price_list_doc.gemstone_grade = self.gemstone_grade

    if self.price_list_type == 'Fixed':
        gemstone_price_list_doc.from_weight = row.from_weight
        gemstone_price_list_doc.to_weight = row.to_weight
        gemstone_price_list_doc.supplier_fg_purchase_rate = row.new_supplier_fg_purchase_rate
        gemstone_price_list_doc.outright_handling_charges_rate = row.new_outright_handling_charges_rate
        gemstone_price_list_doc.outright_handling_charges_in_percentage = row.new_outright_handling_charges_in_
        gemstone_price_list_doc.outwork_handling_charges_rate = row.new_outwork_handling_charges_rate
        gemstone_price_list_doc.outwork_handling_charges_in_percentage = row.new_outwork_handling_charges_in_
        gemstone_price_list_doc.rate = row.new_rate
    else:
        gemstone_price_list_doc.rate = self.revised_rate

    gemstone_price_list_doc.effective_from = frappe.utils.now()
    gemstone_price_list_doc.save()



def custom_sort(item):
    start, end = map(float, item['weight_range'][1:].split('-'))
    return (start, end)

def sort_data(self,output_list):
    if self.price_list_type == 'Fixed':
        sorted_data = sorted(output_list, key=custom_sort)

    return sorted_data

def remove_duplicate_data(gemstone_price_list):
    seen = set()
    output_list = []
    for d in gemstone_price_list:
        frozen_dict = frozenset(d.items())
        if frozen_dict not in seen:
            seen.add(frozen_dict)
            output_list.append(d)
    return output_list

def set_data_in_child_table(self,sorted_data):
    for i in sorted_data:
        if self.price_list_type == 'Fixed':
            for_weight_in_cts(self,i)

def for_weight_in_cts(self,i):
    from_weight, to_weight = i['weight_range'].split('-')
    if 'name' in i:
        rate = i.get('rate')
        name = i.get('name')
        supplier_fg_purchase_rate = i.get('supplier_fg_purchase_rate')
        outright_handling_charges_rate = i.get('outright_handling_charges_rate')
        outright_handling_charges_in_percentage = i.get('outright_handling_charges_in_percentage')
        outwork_handling_charges_rate = i.get('outwork_handling_charges_rate')
        outwork_handling_charges_in_percentage = i.get('outwork_handling_charges_in_percentage')
    else:
        rate_filters = {
					"customer": self.customer,
					"price_list": self.price_list,
					"price_list_type": self.price_list_type,
					"gemstone_type": self.gemstone_type,
					"cut_or_cab": self.cut_or_cab,
					"stone_shape": self.stone_shape,
                    "gemstone_quality": self.gemstone_quality,
                    "from_weight": from_weight,
                    "to_weight": to_weight,
				}
        price_list_row = frappe.db.get_value(
            "Gemstone Price List",rate_filters,
            ["name","rate","supplier_fg_purchase_rate","outright_handling_charges_rate",
             "outright_handling_charges_in_percentage","outwork_handling_charges_rate",
             "outwork_handling_charges_in_percentage"],
            as_dict=True,
        ) or {}
        name = price_list_row.get("name")
        rate = price_list_row.get("rate")
        supplier_fg_purchase_rate = price_list_row.get("supplier_fg_purchase_rate")
        outright_handling_charges_rate = price_list_row.get("outright_handling_charges_rate")
        outright_handling_charges_in_percentage = price_list_row.get("outright_handling_charges_in_percentage")
        outwork_handling_charges_rate = price_list_row.get("outwork_handling_charges_rate")
        outwork_handling_charges_in_percentage = price_list_row.get("outwork_handling_charges_in_percentage")

    rate_details = self.append("revise_gemstone_pricelist_detail", {})
    rate_details.gemstone_price_list = name
    rate_details.rate = rate
    rate_details.from_weight = from_weight
    rate_details.to_weight = to_weight
    rate_details.supplier_fg_purchase_rate = supplier_fg_purchase_rate
    rate_details.outright_handling_charges_rate = outright_handling_charges_rate
    rate_details.outright_handling_charges_in_ = outright_handling_charges_in_percentage
    rate_details.outwork_handling_charges_rate = outwork_handling_charges_rate
    rate_details.outwork_handling_charges_in_ = outwork_handling_charges_in_percentage

    rate_details.new_rate = rate
    rate_details.new_supplier_fg_purchase_rate = supplier_fg_purchase_rate
    rate_details.new_outright_handling_charges_rate = outright_handling_charges_rate
    rate_details.new_outright_handling_charges_in_ = outright_handling_charges_in_percentage
    rate_details.new_outwork_handling_charges_rate = outwork_handling_charges_rate
    rate_details.new_outwork_handling_charges_in_ = outwork_handling_charges_in_percentage
    

@frappe.whitelist()
def get_value(doc):
    json_doc = json.loads(doc)
    data = []
    if json_doc['price_list_type'] == 'Fixed':
        for i in json_doc['revise_gemstone_pricelist_detail']:
            data.append(i['from_weight'])
        
        numeric_ranges = [(float(r.split('-')[0]), float(r.split('-')[1])) for r in data]
        sorted_ranges = sorted(zip(data, numeric_ranges), key=lambda x: x[1])
        sorted_ranges = [r[0] for r in sorted_ranges]
        doc1 = frappe.get_doc('Revise Gemstone Price List',json_doc['name'])
        for j in doc1.revise_gemstone_pricelist_detail:
            frappe.db.set_value('Revise Gemstone Price List Details',j.name,'idx',sorted_ranges.index(j.from_weight))

    