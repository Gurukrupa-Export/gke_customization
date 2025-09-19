// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Advance Bagging Summary Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
        },
        {
            label: "Material Type",
            fieldname: "material_type",
            fieldtype: "Select",
            options: ["", "Diamond", "Metal", "Gemstone", "Finding", "Others"],
            reqd: 0
        },
        {
            fieldname: "workflow_state",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Material Request", {
                    fields: ["distinct workflow_state as value"],
                    filters: {
                        "material_request_type": "Manufacture",
                        "workflow_state": ["!=", "Material Transferred to MOP"]
                    },
                    order_by: "workflow_state"
                }).then(r => {
                    return r
                        .filter(d => d.value && d.value.trim() !== "")
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
        {
            label: "Parent Manufacturing Order",
            fieldname: "manufacturing_order",
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Parent Manufacturing Order", txt);
            }
        },
        {
            fieldname: "item_category",
            label: __("Category"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Parent Manufacturing Order", {
                    fields: ["distinct item_category as value"],
                    order_by: "item_category"
                }).then(r => {
                    return r
                        .filter(d => d.value && d.value.trim() !== "")
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
        {
            fieldname: "setting_type",
            label: __("Setting Type"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Parent Manufacturing Order", {
                    fields: ["distinct setting_type as value"],
                    order_by: "setting_type"
                }).then(r => {
                    return r
                        .filter(d => d.value && d.value.trim() !== "")
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
    ],
    
    onload: function(report) {
        // Clear filters button
        report.page.add_inner_button(__("Clear Filter"), function () {
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);
                if (field && field.df.fieldtype === "MultiSelectList") {
                    field.set_value([]);
                } else if (field && field.df.default) {
                    field.set_value(field.df.default);
                } else if (field) {
                    field.set_value("");
                }
            });
            report.refresh();
        });
        
        // Link to detailed report
        report.page.add_inner_button(__("View Detailed Report"), function () {
            frappe.set_route("query-report", "Advance Bagging Report From MR", report.get_filter_values());
        });
    }
}
