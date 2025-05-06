// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Production Order Report"] = {
    filters: [
		{
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: '2025-04-21',
        },
		{
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: '2025-04-25',
        },
        {
            label: __("Order"),
            fieldname: "order",
            fieldtype: "MultiSelectList",
            options: "Order",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Order", txt);
            },
        },
		{
            label: __("Order Form"),
            fieldname: "order_form",
            fieldtype: "MultiSelectList",
            options: "Order Form",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Order Form", txt);
            },
            default: 'ORD/C/03132',
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Company", txt);
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Branch", txt);
            }
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            }
        },

    ],

    onload: function (report) {
        // frappe.after_ajax(function() {
        //     report.set_filter_value("pmo", ["PMO-KGJPL-BA00726-001-0001", "PMO-KGJPL-NE00507-002-0001","PMO-KGJPL-NE00956-001-0001"]);
        // });

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
        
                        if (filterField === "category" || filterField == "status" || filterField == "diamond_quality" || filterField == "customer_po") {
                            options.unshift("");
                        }
        
                        const filter = report.get_filter(filterField);
                        filter.df.options = options;
                        filter.refresh();
                    }
                },
            });
        }

        fetchOptions("Sales Order", "po_no", "customer_po");
    },
};
