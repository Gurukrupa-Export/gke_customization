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
            default: frappe.defaults.get_user_default("department"),
            get_query: function() {
                return {
                    filters: {}
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
        const is_admin = frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

        if (!is_admin) {
            const user_department = frappe.defaults.get_user_default("department");

            if (user_department) {
                report.set_filter_value("department", user_department);
            }

            report.page.fields_dict.department.df.read_only = 1;
            report.page.fields_dict.department.df.description = __("Department is locked as per user default");
            report.page.fields_dict.department.refresh();
        }
    }
};