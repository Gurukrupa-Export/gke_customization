// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Cash Flow"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                }
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "account_type",
            "label": __("Account Type"),
            "fieldtype": "Select",
            "options": "\nReceive\nPay\nInternal Transfer"
        },
        {
            "fieldname": "voucher_type",
            "label": __("Voucher Type"),
            "fieldtype": "Select",
            "options": "\nPayment Entry\nPurchase Invoice\nSales Invoice\nJournal Entry\nDelivery Note\nExpense Claim\nLoan Disbursement\nLoan Repayment\nPurchase Receipt\nStock Entry\nStock Reconciliation"
        },
        {
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": "\nCustomer\nEmployee\nSupplier\nShareholder"
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Dynamic Link",
            "options": "party_type"
        },
        {
            "fieldname": "party_name",
            "label": __("Party Name"),
            "fieldtype": "Data"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "net_cash_flow" && data) {
            if (data.net_cash_flow > 0) {
                value = `<span style='color: green; font-weight: bold;'>${value}</span>`;
            } else if (data.net_cash_flow < 0) {
                value = `<span style='color: red; font-weight: bold;'>${value}</span>`;
            }
        }
        
        if (column.fieldname === "inflow" && data && data.inflow > 0) {
            value = `<span style='color: green;'>${value}</span>`;
        }
        
        if (column.fieldname === "outflow" && data && data.outflow > 0) {
            value = `<span style='color: red;'>${value}</span>`;
        }
        
        return value;
    }
};
