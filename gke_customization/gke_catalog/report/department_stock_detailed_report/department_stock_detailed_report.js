// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Stock Detailed Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "reqd": 0
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        },
        {
            "fieldname": "category",
            "label": __("Category"),
            "fieldtype": "Data",
            "reqd": 0
        },
        {
            "fieldname": "sub_category",
            "label": __("Sub Category"),
            "fieldtype": "Data",
            "reqd": 0
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "reqd": 0
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 0
        },
        {
            "fieldname": "setting_type",
            "label": __("Setting Type"),
            "fieldtype": "Select",
            "options": " \nOpen \nClose",
            "reqd": 0
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nStock\nTransfer\nLocker\nIssue to Lab\nApprove\nSalesman\nRepair",
            "reqd": 0
        }
    ],

    onload(report) {
        init_user_dept_permissions(report);
    }
};

// Auto‑apply branch/department for non‑management; keep full access for management
function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback(user_res) {
            const roles = (user_res.message && user_res.message.roles || []).map(r => r.role);
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

                    // Company
                    if (r.message.company && report.get_filter("company")) {
                        report.get_filter("company").set_value(r.message.company);
                    }

                    // Branch
                    if (r.message.branch && report.get_filter("branch")) {
                        report.get_filter("branch").set_value(r.message.branch);
                        if (!is_management) {
                            report.get_filter("branch").df.read_only = 1;
                            report.get_filter("branch").refresh();
                        }
                    }

                    // Department
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
