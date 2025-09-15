// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Issue Receive Report"] = {
    "filters": [
        {
            fieldname: "type",
            label: __("Type"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_list("Employee IR", {
                    fields: ["type"],
                    filters: {
                        type: ["like", "%" + txt + "%"]
                    },
                    limit: 50
                }).then(records => {
                    let unique = [...new Set(records.map(r => r.type))];
                    return unique.map(v => ({ value: v, description: v }));
                });
            }

        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_list("Employee IR", {
                    fields: ["distinct department as value"],
                    filters: [["department", "like", "%" + txt + "%"]],
                    limit: 50
                }).then(records => {
                    return records.map(d => ({ value: d.value, description: d.value }));
                });
            }
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_data: function (txt) {
                return frappe.db.get_link_options("Employee", txt);
            }
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        }
    ]
};
