// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

{% include 'gke_customization/gke_hrms/report/punch_error_utils.js' %}

frappe.query_reports["Attendance Punch Error Report"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": 'Company',
			"reqd": 1
		},
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": 'Department',
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company')
				return {
					"doctype": "Department",
					"filters": {"company": company}
				}
			},
		},
		{
			"label": __("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": 'Employee'
		},
		{
			"label": __("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": 'Branch'
		},
	],
	onload: (report) => {
		report.page.add_button(__("Clear Filters"), function() {
			window.open("/app/query-report/Attendance%20Punch%20Error%20Report", "_self")
		}).addClass("btn-info");

		add_mark_attendance_button(report);
		enable_single_row_selection();
	},
	get_datatable_options(options) {
		return get_punch_error_datatable_options(options);
	}
};
