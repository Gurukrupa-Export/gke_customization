// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Ledger Detailed Report"] = {
    filters: [
        // ============= REQUIRED FILTERS =============
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        
        // ============= LOCATION FILTERS =============
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function () {
                const company = frappe.query_report.get_filter_value("company");
                return {
                    filters: { company: company },
                };
            },
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse",
            get_query: function () {
                const company = frappe.query_report.get_filter_value("company");
                return {
                    filters: { company: company },
                };
            },
        },
        
        // ============= ITEM FILTERS =============
        {
            fieldname: "item_code",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            options: "Item Group",
        },
        {
            fieldname: "brand",
            label: __("Brand"),
            fieldtype: "Link",
            options: "Brand",
        },
        {
            fieldname: "batch_no",
            label: __("Batch No"),
            fieldtype: "Link",
            options: "Batch",
            get_query: function () {
                const item_code = frappe.query_report.get_filter_value("item_code");
                if (item_code) {
                    return {
                        filters: { item: item_code },
                    };
                }
            },
        },
        
        // ============= BUSINESS FILTERS =============
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project",
            get_query: function () {
                const company = frappe.query_report.get_filter_value("company");
                return {
                    filters: { company: company },
                };
            },
        },
        {
            fieldname: "inventory_type",
            label: __("Inventory Type"),
            fieldtype: "Link",
            options: "Inventory Type",
        },
        
        // ============= DOCUMENT FILTERS =============
        {
            fieldname: "voucher_no",
            label: __("Voucher #"),
            fieldtype: "Data",
            description: __("Enter specific voucher number to filter"),
        },
        
        // ============= DISPLAY OPTIONS =============
        {
            fieldname: "include_uom",
            label: __("Include UOM"),
            fieldtype: "Link",
            options: "UOM",
            description: __("Show quantities in additional UOM"),
        },
        {
            fieldname: "valuation_field_type",
            label: __("Valuation Field Type"),
            fieldtype: "Select",
            options: "Currency\nFloat",
            default: "Currency",
            description: __("Display valuation rates as currency or float"),
        },
        {
            fieldname: "segregate_serial_batch_bundle",
            label: __("Segregate Serial / Batch Bundle"),
            fieldtype: "Check",
            default: 0,
            description: __("Show individual serial/batch entries separately"),
        },
    ],
    
    // ============= REPORT FORMATTING =============
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Highlight opening balance row
        if (data && data.item_code && data.item_code.includes("'Opening'")) {
            value = `<span style="font-weight: bold; color: #2490ef;">${value}</span>`;
        }
        
        // Color code quantity columns
        if (column.fieldname === "in_qty" && data && flt(data.in_qty) > 0) {
            value = `<span style="color: #5cb85c;">${value}</span>`;
        }
        if (column.fieldname === "out_qty" && data && flt(data.out_qty) < 0) {
            value = `<span style="color: #d9534f;">${value}</span>`;
        }
        
        return value;
    },
};
