// Copyright (c) 2024, Gurukrupa and contributors
/* eslint-disable */

frappe.query_reports["OT Report"] = {
    filters: [
        {
            label: __("Month"),
            fieldtype: "Select",
            fieldname: "month",
            reqd: 1,
            options: [],
            default: () => {
                const dateObject = new Date();
                const options = { month: "short", year: "numeric" };
                const dateString = dateObject.toLocaleDateString("en-US", options);
                return dateString;
            },
            on_change: function(query_report) {
                var _month = query_report.get_filter_value('month');
                if (!_month) return;
                let firstDayOfMonth = moment(_month, "MMM YYYY").toDate();
                firstDayOfMonth = frappe.datetime.obj_to_str(firstDayOfMonth);
                let lastDayOfMonth = frappe.datetime.month_end(firstDayOfMonth);
                query_report.set_filter_value({
                    "from_date": firstDayOfMonth,
                    "to_date":   lastDayOfMonth
                });
            }
        },
        {
            label: __("From Date"),
            fieldtype: "Date",
            fieldname: "from_date",
            read_only: 1,
            default: frappe.datetime.month_start(frappe.datetime.get_today()),
            on_change: function(query_report) {
                var from_date = query_report.get_values().from_date;
                if (!from_date) return;
                let date    = new moment(from_date);
                var to_date = date.endOf('month').format();
                query_report.set_filter_value({ "to_date": to_date });
            }
        },
        {
            label: __("To Date"),
            fieldtype: "Date",
            fieldname: "to_date",
            reqd: 1,
            read_only: 1,
            default: frappe.datetime.month_end(frappe.datetime.get_today())
        },
        {
            label: __("Company"),
            fieldtype: "Link",
            fieldname: "company",
            options: "Company",
            default: frappe.defaults.get_default("company")
        },
        {
            label: __("Branch"),
            fieldtype: "Link",
            fieldname: "branch",
            options: "Branch"
        },
        {
            label: __("Department"),
            fieldtype: "Link",
            fieldname: "department",
            options: "Department"
        },
        {
            label: __("Employee"),
            fieldtype: "Link",
            fieldname: "employee",
            options: "Employee"
        }
    ],

    onload: function(report) {
        fetch_month_list();
    }
};


function fetch_month_list() {
    frappe.call({
        method: "gke_customization.gke_catalog.report.ot_report.ot_report.get_month_range",
        freeze: false,
        callback: function(r) {
            var month = frappe.query_report.get_filter('month');
            month.df.options.push(...r.message);
            month.refresh();
        }
    });
}
