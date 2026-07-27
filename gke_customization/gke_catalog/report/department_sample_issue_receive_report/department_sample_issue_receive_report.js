// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Sample Issue Receive Report"] = {
    onload: function(report) {
        init_user_dept_permissions(report);
    },

    filters: [
        {
            fieldname: "jangad_no",
            label: __("Jangad No"),
            fieldtype: "Link",
            options: "Department IR",
            reqd: 0
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 0,
            default: frappe.defaults.get_user_default("Company"),
            on_change: function() {
                frappe.query_report.set_filter_value("branch", "");
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            reqd: 0,
            get_query: function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            },
            on_change: function() {
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            reqd: 0,
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
            }
        },
        {
            fieldname: "from_dept",
            label: __("From Dept."),
            fieldtype: "Link",
            options: "Department",
            reqd: 0,
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
            }
        },
        {
            fieldname: "from_manager",
            label: __("From Manager"),
            fieldtype: "Link",
            options: "Employee",
            reqd: 0
        },
        {
            fieldname: "to_dept",
            label: __("To Dept."),
            fieldtype: "Link",
            options: "Department",
            reqd: 0,
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
            }
        },
        {
            fieldname: "to_manager",
            label: __("To Manager"),
            fieldtype: "Link",
            options: "Employee",
            reqd: 0
        },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        },
        {
            fieldname: "sample_no",
            label: __("Sample No"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0,
            get_query: function() {
                return {
                    filters: {
                        has_variants: 1
                    }
                };
            }
        },
        {
            fieldname: "category",
            label: __("Category"),
            fieldtype: "Link",
            options: "Attribute Value",
            reqd: 0,
            get_query: function() {
                return {
                    filters: {
                        is_category: 1
                    }
                };
            }
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nIssue\nReceive",
            reqd: 0
        },
        {
            fieldname: "from_date",
            label: __("From"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        }
    ]
};

function init_user_dept_permissions(report) {

    const roles = frappe.user_roles || [];
    const management_roles = [
        "Director",
        "CEO",
        "System Manager",
        "Branch Manager",
        "Department Manager"
    ];

    const is_management = roles.some(role =>
        management_roles.includes(role)
    );

    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: {
                user_id: frappe.session.user
            },
            fieldname: ["company", "branch", "department"]
        },
        callback(r) {
            if (!r.message) return;

            if (r.message.company && report.get_filter("company")) {
                report.set_filter_value("company", r.message.company);
            }

            if (r.message.branch && report.get_filter("branch")) {
                report.set_filter_value("branch", r.message.branch);

                if (!is_management) {
                    report.get_filter("branch").df.read_only = 1;
                    report.get_filter("branch").refresh();
                }
            }

            if (r.message.department && report.get_filter("department")) {
                report.set_filter_value("department", r.message.department);

                if (!is_management) {
                    report.get_filter("department").df.read_only = 1;
                    report.get_filter("department").refresh();
                }
            }

            report.refresh();
        }
    });
}
