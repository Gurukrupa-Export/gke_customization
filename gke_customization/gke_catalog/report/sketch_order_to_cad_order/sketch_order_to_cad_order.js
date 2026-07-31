// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Order to Cad Order"] = {
    "filters": [
        {"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "width": "100px"},
        {"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "width": "100px"},
        {"fieldname": "sketch_order_id", "label": __("Sketch Order Form ID"), "fieldtype": "Link", "options": "Sketch Order Form", "width": "100px"},
        {"fieldname": "order_form_id", "label": __("Order Form ID"), "fieldtype": "Link", "options": "Order", "width": "100px"},
        {"fieldname": "order_type", "label": __("LOC"), "fieldtype": "Select", "options": ["", "Sales", "Stock Order", "Purchase"], "width": "100px"}
    ]
};
