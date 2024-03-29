# Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
# For license information, please see license.txt

import frappe
# import json
from frappe.model.document import Document,json

class ExhibitionSelection(Document):
	pass

@frappe.whitelist()
def create_exhibition(user_data, selected_items):
    user_data_dict = json.loads(user_data)
    selected_items_list = json.loads(selected_items)

    if(user_data_dict and selected_items_list):

        exhibition = frappe.new_doc('Exhibition Selection')
        
        lead_ = 0
        if user_data_dict.get('lead'):
            lead_ = 1

        customer_ = 0
        if user_data_dict.get('customer'):
            customer_ = 1
            
        exhibition.update({
            'user': user_data_dict.get('employee'),
            'branch': user_data_dict.get('branch'),
            'selectionperson': user_data_dict.get('selectionPerson'),
            'salesman': frappe.db.get_value('Employee',{'employee_name':user_data_dict.get('salesman')},'name'),
            'lead_': lead_,
            'lead': frappe.db.get_value('Lead',{'title':user_data_dict.get('lead')}, 'name'),
            'customer_': customer_,
            'customer': frappe.db.get_value('Customer',{'customer_name':user_data_dict.get('customer')}, 'name'),

        })
        exhibition.insert()
        
        # Iterate over each selected item and add to 'item_selection' child table
        for index, item in enumerate(selected_items_list, start=1):
            item_selection = exhibition.append('item_selection', {
                'item_no': item.get('no'),
                # 'category': item.get('category'),
            })

        exhibition.save()
        return frappe.msgprint("Exhibition Selection created successfully")
    
    else:
        frappe.msgprint("Exhibition Selection not created successfully")
         