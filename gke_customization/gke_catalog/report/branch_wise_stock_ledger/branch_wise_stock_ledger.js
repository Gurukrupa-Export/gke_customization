// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Branch wise Stock Ledger"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
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
        { fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
        { fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
        { fieldname: "item_group", label: __("Item Group"), fieldtype: "Link", options: "Item Group" },
        { fieldname: "batch_no", label: __("Batch No"), fieldtype: "Link", options: "Batch" },
        { fieldname: "brand", label: __("Brand"), fieldtype: "Link", options: "Brand" },
        { fieldname: "voucher_no", label: __("Voucher #"), fieldtype: "Data" },
        { fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
        { fieldname: "include_uom", label: __("Include UOM"), fieldtype: "Link", options: "UOM" },  
        { fieldname: "inventory_type", label: __("Inventory Type"), fieldtype: "Link", options: "Inventory Type" },
        { fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
        {
            fieldname: "valuation_field_type",
            label: __("Valuation Field Type"),
            fieldtype: "Select",
            options: "Currency\nFloat",
            default: "Currency",
        },
        {
            fieldname: "segregate_serial_batch_bundle",
            label: __("Segregate Serial / Batch Bundle"),
            fieldtype: "Check",
            default: 0,
        },
    ],
};
