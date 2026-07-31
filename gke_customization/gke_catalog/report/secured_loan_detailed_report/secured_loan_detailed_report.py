import frappe
from frappe.utils import flt, getdate
from datetime import timedelta, date

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []
    total_interest = 0
    last_balances = {}

    loan_conditions = ""
    if filters.get("name"):
        loan_conditions += " AND sl.name = %(name)s"
    if filters.get("lender"):
        loan_conditions += " AND sl.lender = %(lender)s"
    if filters.get("company"):
        loan_conditions += " AND sl.company = %(company)s"
    if filters.get("branch"):
        loan_conditions += " AND sl.branch = %(branch)s"

    loans_query = f"""
        SELECT sl.name, sl.company, sl.branch, sl.lender,
               bp.business_partner, sl.loan_amount, sl.interest_rate,
               sl.start_date, sl.end_date, sl.outstanding_amount
        FROM `tabSecured Loan` sl
        LEFT JOIN `tabBusiness Partner` bp ON sl.lender = bp.name
        WHERE sl.docstatus != 2 {loan_conditions}
        ORDER BY sl.start_date DESC
    """
    loans = frappe.db.sql(loans_query, filters, as_dict=True)

    for loan in loans:
        loan_balance = flt(loan.loan_amount)

        repayments = frappe.db.sql(
            """
            SELECT name, due_date, emi_amount, principal_amount, interest_rate, 
                   outstanding_amount, payment_status, payment_date, payment_entry_created
            FROM `tabSecured Loan Repayment Schedule`
            WHERE parent = %s
            ORDER BY due_date ASC
            """,
            loan.name,
            as_dict=True,
        )

        n = len(repayments)
        for i in range(n):
            r = repayments[i]
            txn_date = getdate(r.payment_date) if r.payment_date else getdate(r.due_date)

            if r.payment_status == "Paid":
                loan_balance -= flt(r.principal_amount)

            if i + 1 < n:
                period_end = getdate(repayments[i + 1]['due_date']) - timedelta(days=1)
            else:
                period_end = txn_date

            days = (period_end - txn_date).days + 1 if (period_end and txn_date) else 0
            interest_amount = flt(loan_balance) * flt(loan.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount

            data.append([
                loan.name,
                loan.company,
                loan.branch,
                loan.lender,
                loan.business_partner,    # Display name from Business Partner
                loan_balance,
                txn_date,
                period_end,
                days,
                loan.interest_rate,
                interest_amount,
                r.payment_status,
                flt(r.emi_amount),
                r.payment_entry_created
            ])

        last_balances[loan.name] = loan_balance

    total_final_balance = sum(last_balances.values()) if last_balances else 0
    if total_final_balance or total_interest:
        footer_row = [""] * 5 + [total_final_balance] + [""] * 4 + [total_interest] + [""] * 3
        data.append(footer_row)

    return columns, data

def get_columns():
    return [
        {"label": "Secured Loan ID", "fieldname": "secured_loan_id", "fieldtype": "Link", "options": "Secured Loan", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 290},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 140},
        {"label": "Lender", "fieldname": "lender", "fieldtype": "Data", "width": 150},
        {"label": "Lender Name", "fieldname": "business_partner", "fieldtype": "Data", "width": 230},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 150},
        {"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 150},
        {"label": "Days", "fieldname": "days", "fieldtype": "Int", "width": 60},
        {"label": "Interest (%)", "fieldname": "interest_rate", "fieldtype": "Percent", "width": 80},
        {"label": "Interest Amount", "fieldname": "interest_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Payment Status", "fieldname": "payment_status", "fieldtype": "Data", "width": 100},
        {"label": "EMI Amount", "fieldname": "emi_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Payment Entry Created", "fieldname": "payment_entry_created", "fieldtype": "Check", "width": 100}
    ]

def get_fy_end(start_date):
    year = start_date.year
    if start_date.month > 3:
        year += 1
    return getdate(f"{year}-03-31")
