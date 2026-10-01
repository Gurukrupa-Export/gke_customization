// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Cad Dashboard Script"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
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
