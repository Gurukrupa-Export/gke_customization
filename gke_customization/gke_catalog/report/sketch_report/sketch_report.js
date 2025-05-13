
// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Report"] = {
    "filters": [
        {
            fieldname: "start_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "end_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
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
            fieldname: "designer_branch",
            label: __("Branch"),
            fieldtype: "Link",
            reqd: 0,
            options:"Branch"
          
        },        
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            options: "Customer",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_list("Customer", {
                    fields: ["name as value", "customer_name as description"], 
                    filters: {
                        "customer_name": ["like", `%${txt}%`]
                    },
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
                return frappe.db.get_list("Order", {
                    fields: ["distinct setting_type as value"],
                    filters: [
                        ["setting_type", "not in", [ " "]],
                        ["setting_type", "like", `%${txt}%`]
                    ],
                    limit: 20
                }).then(r => {
                    return r.map(d => {
                        return {
                            value: d.value,
                            description: ""
                        }
                    });
                });
            }
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Sketch Order", {
                    fields: ["distinct workflow_state as value"],
                }).then(r => {
                    return r.map(d => {
                        return {
                            value: d.value,
                            description: "" 
                        }
                    });
                });
            }
        },
        // {
        //     fieldname: "sketch_workflow_state",
        //     label: __("Sketch Workflow State"),
        //     fieldtype: "MultiSelectList",
        //     options: [],
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return frappe.db.get_list("Order", {
        //             fields: ["distinct custom_sketch_workflow_state as value"],
        //         }).then(r => {
        //             return r.map(d => {
        //                 return {
        //                     value: d.value,
        //                     description: ""  
        //                 }
        //             });
        //         });
        //     }
        // },

        {
            fieldname: "user",
            label: __("User"),
            fieldtype: "MultiSelectList",
            hidden: 0,
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Employee", {
                    fields: ["user_id as value","name as description"],
                    filters: [
                        ["status", "=", "Active"],
                        ["designation", "=", "Manager"],
                        ["department", "in", ["Product Development - GEPL", "Sketch - GEPL"]],
                        ["employee_name", "like", `%${txt}%`]
                    ],
                });
            }
        },
    ],

onload: function (report) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Employee",
            filters: {
                user_id: frappe.session.user,
                status: "Active",
                designation: "Manager",
                department: ["in", ["Product Development - GEPL", "Sketch - GEPL"]]
            },
            fields: ["name"]  
        },
        callback: function (res) {
            // If a matching employee is found, hide the "User" filter
            if (res.message && res.message.length > 0) {
                const userFilter = report.get_filter('user');
                if (userFilter) {
                    userFilter.toggle(false);
                    userFilter.df.hidden = 1;
                    report.refresh_filter_fields();
                }
            }
        }
    });
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
    });
}
}


		