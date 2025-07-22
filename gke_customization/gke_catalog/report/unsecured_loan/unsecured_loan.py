
# import frappe

# def execute(filters=None):
#     filters = frappe._dict(filters or {})
#     conditions = []

#     # Priority: Unsecured Loan ID > Lender
#     if filters.get("name"):
#         conditions.append("parent = %(name)s")
#     elif filters.get("lender"):
#         conditions.append("""
#             parent IN (
#                 SELECT name FROM `tabUnsecured Loan`
#                 WHERE lender = %(lender)s
#             )
#         """)

#     if filters.get("from_date"):
#         conditions.append("payment_date >= %(from_date)s")
#     if filters.get("to_date"):
#         conditions.append("payment_date <= %(to_date)s")

#     where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

#     data = frappe.db.sql(f"""
#         SELECT
#             parent AS `name`,
#             payment_date,
#             payment_type,
#             repay_loan_amount,
#             interest_amount,
#             total_payment,
#             balance_loan_amount
#         FROM `tabUnsecured Loan Repayment Schedule`
#         {where_clause}
#         ORDER BY payment_date ASC
#     """, filters, as_dict=True)

#     # Totals
#     total_interest = sum(d.interest_amount or 0 for d in data)
#     total_receive = sum(d.total_payment or 0 for d in data if d.payment_type == "Receive")
#     total_pay = sum(d.total_payment or 0 for d in data if d.payment_type == "Pay")
#     net_received = total_receive - total_pay

#     # Add total row
#     if data:
#         data.append({})
#     data.append({
#         "name": "Total",
#         "interest_amount": total_interest,
#         "total_payment": net_received
#     })

#     columns = [
#         {"label": "Unsecured Loan ID", "fieldname": "name", "fieldtype": "Link", "options": "Unsecured Loan", "width": 150},
#         {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 100},
#         {"label": "Payment Type", "fieldname": "payment_type", "fieldtype": "Data", "width": 100},
#         {"label": "Repay Amount", "fieldname": "repay_loan_amount", "fieldtype": "Currency", "width": 120},
#         {"label": "Interest Amount", "fieldname": "interest_amount", "fieldtype": "Currency", "width": 120},
#         {"label": "Total Payment", "fieldname": "total_payment", "fieldtype": "Currency", "width": 120},
#         {"label": "Balance Loan Amount", "fieldname": "balance_loan_amount", "fieldtype": "Currency", "width": 150},
#     ]

#     return columns, data

import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []

    conditions = ""
    if filters.get("name"):
        conditions += " AND parent = %(name)s"
    elif filters.get("lender"):
        conditions += """
            AND parent IN (
                SELECT name FROM `tabUnsecured Loan`
                WHERE lender = %(lender)s
            )
        """

    if filters.get("from_date"):
        conditions += " AND payment_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND payment_date <= %(to_date)s"

    records = frappe.db.sql("""
        SELECT 
            uls.parent,
            ul.lender,
            uls.payment_date,
            uls.payment_type,
            uls.repay_loan_amount,
            uls.interest_amount,
            uls.total_payment
        FROM `tabUnsecured Loan Repayment Schedule` uls
        LEFT JOIN `tabUnsecured Loan` ul ON ul.name = uls.parent
        WHERE 1=1 {conditions}
        ORDER BY uls.payment_date ASC
    """.format(conditions=conditions), filters, as_dict=True)

    total_interest = 0
    total_receive = 0
    total_pay = 0
    net_balance = 0

    for row in records:
        receive_amt = 0
        pay_amt = 0
        if row.payment_type == "Receive":
            receive_amt = flt(row.total_payment)
            net_balance += receive_amt
            total_receive += receive_amt
        elif row.payment_type == "Pay":
            pay_amt = flt(row.total_payment)
            net_balance -= pay_amt
            total_pay += pay_amt

        total_interest += flt(row.interest_amount)

        data.append([
            row.parent,
            row.lender,
            row.payment_date,
            row.payment_type,
            row.repay_loan_amount,
            row.interest_amount,
            row.total_payment,
            receive_amt,
            pay_amt,
            net_balance
        ])

    # Totals row
    data.append([""] * 4 + ["", total_interest, "", total_receive, total_pay, net_balance])

    return columns, data


def get_columns():
    return [
        {"label": "Unsecured Loan ID", "fieldname": "parent", "fieldtype": "Link", "options": "Unsecured Loan", "width": 150},
        {"label": "Lender", "fieldname": "lender", "fieldtype": "Link", "options": "Business Partner", "width": 150},
        {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 100},
        {"label": "Payment Type", "fieldname": "payment_type", "fieldtype": "Data", "width": 80},
        {"label": "Repay Loan Amount", "fieldname": "repay_loan_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Interest Amount", "fieldname": "interest_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Total Payment", "fieldname": "total_payment", "fieldtype": "Currency", "width": 120},
        {"label": "Receive Amount", "fieldname": "receive_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Pay Amount", "fieldname": "pay_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Running Net Balance", "fieldname": "net_balance", "fieldtype": "Currency", "width": 140},
    ]




