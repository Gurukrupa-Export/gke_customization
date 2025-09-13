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
        try:
            branch_display = ""
            if loan.get('branch'):
                branch_name = frappe.db.get_value("Branch", loan.branch, "branch_name")
                branch_display = branch_name if branch_name else loan.branch
        except:
            branch_display = loan.branch or ""

        company_display = loan.company or ""
        lender_display = loan.lender_name or loan.lender or ""

        # Get repayment schedule lines with linked Payment Entry + payment_entry_created flag
        repayments = frappe.db.sql("""
            SELECT 
                uls.name AS schedule_id,
                uls.payment_date,
                pe.payment_type,  
                CASE 
                    WHEN pe.payment_type = 'Receive' THEN pe.received_amount
                    WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
                    ELSE 0
                END AS total_payment,
                pe.name AS payment_entry_id,
                uls.payment_entry_created
            FROM `tabUnsecured Loan Repayment Schedule` uls
            LEFT JOIN (
                SELECT 
                    name,
                    payment_type,
                    received_amount,
                    paid_amount,
                    posting_date,
                    custom_unsecured_loan_repayment_schedule
                FROM `tabPayment Entry`
                WHERE custom_unsecured_loan_repayment_schedule IS NOT NULL
                    AND docstatus = 1
                ORDER BY posting_date ASC
            ) pe
                ON pe.custom_unsecured_loan_repayment_schedule = uls.name
            WHERE uls.parent = %s
            ORDER BY uls.payment_date ASC
        """, loan.name, as_dict=True)

        # Keep rows only with a transaction type
        repayments = [r for r in repayments if r.payment_type]

        balance = flt(loan.loan_amount)
        initial_date = getdate(loan.loan_date)

        # Detect if there is a PE Receive on loan start date
        found_initial_pe = None
        for r in repayments:
            if r.payment_type == "Receive" and getdate(r.payment_date) == initial_date and r.payment_entry_id:
                found_initial_pe = r
                break

        tx_rows = []

        # Synthetic initial receive entry if no PE exists on start date
        if not found_initial_pe:
            if repayments:
                next_tx_date = getdate(repayments[0]['payment_date']) - timedelta(days=1)
            elif filters.get("to_date"):
                next_tx_date = getdate(filters["to_date"])
            else:
                next_tx_date = get_fy_end(initial_date)

            today = date.today()
            if not filters.get("to_date") and next_tx_date > today:
                next_tx_date = get_fy_end(initial_date)

            days = (next_tx_date - initial_date).days + 1
            interest_amount = flt(balance) * flt(loan.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount

            tx_rows.append([
                loan.name, 
                company_display,
                branch_display,
                lender_display,
                balance, 
                initial_date, 
                next_tx_date,
                days, 
                loan.interest_rate, 
                interest_amount,
                "Receive", 
                flt(loan.loan_amount),
                0
            ])
            start_idx = 0
        else:
            start_idx = 0

        # Process repayment entries
        n = len(repayments)
        for i in range(start_idx, n):
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

            # Balance update — skip double-add for first real PE Receive
            if not (i == 0 and found_initial_pe):
                if r.payment_type == "Pay":
                    balance -= flt(r.total_payment)
                elif r.payment_type == "Receive":
                    balance += flt(r.total_payment)

            # Interest calculation
            interest_amount = flt(balance) * flt(loan.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount

            tx_rows.append([
                loan.name,
                company_display,
                branch_display,
                lender_display,
                balance,
                txn_date,
                period_end,
                days if days > 0 else 0,
                loan.interest_rate,
                interest_amount,
                r.payment_type,
                flt(r.total_payment),
                r.payment_entry_created or 0
            ])

        data.extend(tx_rows)

    # Add footer for total interest
    if total_interest > 0:
        data.append(["", "", "", "", "", "", "", "", "**Total Interest**", total_interest, "", "", ""])
    
    return columns, data


def get_columns():
    return [
        {"label": "Loan ID", "fieldname": "loan_id", "fieldtype": "Link", "options": "Unsecured Loan", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Lender", "fieldname": "lender", "fieldtype": "Data", "width": 150},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 100},
        {"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 100},
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
