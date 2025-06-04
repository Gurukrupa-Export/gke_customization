# Copyright (c) 2024, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document
from datetime import datetime, timedelta
import frappe.utils


class UnsecuredLoan(Document):
    # pass
	def validate(self):
		loan_amount = self.loan_amount
		interest_rate = self.interest_rate
		repayment_period = self.repayment_period
		loan_date = self.loan_date
		if not loan_amount or not interest_rate or not repayment_period:
			frappe.throw("Please ensure loan amount, interest rate, and repayment period are provided.")
		if self.repayment_schedule: 
			if len(self.repayment_schedule)==1:
				d1 = frappe.utils.getdate(loan_date)
				d2 = frappe.utils.getdate(self.repayment_schedule[0].payment_date)
				days = (d2 - d1).days
				interest = flt((loan_amount*interest_rate*days)/(100*365),2)
				self.repayment_schedule[0].number_of_days = days
				self.repayment_schedule[0].interest_amount = interest
				self.repayment_schedule[0].repay_loan_amount = self.repayment_schedule[0].total_payment - interest
				self.repayment_schedule[0].balance_loan_amount = loan_amount - self.repayment_schedule[0].repay_loan_amount
				if self.repayment_schedule[0].balance_loan_amount > loan_amount:
					frappe.throw("Repayment Loan Amount is not correct")
			else:
				d1 = frappe.utils.getdate(self.repayment_schedule[-2].payment_date)
				d2 = frappe.utils.getdate(self.repayment_schedule[-1].payment_date)
				days = (d2 - d1).days
				interest = flt((self.repayment_schedule[-2].balance_loan_amount*interest_rate*days)/(100*365),2)
				self.repayment_schedule[-1].number_of_days = days
				self.repayment_schedule[-1].interest_amount = interest
				self.repayment_schedule[-1].repay_loan_amount = self.repayment_schedule[-1].total_payment - interest
				self.repayment_schedule[-1].balance_loan_amount = self.repayment_schedule[-2].balance_loan_amount - self.repayment_schedule[-1].repay_loan_amount
				if self.repayment_schedule[-1].repay_loan_amount > self.repayment_schedule[-2].balance_loan_amount:
					frappe.throw("Repayment Loan Amount is not correct")

		# if self.workflow_state == 'Interest Accrual':
		# 	create_gl_entry(self)

# def create_gl_entry(self):
# 	if not self.parent_gl_entry_created:
# 		credit_entry = frappe.get_doc({
# 					"doctype": "GL Entry",
# 					"account": self.principal_gl_account,
# 					"posting_date": self.loan_date,
# 					"credit": self.loan_amount,
# 					"credit_in_account_currency": self.loan_amount,
# 					"credit_in_transaction_currency": self.loan_amount,
# 					"company": self.company,
# 					"voucher_type": "Unsecured Loan",
# 					"voucher_no": self.name,
# 					"party_type":"Customer",
# 					"party":frappe.db.get_value("Business Partner", self.lender, "customer"),
# 					"cost_center":self.cost_center,
# 				})
# 		credit_entry.insert()

# 		debit_entry = frappe.get_doc({
# 					"doctype": "GL Entry",
# 					"account": frappe.db.get_value("Business Partner", self.lender, "account"),
# 					"posting_date": self.loan_date,
# 					"debit": self.loan_amount,
# 					"debit_in_account_currency": self.loan_amount,
# 					"debit_in_transaction_currency": self.loan_amount,
# 					"company": self.company,
# 					"voucher_type": "Unsecured Loan",
# 					"voucher_no": self.name,
# 					"party_type":"Business Partner",
# 					"party":self.lender,
# 					"cost_center":self.cost_center,
# 				})
# 		debit_entry.insert()

# 		frappe.db.commit()
# 		self.parent_gl_entry_created = 1


# 	for schedule_row in self.repayment_schedule:
# 		if not schedule_row.gl_entry_created:
# 			debit_entry = frappe.get_doc({
# 					"doctype": "GL Entry",
# 					"account": self.principal_gl_account,
# 					"posting_date": schedule_row.payment_date,
# 					"debit": schedule_row.repay_loan_amount,
# 					"debit_in_account_currency": schedule_row.repay_loan_amount,
# 					"debit_in_transaction_currency": schedule_row.repay_loan_amount,
# 					"company": self.company,
# 					"voucher_type": "Unsecured Loan",
# 					"voucher_no": self.name,
# 					"party_type":"Supplier",
# 					"party":frappe.db.get_value("Business Partner", self.lender, "supplier"),
# 					"cost_center":self.cost_center,
# 					"remarks": f"Debit GL entry for repayment schedule row {schedule_row.idx}",
# 				})
# 			debit_entry.insert()

# 			debit_entry = frappe.get_doc({
# 					"doctype": "GL Entry",
# 					"account": self.interest_gl_account,
# 					"posting_date": schedule_row.payment_date,
# 					"debit": schedule_row.interest_amount,
# 					"debit_in_account_currency": schedule_row.interest_amount,
# 					"debit_in_transaction_currency": schedule_row.interest_amount,
# 					"company": self.company,
# 					"voucher_type": "Unsecured Loan",
# 					"voucher_no": self.name,
# 					"party_type":"Supplier",
# 					"party":frappe.db.get_value("Business Partner", self.lender, "supplier"),
# 					"cost_center":self.cost_center,
# 					"remarks": f"Debit GL entry for repayment schedule row {schedule_row.idx}",
# 				})
# 			debit_entry.insert()

# 			credit_entry = frappe.get_doc({
# 					"doctype": "GL Entry",
# 					"account": frappe.db.get_value("Business Partner", self.lender, "account"),
# 					"posting_date": schedule_row.payment_date,
# 					"credit": schedule_row.total_payment,
# 					"credit_in_account_currency": schedule_row.total_payment,
# 					"credit_in_transaction_currency": schedule_row.total_payment,
# 					"company": self.company,
# 					"voucher_type": "Unsecured Loan",
# 					"voucher_no": self.name,
# 					"party_type":"Business Partner",
# 					"party":self.lender,
# 					"cost_center":self.cost_center,
# 				})
# 			credit_entry.insert()
	
# 			frappe.db.commit()
# 			schedule_row.gl_entry_created = 1

# 	# return



# @frappe.whitelist()
# def create_receive_payment_entry(loan_name):
# 	try:
# 		loan = frappe.get_doc("Unsecured Loan", loan_name)  # Assuming your Doctype is 'Unsecured Loan'
# 		# Fetch Business Partner details
# 		business_partner = frappe.get_value("Business Partner", loan.lender, ["customer", "account"], as_dict=True)
# 		if not business_partner or not business_partner.get("customer") or not business_partner.get("account"):
# 			frappe.throw("Business Partner details are missing.")
# 		if not loan.parent_gl_entry_created:
# 			# Create Payment Entry
# 			payment_entry = frappe.get_doc({
# 				"doctype": "Payment Entry",
# 				"payment_type": "Receive",
# 				"party_type": "Customer",
# 				"party": business_partner.get("customer"),
# 				"posting_date": frappe.utils.today(),
# 				"paid_amount": loan.loan_amount,
# 				"received_amount":loan.loan_amount,
# 				"company": loan.company,
# 				"cost_center": loan.cost_center,
# 				"mode_of_payment": "Cash",
# 				"paid_from": business_partner.get("account"),
# 				"paid_to": loan.principal_gl_account,
# 				"custom_unsecured_loan":loan.name
# 				})
			
# 			payment_entry.insert(ignore_permissions=True)
# 			payment_entry.submit()
# 			loan.parent_gl_entry_created = 1
# 			loan.save()
# 			return {"status": "success", "payment_entry": payment_entry.name}
# 		else:
# 			frappe.throw("Amount Recevied from this Loan")
# 	except Exception as e:
# 		return {"status": "error", "message": str(e)}

# @frappe.whitelist()
# def create_pay_payment_entry(loan_name):
# 	try:
# 		loan = frappe.get_doc("Unsecured Loan", loan_name)  # Assuming your Doctype is 'Unsecured Loan'
# 		# Fetch Business Partner details
# 		business_partner = frappe.get_value("Business Partner", loan.lender, ["supplier", "account"], as_dict=True)
# 		if not business_partner or not business_partner.get("supplier") or not business_partner.get("account"):
# 			frappe.throw("Business Partner details are missing.")
# 		for i in loan.repayment_schedule:
# 			if i.gl_entry_created:
# 				continue
# 			# Create Payment Entry
# 			payment_entry = frappe.get_doc({
# 				"doctype": "Payment Entry",
# 				"payment_type": "Pay",
# 				"party_type": "Supplier",
# 				"party": business_partner.get("supplier"),
# 				"posting_date": frappe.utils.today(),
# 				"paid_amount": i.total_payment,
# 				"received_amount":i.total_payment,
# 				"company": loan.company,
# 				"cost_center": loan.cost_center,
# 				"mode_of_payment": "Cash",
# 				"paid_from": loan.principal_gl_account,
# 				"paid_to": business_partner.get("account"),
# 				"custom_unsecured_loan":loan.name
# 				})
# 			payment_entry.insert(ignore_permissions=True)
# 			payment_entry.submit()
# 			i.gl_entry_created = 1
# 		loan.save()
# 		return {"status": "success", "payment_entry": payment_entry.name}
# 	except Exception as e:
# 		return {"status": "error", "message": str(e)}





