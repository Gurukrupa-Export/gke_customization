import frappe
from datetime import datetime

def on_submit(self,method):
    calculation_for_shareholder(self)

def calculation_for_shareholder(self):
	if self.party_type == 'Shareholder':
		Shareholder = frappe.get_doc("Shareholder",{"name":self.party,"custom_activate_interest_calculation":1})
		if self.payment_type == 'Receive':
			shareholder_table = Shareholder.custom_shareholder_table
			amount = float(shareholder_table[-1].amount) + float(self.paid_amount)
			interest_rate = Shareholder.custom_interest_rate
			duration = Shareholder.custom_duration
			final_amount = ((float(amount)*float(interest_rate))/100)/float(duration)
			shareholder_table_ = Shareholder.append("custom_shareholder_table", {})
			shareholder_table_.date = self.posting_date
			shareholder_table_.amount = amount
			shareholder_table_.interest_rate = interest_rate
			shareholder_table_.duration = duration
			shareholder_table_.interest = final_amount
			shareholder_table_.plus_amount = float(self.paid_amount)
			Shareholder.custom_final_amount = amount
			# Shareholder.save()
		else:
			shareholder_table = Shareholder.custom_shareholder_table
			amount = float(shareholder_table[-1].amount) - float(self.paid_amount)
			interest_rate = Shareholder.custom_interest_rate
			duration = Shareholder.custom_duration
			final_amount = ((float(amount)*float(interest_rate))/100)/float(duration)
			shareholder_table_ = Shareholder.append("custom_shareholder_table", {})
			shareholder_table_.date = self.posting_date
			shareholder_table_.amount = amount
			shareholder_table_.interest_rate = interest_rate
			shareholder_table_.duration = duration
			shareholder_table_.interest = final_amount
			shareholder_table_.minus_amount = float(self.paid_amount)
			Shareholder.custom_final_amount = amount
		
		if len(Shareholder.custom_shareholder_table) > 0 and Shareholder.custom_activate_interest_calculation == 1:
			calculate_interest_with_days(Shareholder)
		Shareholder.save()

def calculate_interest_with_days(Shareholder):
	# with calculating days
	if len(Shareholder.custom_shareholder_table)==1:
		Shareholder.custom_total_interest_amount = Shareholder.custom_shareholder_table[0].interest
	else:
		for entry in Shareholder.custom_shareholder_table:
			entry.date = datetime.strptime(str(entry.date), "%Y-%m-%d")

		total_interest_amount = 0
		for i in range(len(Shareholder.custom_shareholder_table) - 1):
			current_date = Shareholder.custom_shareholder_table[i].date
			next_date = Shareholder.custom_shareholder_table[i + 1].date
			interest = Shareholder.custom_shareholder_table[i].interest
			days_between = (next_date - current_date).days
			total_interest_amount += days_between * interest
		Shareholder.custom_total_interest_amount = total_interest_amount