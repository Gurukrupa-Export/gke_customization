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
            fieldtype: "Select",
            reqd: 0,
            options:[]
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
            fieldname: "docstatus",
            label: __("Document Status"),
            fieldtype: "Select",
            options: 
            [{ label: "", value: "" },
            { label: "Draft", value: "0" },
            { label: "Submitted", value: "1" },
            { label: "Cancelled", value: "2" }],
            reqd: 0,
            default:"0"
        },
        {
            fieldname: "status",
            label: __("Workflow Status"),
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
    // Get the filter objects
    const branch_field = report.get_filter('designer_branch');
    const user_filter = report.get_filter('user');

    //  Check if user is a restricted Manager
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
            fields: ["name", "branch"]
        },
        callback: function (res) {
            if (res.message && res.message.length > 0) {
                const emp = res.message[0];
                const user_branch = emp.branch;

                // Hide the 'User' filter
                if (user_filter) {
                    user_filter.toggle(false);
                    user_filter.df.hidden = 1;
                }

                // Set value of branch AFTER options are set
                if (branch_field) {
                    // Set a temporary empty list of options first
                    branch_field.df.options = [user_branch].join("\n");
                    branch_field.refresh();
                    
                    // Set the value
                    branch_field.set_value(user_branch);

                    // Disable input box after value is set
                    setTimeout(() => {
                        branch_field.$wrapper.find("select").prop("disabled", true);
                    }, 100);
                }

                report.refresh_filter_fields();
            } else {
                // Not a restricted user — show all branches
                frappe.db.get_list("Employee", {
                    filters: {
                        department: "Sketch - GEPL"
                    },
                    fields: ["branch"],
                    distinct: true
                }).then(records => {
                    const branches = [...new Set(records.map(r => r.branch))].filter(Boolean);
                    if (branch_field) {
                        branch_field.df.options = ["", ...branches].join("\n");
                        branch_field.refresh();
                    }
                });
            }
        }
    });

    // Step 3: Add Clear Filter button
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