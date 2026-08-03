frappe.query_reports["FG History"] = {
    "filters": [
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "reqd": 0
        },
        {
            "fieldname": "serial_no",
            "label": __("Serial No"),
            "fieldtype": "Data",
            "reqd": 0
        }
    ]
};