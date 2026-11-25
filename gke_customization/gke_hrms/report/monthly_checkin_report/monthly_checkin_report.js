// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

const SHOW_FOR_HR = "eval: frappe.user.has_role('System Manager') || frappe.user.has_role('GK HR')";

function is_privileged() {
	return frappe.user.has_role("System Manager") || frappe.user.has_role("GK HR");
}

function set_department_mandatory(report) {
	if (!is_privileged()) return;

	let department_filter = report.get_filter("department");
	department_filter.df.reqd = report.get_filter_value("employee") ? 0 : 1;
	department_filter.refresh();
}

frappe.query_reports["Monthly Checkin Report"] = {
	filters: [
		{
			label: __("From Date"),
			fieldtype: "Date",
			fieldname: "from_date",
			reqd: 1,
			default: frappe.datetime.get_today(),
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
			reqd: is_privileged() ? 1 : 0,
			depends_on: SHOW_FOR_HR,
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				let filters = {};
				if (company) filters.company = company;

				return {
					filters: filters,
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
			on_change: function (report) {
				set_department_mandatory(report);
				report.refresh(true);
			},
		},
	],
	onload: (report) => {
		set_department_mandatory(report);

		report.page
			.add_button(__("Clear Filters"), function () {
				window.open("/app/query-report/Monthly%20Checkin%20Report", "_self");
			})
			.addClass("btn-info");

		report.page
			.add_button(__("Generate"), function () {
				if (is_privileged()) {
					let department = report.get_filter_value("department");
					let employee = report.get_filter_value("employee");
					if (!department && !employee) {
						frappe.msgprint(__("Please select a Department or an Employee"));
						return;
					}
				}
				report.refresh();
			})
			.addClass("btn-primary");
	},
};
