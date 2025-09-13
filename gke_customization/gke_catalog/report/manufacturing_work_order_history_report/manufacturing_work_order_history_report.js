// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Manufacturing Work Order History Report"] = {
    "filters": [
        {
            "fieldname": "manufacturing_work_order",
            "label": __("Manufacturing Work Order"),
            "fieldtype": "Link",
            "options": "Manufacturing Work Order",
            "reqd": 0,
            "width": "200px"
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 0,
            "width": "200px"
        }
    ]
};
