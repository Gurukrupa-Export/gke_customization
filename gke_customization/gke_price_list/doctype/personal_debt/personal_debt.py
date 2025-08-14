# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate 
import frappe



class PersonalDebt(Document):	
	def before_save(self):
		
		if not (self.start_date and self.end_date and self.loan_amount and self.interest_rate):
			frappe.throw("Start Date, End Date, Loan Amount, and Interest Rate are required.")

		start = getdate(self.start_date)
		end = getdate(self.end_date)
		
		total_months=self.tenure
		P = self.loan_amount
		R = (self.interest_rate / 12) / 100  
		
		N = total_months

		emi=self.emi

		# outstanding = self.outstanding
		# # interest=R
		# due_date = start
		# # first_row = self.repayment_schedule[0]
		# # outstanding = first_row.outstanding
		# if not self.repayment_schedule:
		# 	for i in range(N):
				
		# 		if i==0:
					
		# 			# outstanding = self.outstanding
		# 			interest = round(P* R)
		# 			principal = (emi - interest)


		# 		else:
					
		# 			principal = (emi - interest)
		# 			outstanding = (outstanding - principal)
		# 		self.append("repayment_schedule", {
		# 			"due_date": due_date,
		# 			"emi_amount": emi,
		# 			"principal": principal, 
		# 			"interest": interest,
		# 			"outstanding": outstanding if outstanding > 0 else 0,
		# 			"payment_status": "Unpaid"
		# 		})
				
				
		# 		interest = round(outstanding * R)	
		# 		due_date += relativedelta(months=1)
	
	
		if not self.repayment_schedule or not self.repayment_schedule[0].outstanding:
			frappe.throw("Please enter the first row's Outstanding.")
		first_row = self.repayment_schedule[0]
		outstanding = round(first_row.outstanding, 2)
		due_date = getdate(self.start_date)

		# Clear repayment_schedule before regenerating
		self.set("repayment_schedule", [])

		for i in range(N):
			if i == 0:
				interest = round(P * R)
				principal = emi - interest
			else:
				principal = emi - interest
				outstanding = outstanding - principal

			self.append("repayment_schedule", {
				"due_date": due_date,
				"emi_amount": emi,
				"principal": principal,
				"interest": interest,
				"outstanding": outstanding if outstanding > 0 else 0,
				"payment_status": "Unpaid"
			})

			interest = round(outstanding * R)
			due_date += relativedelta(months=1)
