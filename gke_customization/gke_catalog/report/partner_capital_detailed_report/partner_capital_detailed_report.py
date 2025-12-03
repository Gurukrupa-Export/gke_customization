import frappe
from frappe.utils import flt, getdate
from datetime import timedelta, date

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []
    total_interest = 0
    last_balances = {}

    # Build filters
    capital_conditions = ""
    if filters.get("name"):
        capital_conditions += " AND name = %(name)s"
    if filters.get("lender"):
        capital_conditions += " AND lender = %(lender)s"
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

        repayments = frappe.db.sql(
            """
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
            ORDER BY payment_date ASC
            """,
            capital.name,
            as_dict=True,
        )

        n = len(repayments)
        balance = flt(capital.loan_amount)  # Start with loan amount
        initial_date = getdate(capital.date)

        for i in range(n):
            r = repayments[i]
            txn_date = getdate(r.payment_date)

            # Apply transaction for the current row
            if r.payment_type == "Pay":
                balance -= flt(r.total_payment)
            elif r.payment_type == "Receive":
                # For receive, only add if not the initial capital receive (date/amount match)
                if not (txn_date == initial_date and flt(r.total_payment) == flt(capital.loan_amount)):
                    balance += flt(r.total_payment)

            # Period end calculation
            if i + 1 < n:
                period_end = getdate(repayments[i + 1]['payment_date']) - timedelta(days=1)
            else:
                period_end = getdate(filters.get("to_date")) if filters.get("to_date") else get_fy_end(txn_date)
                if not filters.get("to_date") and period_end > date.today():
                    period_end = get_fy_end(txn_date)
            days = (period_end - txn_date).days + 1

            interest_amount = flt(balance) * flt(capital.interest_rate) * days / 36500 if days > 0 else 0
            total_interest += interest_amount

            data.append([
                capital.name,
                company_display,
                branch_display,
                lender_display,
                lender_name,
                balance,
                txn_date,
                period_end,
                days if days > 0 else 0,
                capital.interest_rate,
                interest_amount,
                r.payment_type,
                flt(r.total_payment),
                r.payment_entry_created
            ])

        last_balances[capital.name] = balance

    # Footer: sum only the last balance for each capital, plus total interest
    total_final_balance = sum(last_balances.values()) if last_balances else 0
    if total_final_balance or total_interest:
        footer_row = [""] * 5 + [total_final_balance] + [""] * 4 + [total_interest] + [""] * 3
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
        {"label": "Transaction Type", "fieldname": "payment_type", "fieldtype": "Data", "width": 100},
        {"label": "Total Payment", "fieldname": "total_payment", "fieldtype": "Currency", "width": 120},
        {"label": "PE Created", "fieldname": "payment_entry_created", "fieldtype": "Check", "width": 100}
    ]

def get_fy_end(start_date):
    year = start_date.year
    if start_date.month > 3:
        year += 1
    return getdate(f"{year}-03-31")
