
// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["CAD Report"] = {
    "filters": [
        {
            fieldname: "start_date",
            label: __("From Date(Order Creation)"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "end_date",
            label: __("To Date(Order Creation)"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
        },  
        // {
        //     fieldname: "order_id",
        //     label: __("Order"),
        //     fieldtype: "MultiSelectList",
        //     options: 'Order',
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return frappe.db.get_link_options('Order', txt, {
        //             owner: frappe.session.user
        //         });
        //     }
        // },
        
        
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
        const current_user = frappe.session.user;
        const arun_only = ["Close Setting", "Close"];
        const restricted_users = [
            "khushal_r@gkexport.com","ashish_m@gkexport.com","rahul_k@gkexport.com",
            "kaushik_g@gkexport.com","chandan_d@gkexport.com","soumaya_d@gkexport.com",
            "arun_l@gkexport.com","sudip_k@gkexport.com"
        ];

        let filters = [["setting_type", "!=", ""]];

        if (current_user === "arun_l@gkexport.com") {
            filters.push(["setting_type", "in", arun_only]);
        } else if (restricted_users.includes(current_user)) {
            filters.push(["setting_type", "not in", arun_only]);
        } else {
        }
        if (txt) {
            filters.push(["setting_type", "like", `%${txt}%`]);
        }

        return frappe.db.get_list("Order", {
            fields: ["distinct setting_type as value"],
            filters: filters,
            limit: 20
        }).then(r => {
            return r.map(d => ({
                value: d.value,
                description: ""
            }));
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
            label: __("Workflow State"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Order", {
                    fields: ["distinct workflow_state as value"],
                }).then(r => {
                    return r.map(d => {
                        return {
                            value: d.value,
                            description: ""  // manually adding empty description
                        }
                    });
                });
            }
        },

        {
            fieldname: "bom_or_cad",
            label: __("BOM or CAD"),
            fieldtype: "Select",
            options: ["CAD"],
            read_only: 1,
            default:"CAD"
        },

    ],
    onload: function(report) {
   

     frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback: function (res) {
            const roles = res.message.roles.map(role => role.role);
            const isSystemManager = roles.includes("System Manager");

            if (!isSystemManager) {
                const user_filter = report.get_filter("employee");
                if (user_filter) {
                    user_filter.$wrapper.hide(); // Hide the filter UI
                }
            }
        }
    });

        const workflow_type_filter = report.get_filter('workflow_type');
        if (workflow_type_filter) {
        workflow_type_filter.set_value(["CAD"]);
    }

        report.page.add_inner_button(__("Clear Filter"), function () {
        report.filters.forEach(function (filter) {
            let field = report.get_filter(filter.fieldname);

            if (field.df.fieldtype === "MultiSelectList") {
                if (Array.isArray(field.df.default)) {
                    field.set_value(field.df.default);
                } else {
                    field.set_value([]);
                }
            } else if (field.df.default !== undefined) {
                field.set_value(field.df.default);
            } else {
                field.set_value("");
            }
        });

        if (workflow_type_filter) {
            workflow_type_filter.set_value(["CAD"]);
        }

        frappe.query_report.refresh();
    });
}
}