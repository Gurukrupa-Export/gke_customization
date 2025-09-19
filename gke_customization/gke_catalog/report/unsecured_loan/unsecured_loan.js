// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Unsecure Loan Detail Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value("company");
                if (company) {
                    return { 
                        filters: { 
                            company: company 
                        } 
                    };
                }
            }
        },
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
                var company = frappe.query_report.get_filter_value("company");
                var branch = frappe.query_report.get_filter_value("branch");
                var lender = frappe.query_report.get_filter_value("lender");
                
                var filters = { docstatus: ["!=", 2] };
                if (company) filters.company = company;
                if (branch) filters.branch = branch;
                if (lender) filters.lender = lender;
                
                return { filters: filters };
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
