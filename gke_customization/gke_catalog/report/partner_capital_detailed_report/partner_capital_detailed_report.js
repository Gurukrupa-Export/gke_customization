// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Partner Capital Detailed Report"] = {
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
                        "filters": {
                            "company": company
                        }
                    };
                }
            }
        },
        {
            "fieldname": "business_partner",
            "label": __("Business Partner"),
            "fieldtype": "Link",
            "options": "Business Partner"
        },
        {
            "fieldname": "name",
            "label": __("Partner Capital ID"),
            "fieldtype": "Link",
            "options": "Partner Capital",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value("company");
                var branch = frappe.query_report.get_filter_value("branch");
                var business_partner = frappe.query_report.get_filter_value("business_partner");


                var filters = { "docstatus": ["!=", 2] };
                if (company) filters.company = company;
                if (branch) filters.branch = branch;
                if (business_partner) filters.business_partner = business_partner;


                return { "filters": filters };
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
