// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Duplicate Orders"] = {
    tree: true,
    name_field: "order_id",
    parent_field: "parent_order",
    initial_depth: 0,
    
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -30)
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        }
    ]
};
