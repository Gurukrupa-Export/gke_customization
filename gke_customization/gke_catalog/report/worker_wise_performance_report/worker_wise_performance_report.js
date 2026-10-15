frappe.query_reports["Worker Wise Performance Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },

        /*
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            on_change: function(report) {
                report.set_filter_value("branch", "");
                report.set_filter_value("department", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        */

        /*
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");

                let filters = {};
                if (company) filters.company = company;

                return {
                    filters: filters
                };
            },
            on_change: function(report) {
                report.set_filter_value("department", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        */

        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            read_only: !(frappe.user.has_role("System Manager") || frappe.session.user === "Administrator"),
            on_change: function() {
                // Clear employee when department changes
                frappe.query_report.set_filter_value("employee", "");
            }
        },

        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let department = frappe.query_report.get_filter_value("department");

                let filters = {};
                if (department) filters.department = department;

                return {
                    filters: filters
                };
            }
        },

        {
            fieldname: "touch",
            label: __("Touch"),
            fieldtype: "Select",
            options: ["", "10KT", "18KT", "20KT", "22KT", "24KT"]
        }
    ],

    onload: function(report) {
        // Pre-select the Department from the user's Employee record
        frappe.call({
            method: "gke_customization.gke_catalog.report.worker_wise_performance_report.worker_wise_performance_report.get_default_department",
            callback: function(r) {
                if (r.message) {
                    frappe.query_report.set_filter_value("department", r.message);
                }
            }
        });
    }
};