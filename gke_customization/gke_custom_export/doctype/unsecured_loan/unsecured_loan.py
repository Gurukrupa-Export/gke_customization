# Copyright (c) 2024, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document
from datetime import datetime, timedelta

import frappe.utils


class UnsecuredLoan(Document):
    
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

		if self.workflow_state == 'Interest Accrual':
			create_gl_entry(self)





	# def validate(self, method=None):
	# 	loan_amount = self.loan_amount
	# 	interest_rate = self.interest_rate
	# 	repayment_period = self.repayment_period
	# 	loan_date = self.loan_date

	# 	if not loan_amount or not interest_rate or not repayment_period:
	# 		frappe.throw("Please ensure loan amount, interest rate, and repayment period are provided.")

	# 	# Calculate monthly interest
	# 	monthly_interest = (loan_amount * interest_rate) / (repayment_period * 100)
	# 	interest_rate = interest_rate / (repayment_period * 100)

	# 	# Optionally save the calculated value in a field if needed
	# 	self.monthly_interest = monthly_interest
	# 	month_emi = (loan_amount * interest_rate * (1 + interest_rate) ** repayment_period) / ((1 + interest_rate) ** repayment_period - 1)

	# 	if not loan_date:
	# 		frappe.throw("Please ensure payment date is provided.")

	# 	try:
	# 		# Check if loan_date is already a datetime.date object (without using isinstance)
	# 		if hasattr(loan_date, 'year') and hasattr(loan_date, 'month') and hasattr(loan_date, 'day'):
	# 			# This checks if loan_date is a datetime.date or datetime.datetime object
	# 			loan_date_obj = loan_date
	# 		else:
	# 			loan_date_obj = datetime.strptime(loan_date, '%Y-%m-%d').date()  # Convert string to date if it's a string
	# 	except ValueError:
	# 		frappe.throw("Payment date must be in YYYY-MM-DD format.")

	# 	self.repayment_schedule = []
	# 	balance_loan_amount = loan_amount
	# 	principal_amount = loan_amount  # Initialize principal amount with the loan amount

	# 	for month in range(1, repayment_period + 1):
	# 		total_payment = month_emi
	# 		interest_amount = monthly_interest
	# 		balance_loan_amount -= total_payment
	# 		balance_loan_amount = max(0, balance_loan_amount)

	# 		# For the first row, principal amount is the loan amount
	# 		# For subsequent rows, principal amount is reduced by total payment
	# 		if month == 1:
	# 			current_principal = loan_amount
	# 		else:
	# 			current_principal -= total_payment

	# 		# Calculate due_date manually by adjusting month and year
	# 		new_month = loan_date_obj.month + month
	# 		new_year = loan_date_obj.year + (new_month - 1) // 12
	# 		new_month = (new_month - 1) % 12 + 1
	# 		payment_date = loan_date_obj.replace(year=new_year, month=new_month)

	# 		# Add a new row to the repayment schedule child table
	# 		self.append("repayment_schedule", {
	# 			"total_payment": total_payment,
	# 			"balance_loan_amount": balance_loan_amount,
	# 			"interest_amount": interest_amount,
	# 			"principal_amount": current_principal,  # Set the principal amount here
	# 			"payment_date": payment_date.strftime('%Y-%m-%d')  # Format as YYYY-MM-DD
	# 		})

	# 	self.create_gl_entries()

	# def create_gl_entries(self):
	# 	"""
	# 	Creates GL Entries for each row in the repayment_schedule child table.
	# 	Ensures proper validation and workflow state checks.
	# 	"""
	# 	# Validate mandatory fields
	# 	if not self.company:
	# 		frappe.throw("Company is mandatory for creating GL Entry.")
		
	# 	if not self.loan_amount or self.loan_amount <= 0:
	# 		frappe.throw("Loan amount must be greater than zero.")
		
	# 	# Check if the workflow state is 'Completion'
	# 	if self.workflow_state == 'Completion':
	# 		if not self.repayment_schedule:
	# 			frappe.throw("Repayment schedule is missing in the loan document.")

	# 		for schedule_row in self.repayment_schedule:
	# 			if not schedule_row.total_payment or schedule_row.total_payment <= 0:
	# 				frappe.throw(f"Invalid total_payment value in repayment schedule row: {schedule_row.idx}")
				
	# 			# Create a debit GL entry for the schedule row
	# 			debit_entry = frappe.get_doc({
	# 				"doctype": "GL Entry",
	# 				"account": "FACTORY - 7291 - HDFC - GEPL",
	# 				"posting_date": self.loan_date,
	# 				"debit": schedule_row.total_payment,
	# 				"debit_in_account_currency": schedule_row.total_payment,
	# 				"debit_in_transaction_currency": schedule_row.total_payment,
	# 				"transaction_currency": "INR",
	# 				"company": self.company,
	# 				"voucher_type": "Unsecured Loan",
	# 				"voucher_no": self.name,
	# 				"party":self.name,
	# 				"party_type":"Supplier",
	# 				"remarks": f"Debit GL entry for repayment schedule row {schedule_row.idx}",
	# 			})
	# 			debit_entry.insert()
				
	# 			# Create a credit GL entry for the schedule row
	# 			credit_entry = frappe.get_doc({
	# 				"doctype": "GL Entry",
	# 				"account": "Unsecured Loan from Related Parties - GEPL",  # Replace with the actual liability account
	# 				"posting_date": self.loan_date,
	# 				"credit": schedule_row.total_payment,
	# 				"credit_in_account_currency": schedule_row.total_payment,
	# 				"credit_in_transaction_currency": schedule_row.total_payment,
	# 				"transaction_currency": "INR",
	# 				"company": self.company,
	# 				"voucher_type": "Unsecured Loan",
	# 				"voucher_no": self.name,
	# 				"party":self.name,
	# 				"party_type":"Supplier",
	# 				"remarks": f"Credit GL entry for repayment schedule row {schedule_row.idx}",
	# 			})
	# 			credit_entry.insert()
	# 		frappe.db.commit()

def create_gl_entry(self):
	if not self.parent_gl_entry_created:
		credit_entry = frappe.get_doc({
					"doctype": "GL Entry",
					"account": "Unsecured Loan from Related Parties - GEPL",
					"posting_date": self.loan_date,
					"credit": self.loan_amount,
					"credit_in_account_currency": self.loan_amount,
					"credit_in_transaction_currency": self.loan_amount,
					"company": self.company,
					"voucher_type": "Unsecured Loan",
					"voucher_no": self.name,
					"party_type":"Supplier",
					"party":self.name,
				})
		credit_entry.insert()
		frappe.db.commit()
		self.parent_gl_entry_created = 1


	for schedule_row in self.repayment_schedule:
		if not schedule_row.gl_entry_created:
			debit_entry = frappe.get_doc({
					"doctype": "GL Entry",
					"account": "FACTORY - 7291 - HDFC - GEPL",
					"posting_date": schedule_row.payment_date,
					"debit": schedule_row.total_payment,
					"debit_in_account_currency": schedule_row.total_payment,
					"debit_in_transaction_currency": schedule_row.total_payment,
					"company": self.company,
					"voucher_type": "Unsecured Loan",
					"voucher_no": self.name,
					"party_type":"Supplier",
					"party":self.name,
					"remarks": f"Debit GL entry for repayment schedule row {schedule_row.idx}",
				})
			debit_entry.insert()
			frappe.db.commit()
			schedule_row.gl_entry_created = 1

	# return


