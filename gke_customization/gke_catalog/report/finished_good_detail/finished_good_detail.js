// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Finished Good Detail"] = {
    "filters": [
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("department")
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.month_end()
        }
    ],

    onload: function(report) {
        const can_change_department =
            frappe.user.has_role("System Manager") ||
            frappe.session.user === "Administrator";

        if (!can_change_department) {
            frappe.after_ajax(() => {
                const dept = frappe.defaults.get_user_default("department");
                if (dept) {
                    report.set_filter_value("department", dept);
                }

                const field = report.get_filter("department");
                if (field) {
                    field.df.read_only = 1;
                    field.refresh();
                    $(field.$wrapper).find("input, select").prop("disabled", true);
                }
            });
        }
    }
};