// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Mould Report"] = {
    filters: [
        {
            fieldname: "mwo",
            label: __("MWO"),
            fieldtype: "Link",
            options: "Manufacturing Work Order",
            reqd: 1,
            width: 220
        }
    ]
};