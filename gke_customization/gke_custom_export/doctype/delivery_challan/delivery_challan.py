# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document
# from frappe.desk.notifications import clear_doctype_notifications

class DeliveryChallan(Document):
	pass

@frappe.whitelist()
def get_company_address(company):
	adress_name = frappe.db.sql(f"""select parent  from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Company' and link_name = '{company}'""",as_dict=1)

	for add in adress_name:
		if 'Billing' in add['parent']:
			gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
			address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','state','pincode','country'])
			new_address_list = [str(0) if element is None else element for element in address_list]
			address = ', '.join(new_address_list).replace(' 0,','')
			# city = frappe.db.get_value('Address',{'name':add['parent']},'city')
			return address,gstin 

@frappe.whitelist()
def get_customer_address(customer):
	adress_name = frappe.db.sql(f"""select parent  from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Customer' and link_name = '{customer}'""",as_dict=1)
	for add in adress_name:
		# if 'Shipping' in add['parent']:
		city = frappe.db.get_value('Address',{'name':add['parent']},'city')
		country = frappe.db.get_value('Address',{'name':add['parent']},'country')
		address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','city','county','state','pincode','country'])
		new_address_list = [str(0) if element is None else element for element in address_list]
		address = ', '.join(new_address_list).replace(' 0,','')
		gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
		state = frappe.db.get_value('Address',{'name':add['parent']},['state','pincode']) 
		state_code_list = [str(0) if element is None else element for element in state]
		state_code = ', '.join(state_code_list).replace(' 0,','') 
		return address,city,country,gstin,state_code
	

# @frappe.whitelist()
# def get_delivery_challan(source_name, target_doc=None):
# 	if isinstance(target_doc, str):
# 		target_doc = json.loads(target_doc)
# 	if not target_doc:
# 		target_doc = frappe.new_doc("Dispatch Slip")
# 	else:
# 		target_doc = frappe.get_doc(target_doc)

# 	# sales_invoice_items = frappe.db.get_value("Sales Invoice", source_name, "*").items
# 	sales_invoice_items = frappe.db.get_list("Sales Invoice Item",filters={"parent":source_name},fields=["*"])
	
# 	# print(sales_invoice_items)
# 	for i in sales_invoice_items:
# 		target_doc.append("delivery_challan_detail", {
# 			"item_code": i.get("item_code"),
# 			"gst_hsn_code": i.get("gst_hsn_code"),
# 			"description": i.get("description"),
# 			"qty": i.get("qty"),
# 			"amount": i.get("net_amount"),
# 			# "item_code": sales_invoice.get("description"),
# 	})
	
# 	stock_entry_items = frappe.db.get_list("Stock Entry Detail",filters={"parent":source_name},fields=["*"])

# 	print(stock_entry_items)

# 	return target_doc
