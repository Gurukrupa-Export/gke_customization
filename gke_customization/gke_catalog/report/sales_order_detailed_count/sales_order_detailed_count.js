// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Order Detailed Count"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "MultiSelectList",
            options: "Company",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Company", txt);
                },
        },
		{
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "MultiSelectList",
            options: "Branch",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Branch", txt);
                },
        },
        {
            fieldname: "diamond_quality",
            label: __("Diamond Quality"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "order_id",
            label: __("Sales Order"),
            fieldtype: "MultiSelectList",
            options: "Sales Order",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Sales Order", txt);
                },
        },
        {
            fieldname: "quotation",
            label: __("Quotation"),
            fieldtype: "MultiSelectList",
            options: "Quotation",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Quotation", txt);
                },
        },
        // {
        //     "fieldname": "order_id",
        //     "label": __("Order"),
        //     "fieldtype": "MultiSelectList",
        //     "options": "Sales Order",
        //     "reqd": 0,
        //     "get_data": function(txt) {
        //         return frappe.db.get_link_options("Sales Order", txt);
        //     }
        // },
        {
            "fieldname": "customer_code",
            "label": __("Customer"),
            "fieldtype": "MultiSelectList",
            "options": "Customer",
            "reqd": 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            }
        },
        // {
        //     fieldname: "category",
        //     label: __("Category"),
        //     fieldtype: "Select",
        //     options: [],
        //     reqd: 0,
        // },
		{
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        }
    ],

    onload: function (report) {
        // const customText = '<div style="text-align: center; left-padding: 8px; font-weight: bold; font-size: 15px; color:rgb(100, 151, 197) ;">Note: The standard deadline for this process is 5 hrs.';
        // $(report.page.wrapper).find('.page-form').after(customText);
        const clearFilterButton = report.page.add_inner_button(__("Clear Filter"), function () {
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);

                if (field.df.fieldtype === "MultiSelectList") {
                    field.set_value([]);
                } else if (field.df.default) {
                    field.set_value(field.df.default);
                } else {
                    field.set_value("");
                }
            });
        });

        // $(clearFilterButton).css({
        //     "background-color": "#17a2b8",
        //     "color": "white",
        //     "border-radius": "5px",
        //     "margin": "5px",
        // });

        function fetchOptions(doctype, field, filterField) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: doctype,
                    fields: [`distinct ${field}`],
                    order_by: `${field} asc`,
                    limit_page_length: 20000,
                },
                callback: function (r) {
                    if (r.message) {
                        const options = r.message
                            .map(row => row[field])
                            .filter(value => value !== null && value !== "");
        
                        if (filterField === "category" || filterField == "status" || filterField == "diamond_quality") {
                            options.unshift("");
                        }
        
                        const filter = report.get_filter(filterField);
                        filter.df.options = options;
                        filter.refresh();
                    }
                },
            });
        }

        // Fetch filters without additional fields
        // fetchOptions("Item", "item_category", "category");
		fetchOptions("Sales Order", "status", "status");
        fetchOptions("Sales Order", "custom_diamond_quality", "diamond_quality");


        // fetchOptions("Customer", "old_customer_code", "old_customer_code");
        // fetchOptions("Item", "stylebio", "stylebio");
        // fetchOptions("Order Form", "po_no", "po_no");
    },
};
