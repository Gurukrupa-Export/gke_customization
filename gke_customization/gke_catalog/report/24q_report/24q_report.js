// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["24Q Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
            on_change: function () {
                let company = frappe.query_report.get_filter_value("company");

                if (!company) {
                    frappe.query_report.set_filter_value(
                        "company",
                        frappe.defaults.get_user_default("Company")
                    );
                }
            },
        },
        {
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
        },
        {
            fieldname: "quarter",
            label: __("Quarter"),
            fieldtype: "Select",
            options: "\nQ1\nQ2\nQ3\nQ4",
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options:
                "\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember\nJanuary\nFebruary\nMarch",
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },
    ],

    onload: function (report) {

        let user_roles = frappe.user_roles || [];

        let can_change_company =
            user_roles.includes("System Manager") ||
            user_roles.includes("Manager");

        let company_filter = report.get_filter("company");

        if (!can_change_company) {
            company_filter.df.read_only = 1;
            company_filter.refresh();
        }
    },
};