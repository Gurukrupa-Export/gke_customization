# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document
# from frappe.desk.notifications import clear_doctype_notifications

class DeliveryChallan(Document):
	pass

@frappe.whitelist()
def get_company_address(company, company_branch):
	adress_name = frappe.db.sql(f"""select parent  from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Company' and link_name = '{company}'""",as_dict=1)
	# branch = frappe.db.get_value('Branch',{'name': company_branch },'branch')
	branch = frappe.db.get_value('Branch',{'name': company_branch },'branch_address')

	for add in adress_name:
		if  branch in add['parent']:
			# frappe.throw("IF")
			gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
			address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','state','pincode','country'])
			new_address_list = [str(0) if element is None else element for element in address_list]
			address = ', '.join(new_address_list).replace(' 0,','')
			# city = frappe.db.get_value('Address',{'name':add['parent']},'city')
			return address,gstin
		# elif company in add['parent']:
		# 	frappe.throw("ELSE")
		# 	gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
		# 	address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','state','pincode','country'])
		# 	new_address_list = [str(0) if element is None else element for element in address_list]
		# 	address = ', '.join(new_address_list).replace(' 0,','')
		# 	return address,gstin 
	

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
	

@frappe.whitelist()
def get_supplier_address(supplier):
	adress_name = frappe.db.sql(f"""select parent from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Supplier' and link_name = '{supplier}'""",as_dict=1)
	for add in adress_name:
		address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','city','county','state','pincode'])
		new_address_list = [str(0) if element is None else element for element in address_list]
		address = ', '.join(new_address_list).replace(' 0,','') 
		gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
		state = frappe.db.get_value('Address',{'name':add['parent']},['state','pincode']) 
		state_code_list = [str(0) if element is None else element for element in state]
		state_code = ', '.join(state_code_list).replace(' 0,','') 

		return address,gstin,state_code
