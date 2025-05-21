// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Order Detailed Count"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "order_id",
            label: __("Order Form"),
            fieldtype: "MultiSelectList",
            options: "Order Form",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Order Form", txt);
            }
        },
         {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Select",
            options: ["Gurukrupa Export Private Limited"],
            reqd: 0,
            default: "Gurukrupa Export Private Limited",
            // get_data: function (txt) {
            //     return frappe.db.get_link_options("Company", txt);
            //     },
        },
          {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
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
            fieldname: "diamond_quality",
            label: __("Diamond Quality"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
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
        },
        {
            fieldname: "status",
            label: __("Workflow Status"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
            default: "Draft",
        },



    ],
onload: function (report) {
    // Clear Filter Button
    report.page.add_inner_button(__("Clear Filter"), function () {
        report.filters.forEach(function (filter) {
            let field = report.get_filter(filter.fieldname);
            if (filter.fieldname === "branch" || filter.fieldname === "status") return;  // Skip resetting branch

            if (field.df.fieldtype === "MultiSelectList") {
                field.set_value([]);
            } else if (field.df.default) {
                field.set_value(field.df.default);
            } else {
                field.set_value("");
            }
        });
    });

    // Utility to fetch distinct field options
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
                    let options = r.message
                        .map(row => row[field])
                        .filter(value => value && value.trim() !== "");

                    if (filterField === "status") {
                        options = options.filter(val => val !== "Approved" && val !== "Cancelled");
                    }

                    if (["category", "docstatus", "company","status","diamond_quality"].includes(filterField)) {
                        options.unshift("");
                    }

                    const filter = report.get_filter(filterField);
                    filter.df.options = options;
                    filter.refresh();

                    if (filterField === "status" && options.includes("Draft")) {
                        filter.set_value("Draft");
                    }
                }
            },
        });
    }

    // Load options for standard filters
    fetchOptions("Order", "diamond_quality", "diamond_quality", true);
    fetchOptions("Order", "po_no", "customer_po", true);
    fetchOptions("Order", "docstatus", "docstatus", true);
    fetchOptions("Order", "workflow_state", "status", true);




    // Fetch and set Branch based on logged-in user's Employee record
    frappe.call({
    method: "frappe.client.get",
    args: {
        doctype: "User",
        name: frappe.session.user
    },
    callback: function (user_res) {
        const roles = user_res.message.roles.map(role => role.role);
        const isSystemManager = roles.includes("System Manager");

        if (isSystemManager) {
            // If System Manager, fetch all distinct branches 
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Branch",
                    fields: ["name"],
                    limit_page_length: 1000
                },
                callback: function (branch_res) {
                    const branches = (branch_res.message || []).map(b => b.name);
                    const branch_filter = report.get_filter("branch");

                    if (branch_filter) {
                        branch_filter.df.options = branches;
                        branch_filter.refresh();
                    }
                }
            });
        } else {
            // For regular users, fetch branch from Employee record
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fields: ["branch"]
                },
                callback: function (emp_res) {
                    const branches = (emp_res.message || []).map(e => e.branch).filter(b => !!b);
                    const branch_filter = report.get_filter("branch");

                    if (branch_filter) {
                        branch_filter.df.options = branches;
                        branch_filter.refresh();

                        if (branches.length === 1) {
                            branch_filter.set_value(branches[0]);
                        }
                    }
                }
            });
        }
    }
});

}
}