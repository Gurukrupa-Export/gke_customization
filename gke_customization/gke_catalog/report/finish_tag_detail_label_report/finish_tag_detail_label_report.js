// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Finish Tag Detail Label Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company"),
            "on_change": function() {
                frappe.query_report.set_filter_value("branch", "");
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "reqd": 0,
            "get_query": function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            },
            "on_change": function() {
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 0,
            "get_query": function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let filters = {};

                if (company) {
                    filters.company = company;
                }

                if (branch) {
                    filters.branch = branch;
                }

                return {
                    filters: filters
                };
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.month_end()
        }
    ]
}
;