frappe.query_reports["Diamond Broken-Lost Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(
                frappe.datetime.get_today(),
                -6
            )
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
            on_change: function(report) {
                report.set_filter_value("branch", "");
                report.set_filter_value("department", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");

                let filters = {};
                if (company) {
                    filters.company = company;
                }

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
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");

                let filters = {};
                if (company) {
                    filters.company = company;
                }
                if (branch) {
                    filters.branch = branch;
                }

                return {
                    filters: filters
                };
            },
            on_change: function(report) {
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let department = frappe.query_report.get_filter_value("department");

                let filters = {};
                if (company) {
                    filters.company = company;
                }
                if (branch) {
                    filters.branch = branch;
                }
                if (department) {
                    filters.department = department;
                }

                return {
                    filters: filters
                };
            }
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacturer"),
            fieldtype: "Link",
            options: "Manufacturer"
        }
    ]
};