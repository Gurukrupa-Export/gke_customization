// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Consumable Stock Report"] = {
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
                var company = frappe.query_report.get_filter_value('company');
                return {
                    "filters": {
                        "company": company
                    }
                }
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group",
            "get_query": function() {
                return {
                    "filters": {
                        "parent_item_group": ["like", "%Consumable%"]
                    }
                }
            }
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                var item_group = frappe.query_report.get_filter_value('item_group');
                var filters = {
                    "item_group": ["in", [
                        "Chemicals", "Electric Accessories", "Machinery",
                        "Medical Supplies", "Office Supplies", "Spare Accessories",
                        "Stationary", "Tools & Accessories", "Wax"
                    ]],
                    "disabled": 0
                };
                
                if (item_group) {
                    filters["item_group"] = item_group;
                }
                
                return { "filters": filters };
            }
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color code the status column
        if (column.fieldname == "stock_status") {
            if (value == "Out of Stock") {
                value = "<span style='color: red; font-weight: bold;'>" + value + "</span>";
            } else if (value == "Below Min") {
                value = "<span style='color: orange; font-weight: bold;'>" + value + "</span>";
            } else if (value == "Above Max") {
                value = "<span style='color: blue; font-weight: bold;'>" + value + "</span>";
            } else if (value == "In Stock") {
                value = "<span style='color: green;'>" + value + "</span>";
            }
        }
        
        // Highlight low stock items
        if (column.fieldname == "total_bal" && data && data.stock_status == "Below Min") {
            value = "<span style='background-color: #fff3cd;'>" + value + "</span>";
        }
        
        return value;
    },
    
};
