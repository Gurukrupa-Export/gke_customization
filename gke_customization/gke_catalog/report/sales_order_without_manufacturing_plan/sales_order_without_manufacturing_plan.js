// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sales order without manufacturing plan"] = {
    "filters": [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate()
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Company", txt);
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Branch", txt);
            }
        },
        {
            fieldname: "sales_order_id",
            label: __("Sales Order"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Sales Order", txt);
            }
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            }
        },
        {
            fieldname: "order_type",
            label: __("Order Type"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_list("Sales Order", {
                    fields: ["distinct order_type as value"],
                    filters: [["order_type", "like", "%" + txt + "%"]],
                    limit: 50
                }).then(records => {
                    return records.map(d => ({ value: d.value, description: d.value }));
                });
            }
        }
    ]
};