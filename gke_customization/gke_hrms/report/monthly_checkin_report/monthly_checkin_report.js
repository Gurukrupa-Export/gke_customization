// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

// Only System Manager / GK HR see Company, Branch, Department and Employee filters.
// Managers and normal employees get their data resolved on the server from their login.
const SHOW_FOR_HR = "eval: frappe.user.has_role('System Manager') || frappe.user.has_role('GK HR')";

function is_privileged() {
	return frappe.user.has_role("System Manager") || frappe.user.has_role("GK HR");
}

frappe.query_reports["Monthly Checkin Report"] = {
	filters: [
		{
			label: __("From Date"),
			fieldtype: "Date",
			fieldname: "from_date",
			reqd: 1,
			default: frappe.datetime.get_today(),
			on_change: function (query_report) {
				var from_date = query_report.get_values().from_date;
				if (!from_date) {
					return;
				}
			},
		},
		{
			label: __("To Date"),
			fieldtype: "Date",
			fieldname: "to_date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			label: __("Company"),
			fieldtype: "Link",
			fieldname: "company",
			options: "Company",
			reqd: is_privileged() ? 1 : 0,
			default: frappe.defaults.get_user_default("Company"),
			depends_on: SHOW_FOR_HR,
		},
		{
			label: __("Branch"),
			fieldtype: "Link",
			fieldname: "branch",
			options: "Branch",
			depends_on: SHOW_FOR_HR,
		},
		{
			label: __("Department"),
			fieldtype: "Link",
			fieldname: "department",
			options: "Department",
			depends_on: SHOW_FOR_HR,
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: company ? { company: company } : {},
				};
			},
		},
		{
			label: __("Employee"),
			fieldtype: "Link",
			fieldname: "employee",
			options: "Employee",
			depends_on: SHOW_FOR_HR,
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				let department = frappe.query_report.get_filter_value("department");
				let filters = { status: "Active" };
				if (company) filters.company = company;
				if (department) filters.department = department;

				return {
					filters: filters,
				};
			},
		},
	],
	onload: (report) => {
		report.page
			.add_button("Clear Filters", function () {
				window.open("/app/query-report/Monthly%20Checkin%20Report", "_self");
			})
			.addClass("btn-info");

		report.page
			.add_button("Generate", function () {
				var department = frappe.query_report.get_filter_value("department");
				if (is_privileged() && !department && !frappe.query_report.get_filter_value("employee")) {
					frappe.query_report.set_filter_value({
						department: department,
					});
					frappe.msgprint(__("No department Selected"));
				} else if (is_privileged()) {
					frappe.query_report.set_filter_value({
						department: department,
					});
				}
				report.refresh();
			})
			.addClass("btn-primary");
	},
};
