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
				"gemstone_type": self.stone_type,
				"cut_or_cab": self.cut_or_cab,
				"stone_shape": self.stone_shape,
                "gemstone_quality": self.stone_quality,
			}
                   
        if self.price_list_type == 'Weight (in cts)':
            if len(self.revise_gemstone_price_list_details) != len(frappe.db.get_list("Gemstone Price List",filters=filters,fields=["from_weight","to_weight"])):
                if self.revise_gemstone_price_list_details==[]:
                    self.set("revise_gemstone_price_list_details", [])
                    # old_diamond_price_list = frappe.db.get_list("Gemstone Price List",filters=filters,fields=["from_weight","to_weight"])
                    old_gemstone_price_list = frappe.db.get_list("Gemstone Price List",filters=filters,fields=["from_weight","to_weight"])
                    gemstone_price_list = []
                    for j in old_gemstone_price_list:
                        gemstone_price_list.append({"weight_range":f"{j['from_weight']}-{j['to_weight']}"})

                    output_list = remove_duplicate_data(gemstone_price_list)
                    sorted_data = sort_data(self,output_list)
                    set_data_in_child_table(self,sorted_data)
                else:
                    old_gemstone_price_list = [d.gemstone_price_list for d in self.revise_gemstone_price_list_details]
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
        if self.price_list_type == 'Weight (in cts)':
            for i in self.revise_gemstone_price_list_details:
                # if i.difference!=0:
                frappe.db.set_value('Gemstone Price List',i.gemstone_price_list,{'rate':i.revised_rate,'effective_from':self.date})
        else:
            frappe.db.set_value('Gemstone Price List',self.gemstone_price_list,{'rate':self.revised_rate,'effective_from':self.date})
        if not i.gemstone_price_list:
            crate_price_list(self,i)
        frappe.msgprint("Price List Updated")
            
def crate_price_list(self,row):
    gemstone_price_list_doc = frappe.new_doc("Gemstone Price List")
    gemstone_price_list_doc.customer = self.customer
    gemstone_price_list_doc.price_list = self.price_list
    gemstone_price_list_doc.price_list_type = self.price_list_type
    gemstone_price_list_doc.gemstone_type = self.stone_type
    gemstone_price_list_doc.cut_or_cab = self.cut_or_cab
    gemstone_price_list_doc.stone_shape = self.stone_shape
    gemstone_price_list_doc.gemstone_quality = self.stone_quality
    gemstone_price_list_doc.gemstone_size = self.stone_size

    if self.handling_charges_for_outright:
        gemstone_price_list_doc.outright_handling_charges_in_percentage = self.custom_outright_handling_charges_in_percentage
        gemstone_price_list_doc.outright_handling_charges_rate = self.custom_outright_handling_charges_rate

    if self.handling_charges_for_outwork_handling_rate:
        gemstone_price_list_doc.outwork_handling_charges_in_percentage = self.custom_outwork_handling_charges_in_percentage
        gemstone_price_list_doc.outwork_handling_charges_rate = self.custom_outwork_handling_charges_rate


    if self.price_list_type == 'Weight (in cts)':
        from_weight = float(row.weight.split('-')[0])
        to_weight = float(row.weight.split('-')[1])
        gemstone_price_list_doc.from_weight = from_weight
        gemstone_price_list_doc.to_weight = to_weight

    gemstone_price_list_doc.effective_from = frappe.utils.now()
    gemstone_price_list_doc.rate = row.revised_rate
    gemstone_price_list_doc.save()



def custom_sort(item):
    start, end = map(float, item['weight_range'][1:].split('-'))
    return (start, end)

def sort_data(self,output_list):
    if self.price_list_type == 'Weight (in cts)':
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
        if self.price_list_type == 'Weight (in cts)':
            for_weight_in_cts(self,i)

def for_weight_in_cts(self,i):
    rate_filters = {
				"customer": self.customer,
				"price_list": self.price_list,
				"price_list_type": self.price_list_type,
				"gemstone_type": self.stone_type,
				"cut_or_cab": self.cut_or_cab,
				"stone_shape": self.stone_shape,
                "gemstone_quality": self.stone_quality,
                "from_weight": i['weight_range'].split('-')[0],
                "to_weight": i['weight_range'].split('-')[1],
			}
    rate = frappe.db.get_value("Gemstone Price List",rate_filters,"rate")
    name = frappe.db.get_value("Gemstone Price List",rate_filters,"name")
    handling_rate = frappe.db.get_value("Gemstone Price List",rate_filters,"handling_rate")
    rate_details = self.append("revise_gemstone_price_list_details", {})
    rate_details.rate_per_carat = rate
    rate_details.gemstone_price_list = name
    rate_details.gemstone_price_list = handling_rate
    rate_details.revised_rate = rate
    rate_details.weight = i['weight_range']
    

@frappe.whitelist()
def get_value(doc):
    json_doc = json.loads(doc)
    data = []
    if json_doc['price_list_type'] == 'Weight (in cts)':
        for i in json_doc['revise_gemstone_price_list_details']:
            data.append(i['weight'])
        
        numeric_ranges = [(float(r.split('-')[0]), float(r.split('-')[1])) for r in data]
        sorted_ranges = sorted(zip(data, numeric_ranges), key=lambda x: x[1])
        sorted_ranges = [r[0] for r in sorted_ranges]
        doc1 = frappe.get_doc('Revise Gemstone Price List',json_doc['name'])
        for j in doc1.revise_gemstone_price_list_details:
            frappe.db.set_value('Revise Gemstone Price List Details',j.name,'idx',sorted_ranges.index(j.weight))

    