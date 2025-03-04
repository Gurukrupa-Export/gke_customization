// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Order Report"] = {
    filters: [
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
            fieldname: "order_f",
            fieldtype: "MultiSelectList",
            options: "Order Form",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Order Form", txt);
            },
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
            fieldname: "customer_code",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            }
        },

        {
            "fieldname": "customer_po",
            "label": __("Customer PO No."),
            "fieldtype": "MultiSelectList",
            "options": [],
        },

		{
            label: __("BOM"),
            fieldname: "bom",
            fieldtype: "MultiSelectList",
            options: "BOM",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("BOM", txt);
            },
        },

		{
            label: __("Quotation"),
            fieldname: "quotation",
            fieldtype: "MultiSelectList",
            options: "Quotation",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Quotation", txt);
            },
        },

		{
            label: __("Sales Order"),
            fieldname: "so",
            fieldtype: "MultiSelectList",
            options: "Sales Order",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Sales Order", txt);
            },
        },
        // {
        //     label: __("Manufacturing Operation ID"),
        //     fieldname: "mop",
        //     fieldtype: "MultiSelectList",
        //     options: "Manufacturing Operation",
        //     reqd: 0,
        //     "get_data": function(txt) {
        //         return frappe.db.get_link_options("Manufacturing Operation", txt);
        //     },
        // },

        // {
        //     label: __("Parent Manufacturing Order"),
        //     fieldname: "pmo",
        //     fieldtype: "MultiSelectList",
        //     options: "Parent Manufacturing Order",
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return frappe.call({
        //             method: "frappe.desk.search.search_link",
        //             args: {
        //                 doctype: "Parent Manufacturing Order",
        //                 txt: txt,
        //                 page_length: 5
        //             }
        //         }).then(response => {
        //             return (response.message || []).map(d => ({
        //                 value: d.value,
        //                 label: d.label
        //             }));
        //         });
        //     }
        // },
        

        // {
        //     label: __("Quotation"),
        //     fieldname: "qt",
        //     fieldtype: "MultiSelectList",
        //     options: "Quotation",
        //     reqd: 0,
        //     "get_data": function(txt) {
        //         return frappe.db.get_link_options("Quotation", txt);
        //     },
        // },

        // {
        //     label: __("Sales Order"),
        //     fieldname: "so",
        //     fieldtype: "MultiSelectList",
        //     options: "Sales Order",
        //     reqd: 0,
        //     "get_data": function(txt) {
        //         return frappe.db.get_link_options("Sales Order",txt);
        //     },
        //     // default: "SAL-ORD-2024-01736",
        // },
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
