// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Invoice Summary Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "invoice_no",
            "label": __("Invoice No"),
            "fieldtype": "Link",
            "options": "Sales Invoice"
        },
        {
            "fieldname": "serial_no",
            "label": __("Serial No"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        // NEW FILTERS
        {
            "fieldname": "raw_material",
            "label": __("Raw Material"),
            "fieldtype": "Select",
            "options": "\nMetal\nFinding\nDiamond\nGemstone"
        },
        {
            "fieldname": "setting_type",
            "label": __("Setting Type"),
            "fieldtype": "Select",
            "options": "\nOpen \nClose",
            "width": "120px"
        }
    ],
    
    "onload": function(report) {
        // Add button to go back to Detail Report
        report.page.add_inner_button(__("Sales Invoice Detail"), function() {
            const f = report.get_values();
            frappe.set_route('query-report', 'Sales Invoice Detail Report', {
                company: f.company,
                branch: f.branch || '',
                from_date: f.from_date,
                to_date: f.to_date,
                invoice_no: f.invoice_no || '',
                serial_no: f.serial_no || '',
                customer: f.customer || ''
            });
        });
    }
};
