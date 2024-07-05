# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document
import frappe.utils
from erpnext.accounts.general_ledger import make_gl_entries

class GSTReconciliation(Document):
	def on_submit(self):
		invoice_type = self.invoice_type
		if self.invoice_type == 'Sales Invoice':
			create_gl_entry_for_sales_invoice(self,invoice_type)
		else:
			create_gl_entry_for_purchase_invoice(self,invoice_type)
		# for i in self.gst_reconciliation:
		# 	frappe.db.set_value(i.type,i.invoice,'custom_is_gst_reconciliation','1')

@frappe.whitelist()
def get_invoice(from_date,to_date,invoice_type,company):
	if invoice_type == 'Sales Invoice':
		doctype = 'Sales Invoice'
		child_table = 'Sales Taxes and Charges'
		party = 'customer'
		party_name = 'customer_name'
		party_type = 'Customer'
	else:
		doctype = 'Purchase Invoice'
		child_table = 'Purchase Taxes and Charges'
		party = 'supplier'
		party_name = 'supplier_name'
		party_type = 'Supplier'

	invoice = frappe.db.sql(
		f"""
			SELECT
			si.name AS invoice,
			si.{party} AS party,
			si.{party_name} AS party_name,
			si.total AS item_total,
			si.posting_date AS date,
			si.total_taxes_and_charges
		FROM
			`tab{doctype}` si
		WHERE
			si.company = "{company}" AND
			si.docstatus = 1 AND 
			si.custom_is_gst_reconciliation = 0
			AND si.posting_date >= "{from_date}"
			AND si.posting_date <= "{to_date}";
		""",as_dict=1,
	)

	for i in invoice:
		i['type'] = invoice_type
		i['party_type'] = party_type
		taxes_and_charges = frappe.db.sql(f"""
				select 
					description,account_head,
					rate,tax_amount,total 
				from `tab{child_table}` 
				where parent = '{i["invoice"]}'
			""" ,as_dict=1          
        )
		total_cgst = 0
		total_sgst = 0
		total_igst = 0
		if taxes_and_charges:
			for tax in taxes_and_charges:
				if 'CGST' in tax['description']:
					total_cgst += tax.get('tax_amount')
				elif 'SGST' in tax['description']:
					total_sgst += tax.get('tax_amount')
				elif 'IGST' in tax['description']:
					total_igst += tax.get('tax_amount')
			
			i['total_cgst'] = total_cgst
			i['total_sgst'] = total_sgst
			i['total_igst'] = total_igst
		i['grand_total'] = float(i['total_taxes_and_charges']) + float(i['item_total'])
	return invoice


def create_gl_entry_for_sales_invoice(self):
	all_tax = []
	if self.total_cgst != 0:
		all_tax.append({"tax_type":"CGST","tax_amount":self.total_cgst})
		
	if self.total_igst != 0:
		all_tax.append({"tax_type":"IGST","tax_amount":self.total_igst})

	if self.total_sgst != 0:
		all_tax.append({"tax_type":"SGST","tax_amount":self.total_sgst})
	
	for i in all_tax:
		make_gl_entry_for_sale(self,i)
		make_payable_entry_for_sale(self,i)

def make_gl_entry_for_sale(self,tax_dict):
	tax_type = tax_dict["tax_type"]
	tax_amount = tax_dict["tax_amount"]

	debit_account = frappe.db.sql(f"""select name from `tabAccount` where company = '{self.company}' and account_type = 'Tax' and is_group = 0  and name like '%Output Tax {tax_type}%'""",as_dict=1)
	if not debit_account:
		frappe.throw("Account not found")

	debit_account_currency = frappe.db.get_value("Account",debit_account[0]['name'],"account_currency")
	if not debit_account_currency:
		frappe.throw(f"Account Currency is not available for {debit_account[0]['name']}")

	doc = frappe.get_doc({
		'doctype': 'GL Entry',
		'posting_date': frappe.utils.getdate(),
		'account': debit_account[0]['name'],
		'debit': tax_amount,
		'account_currency':debit_account_currency,
		'voucher_type': 'GST Reconciliation',
		'voucher_no':self.name,
		'is_opening': 'No',
		'is_advance': 'No',
		'fiscal_year': frappe.db.get_list("Fiscal Year",pluck='name',order_by='name desc')[0],
		'company': self.company,
		'company_gstin': frappe.db.get_value("Company",self.company,"gstin"),
	})
	doc.insert()

def make_payable_entry_for_sale(self,tax_dict):
	tax_type = tax_dict["tax_type"]
	credit_account = frappe.db.sql(f"""select name from `tabAccount` where company = '{self.company}' and account_type = 'Tax' and is_group = 0 and name like '%{tax_type} Payable - %'""",as_dict=1)
	if not credit_account:
		frappe.throw("Account not found")
	
	credit_account_currency = frappe.db.get_value("Account",credit_account[0]['name'],"account_currency")
	if not credit_account_currency:
		frappe.throw(f"Account Currency is not available for {credit_account[0]['name']}")

	doc = frappe.get_doc({
		'doctype': 'GL Entry',
		'posting_date': frappe.utils.getdate(),
		'account': credit_account[0]['name'],
		'credit': self.total_sales,
		'account_currency':credit_account_currency,
		'voucher_type': 'GST Reconciliation',
		'voucher_no':self.name,
		'is_opening': 'No',
		'is_advance': 'No',
		'fiscal_year': frappe.db.get_list("Fiscal Year",pluck='name',order_by='name desc')[0],
		'company': self.company,
		'company_gstin': frappe.db.get_value("Company",self.company,"gstin"),
	})
	doc.insert()


def create_gl_entry_for_purchase_invoice(self):
	all_tax = []
	if self.total_cgst != 0:
		all_tax.append({"tax_type":"CGST","tax_amount":self.total_cgst})
		
	if self.total_igst != 0:
		all_tax.append({"tax_type":"IGST","tax_amount":self.total_igst})

	if self.total_sgst != 0:
		all_tax.append({"tax_type":"SGST","tax_amount":self.total_sgst})
	
	for i in all_tax:
		make_gl_entry_for_purchase(self,i)
	make_payable_entry_for_purchase(self)


def make_gl_entry_for_purchase(self,tax_dict):
	tax_type = tax_dict["tax_type"]
	tax_amount = tax_dict["tax_amount"]

	credit_account = frappe.db.sql(f"""select name from `tabAccount` where company = '{self.company}' and account_type = 'Tax' and is_group = 0  and name like '%Input Tax {tax_type}%'""",as_dict=1)
	if not credit_account:
		frappe.throw("Account not found")

	credit_account_currency = frappe.db.get_value("Account",credit_account[0]['name'],"account_currency")
	if not credit_account_currency:
		frappe.throw(f"Account Currency is not available for {credit_account[0]['name']}")

	doc = frappe.get_doc({
		'doctype': 'GL Entry',
		'posting_date': frappe.utils.getdate(),
		'account': credit_account[0]['name'],
		'credit': tax_amount,
		'account_currency':credit_account_currency,
		'voucher_type': 'GST Reconciliation',
		'voucher_no':self.name,
		'is_opening': 'No',
		'is_advance': 'No',
		'fiscal_year': frappe.db.get_list("Fiscal Year",pluck='name',order_by='name desc')[0],
		'company': self.company,
		'company_gstin': frappe.db.get_value("Company",self.company,"gstin"),
	})
	doc.insert()

def make_payable_entry_for_purchase(self,tax_dict):
	tax_type = tax_dict["tax_type"]
	debit_account = frappe.db.sql(f"""select name from `tabAccount` where company = '{self.company}' and account_type = 'Tax' and is_group = 0 and name like '%{tax_type} Payable - %'""",as_dict=1)
	if not debit_account:
		frappe.throw("Account not found")
	
	debit_account_currency = frappe.db.get_value("Account",debit_account[0]['name'],"account_currency")
	if not debit_account_currency:
		frappe.throw(f"Account Currency is not available for {debit_account[0]['name']}")

	doc = frappe.get_doc({
		'doctype': 'GL Entry',
		'posting_date': frappe.utils.getdate(),
		'account': debit_account[0]['name'],
		'debit': self.total_sales,
		'account_currency':debit_account_currency,
		'voucher_type': 'GST Reconciliation',
		'voucher_no':self.name,
		'is_opening': 'No',
		'is_advance': 'No',
		'fiscal_year': frappe.db.get_list("Fiscal Year",pluck='name',order_by='name desc')[0],
		'company': self.company,
		'company_gstin': frappe.db.get_value("Company",self.company,"gstin"),
	})
	doc.insert()
