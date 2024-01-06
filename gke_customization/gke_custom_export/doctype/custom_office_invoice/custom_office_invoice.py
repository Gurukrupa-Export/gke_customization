# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe,json
from frappe.utils import now,getdate
from frappe.model.document import Document

class CustomOfficeInvoice(Document):
	# pass
	def before_insert(self):
		current_date = getdate()
		current_year = current_date.year
		next_year = current_year + 1
		
		max_sequence = frappe.db.get_list("Custom Office Invoice", pluck="sequence")
		max_sequence.sort()
		if max_sequence:
			sequence = int(max_sequence[-1]) + 1
			sequence = f"{sequence:03}"
		else:
			sequence = '001'

		invoice_no = f"EXP/{sequence}/{str(current_year)[2:]}-{str(next_year)[2:]}"

		self.sequence = sequence
		self.i_no = invoice_no
		self.invoice_no = invoice_no
		self.marks_and_nos = invoice_no
	
	def before_save(self):
		total_pcs = 0
		total_gross_weight = 0
		total_gold_weight = 0
		total_rate = 0
		for i in self.description_of_goods_1:
			total_pcs = total_pcs + i.quantity
			total_gross_weight = total_gross_weight + float(i.gross_weight)
			total_gold_weight = total_gold_weight + float(i.metal_weight)
			
			total_rate = total_rate + float(i.total_value)

		self.total_pcs = total_pcs
		self.total_gross_weight = total_gross_weight
		self.total_gold_weight = total_gold_weight
		self.fob_in_usd = total_rate
		if self.freight_charge_in_usd == None:
			self.freight_charge_in_usd = 0.0
		self.total_rate = float(self.freight_charge_in_usd) + float(total_rate)

@frappe.whitelist()
def get_exporter_address(exporter):
	adress_name = frappe.db.sql(f"""select parent  from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Company' and link_name = '{exporter}'""",as_dict=1)

	for add in adress_name:
		if 'Shipping' in add['parent']:
			city = frappe.db.get_value('Address',{'name':add['parent']},'city')
			gstin = frappe.db.get_value('Address',{'name':add['parent']},'gstin')
			pan = frappe.db.get_value('Address',{'name':add['parent']},'custom_pan')
			iec_no = frappe.db.get_value('Address',{'name':add['parent']},'custom_iec_no')
			
			address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','city','state','pincode','country'])
			new_address_list = [str(0) if element is None else element for element in address_list]
			address = ', '.join(new_address_list).replace(' 0,','')
			
			return address,city,gstin,pan,iec_no
		
@frappe.whitelist()		
def get_exporter_bank(exporter):
	exporter_bank = frappe.db.sql(f"""select name from `tabBank Account` tba where company = '{exporter}' and is_company_account = '1'""",as_dict=1)
	# bankName = exporter_bank[0]['name']
	if exporter_bank:
		bankName = exporter_bank[0]['name']
	else:
		return [], ""
	
	adress_name = frappe.db.sql(f"""select parent from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Bank Account' and link_name = '{bankName}'""",as_dict=1)
	bank_details = []

	for bank in exporter_bank:
		bankname = frappe.db.get_value('Bank Account',{'name':bank['name']},'bank')	
		bankAccountno = frappe.db.get_value('Bank Account',{'name':bank['name']},'bank_account_no')	
		bankIFSC = frappe.db.get_value('Bank Account',{'name':bank['name']},'custom_ifsc_code')	
		bankAD = frappe.db.get_value('Bank Account',{'name':bank['name']},'custom_ad_code')	
		
		bank_details.extend([bankname, bankAccountno, bankIFSC, bankAD])

	for add in adress_name:
		# if 'Billing' in add['parent']:
		address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','city','state','pincode','country'])
		new_address_list = [str(0) if element is None else element for element in address_list]
		address = ', '.join(new_address_list).replace(' 0,','')
	
	return bank_details, address

@frappe.whitelist()
def get_customer_address(consignee):
	adress_name = frappe.db.sql(f"""select parent  from `tabDynamic Link` tdl where parenttype = 'Address' and link_doctype = 'Customer' and link_name = '{consignee}'""",as_dict=1)
	for add in adress_name:
		if 'Shipping' in add['parent']:
			city = frappe.db.get_value('Address',{'name':add['parent']},'city')
			country = frappe.db.get_value('Address',{'name':add['parent']},'country')
			address_list = frappe.db.get_value('Address',{'name':add['parent']},['address_line1','address_line2','city','county','state','pincode','country'])
			new_address_list = [str(0) if element is None else element for element in address_list]
			address = ', '.join(new_address_list).replace(' 0,','')
			return address,city,country


@frappe.whitelist()
def get_items_from_packing_list(source_name,target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Custom Office Invoice")
	else:
		target_doc = frappe.get_doc(target_doc)

	packing_list_detail = frappe.db.get_list("Packing List Detail",filters={"parent":source_name},fields=["*"])
	
	for i in packing_list_detail:
		target_doc.append("description_of_goods_1", {
			"item_code": i.item_code,
		})

	return target_doc