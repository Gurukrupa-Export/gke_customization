// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Metal Convert to Pure Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "slip_no",
            label: __("Slip No"),
            fieldtype: "Data"
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "from_touch",
            label: __("From Touch"),
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "to_touch",
            label: __("To Touch"),
            fieldtype: "Link",
            options: "Item"
        }
    ]
};
