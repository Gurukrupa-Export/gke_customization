// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Unsecure Loan Detail Report"] = {
    "filters": [
        {
            "fieldname": "lender",
            "label": __("Lender"),
            "fieldtype": "Link",
            "options": "Business Partner"
        },
        {
            "fieldname": "name",
            "label": __("Unsecured Loan ID"),
            "fieldtype": "Link",
            "options": "Unsecured Loan",
            "get_query": function() {
                var lender = frappe.query_report.get_filter_value("lender");
                if (lender) {
                    return { filters: { lender: lender } };
                }
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date"
        }
    ]
};
