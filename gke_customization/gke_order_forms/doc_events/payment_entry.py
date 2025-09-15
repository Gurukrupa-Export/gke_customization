import frappe
from datetime import datetime

def on_update_after_submit(self, method):
    if not getattr(self, "_in_update_after_submit", False):  # Check for the flag
        self._in_update_after_submit = True  # Set the flag to prevent recursion
        
        invoice_branchs = []
        for i in self.references:
            branch = frappe.db.get_value(i.reference_doctype, i.reference_name, 'branch')
            invoice_branchs.append(branch)
        if len(set(invoice_branchs)) > 1:
            frappe.throw("Multiple Branches of invoice in reconciliation")
        
        self.append("deductions", 
                    {
                        "branch": list(set(invoice_branchs))[0],
                        "account": "Inter Branch Clearing Account - GEPL",
                        "amount": self.paid_amount
                    }
                    )
        self.append("deductions", 
                    {
                        "branch": self.branch,
                        "account": self.paid_to,
                        "amount": self.paid_amount*-1
                    }
                    )
        self.save(ignore_permissions=True)
        self._in_update_after_submit = False

        if self.payment_type == 'Receive':
            create_gl_entries(self)

def create_gl_entries(self):
    gl_entries = []
    # ho
    gl_entries.append({
        'posting_date': self.posting_date,
        'account': self.deductions[0].account, 
        'debit': 0,
        'credit': self.deductions[0].amount,
        'party_type': self.party_type,
        'party': self.party,
        # 'cost_center': self.deductions[0].cost_center,
        'voucher_type': 'Payment Entry',
        'voucher_no': self.name,
        'branch': self.deductions[1].branch,
    })
    # ho
    gl_entries.append({
        'posting_date': self.posting_date,
        'account': self.paid_from, 
        'debit': self.deductions[0].amount,
        'credit': 0,
        'party_type': self.party_type,
        'party': self.party,
        # 'cost_center': self.deductions[0].cost_center,
        'voucher_type': 'Payment Entry',
        'voucher_no': self.name,
        'branch': self.deductions[1].branch,
    })

    # ch
    gl_entries.append({
        'posting_date': self.posting_date,
        'account': self.deductions[0].account,
        'debit': self.deductions[0].amount,
        'credit': 0,
        'party_type': self.party_type,
        'party': self.party,
        # 'cost_center': self.deductions[1].cost_center,
        'voucher_type': 'Payment Entry',
        'voucher_no': self.name,
        'branch': self.deductions[0].branch,
    })

    # ch
    for j in self.references:
        gl_entries.append({
            'posting_date': self.posting_date,
            'account': self.paid_from,
            'debit': 0,
            'credit': j.allocated_amount,
            'party_type': self.party_type,
            'party': self.party,
            # 'cost_center': self.deductions[0].cost_center,
            'against_voucher_type':j.reference_doctype,
            'against_voucher':j.reference_name,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
            'branch': self.deductions[0].branch,
        })

# 	# Insert GL Entries
    for entry in gl_entries:
        gl_entry = frappe.get_doc({
            'doctype': 'GL Entry',
            **entry
        })
        gl_entry.insert(ignore_permissions=True)
        gl_entry.submit()
        frappe.flags.ignore_permissions = False




# def on_submit(self,method):
#     calculation_for_shareholder(self)

# def calculation_for_shareholder(self):
# 	if self.party_type == 'Shareholder':
# 		Shareholder = frappe.get_doc("Shareholder",{"name":self.party,"custom_activate_interest_calculation":1})
# 		if self.payment_type == 'Receive':
# 			shareholder_table = Shareholder.custom_shareholder_table
# 			amount = float(shareholder_table[-1].amount) + float(self.paid_amount)
# 			interest_rate = Shareholder.custom_interest_rate
# 			duration = Shareholder.custom_duration
# 			final_amount = ((float(amount)*float(interest_rate))/100)/float(duration)
# 			shareholder_table_ = Shareholder.append("custom_shareholder_table", {})
# 			shareholder_table_.date = self.posting_date
# 			shareholder_table_.amount = amount
# 			shareholder_table_.interest_rate = interest_rate
# 			shareholder_table_.duration = duration
# 			shareholder_table_.interest = final_amount
# 			shareholder_table_.plus_amount = float(self.paid_amount)
# 			Shareholder.custom_final_amount = amount
# 			# Shareholder.save()
# 		else:
# 			shareholder_table = Shareholder.custom_shareholder_table
# 			amount = float(shareholder_table[-1].amount) - float(self.paid_amount)
# 			interest_rate = Shareholder.custom_interest_rate
# 			duration = Shareholder.custom_duration
# 			final_amount = ((float(amount)*float(interest_rate))/100)/float(duration)
# 			shareholder_table_ = Shareholder.append("custom_shareholder_table", {})
# 			shareholder_table_.date = self.posting_date
# 			shareholder_table_.amount = amount
# 			shareholder_table_.interest_rate = interest_rate
# 			shareholder_table_.duration = duration
# 			shareholder_table_.interest = final_amount
# 			shareholder_table_.minus_amount = float(self.paid_amount)
# 			Shareholder.custom_final_amount = amount
		
# 		if len(Shareholder.custom_shareholder_table) > 0 and Shareholder.custom_activate_interest_calculation == 1:
# 			calculate_interest_with_days(Shareholder)
# 		Shareholder.save()

# def calculate_interest_with_days(Shareholder):
# 	# with calculating days
# 	if len(Shareholder.custom_shareholder_table)==1:
# 		Shareholder.custom_total_interest_amount = Shareholder.custom_shareholder_table[0].interest
# 	else:
# 		for entry in Shareholder.custom_shareholder_table:
# 			entry.date = datetime.strptime(str(entry.date), "%Y-%m-%d")

# 		total_interest_amount = 0
# 		for i in range(len(Shareholder.custom_shareholder_table) - 1):
# 			current_date = Shareholder.custom_shareholder_table[i].date
# 			next_date = Shareholder.custom_shareholder_table[i + 1].date
# 			interest = Shareholder.custom_shareholder_table[i].interest
# 			days_between = (next_date - current_date).days
# 			total_interest_amount += days_between * interest
# 		Shareholder.custom_total_interest_amount = total_interest_amount

import frappe
import erpnext.accounts.doctype.payment_entry.payment_entry as pe_module
import erpnext.accounts.party as party_module

# def skip_party_account_check(self):
#     pass  # no validation = bypassed

# party_module.validate_account_party_type = skip_party_account_check
def on_submit(self, method):
    if self.custom_unsecured_loan and self.payment_type == 'Receive':
        bussiness_patner = frappe.db.get_value("Unsecured Loan",self.custom_unsecured_loan,"lender")
        unsecured_laon_account = frappe.db.sql(f"""select unsecured_loan_account from `tabLoan Accounts` where parent = '{bussiness_patner}' and company = '{self.company}'""",as_dict=1)
        if not unsecured_laon_account:
            frappe.throw("Unsecured Loan account is not available for this Company")

        gl_entries = []
    
        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': self.paid_from, 
            'debit': self.paid_amount,
            'debit_in_account_currency': self.paid_amount,
            'debit_in_transaction_currency': self.paid_amount,
            'credit': 0,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': unsecured_laon_account[0]['unsecured_loan_account'],
            'debit': 0,
            'credit': self.paid_amount,
            'credit_in_account_currency': self.paid_amount,
            'credit_in_transaction_currency': self.paid_amount,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        for entry in gl_entries:
            gl_entry = frappe.get_doc({
                'doctype': 'GL Entry',
                **entry
            })
            gl_entry.insert(ignore_permissions=True)
            gl_entry.submit()
            frappe.flags.ignore_permissions = False
        frappe.msgprint("Done")

    if self.custom_unsecured_loan and self.payment_type == 'Pay':
        bussiness_patner = frappe.db.get_value("Unsecured Loan",self.custom_unsecured_loan,"lender")
        unsecured_laon_account = frappe.db.sql(f"""select unsecured_loan_account from `tabLoan Accounts` where parent = '{bussiness_patner}' and company = '{self.company}'""",as_dict=1)
        if not unsecured_laon_account:
            frappe.throw("Unsecured Loan account is not available for this Company")

        gl_entries = []
    
        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': self.paid_to, 
            'debit': 0,
            'credit': self.paid_amount,
            'credit_in_account_currency': self.paid_amount,
            'credit_in_transaction_currency': self.paid_amount,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': unsecured_laon_account[0]['unsecured_loan_account'], 
            'debit': self.paid_amount,
            'debit_in_account_currency': self.paid_amount,
            'debit_in_transaction_currency': self.paid_amount,
            'credit': 0,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        for entry in gl_entries:
            gl_entry = frappe.get_doc({
                'doctype': 'GL Entry',
                **entry
            })
            gl_entry.insert(ignore_permissions=True)
            gl_entry.submit()
            frappe.flags.ignore_permissions = False

    if self.custom_secured_loan and self.payment_type == 'Receive':
        bussiness_patner = frappe.db.get_value("Secured Loan",self.custom_secured_loan,"lender")
        secured_laon_account = frappe.db.sql(f"""select secured_loan_account from `tabLoan Accounts` where parent = '{bussiness_patner}' and company = '{self.company}'""",as_dict=1)
        if not secured_laon_account:
            frappe.throw("Secured Loan account is not available for this Company")
        gl_entries = []
    
        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': self.paid_from, 
            'debit': self.paid_amount,
            'debit_in_account_currency': self.paid_amount,
            'debit_in_transaction_currency': self.paid_amount,
            'credit': 0,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': secured_laon_account[0]['secured_loan_account'],
            'debit': 0,
            'credit': self.paid_amount,
            'credit_in_account_currency': self.paid_amount,
            'credit_in_transaction_currency': self.paid_amount,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        for entry in gl_entries:
            gl_entry = frappe.get_doc({
                'doctype': 'GL Entry',
                **entry
            })
            gl_entry.insert(ignore_permissions=True)
            gl_entry.submit()
            frappe.flags.ignore_permissions = False

    if self.custom_secured_loan and self.payment_type == 'Pay':
        bussiness_patner = frappe.db.get_value("Secured Loan",self.custom_secured_loan,"lender")
        secured_laon_account = frappe.db.sql(f"""select secured_loan_account from `tabLoan Accounts` where parent = '{bussiness_patner}' and company = '{self.company}'""",as_dict=1)
        if not secured_laon_account:
            frappe.throw("Secured Loan account is not available for this Company")
        gl_entries = []
    
        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': self.paid_to, 
            'debit': 0,
            'credit': self.paid_amount,
            'credit_in_account_currency': self.paid_amount,
            'credit_in_transaction_currency': self.paid_amount,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        gl_entries.append({
            'company':self.company,
            'posting_date': self.posting_date,
            'account': secured_laon_account[0]['secured_loan_account'],
            'debit': self.paid_amount,
            'debit_in_account_currency': self.paid_amount,
            'debit_in_transaction_currency': self.paid_amount,
            'credit': 0,
            'party_type': self.party_type,
            'party': self.party,
            'voucher_type': 'Payment Entry',
            'voucher_no': self.name,
        })

        for entry in gl_entries:
            gl_entry = frappe.get_doc({
                'doctype': 'GL Entry',
                **entry
            })
            gl_entry.insert(ignore_permissions=True)
            gl_entry.submit()
            frappe.flags.ignore_permissions = False


