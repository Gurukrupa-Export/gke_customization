// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Batch Wise Sales Cycle - SAM"] = {
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
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "batch_no",
            label: __("Batch No"),
            fieldtype: "Link",
            options: "Batch",
            get_query: function () {
                let item = frappe.query_report.get_filter_value("item");
                return {
                    filters: item ? { item: item } : {},
                };
            },
        },
        {
            fieldname: "sales_order_id",
            label: __("Sales Order"),
            fieldtype: "Link",
            options: "Sales Order",
            get_query: function () {
                let customer = frappe.query_report.get_filter_value("customer");
                let company  = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        docstatus: 1,
                        ...(customer && { customer }),
                        ...(company  && { company }),
                    },
                };
            },
        },
        {
            fieldname: "dn_id",
            label: __("Delivery Note"),
            fieldtype: "Link",
            options: "Delivery Note",
            get_query: function () {
                let customer = frappe.query_report.get_filter_value("customer");
                let company  = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        docstatus: 1,
                        is_return: 0,
                        ...(customer && { customer }),
                        ...(company  && { company }),
                    },
                };
            },
        },
        {
            fieldname: "si_id",
            label: __("Sales Invoice"),
            fieldtype: "Link",
            options: "Sales Invoice",
            get_query: function () {
                let customer = frappe.query_report.get_filter_value("customer");
                let company  = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        docstatus: 1,
                        is_return: 0,
                        ...(customer && { customer }),
                        ...(company  && { company }),
                    },
                };
            },
        },
    ],
};
