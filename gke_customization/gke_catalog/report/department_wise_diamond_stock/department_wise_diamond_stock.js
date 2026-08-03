frappe.query_reports["Department Wise Diamond Stock"] = {
	onload(report) {
		init_user_dept_permissions(report);
	},

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			hidden: 1
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
			hidden: 1
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department"
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
		callback: function (user_res) {
			const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
			const is_admin = frappe.session.user === "Administrator" || roles.includes("System Manager");

			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Employee",
					filters: { user_id: frappe.session.user },
					fieldname: ["company", "branch", "department"]
				},
				callback: function (r) {
					if (!r.message) return;

					if (r.message.company && report.get_filter("company")) {
						report.get_filter("company").set_value(r.message.company);
					}

					if (r.message.branch && report.get_filter("branch")) {
						report.get_filter("branch").set_value(r.message.branch);
					}

					if (r.message.department && report.get_filter("department")) {
						report.get_filter("department").set_value(r.message.department);

						if (!is_admin) {
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