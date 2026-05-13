frappe.query_reports["OT Report"] = {
    onload: function (report) {
        frappe.call({
            method: "gke_customization.gke_catalog.report.ot_report.ot_report.get_month_range",
            callback: function (r) {
                if (r.message) {
                    let month_field = report.get_filter("month");
                    if (month_field) {
                        month_field.df.options = [""].concat(r.message);
                        month_field.refresh();
                    }
                }
            }
        });
    },

    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },

        // --- Mode: Single Month ---
        {
            fieldname: "month",
            label: __("Month (Single)"),
            fieldtype: "Select",
            options: "",
            description: "Select a single month. Overrides all other date filters.",
            on_change: function () {
                let report = frappe.query_report;
                let val    = report.get_filter_value("month");
                if (val) {
                    report.set_filter_value("months", "");
                    report.set_filter_value("from_date", "");
                    report.set_filter_value("to_date", "");
                }
            }
        },

        // --- Mode: Multiple Months ---
        {
            fieldname: "months",
            label: __("Months (Multi)"),
            fieldtype: "Data",
            placeholder: "e.g. Jan 2026, Feb 2026, Mar 2026",
            description: "Comma separated months. Used when Single Month is not selected.",
            on_change: function () {
                let report = frappe.query_report;
                let val    = report.get_filter_value("months");
                if (val) {
                    report.set_filter_value("month", "");
                    report.set_filter_value("from_date", "");
                    report.set_filter_value("to_date", "");
                }
            }
        },

        // --- Mode: Date Range ---
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            description: "Used when neither Single Month nor Multi Month is selected.",
            on_change: function () {
                let report = frappe.query_report;
                let val    = report.get_filter_value("from_date");
                if (val) {
                    report.set_filter_value("month", "");
                    report.set_filter_value("months", "");
                }
            }
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            on_change: function () {
                let report = frappe.query_report;
                let val    = report.get_filter_value("to_date");
                if (val) {
                    report.set_filter_value("month", "");
                    report.set_filter_value("months", "");
                }
            }
        },
    ]
};
