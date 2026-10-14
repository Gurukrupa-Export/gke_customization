// Copyright (c) 2024, Gurukrupa Export Private Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Department Stock Issue Report"] = {
    "filters": [
        // {
        //     "fieldname": "company",
        //     "label": __("Company"),
        //     "fieldtype": "Link",
        //     "options": "Company",
        //     "default": frappe.defaults.get_user_default("Company"),
        //     "reqd": 1,
        //     "on_change": function() {
        //         // Clear department filters when company changes
        //         frappe.query_report.set_filter_value('from_department', '');
        //         frappe.query_report.set_filter_value('to_department', '');
        //     }
        // },
        // {
        //     "fieldname": "branch",
        //     "label": __("Branch"),
        //     "fieldtype": "Link",
        //     "options": "Branch"
        // },
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
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": ["", "Transit", "Received", "Issued"],
            "default": ""
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "from_department",
            "label": __("From Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        'company': company
                    }
                };
            }
        },
        {
            "fieldname": "to_department",
            "label": __("To Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        'company': company
                    }
                };
            }
        },
        {
            "fieldname": "raw_material",
            "label": __("Raw Material"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ],

    "tree": true,
    "parent_field": "stock_entry_id",
    "initial_depth": 1,

    onload: function (report) {
        // Only System Manager / Administrator can view/change other departments.
        // Everyone else is locked to their own default (Employee) department.
        // Resolved server-side (not via a direct Employee lookup) since most report
        // users don't have read permission on the Employee doctype.
        frappe.call({
            method: "gke_customization.gke_catalog.report.department_stock_issue_report.department_stock_issue_report.get_user_department_filter",
            callback: function (r) {
                var res = r.message || {};
                if (res.can_change_department) return;

                var filter = report.get_filter("from_department");
                if (!filter) return;

                filter.set_value(res.department || "");
                filter.df.read_only = 1;
                filter.df.get_query = null;
                filter.refresh();
            }
        });
    },

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "status") {
            if (value == "Transit") {
                value = "<span style='color: orange; font-weight: bold;'>Transit</span>";
            } else if (value == "Received") {
                value = "<span style='color: green; font-weight: bold;'>Received</span>";
            } else if (value == "Issued") {
                value = "<span style='color: #2490ef; font-weight: bold;'>Issued</span>";
            }
        }
        
        if (data && data.indent === 0) {
            if (column.fieldname == "stock_entry_id") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "to_department") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "manufacturer") {
                value = `<span style='font-weight: bold; color: #666;'>${value}</span>`;
            }
            if (column.fieldname == "qty") {
                value = `<span style='font-weight: bold; color: #333;'>${value}</span>`;
            }
            if (column.fieldname == "pcs") {
                value = `<span style='font-weight: bold; color: #333;'>${value}</span>`;
            }
        }
        
        return value;
    }
};
