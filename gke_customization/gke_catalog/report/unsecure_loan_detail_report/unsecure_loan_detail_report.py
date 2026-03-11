import frappe
from frappe.utils import flt, getdate
from datetime import timedelta, date

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []
    total_interest = 0

    # Loan filters
    loan_conditions = ""
    if filters.get("name"):
        loan_conditions += " AND name = %(name)s"
    if filters.get("lender"):
        loan_conditions += " AND lender = %(lender)s"
    if filters.get("company"):
        loan_conditions += " AND company = %(company)s"
    if filters.get("branch"):
        loan_conditions += " AND branch = %(branch)s"

    # Fetch loans with all required fields
    loan_query = f"""
        SELECT name, lender, lender_name, loan_amount, loan_date, interest_rate, company, branch
        FROM `tabUnsecured Loan`
        WHERE docstatus != 2 {loan_conditions}
        ORDER BY loan_date DESC
    """
    loans = frappe.db.sql(loan_query, filters, as_dict=True)

    for loan in loans:
        # Get display names with better error handling
        # try:
        #     branch_display = ""
        #     if loan.get('branch'):
        #         branch_name = frappe.db.get_value("Branch", loan.branch, "branch_name")
        #         branch_display = branch_name if branch_name else loan.branch
        # except:
        #     branch_display = loan.branch or ""
        branch_display = loan.get('branch')
        company_display = loan.company or ""
        # lender_display = loan.lender_name or loan.lender or ""
        lender_display = loan.lender
        lender_name = frappe.db.get_value("Business Partner",loan.lender,"business_partner")
        # Get repayment schedule lines - only those with payment_type
        repayments = frappe.db.sql("""
            SELECT 
                name AS schedule_id,
                payment_date,
                payment_type,
                total_payment,
                payment_entry_created
            FROM `tabUnsecured Loan Repayment Schedule`
            WHERE parent = %s 
                AND payment_type IS NOT NULL 
                AND payment_type != ''
            ORDER BY payment_date ASC
        """, loan.name, as_dict=True)

        balance = flt(loan.loan_amount)
        initial_date = getdate(loan.loan_date)

        # Detect if there is a Receive entry on loan start date
        found_initial_receive = None
        for r in repayments:
            if r.payment_type == "Receive" and getdate(r.payment_date) == initial_date:
                found_initial_receive = r
                break

        tx_rows = []

        # Process repayment entries
        n = len(repayments)
        for i in range(n):
            r = repayments[i]
            txn_date = getdate(r.payment_date)

            # Period end calculation
            if i + 1 < n:
                period_end = getdate(repayments[i+1]['payment_date']) - timedelta(days=1)
            else:
                period_end = getdate(filters["to_date"]) if filters.get("to_date") else get_fy_end(txn_date)
                if not filters.get("to_date") and period_end > date.today():
                    period_end = get_fy_end(txn_date)

            days = (period_end - txn_date).days + 1

            # Balance update based on transaction type
            if r.payment_type == "Pay":
                balance -= flt(r.total_payment)
            elif r.payment_type == "Receive":
                # For receive, only add if it's not the initial loan amount
                if not (getdate(r.payment_date) == initial_date and flt(r.total_payment) == flt(loan.loan_amount)):
                    balance += flt(r.total_payment)

            # Interest calculation
            interest_amount = flt(balance) * flt(loan.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount

            tx_rows.append([
                loan.name,
                company_display,
                branch_display,
                lender_display,
                lender_name,
                balance,
                txn_date,
                period_end,
                days if days > 0 else 0,
                loan.interest_rate,
                interest_amount,
                r.payment_type,
                flt(r.total_payment),
                r.payment_entry_created
            ])

        data.extend(tx_rows)

    # Add footer for total interest
    if total_interest > 0:
        data.append(["", "", "", "", "", "", "", "", "", "**Total Interest**", total_interest, "", "", ""])
    
    return columns, data

def get_columns():
    return [
        {"label": "Loan ID", "fieldname": "loan_id", "fieldtype": "Link", "options": "Unsecured Loan", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 290},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Lender", "fieldname": "lender", "fieldtype": "Data", "width": 150},
        {"label": "Lender name", "fieldname": "lender_name", "fieldtype": "Data", "width": 150},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 150},
        {"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 150},
        {"label": "Days", "fieldname": "days", "fieldtype": "Int", "width": 60},
        {"label": "Interest (%)", "fieldname": "interest_rate", "fieldtype": "Percent", "width": 80},
        {"label": "Interest Amount", "fieldname": "interest_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Transaction Type", "fieldname": "payment_type", "fieldtype": "Data", "width": 100},
        {"label": "Total Payment", "fieldname": "total_payment", "fieldtype": "Currency", "width": 120},
        {"label": "PE Created", "fieldname": "pe_created", "fieldtype": "Check", "width": 100}
    ]

def get_fy_end(start_date):
    year = start_date.year
    if start_date.month > 3:
        year += 1
    return getdate(f"{year}-03-31")
