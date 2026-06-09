// Copyright (c) 2025, Gurukrupa Export Private Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Stone Assortment Report"] = {
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
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                };
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                };
            }
        },
        {
            "fieldname": "inventory_type",
            "label": __("Inventory Type"),
            "fieldtype": "Select",
            "options": ["", "Customer Goods", "Regular Stock"]
        }
    ]
};
