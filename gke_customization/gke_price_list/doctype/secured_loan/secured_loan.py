from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate  # ✅ important
import frappe

class SecuredLoan(Document):
    # def before_save(self):
    #     if not (self.start_date and self.end_date and self.loan_amount and self.interest_rate):
    #         frappe.throw("Start Date, End Date, Loan Amount, and Interest Rate are required.")

    #     # Convert string dates to datetime.date
    #     start = getdate(self.start_date)
    #     end = getdate(self.end_date)

    #     # Clear existing schedule
    #     self.secured_loan_repayment_schedule = []

    #     # Calculate total months
    #     total_months = (end.year - start.year) * 12 + (end.month - start.month) + 1

    #     P = self.loan_amount
    #     R = (self.interest_rate / 12) / 100  # monthly interest rate
    #     N = total_months

    #     if R == 0:
    #         emi = round(P / N, 2)
    #     else:
    #         emi = round(P * R * ((1 + R) ** N) / (((1 + R) ** N) - 1), 2)

    #     outstanding = P
    #     due_date = start

    #     for i in range(N):
    #         interest = round(outstanding * R, 2)
    #         principal = round(emi - interest, 2)
    #         outstanding = round(outstanding - principal, 2)

    #         self.append("secured_loan_repayment_schedule", {
    #             "due_date": due_date,
    #             "emi_amount": emi,
    #             "principal_amount": principal,
    #             "interest_rate": self.interest_rate,
    #             "outstanding_amount": outstanding if outstanding > 0 else 0,
    #             "payment_status": "Unpaid"
    #         })

    #         due_date += relativedelta(months=1)

    def on_submit(self):
        total_supllier_amount = 0
        if not self.secured_loan_supplier_details:
            frappe.throw("Add Deatils of Supplier")
        for i in self.secured_loan_supplier_details:
            total_supllier_amount += i.amount
        if self.loan_amount != total_supllier_amount:
            frappe.throw("Loan Amount and Supllier amount is not match")
            

@frappe.whitelist()
def add_row(name, lender, loan_amount, company):
  
    bp = frappe.get_doc("Business Partner", lender)

  
    je = frappe.new_doc("Journal Entry")
    je.company = company
    je.posting_date = frappe.utils.nowdate()

    # bp_sup = frappe.get_doc("Supplier", bp.supplier)

    je.custom_secure_loan = name
    sl_doc = frappe.get_doc("Secured Loan",name)
    for i in sl_doc.secured_loan_supplier_details:
        bp_sup = frappe.get_doc("Supplier", i.supplier)
        for row in bp_sup.accounts:
            if row.company == company:
                je.append("accounts", {
                    "account": row.account,
                    "debit_in_account_currency": i.amount or 0,
                    "party_type": "Supplier",
                    "party": i.supplier
                })
                
    for row in bp.loan_accounts:
        if row.company == company:
            je.append("accounts", {
                "account": row.secured_loan_account,
                "credit_in_account_currency": loan_amount or 0,
                # "party_type": "Customer",
                # "party": bp.customer
            })

   
    je.insert(ignore_permissions=True)
    frappe.db.commit()

    return je.name

