import frappe

def on_submit(self,method):
    for i in self.accounts:
        if i.party_type == 'Shareholder' and self.is_opening == 'Yes':
            calculation_for_shareholder(self,i)

def calculation_for_shareholder(self,row):
	Shareholder = frappe.get_doc("Shareholder",row.party)
	if Shareholder.custom_activate_interest_calculation:
		Shareholder.custom_amount = row.credit_in_account_currency
		Shareholder.custom_final_amount = row.credit_in_account_currency
		shareholder_table = Shareholder.append("custom_shareholder_table", {})
		shareholder_table.date = self.posting_date
		shareholder_table.amount = row.credit_in_account_currency
		shareholder_table.interest_rate = Shareholder.custom_interest_rate
		shareholder_table.duration = Shareholder.custom_duration
		shareholder_table.interest = ((float(row.credit_in_account_currency) * float(Shareholder.custom_interest_rate))/100)/float(Shareholder.custom_duration)

		total_ = 0
		for j in Shareholder.custom_shareholder_table:
			total_ += j.interest
		Shareholder.custom_total_interest_amount = total_
		Shareholder.save()