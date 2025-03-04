// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Order Detail Report"] = {
    filters: [
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
            options: "Branch",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Branch", txt);
                },
        },
        {
            label: __("Manufacturing Work Order"),
            fieldname: "mp",
            fieldtype: "MultiSelectList",
            options: "Manufacturing Work Order",
            reqd: 0,
            "get_data": function(txt) {
                return frappe.db.get_link_options("Manufacturing Work Order", txt);
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
        

        {
            label: __("Quotation"),
            fieldname: "qt",
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
            // default: "SAL-ORD-2024-01736",
        },
        {
            "fieldname": "customer_po",
            "label": __("Customer PO No."),
            "fieldtype": "MultiSelectList",
            "options": [],
        },
        {
            "fieldname": "customer",
            "label": __("Customer Code"),
            "fieldtype": "MultiSelectList",
            "options": [],
        },
        {
            fieldname: "category",
            label: __("Item Category"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "delivery_date",
            label: __("Delivery Date"),
            fieldtype: "Date",
            reqd: 0,
            // default: frappe.datetime.month_start(),
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
        
                        if (filterField === "category" || filterField == "status" || filterField == "diamond_quality" || filterField == "customer_po" || filterField == "customer" || filterField == "department") {
                            options.unshift("");
                        }
        
                        const filter = report.get_filter(filterField);
                        filter.df.options = options;
                        filter.refresh();
                    }
                },
            });
        }

        fetchOptions("Parent Manufacturing Order", "po_no", "customer_po");
        fetchOptions("Parent Manufacturing Order", "customer", "customer");
        fetchOptions("Manufacturing Operation", "department", "department");
        fetchOptions("Parent Manufacturing Order", "item_category", "category");

    },
};
