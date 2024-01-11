# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class UpdateDiamondPriceList(Document):
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
            if len(self.update_diamond_price_list_details_sieve_size_range) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["sieve_size_range"])):
                if self.update_diamond_price_list_details_sieve_size_range==[]:
                    self.set("update_diamond_price_list_details_sieve_size_range", [])
                    diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["sieve_size_range"])
                    output_list = remove_duplicate_data(diamond_price_list)
                    sorted_data = sort_data(self,output_list)
                    set_data_in_child_table(self,sorted_data)
                else:
                    old_diamond_price_list = [d.diamond_price_list for d in self.update_diamond_price_list_details_sieve_size_range]
                    for j in frappe.db.get_list("Diamond Price List",filters=filters,pluck="name"):
                        if j not in old_diamond_price_list:
                            sorted_data = frappe.db.get_list("Diamond Price List",filters={"name":j},fields=["sieve_size_range"])
                            set_data_in_child_table(self,sorted_data)
                    


    def validate(self):
        doc = frappe.get_doc('Update Diamond Price List',self.name).update_diamond_price_list_details_sieve_size_range
        sort_d = sort_data(self,doc)
        

        return
        # elif self.price_list_type == 'Size (in mm)':
        #     if len(self.update_diamond_price_list_details_size_in_mm) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["size_in_mm"])):
        #         self.set("update_diamond_price_list_details_size_in_mm", [])
        #         diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["size_in_mm"])
        #         output_list = remove_duplicate_data(diamond_price_list)
        #         sorted_data = sort_data(self,output_list)
        #         set_data_in_child_table(self,sorted_data)
            
        # else:
        #     if len(self.update_diamond_price_list_details) != len(frappe.db.get_list("Diamond Price List",filters=filters,fields=["size_in_mm"])):
        #         self.set("update_diamond_price_list_details", [])
        #         old_diamond_price_list = frappe.db.get_list("Diamond Price List",filters=filters,fields=["from_weight","to_weight"])
        #         diamond_price_list = []
        #         for j in old_diamond_price_list:
        #             diamond_price_list.append({"weight_range":f"{j['from_weight']}-{j['to_weight']}"})

        #         output_list = remove_duplicate_data(diamond_price_list)
        #         sorted_data = sort_data(self,output_list)
        #         set_data_in_child_table(self,sorted_data)

        

        # output_list = remove_duplicate_data(diamond_price_list)

        # sorted_data = sort_data(self,output_list)

        # set_data_in_child_table(self,sorted_data)


        
            
    # def validate(self):
    #     if self.price_list_type == 'Sieve Size Range':
    #         table = 'update_diamond_price_list_details_sieve_size_range'
    #     elif self.price_list_type == 'Size (in mm)':
    #         table = 'update_diamond_price_list_details_size_in_mm'
    #     else:
    #         table = 'update_diamond_price_list_details'

    #     for i in self.get(table):
    #         frappe.db.set_value('Diamond Price List',i.diamond_price_list,{'rate':i.revised_rate,'effective_from':self.date})


def custom_sort(item):
    print(item.sieve_size_range)
    start, end = map(float, item.sieve_size_range[1:].split('-'))
    return (start, end)

def custom_sort1(item):
    start, end = map(float, item['weight_range'][1:].split('-'))
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

def for_sieve_size_range(self,i):
    rate_filters =  {
                "price_list": self.price_list,
                "diamond_type": self.diamond_type,
                "stone_shape": self.stone_shape,
                "diamond_quality": self.diamond_quality,
                "price_list_type": self.price_list_type,
                "customer": self.customer,
                "sieve_size_range": i['sieve_size_range'],
            }
    rate = frappe.db.get_value("Diamond Price List",rate_filters,"rate")
    name = frappe.db.get_value("Diamond Price List",rate_filters,"name")
    rate_details = self.append("update_diamond_price_list_details_sieve_size_range", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.revised_rate = rate
    rate_details.sieve_size_range = i['sieve_size_range']
    return

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
    rate_details = self.append("update_diamond_price_list_details_size_in_mm", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.revised_rate = rate
    rate_details.size_in_mm = i['size_in_mm']
    return

def for_weight_in_cts(self,i):
    rate_filters = {
                "price_list": self.price_list,
                "diamond_type": self.diamond_type,
                "stone_shape": self.stone_shape,
                "diamond_quality": self.diamond_quality,
                "price_list_type": self.price_list_type,
                "customer": self.customer,
                "from_weight": i['weight_range'].split('-')[0],
                "to_weight": i['weight_range'].split('-')[1],
            }
    rate = frappe.db.get_value("Diamond Price List",rate_filters,"rate")
    name = frappe.db.get_value("Diamond Price List",rate_filters,"name")
    rate_details = self.append("update_diamond_price_list_details", {})
    rate_details.rate_per_carat = rate
    rate_details.diamond_price_list = name
    rate_details.revised_rate = rate
    rate_details.weight = i['weight_range']
    return


