// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Order Form Summary Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Select",
            "options": "\nGurukrupa Export Private Limited\nKG GK Jewellers Private Limited",
            "default": "Gurukrupa Export Private Limited",
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
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
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
        
        // Get Order Form name from second column
        const order_form = data.erp_order_no;
        
        // Make No. of Orders clickable
        if (column.fieldname === "no_of_orders" && value && parseInt(value) > 0) {
            return `<a onclick="openOrderList('${order_form}', 'All Orders')" style="cursor: pointer;">${value}</a>`;
        }
        
        // No. of Designs - NOT clickable (removed formatter)
        
        if (column.fieldname === "bom_pending" && value && parseInt(value) > 0) {
            return `<a onclick="openOrderList('${order_form}', 'BOM Pending')" style="cursor: pointer;">${value}</a>`;
        }
        
        if (column.fieldname === "cad_pending" && value && parseInt(value) > 0) {
            return `<a onclick="openOrderList('${order_form}', 'CAD Pending')" style="cursor: pointer;">${value}</a>`;
        }
        
        if (column.fieldname === "total_pending_orders" && value && parseInt(value) > 0) {
            return `<a onclick="openOrderList('${order_form}', 'Total Pending')" style="cursor: pointer;">${value}</a>`;
        }
        
        return value;
    }
};

// Global function to open Order list with filters
function openOrderList(order_form, status_type) {
    let filters = [
        ["Order", "cad_order_form", "=", order_form]
    ];
    
    // Add status-specific filters for PENDING orders only
    if (status_type === "All Orders") {
        // Show all orders for this Order Form
        // No additional filter needed
    }
    else if (status_type === "BOM Pending") {
        // BOM states - NOT in CAD idx AND not approved
        filters.push(["Order", "workflow_state", "!=", "Approved"]);
    } 
    else if (status_type === "CAD Pending") {
        // CAD states AND not approved
        filters.push(["Order", "workflow_state", "!=", "Approved"]);
    } 
    else if (status_type === "Total Pending") {
        filters.push(["Order", "workflow_state", "!=", "Approved"]);
    }
    
    // Navigate to Order List with filters
    frappe.route_options = {
        "cad_order_form": order_form
    };
    
    if (status_type !== "All Orders") {
        frappe.route_options.workflow_state = ["!=", "Approved"];
    }
    
    frappe.set_route("List", "Order");
}

