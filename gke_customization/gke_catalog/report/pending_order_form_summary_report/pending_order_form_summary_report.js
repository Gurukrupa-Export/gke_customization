// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Order Form Summary Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Select",
            "options": "\nGurukrupa Export Private Limited\nKG GK Jewellers Private Limited",
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "reqd": 0
        },
        {
            "fieldname": "order_form_no",
            "label": __("Order Form No."),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Order Form', txt);
            },
            "reqd": 0
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        const order_form = data.erp_order_no;

        // Skip SUMMARY row checks
        if (order_form && order_form.toString().includes('Total Order Forms:')) {
            // Make summary clickable with bold styling
            if (["no_of_orders", "no_of_orders_approved", "no_of_orders_pending", "cad_pending", "bom_pending"].includes(column.fieldname) && value && parseInt(value) > 0) {
                return `<a onclick="openSummaryDetail('${column.fieldname}')" style="cursor: pointer; font-weight: bold;">${value}</a>`;
            }
            return value;
        }

        // Make numeric columns clickable for data rows
        if (value && parseInt(value) > 0) {
            if (column.fieldname === "no_of_orders") {
                return `<a onclick="openOrderList('${order_form}', 'All Orders')" style="cursor: pointer;">${value}</a>`;
            }
            if (column.fieldname === "no_of_orders_approved") {
                return `<a onclick="openOrderList('${order_form}', 'Orders Approved')" style="cursor: pointer;">${value}</a>`;
            }
            if (column.fieldname === "no_of_orders_pending") {
                return `<a onclick="openOrderList('${order_form}', 'Orders Pending')" style="cursor: pointer;">${value}</a>`;
            }
            if (column.fieldname === "cad_pending") {
                return `<a onclick="openOrderList('${order_form}', 'CAD Pending')" style="cursor: pointer;">${value}</a>`;
            }
            if (column.fieldname === "bom_pending") {
                return `<a onclick="openOrderList('${order_form}', 'IBM Pending')" style="cursor: pointer;">${value}</a>`;
            }
        }

        return value;
    },

    "onload": function(report) {
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

function openOrderList(order_form, status_type) {
    frappe.route_options = {
        "cad_order_form": order_form
    };

    if (status_type === "All Orders") {
        // Show all orders
    } 
    else if (status_type === "Orders Approved") {
        frappe.route_options.workflow_state = "Approved";  
    }
    else if (status_type === "Orders Pending") {
        frappe.route_options.workflow_state = ["!=", "Approved"];
    }
    else if (status_type === "CAD Pending") {
        frappe.route_options.workflow_state = ["!=", "Approved"];
    } 
    else if (status_type === "IBM Pending") {
        frappe.route_options.workflow_state = ["!=", "Approved"];
    }

    frappe.set_route("List", "Order");
}

function openSummaryDetail(fieldname) {
    frappe.msgprint(`Summary Detail: ${fieldname}`, "Summary Information");
}
