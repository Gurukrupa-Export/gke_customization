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
            get_data: function(txt) {
                return frappe.db.get_link_options("Manufacturing Work Order", txt);
            },
        },
        {
            label: __("Quotation"),
            fieldname: "qt",
            fieldtype: "MultiSelectList",
            options: "Quotation",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Quotation", txt);
            },
        },
        {
            label: __("Sales Order"),
            fieldname: "so",
            fieldtype: "MultiSelectList",
            options: "Sales Order",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Sales Order", txt);
            },
        },
        {
            fieldname: "customer_po",
            label: __("Customer PO No."),
            fieldtype: "MultiSelectList",
            options: [],
        },
        {
            fieldname: "customer",
            label: __("Customer Code"),
            fieldtype: "MultiSelectList",
            options: [],
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
        },
        {
            fieldname: "posting_date",
            label: __("Posting Date"),
            fieldtype: "Date",
            reqd: 0,
        },
    ],

    onload: function (report) {
    // ✅ Clear Filter button
    report.page.add_inner_button(__("Clear Filter"), function () {
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
        report.run();
    });

    // ✅ Fetch logged-in user's employee Company + Department
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: ["company", "department"]
        },
        callback: function (r) {
            if (r.message) {
                // Set default Company
                if (r.message.company) {
                    let company_filter = report.get_filter("company");
                    if (company_filter) {
                        company_filter.set_value(r.message.company);
                        // Make read-only if needed
                        company_filter.df.read_only = 1;
                        company_filter.refresh();
                    }
                }

                // Set default Department
                if (r.message.department) {
                    let department_filter = report.get_filter("department");
                    if (department_filter && !department_filter.get_value()) {
                        department_filter.set_value(r.message.department);
                    }
                }

                // ✅ Auto load report after setting defaults
                report.refresh();
            }
        }
    });

    // ✅ Fetch dynamic options (unchanged from before)
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

                    if (["category", "status", "diamond_quality", "customer_po", "customer", "department"].includes(filterField)) {
                        options.unshift("");
                    }

                    const filter = report.get_filter(filterField);
                    if (filter) {
                        filter.df.options = options;
                        filter.refresh();
                    }
                }
            },
        });
    }

    // Fetch dropdown options
    fetchOptions("Parent Manufacturing Order", "po_no", "customer_po");
    fetchOptions("Parent Manufacturing Order", "customer", "customer");
    fetchOptions("Manufacturing Operation", "department", "department");
    fetchOptions("Parent Manufacturing Order", "item_category", "category");
},
};