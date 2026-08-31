// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Diamond Stock Recevice Report"] = {
    onload(report) {
        init_user_dept_permissions(report);
    },

    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company"),
            "on_change": function() {
                frappe.query_report.set_filter_value("branch", "");
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "reqd": 0,
            "get_query": function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            },
            "on_change": function() {
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 1,
            "get_query": function() {
                let company = frappe.query_report.get_filter_value("company");
                let filters = {};
                if (company) {
                    filters.company = company;
                }
                return { filters: filters };
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "manager",
            "label": __("Manager"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value("company");
                let department = frappe.query_report.get_filter_value("department");
                let filters = {};
                if (company) {
                    filters.company = company;
                }
                if (department) {
                    filters.department = department;
                }
                return { filters: filters };
            },
            "on_change": function() {
                frappe.query_report.set_filter_value("employee", "");
            }
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value("company");
                let department = frappe.query_report.get_filter_value("department");
                let manager = frappe.query_report.get_filter_value("manager");
                let filters = {};
                if (company) {
                    filters.company = company;
                }
                if (department) {
                    filters.department = department;
                }
                if (manager) {
                    filters.reports_to = manager;
                }
                return { filters: filters };
            }
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                const options = [
                    { value: "Issue", description: "Issue" },
                    { value: "Receive", description: "Receive" }
                ];
                return options.filter(d => !txt || d.value.toLowerCase().includes(txt.toLowerCase()));
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end()
        }
    ]
};


// Auto-apply branch/department for non-management; keep full access for management
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