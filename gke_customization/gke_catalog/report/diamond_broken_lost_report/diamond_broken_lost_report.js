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
function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback(user_res) {
            const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
            const management_roles = ["Director", "CEO", "System Manager", "Branch Manager", "Department Manager"];
            const is_management = roles.some(r => management_roles.includes(r));

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fieldname: ["company", "branch", "department"]
                },
                callback(r) {
                    if (!r.message) return;

                    if (r.message.company && report.get_filter("company")) {
                        report.get_filter("company").set_value(r.message.company);
                    }

                    if (r.message.branch && report.get_filter("branch")) {
                        report.get_filter("branch").set_value(r.message.branch);
                        if (!is_management) {
                            report.get_filter("branch").df.read_only = 1;
                            report.get_filter("branch").refresh();
                        }
                    }

                    if (r.message.department && report.get_filter("department")) {
                        report.get_filter("department").set_value(r.message.department);
                        if (!is_management) {
                            report.get_filter("department").df.read_only = 1;
                            report.get_filter("department").refresh();
                        }
                    }

                    setTimeout(() => report.refresh(), 500);
                }
            });
        }
    });
}