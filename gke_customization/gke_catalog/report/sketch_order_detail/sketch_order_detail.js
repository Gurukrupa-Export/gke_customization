// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Order Detail"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date"
        },
        {
            fieldname: "branch",
            label: "Branch",
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            },
            //hidden:1
        },
        {
            fieldname: "customer_group",
            label: "Customer Group",
            fieldtype: "Link",
            options: "Customer Group",
            hidden:1
        },
 {
    fieldname: "docstatus",
    label: "Sketch Order Docstatus",
    fieldtype: "Data",
    hidden: 1
},

//  {
//     fieldname: "docstatus",
//     label: "Sketch Order Docstatus",
//     fieldtype: "MultiSelectList",
//     hidden: 1,
//     get_data: () => [
//         { value: "0", description: "Draft" },
//         { value: "1", description: "Submitted" },
//         { value: "2", description: "Cancelled" }
//     ]
// },
    {
        fieldname: "workflow_state",
        label: "Workflow State",
        fieldtype: "Data",
        hidden: 1
    }
    ],
     onload: function(report) {
        // const params = frappe.query_string;

        // if (params.customer) {
        //     report.set_filter_value("customer", params.customer.split(","));
        // }

        // if (params.workflow_state) {
        //     report.set_filter_value("workflow_state", params.workflow_state);
        // }

        // if (params.docstatus) {
        //     report.set_filter_value("docstatus", params.docstatus);
        // }

        // if (params.from_date) {
        //     report.set_filter_value("from_date", params.from_date);
        // }

        // if (params.to_date) {
        //     report.set_filter_value("to_date", params.to_date);
        // }

        
        report.page.add_inner_button(__("← Back"), function () {
            frappe.set_route("query-report", "Sketch Order Summary");
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
};
