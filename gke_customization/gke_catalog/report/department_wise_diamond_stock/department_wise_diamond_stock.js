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
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
			on_change: function () {
				frappe.query_report.set_filter_value("branch", "");
				frappe.query_report.set_filter_value("department", "");
			}
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
			reqd: 1,
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company")
					}
				};
			},
			on_change: function () {
				frappe.query_report.set_filter_value("department", "");
			}
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			reqd: 1,
			get_query: function () {
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
			const management_roles = [
				"Director",
				"CEO",
				"System Manager",
				"Branch Manager",
				"Department Manager"
			];
			const is_management = roles.some(role => management_roles.includes(role));

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

						if (!is_management) {
							report.get_filter("company").df.read_only = 1;
							report.get_filter("company").refresh();
						}
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