import frappe
from frappe.utils import flt, getdate, add_days
from datetime import timedelta, date


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []
    total_interest = 0
    last_balances = {}


    # Build filters for Partner Capital (no date filter here)
    capital_conditions = ""
    if filters.get("name"):
        capital_conditions += " AND name = %(name)s"
    if filters.get("business_partner"):
        capital_conditions += " AND lender = %(business_partner)s"
    if filters.get("company"):
        capital_conditions += " AND company = %(company)s"
    if filters.get("branch"):
        capital_conditions += " AND branch = %(branch)s"


    capital_query = f"""
        SELECT name, lender, lender_name, date, interest_rate,
               loan_amount, company, branch
        FROM `tabPartner Capital`
        WHERE docstatus != 2 {capital_conditions}
        ORDER BY date DESC
    """
    capitals = frappe.db.sql(capital_query, filters, as_dict=True)


    for capital in capitals:
        branch_display = capital.get('branch') or ""
        company_display = capital.get("company") or ""
        lender_display = capital.get('lender') or ""
        lender_name = capital.get('lender_name') or ""


        # Fetch repayment schedule entries with date filter
        repayment_query = """
            SELECT
                name AS schedule_id,
                payment_date,
                payment_type,
                total_payment,
                payment_entry_created
            FROM `tabPartner Capital Repayment Schedule`
            WHERE parent = %s
                AND payment_type IS NOT NULL
                AND payment_type != ''
        """
        repayment_params = [capital.name]
        
        if filters.get("from_date"):
            repayment_query += " AND payment_date >= %s"
            repayment_params.append(filters.get("from_date"))
        if filters.get("to_date"):
            repayment_query += " AND payment_date <= %s"
            repayment_params.append(filters.get("to_date"))
            
        repayment_query += " ORDER BY payment_date ASC"
        
        repayments = frappe.db.sql(repayment_query, tuple(repayment_params), as_dict=True)


        # Fetch Journal Entry interest payments with date filter
        je_query = """
            SELECT 
                je.name AS journal_entry,
                je.posting_date,
                je.title,
                jea.credit AS interest_paid
            FROM 
                `tabJournal Entry` je
            INNER JOIN 
                `tabBusiness Partner` bp ON bp.name = %s
            INNER JOIN 
                `tabLoan Accounts` la ON la.parent = bp.name 
                AND la.company = %s
            INNER JOIN 
                `tabJournal Entry Account` jea ON jea.parent = je.name 
                AND jea.account = la.partner_capital_account
                AND jea.credit > 0
            WHERE 
                je.custom_partner_capital = %s
                AND je.docstatus = 1
        """
        je_params = [capital.lender, capital.company, capital.name]
        
        if filters.get("from_date"):
            je_query += " AND je.posting_date >= %s"
            je_params.append(filters.get("from_date"))
        if filters.get("to_date"):
            je_query += " AND je.posting_date <= %s"
            je_params.append(filters.get("to_date"))
            
        je_query += " ORDER BY je.posting_date ASC"
        
        je_payments = frappe.db.sql(je_query, tuple(je_params), as_dict=True)


        # Skip if no transactions in date range
        if not repayments and not je_payments:
            continue


        # Merge repayments and JE payments into one list
        all_transactions = []
        
        for r in repayments:
            all_transactions.append({
                'date': getdate(r.payment_date),
                'type': 'repayment',
                'payment_type': r.payment_type,
                'amount': flt(r.total_payment),
                'pe_created': r.payment_entry_created,
                'reference': 'Payment Entry'
            })
        
        for je in je_payments:
            all_transactions.append({
                'date': getdate(je.posting_date),
                'type': 'interest_payment',
                'payment_type': 'Interest Payment',
                'amount': flt(je.interest_paid),
                'pe_created': '',
                'reference': 'Journal Entry'
            })


        # Sort all transactions by date
        all_transactions.sort(key=lambda x: x['date'])


        n = len(all_transactions)
        balance = flt(capital.loan_amount)
        previous_to_date = None


        for i in range(n):
            txn = all_transactions[i]
            txn_date = txn['date']


            # From Date: first row uses transaction date, subsequent rows use day after previous To Date
            if i == 0:
                from_date = txn_date
            else:
                from_date = add_days(previous_to_date, 1)


            # Apply transaction (skip first receive if it matches loan amount)
            if i == 0 and txn['type'] == 'repayment' and txn['payment_type'] == "Receive" and flt(txn['amount']) == flt(capital.loan_amount):
                # Skip the first receive that matches the initial loan amount
                pass
            else:
                # Apply normal transaction logic
                if txn['payment_type'] == "Pay":
                    balance -= flt(txn['amount'])
                elif txn['payment_type'] == "Receive":
                    balance += flt(txn['amount'])
                elif txn['payment_type'] == "Interest Payment":
                    balance += flt(txn['amount'])


            # Balance AFTER the transaction for display
            current_balance = balance


            # To Date calculation
            if i + 1 < n:
                # Use next transaction date as To Date
                to_date = all_transactions[i + 1]['date']
            else:
                # Last entry: use filter to_date or FY end
                to_date = getdate(filters.get("to_date")) if filters.get("to_date") else get_fy_end(txn_date)
                if not filters.get("to_date") and to_date > date.today():
                    to_date = get_fy_end(txn_date)


            # Store To Date for next iteration
            previous_to_date = to_date


            # Calculate days
            days = (to_date - from_date).days + 1
            if days < 0:
                days = 0


            # Interest calculation
            interest_amount = flt(current_balance) * flt(capital.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount


            # Add row to data
            data.append([
                capital.name,
                company_display,
                branch_display,
                lender_display,
                lender_name,
                current_balance,
                from_date,
                to_date,
                days,
                capital.interest_rate,
                interest_amount,
                txn['payment_type'],
                flt(txn['amount']),
                txn['pe_created'],
                txn['reference']
            ])


        last_balances[capital.name] = balance


    # Footer: sum only the last balance for each capital, plus total interest
    total_final_balance = sum(last_balances.values()) if last_balances else 0
    
    if total_final_balance or total_interest:
        footer_row = [""] * 5 + [total_final_balance] + [""] * 4 + [total_interest] + [""] * 4
        data.append(footer_row)


    return columns, data


def get_columns():
    return [
        {"label": "Partner Capital ID", "fieldname": "partner_capital_id", "fieldtype": "Link", "options": "Partner Capital", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 290},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Lender", "fieldname": "lender", "fieldtype": "Data", "width": 150},
        {"label": "Lender Name", "fieldname": "lender_name", "fieldtype": "Data", "width": 150},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 150},
        {"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 150},
        {"label": "Days", "fieldname": "days", "fieldtype": "Int", "width": 60},
        {"label": "Interest (%)", "fieldname": "interest_rate", "fieldtype": "Percent", "width": 80},
        {"label": "Interest Amount", "fieldname": "interest_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Transaction Type", "fieldname": "payment_type", "fieldtype": "Data", "width": 120},
        {"label": "Total Payment", "fieldname": "total_payment", "fieldtype": "Currency", "width": 120},
        {"label": "PE Created", "fieldname": "payment_entry_created", "fieldtype": "Check", "width": 100},
        {"label": "Reference Doctype", "fieldname": "reference_doctype", "fieldtype": "Data", "width": 150}
    ]


def get_fy_end(start_date):
    year = start_date.year
    if start_date.month > 3:
        year += 1
    return getdate(f"{year}-03-31")
