// Copyright (c) 2026, Sajith and contributors
// For license information, please see license.txt

frappe.query_reports["Item wise Stock Dashboard"] = {
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
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "get_query": function() {
                var branch = frappe.query_report.get_filter_value("branch");

                var allowed_warehouses = [
                    "BL - CSB Procurement 1 - GEPL",
                    "CH - CSB Procurement 1 - GEPL",
                    "CSB Procurement - GEPL",
                    "HD - CSB Procurement 1 - GEPL",
                    "MU - CSB Procurement 1 - GEPL",
                    "CSB Product Certification - SHC",
                    "CSB Procurement - SHC",
                    "CSB Procurement 1 - GEPL",
                    "CSB Procurement 2 - GEPL",
                    "CSB Procurement 1 - KGJPL",
                    "CSB Procurement 2 - KGJPL"
                ];

                var filters = {
                    "name": ["in", allowed_warehouses],
                    "is_group": 0
                };

                if (branch) {
                    filters["custom_branch"] = branch;
                }

                return {
                    "filters": filters
                };
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    "filters": {
                        "is_stock_item": 1,
                        "disabled": 0
                    }
                };
            }
        },
        {
            "fieldname": "item_name",
            "label": __("Item Name"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    query: "gke_customization.gke_catalog.report.item_wise_stock_dashboard.item_wise_stock_dashboard.item_name_query"
                };
            }
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "closing_stock" && data && data.min_qty > 0) {
            if (data.closing_stock <= data.min_qty) {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }

        return value;
    }
};