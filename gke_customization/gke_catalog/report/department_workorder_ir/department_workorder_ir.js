// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Workorder IR"] = {
    onload: function(report) {
        init_user_dept_permissions(report);
        show_missing_filters_by_name(report);
    },

    filters: [
        {
            fieldname: "jangad_no",
            label: __("Department IR"),
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
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            reqd: 0,
            hidden: 1, // Department IR has no "branch" field in this app; kept for other apps where it exists
            get_query: function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            }
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nIssue\nReceive",
            reqd: 1,
            on_change: function() {
                apply_status_department_restriction(frappe.query_report);
            }
        },
        {
            fieldname: "from_dept",
            label: __("From Dept."),
            fieldtype: "Link",
            options: "Department",
            reqd: 0,
            get_query: function() {
                // Department has no "branch" field, so filter by company only
                let company = frappe.query_report.get_filter_value("company");

                return {
                    filters: company ? { company: company } : {}
                };
            }
        },
        // {
        //     fieldname: "from_manager",
        //     label: __("From Manager"),
        //     fieldtype: "Link",
        //     options: "Employee",
        //     reqd: 0
        // },
        {
            fieldname: "to_dept",
            label: __("To Dept."),
            fieldtype: "Link",
            options: "Department",
            reqd: 0,
            get_query: function() {
                // Department has no "branch" field, so filter by company only
                let company = frappe.query_report.get_filter_value("company");

                return {
                    filters: company ? { company: company } : {}
                };
            }
        },
        // {
        //     fieldname: "to_manager",
        //     label: __("To Manager"),
        //     fieldtype: "Link",
        //     options: "Employee",
        //     reqd: 0
        // },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        },
        // {
        //     fieldname: "sample_no",
        //     label: __("Sample No"),
        //     fieldtype: "Link",
        //     options: "Item",
        //     reqd: 0,
        //     get_query: function() {
        //         return {
        //             filters: {
        //                 has_variants: 1
        //             }
        //         };
        //     }
        // },
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

const MANAGEMENT_ROLES = [
    "Director",
    "CEO",
    "System Manager",
    "Branch Manager",
    "Department Manager"
];

function is_management_user() {
    const roles = frappe.user_roles || [];
    return roles.some(role => MANAGEMENT_ROLES.includes(role));
}

function show_missing_filters_by_name(report) {
    const original_get_filter_values = report.get_filter_values.bind(report);

    report.get_filter_values = function(raise) {
        if (raise) {
            const mandatory = report.filters.filter(f => f.df.reqd || f.df.mandatory);
            const missing_mandatory = mandatory.filter(f => !f.get_value());

            if (missing_mandatory.length > 0) {
                const labels = missing_mandatory.map(f => __(f.df.label)).join(", ");
                const message = __("Please set the following mandatory filter(s): {0}", [labels]);

                report.hide_loading_screen();
                report.toggle_message(raise, message);
                throw "Filter missing";
            }
        }

        return original_get_filter_values(raise);
    };
}

function init_user_dept_permissions(report) {

    const is_management = is_management_user();
    report._is_management = is_management;

    if (!is_management) {
        const status_filter = report.get_filter("status");
        if (status_filter) {
            status_filter.df.options = "Issue\nReceive";
            status_filter.refresh();
        }
    }

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

            report._user_department = r.message.department;

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

            apply_status_department_restriction(report);

            report.refresh();
        }
    });
}

function apply_status_department_restriction(report) {
    if (!report) return;

    const user_department = report._user_department;
    if (!user_department) return;

    const is_management = report._is_management;
    const status = report.get_filter_value("status");
    const from_dept_filter = report.get_filter("from_dept");
    const to_dept_filter = report.get_filter("to_dept");

    if (!from_dept_filter || !to_dept_filter) return;

    if (!is_management) {
        from_dept_filter.df.read_only = 0;
        to_dept_filter.df.read_only = 0;
    }

    if (status === "Issue") {
        report.set_filter_value("from_dept", user_department);
        if (!is_management) {
            from_dept_filter.df.read_only = 1;
        }
    } else if (status === "Receive") {
        report.set_filter_value("to_dept", user_department);
        if (!is_management) {
            to_dept_filter.df.read_only = 1;
        }
    }

    from_dept_filter.refresh();
    to_dept_filter.refresh();
}
