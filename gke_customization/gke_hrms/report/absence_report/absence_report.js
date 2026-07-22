// Copyright (c) 2024, Gurapps/gke_customization/gke_customization/gke_hrms/report/absence_report/absence_report.jsukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Absence Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            on_change: function (report) {
                let company = frappe.query_report.get_filter_value("company");
                let branch_filter = frappe.query_report.get_filter("branch");
                let department_filter = frappe.query_report.get_filter("department");

                if (company === "KG GK Jewellers Private Limited") {
                    branch_filter.df.read_only = 1;
                    branch_filter.set_value("");
                    branch_filter.refresh();
                } else {
                    branch_filter.df.read_only = 0;
                    branch_filter.refresh();
                }

                department_filter.set_value("");
                department_filter.refresh();
            },
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            depends_on: "eval:doc.company && doc.company != 'KG GK Jewellers Private Limited'",
            get_query: function () {
                let company = frappe.query_report.get_filter_value("company");
                return company ? { filters: { company } } : {};
            },
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            get_query: function () {
                let company = frappe.query_report.get_filter_value("company");
                return company ? { filters: { company: company } } : {};
            },
        },
    ],

    onload: function (report) {
        report.refresh();
    },
};