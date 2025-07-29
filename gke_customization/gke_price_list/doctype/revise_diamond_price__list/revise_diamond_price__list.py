# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ReviseDiamondPriceList(Document):
        def before_save(self):
        filters = {
				"price_list": self.price_list,
				"diamond_type": self.diamond_type,
				"stone_shape": self.stone_shape,
				"diamond_quality": self.diamond_quality,
				"price_list_type": self.price_list_type,
				"customer": self.customer,
			}

        if self.price_list_type == 'Sieve Size Range':
            if len(self.revise_diamond_price_list_details_sieve_size_range) == 0:
            # if len(self.revise_diamond_price_list_details_sieve_size_range) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["sieve_size_range"])):
            #     if self.revise_diamond_price_list_details_sieve_size_range==[]:
                self.set("revise_diamond_price_list_details_sieve_size_range", [])
                diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["sieve_size_range"])
                output_list = remove_duplicate_data(diamond_price_list)
                sorted_data = sort_data(self,output_list)
                set_data_in_child_table(self,sorted_data)
                # else:
                #     old_diamond_price_list = [d.diamond_price_list for d in self.revise_diamond_price_list_details_sieve_size_range]
                #     for j in frappe.db.get_list("Diamond Price List",filters=filters,pluck="name"):
                #         if j not in old_diamond_price_list:
                #             sorted_data = frappe.db.get_list("Diamond Price List",filters={"name":j},fields=["sieve_size_range"])
                #             set_data_in_child_table(self,sorted_data)
        
        elif self.price_list_type == 'Size (in mm)':
            if len(self.revise_diamond_price_list_details_size_in_mm) == 0:
            # if len(self.revise_diamond_price_list_details_size_in_mm) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["size_in_mm"])):
                # if self.revise_diamond_price_list_details_size_in_mm==[]:
                self.set("revise_diamond_price_list_details_size_in_mm", [])
                diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["size_in_mm"])
                output_list = remove_duplicate_data(diamond_price_list)
                sorted_data = sort_data(self,output_list)
                set_data_in_child_table(self,sorted_data)
                # else:
                #     old_diamond_price_list = [d.diamond_price_list for d in self.revise_diamond_price_list_details_size_in_mm]
                #     for j in frappe.db.get_list("Diamond Price List",filters=filters,pluck="name"):
                #         if j not in old_diamond_price_list:
                #             sorted_data = frappe.db.get_list("Diamond Price List",filters={"name":j},fields=["size_in_mm"])
                #             set_data_in_child_table(self,sorted_data)
                    
        else:
            if len(self.revise_diamond_price_list_details) == 0:
            # if len(self.revise_diamond_price_list_details) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["from_weight","to_weight"])):
                # if self.revise_diamond_price_list_details==[]:
                self.set("revise_diamond_price_list_details", [])
                old_diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["from_weight","to_weight"])
                diamond_price_list = []
                for j in old_diamond_price_list:
                    diamond_price_list.append({"weight":f"{j['from_weight']}-{j['to_weight']}"})

                output_list = remove_duplicate_data(diamond_price_list)
                sorted_data = sort_data(self,output_list)
                set_data_in_child_table(self,sorted_data)
                # else:
                #     old_diamond_price_list = [d.diamond_price_list for d in self.revise_diamond_price_list_details]
                #     for j in frappe.db.get_list("Diamond Price List",filters=filters,pluck="name"):
                #         if j not in old_diamond_price_list:
                #             # sorted_data = frappe.db.get_list("Diamond Price List",filters={"name":j},fields=["from_weight","to_weight"])
                #             raw_data = frappe.db.get_list("Diamond Price List",filters={"name":j},fields=["from_weight","to_weight"])
                            
                #             # sorted_data = [{"weight": f"{d['from_weight']}-{d['to_weight']}"} for d in raw_data]
                #             set_data_in_child_table(self,sorted_data)



    def on_submit(self):
        if self.price_list_type == 'Sieve Size Range':
            table = 'revise_diamond_price_list_details_sieve_size_range'
        elif self.price_list_type == 'Size (in mm)':
            table = 'revise_diamond_price_list_details_size_in_mm'
        else:
            table = 'revise_diamond_price_list_details'

        for i in self.get(table):
            
            frappe.db.set_value('Diamond Price List',i.diamond_price_list,{'rate':i.revised_rate,'effective_from':self.date,'supplier_fg_purchase_rate':i.supplier_fg_purchase_rate})
            if not i.diamond_price_list:
                crate_price_list(self,i)
        frappe.msgprint("Price List Updated")

def crate_price_list(self,row):
    diamond_price_list_doc = frappe.new_doc("Diamond Price List")
    diamond_price_list_doc.customer = self.customer
    diamond_price_list_doc.price_list = self.price_list
    diamond_price_list_doc.price_list_type = self.price_list_type
    diamond_price_list_doc.diamond_type = self.diamond_type
    diamond_price_list_doc.diamond_quality = self.diamond_quality
    diamond_price_list_doc.stone_shape = self.stone_shape

    if self.handling_charges_for_outright:
        diamond_price_list_doc.custom_outright_handling_charges_in_percentage = self.outright_handling_charges_in_percentage
        diamond_price_list_doc.custom_outright_handling_charges_rate = self.outright_handling_charges_rate
    if self.handling_charges_for_outwork:
        diamond_price_list_doc.custom_outwork_handling_charges_in_percentage = self.outwork_handling_charges_in_percentage
        diamond_price_list_doc.custom_outwork_handling_charges_rate = self.outwork_handling_charges_rate

    if self.price_list_type == 'Sieve Size Range':
        diamond_price_list_doc.sieve_size_range = row.sieve_size_range
    elif self.price_list_type == 'Size (in mm)':
        diamond_price_list_doc.size_in_mm = row.size_in_mm
        diamond_price_list_doc.diamond_size_in_mm = row.diamond_size_in_mm
    else:
        from_weight = float(row.weight.split('-')[0])
        to_weight = float(row.weight.split('-')[1])
        diamond_price_list_doc.from_weight = from_weight
        diamond_price_list_doc.to_weight = to_weight
    diamond_price_list_doc.effective_from = frappe.utils.now()
    diamond_price_list_doc.rate = row.revised_rate
    diamond_price_list_doc.handling_rate = row.revised_diamond_handling_rate
    diamond_price_list_doc.save()



def custom_sort(item):
    start, end = map(float, item.sieve_size_range[1:].split('-'))
    return (start, end)

def custom_sort1(item):
    # frappe.throw(f"{item}")
    start, end = map(float, item['weight'][1:].split('-'))
    return (start, end)

def sort_data(self,output_list):
    if self.price_list_type == 'Sieve Size Range':
        sorted_data = sorted(output_list, key=custom_sort)


    elif self.price_list_type == 'Size (in mm)':
        sorted_data = sorted(output_list, key=lambda x: x['size_in_mm'])

    else:
        sorted_data = sorted(output_list, key=custom_sort1)

    return sorted_data

def remove_duplicate_data(diamond_price_list):
    seen = set()
    output_list = []
    for d in diamond_price_list:
        frozen_dict = frozenset(d.items())
        if frozen_dict not in seen:
            seen.add(frozen_dict)
            output_list.append(d)
    return output_list

def set_data_in_child_table(self,sorted_data):
    for i in sorted_data:
        if self.price_list_type == 'Sieve Size Range':
            for_sieve_size_range(self,i)

        elif self.price_list_type == 'Size (in mm)':
            for_size_in_mm(self,i)

        else:
            for_weight_in_cts(self,i)
    # sort_data(self,rate_details)

def for_sieve_size_range(self,i):
    rate_filters =  {
                "price_list": self.price_list,
                "diamond_type": self.diamond_type,
                "stone_shape": self.stone_shape,
                "diamond_quality": self.diamond_quality,
                "price_list_type": self.price_list_type,
                "customer": self.customer,
                "sieve_size_range": i.sieve_size_range,
            }
    rate = frappe.db.get_value("Diamond Price List",rate_filters,"rate")
    name = frappe.db.get_value("Diamond Price List",rate_filters,"name")
    handling_rate = frappe.db.get_value("Diamond Price List",rate_filters,"handling_rate")
    rate_details = self.append("revise_diamond_price_list_details_sieve_size_range", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.diamond_handling_rate = handling_rate
    rate_details.revised_rate = rate
    rate_details.sieve_size_range = i.sieve_size_range
    

def for_size_in_mm(self,i):
    rate_filters = {
                "price_list": self.price_list,
                "diamond_type": self.diamond_type,
                "stone_shape": self.stone_shape,
                "diamond_quality": self.diamond_quality,
                "price_list_type": self.price_list_type,
                "customer": self.customer,
                "size_in_mm": i['size_in_mm'],
            }
    rate = frappe.db.get_value("Diamond Price List",rate_filters,"rate")
    name = frappe.db.get_value("Diamond Price List",rate_filters,"name")
    handling_rate = frappe.db.get_value("Diamond Price List",rate_filters,"handling_rate")
    rate_details = self.append("revise_diamond_price_list_details_size_in_mm", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.diamond_handling_rate = handling_rate
    rate_details.revised_rate = rate
    rate_details.size_in_mm = i['size_in_mm']
    

def for_weight_in_cts(self,i):
    rate_filters = {
                "price_list": self.price_list,
                "diamond_type": self.diamond_type,
                "stone_shape": self.stone_shape,
                "diamond_quality": self.diamond_quality,
                "price_list_type": self.price_list_type,
                "customer": self.customer,
                "from_weight": i['weight'].split('-')[0],
                "to_weight": i['weight'].split('-')[1],
            }
    rate = frappe.db.get_value("Diamond Price List",rate_filters,"rate")
    name = frappe.db.get_value("Diamond Price List",rate_filters,"name")
    handling_rate = frappe.db.get_value("Diamond Price List",rate_filters,"handling_rate")
    rate_details = self.append("revise_diamond_price_list_details", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.diamond_handling_rate = handling_rate
    rate_details.revised_rate = rate
    rate_details.weight = i['weight']
    rate_details.from_weight= i['weight'].split('-')[0]
    rate_details.to_weight= i['weight'].split('-')[1]



