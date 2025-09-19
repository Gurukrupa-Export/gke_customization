# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Date & Time"),
            "fieldname": "date_time",
            "fieldtype": "Datetime",
            "width": 190
        },
        {
            "label": _("Voucher No."),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 200
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 100,
            "hidden": 1
        },
        {
            "label": _("Account Type"),
            "fieldname": "account_type",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Particulars"),
            "fieldname": "particulars",
            "fieldtype": "Data",
            "width": 350
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Dynamic Link",
            "options": "party_type_hidden",
            "width": 150
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type_hidden",
            "fieldtype": "Data",
            "width": 100,
            "hidden": 1
        },
        {
            "label": _("Party Name"),
            "fieldname": "party_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Inflow"),
            "fieldname": "inflow",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Outflow"),
            "fieldname": "outflow",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Net Cash Flow"),
            "fieldname": "net_cash_flow",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Mode of Payment"),
            "fieldname": "mode_of_payment",
            "fieldtype": "Data",
            "width": 150
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT 
            CONCAT(gle.posting_date, ' ', TIME(gle.creation)) as date_time,
            gle.voucher_no,
            gle.voucher_type,
            CASE 
                WHEN gle.voucher_type = 'Payment Entry' AND pe.payment_type = 'Receive' THEN 'Receive'
                WHEN gle.voucher_type = 'Payment Entry' AND pe.payment_type = 'Pay' THEN 'Pay'
                WHEN gle.voucher_type = 'Payment Entry' AND pe.payment_type = 'Internal Transfer' THEN 'Internal Transfer'
                WHEN gle.voucher_type = 'Purchase Invoice' THEN 'Pay'
                WHEN gle.voucher_type = 'Sales Invoice' THEN 'Receive'
                WHEN gle.voucher_type = 'Delivery Note' THEN 'Receive'
                WHEN gle.voucher_type = 'Purchase Receipt' THEN 'Pay'
                WHEN gle.voucher_type = 'Expense Claim' THEN 'Pay'
                WHEN gle.voucher_type = 'Loan Disbursement' THEN 'Pay'
                WHEN gle.voucher_type = 'Loan Repayment' THEN 'Receive'
                WHEN gle.voucher_type = 'Journal Entry' THEN 'Internal Transfer'
                WHEN gle.voucher_type = 'Stock Entry' THEN 'Internal Transfer'
                WHEN gle.voucher_type = 'Stock Reconciliation' THEN 'Internal Transfer'
                ELSE 'Pay'
            END as account_type,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN 
                    CONCAT('Purchase from ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Sales Invoice' THEN 
                    CONCAT('Sales to ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Delivery Note' THEN 
                    CONCAT('Delivery to ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Purchase Receipt' THEN 
                    CONCAT('Purchase Receipt from ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Expense Claim' THEN 
                    CONCAT('Expense Claim by ', IFNULL(gle.party, IFNULL(gle.against, 'Employee')))
                WHEN gle.voucher_type = 'Loan Disbursement' THEN 
                    CONCAT('Loan Disbursement to ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Loan Repayment' THEN 
                    CONCAT('Loan Repayment from ', IFNULL(gle.party, IFNULL(gle.against, 'Unknown')))
                WHEN gle.voucher_type = 'Payment Entry' THEN 
                    CONCAT(
                        CASE 
                            WHEN pe.payment_type = 'Pay' THEN 'Payment to '
                            WHEN pe.payment_type = 'Receive' THEN 'Receipt from '
                            WHEN pe.payment_type = 'Internal Transfer' THEN 'Internal Transfer - '
                            ELSE 'Payment - '
                        END,
                        IFNULL(pe.party_name, IFNULL(gle.party, gle.against))
                    )
                WHEN gle.voucher_type = 'Journal Entry' THEN 
                    CONCAT('Journal Entry - ', IFNULL(je.user_remark, 'Transfer'))
                WHEN gle.voucher_type = 'Stock Entry' THEN 
                    CONCAT('Stock Entry - ', gle.voucher_no)
                WHEN gle.voucher_type = 'Stock Reconciliation' THEN 
                    CONCAT('Stock Reconciliation - ', gle.voucher_no)
                ELSE CONCAT(gle.voucher_type, ' - ', gle.voucher_no)
            END as particulars,
            CASE 
                WHEN pe.party IS NOT NULL THEN pe.party
                WHEN gle.party IS NOT NULL THEN gle.party
                WHEN gle.against IS NOT NULL THEN gle.against
                ELSE NULL
            END as party,
            CASE 
                WHEN pe.party_type IS NOT NULL THEN pe.party_type
                WHEN gle.party_type IS NOT NULL THEN gle.party_type
                WHEN gle.against IS NOT NULL THEN (
                    SELECT party_type FROM `tabGL Entry` gle2 
                    WHERE gle2.voucher_no = gle.voucher_no 
                    AND gle2.party = gle.against 
                    AND gle2.party_type IS NOT NULL 
                    LIMIT 1
                )
                ELSE NULL
            END as party_type_hidden,
            CASE 
                WHEN pe.party_name IS NOT NULL THEN pe.party_name
                WHEN gle.party IS NOT NULL THEN gle.party
                WHEN gle.against IS NOT NULL THEN gle.against
                ELSE ''
            END as party_name,
            CASE WHEN gle.debit > 0 THEN gle.debit ELSE 0 END as inflow,
            CASE WHEN gle.credit > 0 THEN gle.credit ELSE 0 END as outflow,
            (CASE WHEN gle.debit > 0 THEN gle.debit ELSE 0 END - 
             CASE WHEN gle.credit > 0 THEN gle.credit ELSE 0 END) as net_cash_flow,
            IFNULL(pe.mode_of_payment, '') as mode_of_payment
        FROM 
            `tabGL Entry` gle
        LEFT JOIN 
            `tabPayment Entry` pe ON gle.voucher_no = pe.name AND gle.voucher_type = 'Payment Entry'
        LEFT JOIN 
            `tabJournal Entry` je ON gle.voucher_no = je.name AND gle.voucher_type = 'Journal Entry'
        WHERE 
            gle.account IN (
                SELECT name FROM `tabAccount` 
                WHERE account_type IN ('Bank', 'Cash') 
                AND is_group = 0
                AND company = '{filters.get("company", "Gurukrupa Export Private Limited")}'
            )
            {conditions}
        ORDER BY date_time DESC
    """
    
    data = frappe.db.sql(query, as_dict=1)
    
    # Add total row with inflow, outflow, and net cash flow totals
    if data:
        total_inflow = sum(row.get('inflow', 0) for row in data)
        total_outflow = sum(row.get('outflow', 0) for row in data)
        total_net = total_inflow - total_outflow
        
        total_row = {
            'date_time': '',
            'voucher_no': '',
            'voucher_type': '',
            'account_type': '',
            'particulars': '',
            'party': '',
            'party_type_hidden': '',
            'party_name': '<b>Total</b>',
            'inflow': total_inflow,
            'outflow': total_outflow,
            'net_cash_flow': total_net,
            'mode_of_payment': ''
        }
        data.append(total_row)
    
    return data

def get_conditions(filters):
    conditions = []
    
    # Date range filter
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(f"gle.posting_date BETWEEN '{filters.get('from_date')}' AND '{filters.get('to_date')}'")
    elif filters.get("from_date"):
        conditions.append(f"gle.posting_date >= '{filters.get('from_date')}'")
    elif filters.get("to_date"):
        conditions.append(f"gle.posting_date <= '{filters.get('to_date')}'")
    else:
        conditions.append("gle.posting_date = CURDATE()")
    
    if filters.get("voucher_type"):
        conditions.append(f"gle.voucher_type = '{filters.get('voucher_type')}'")
    
    if filters.get("party_type"):
        conditions.append(f"""(
            pe.party_type = '{filters.get('party_type')}' 
            OR gle.party_type = '{filters.get('party_type')}'
            OR EXISTS (
                SELECT 1 FROM `tabGL Entry` gle2 
                WHERE gle2.voucher_no = gle.voucher_no 
                AND gle2.party = gle.against 
                AND gle2.party_type = '{filters.get('party_type')}'
            )
        )""")
    
    if filters.get("party"):
        conditions.append(f"(pe.party = '{filters.get('party')}' OR gle.party = '{filters.get('party')}' OR gle.against = '{filters.get('party')}')")
    
    if filters.get("party_name"):
        conditions.append(f"(pe.party_name LIKE '%{filters.get('party_name')}%' OR gle.party LIKE '%{filters.get('party_name')}%')")
    
    # Branch filter - checks branch field in GL Entry, Payment Entry, and Journal Entry
    if filters.get("branch"):
        conditions.append(f"(gle.branch = '{filters.get('branch')}' OR pe.branch = '{filters.get('branch')}' OR je.branch = '{filters.get('branch')}')")
    
    # Updated filter for account type (transaction type) - Added all voucher types
    if filters.get("account_type"):
        account_type_condition = f"""(
            (gle.voucher_type = 'Payment Entry' AND pe.payment_type = '{filters.get("account_type")}') OR
            (gle.voucher_type = 'Purchase Invoice' AND '{filters.get("account_type")}' = 'Pay') OR
            (gle.voucher_type = 'Sales Invoice' AND '{filters.get("account_type")}' = 'Receive') OR
            (gle.voucher_type = 'Delivery Note' AND '{filters.get("account_type")}' = 'Receive') OR
            (gle.voucher_type = 'Purchase Receipt' AND '{filters.get("account_type")}' = 'Pay') OR
            (gle.voucher_type = 'Expense Claim' AND '{filters.get("account_type")}' = 'Pay') OR
            (gle.voucher_type = 'Loan Disbursement' AND '{filters.get("account_type")}' = 'Pay') OR
            (gle.voucher_type = 'Loan Repayment' AND '{filters.get("account_type")}' = 'Receive') OR
            (gle.voucher_type = 'Journal Entry' AND '{filters.get("account_type")}' = 'Internal Transfer') OR
            (gle.voucher_type = 'Stock Entry' AND '{filters.get("account_type")}' = 'Internal Transfer') OR
            (gle.voucher_type = 'Stock Reconciliation' AND '{filters.get("account_type")}' = 'Internal Transfer')
        )"""
        conditions.append(account_type_condition)
    
    return " AND " + " AND ".join(conditions) if conditions else ""
