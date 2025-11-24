# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate,nowdate

class PartnerCapital(Document):
	def validate(self):
		if not self.loan_amount or not self.interest_rate:
			frappe.throw("Please ensure loan amount, interest rate, and repayment period are provided.")

		# # Set first row if empty
		if not self.partner_capital_repayment_schedule:
			self.append("partner_capital_repayment_schedule", {
				"payment_type": "Receive",
				"payment_date": self.date,
				"number_of_days": 0,
				"total_payment": self.loan_amount,
				"balance_loan_amount": self.loan_amount,
				"loan_amount": self.loan_amount,
				"interest_rate": self.interest_rate
			})

		total_interest = 0
		total_amount = 0
		for i in range(1, len(self.partner_capital_repayment_schedule)):
			prev_row = self.partner_capital_repayment_schedule[i - 1]
			row = self.partner_capital_repayment_schedule[i]

			if not row.payment_date or not prev_row.payment_date:
				continue

			prev_date = getdate(prev_row.payment_date)
			curr_date = getdate(row.payment_date)
			days = (curr_date - prev_date).days
			row.number_of_days = days

			prev_balance = prev_row.balance_loan_amount or 0
			interest = (prev_balance * self.interest_rate / 100) * (days / 365)
			row.interest_amount = interest
			row.interest_rate = self.interest_rate

			row.total_payment = row.total_payment or 0
			row.repay_loan_amount = row.repay_loan_amount or 0

			if row.payment_type == "Pay":
				row.balance_loan_amount = prev_balance - row.total_payment
			elif row.payment_type == "Receive":
				row.repay_loan_amount = 0
				row.balance_loan_amount = prev_balance + row.total_payment
			
			total_interest = total_interest + row.interest_amount
			total_amount = row.balance_loan_amount

		self.total_interest = total_interest
		self.total_amount = total_amount

	def on_update_after_submit(self):
		total_interest = 0
		total_amount = 0
		for i in range(1, len(self.partner_capital_repayment_schedule)):
			prev_row = self.partner_capital_repayment_schedule[i - 1]
			row = self.partner_capital_repayment_schedule[i]

			if not row.payment_date or not prev_row.payment_date:
				continue

			prev_date = getdate(prev_row.payment_date)
			curr_date = getdate(row.payment_date)
			days = (curr_date - prev_date).days
			row.number_of_days = days

			prev_balance = prev_row.balance_loan_amount or 0
			interest = (prev_balance * self.interest_rate / 100) * (days / 365)
			row.interest_amount = interest
			row.interest_rate = self.interest_rate

			row.total_payment = row.total_payment or 0
			row.repay_loan_amount = row.repay_loan_amount or 0

			if row.payment_type == "Pay":
				row.balance_loan_amount = prev_balance - row.total_payment
			elif row.payment_type == "Receive":
				row.repay_loan_amount = 0
				row.balance_loan_amount = prev_balance + row.total_payment
			
			total_interest = total_interest + row.interest_amount
			total_amount = row.balance_loan_amount

		self.total_interest = total_interest
		self.total_amount = total_amount
		frappe.db.set_value("Partner Capital",self.name,"total_interest",total_interest)
		frappe.db.set_value("Partner Capital",self.name,"total_amount",total_amount)


@frappe.whitelist()
def create_journal_entry(name, lender, loan_amount, company):
  
	bp = frappe.get_doc("Business Partner", lender)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = frappe.utils.nowdate()

	# bp_sup = frappe.get_doc("Supplier", bp.supplier)

	je.custom_partner_capital = name
	pc_account = frappe.db.sql(f"select partner_capital_account from `tabLoan Accounts` where parent = '{lender}'",as_dict=1)
	total_interest = frappe.db.get_value("Partner Capital",name,"total_interest")
	customer_account = frappe.db.sql(f"select account from `tabParty Account` where parent = '{bp.customer}' and company = '{company}'",as_dict=1)
	je.append("accounts", {
		"account": pc_account[0]['partner_capital_account'],
		"debit_in_account_currency": total_interest,
	})
	je.append("accounts", {
                "account": customer_account[0]['account'],
                "credit_in_account_currency": total_interest,
                "party_type": "Customer",
				"party": bp.customer
            })
	je.insert(ignore_permissions=True)
	frappe.db.commit()

	return je.name



from frappe.utils import getdate, nowdate

@frappe.whitelist()
def get_total_interest_upto_today(name):
    doc = frappe.get_doc("Partner Capital", name)
    total_interest = 0
    total_amount = 0
    current_date = getdate(nowdate())
    schedule = doc.partner_capital_repayment_schedule

    # Calculate interest between payment rows
    for i in range(1, len(schedule)):
        prev_row = schedule[i - 1]
        row = schedule[i]

        if not prev_row.payment_date:
            continue

        prev_date = getdate(prev_row.payment_date)
        curr_date = getdate(row.payment_date) if row.payment_date else current_date

        days = (curr_date - prev_date).days
        if days < 0:
            days = 0

        # Interest for current interval
        prev_balance = prev_row.balance_loan_amount or 0
        interest = (prev_balance * doc.interest_rate / 100) * (days / 365)

        row.number_of_days = days
        row.interest_amount = interest
        row.interest_rate = doc.interest_rate

        row.total_payment = row.total_payment or 0
        row.repay_loan_amount = row.repay_loan_amount or 0

        if row.payment_type == "Pay":
            row.balance_loan_amount = prev_balance - row.total_payment
        elif row.payment_type == "Receive":
            row.repay_loan_amount = 0
            row.balance_loan_amount = prev_balance + row.total_payment

        total_interest += interest
        total_amount = row.balance_loan_amount

    # Calculate interest for last interval (last payment to current date)
    if len(schedule) > 0:
        last_row = schedule[-1]
        if last_row.payment_date:
            last_payment_date = getdate(last_row.payment_date)
            if current_date > last_payment_date:
                days = (current_date - last_payment_date).days
                prev_balance = last_row.balance_loan_amount or 0
                interest = (prev_balance * doc.interest_rate / 100) * (days / 365)

                total_interest += interest

    frappe.db.set_value("Partner Capital", name, "total_interest", total_interest)
    frappe.db.set_value("Partner Capital", name, "total_amount", total_amount)

    return {"total_interest": total_interest, "total_amount": total_amount}
