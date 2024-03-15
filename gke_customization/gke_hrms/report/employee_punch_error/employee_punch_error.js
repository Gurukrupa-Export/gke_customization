// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Punch Error"] = {
	"filters": [
		{
			"label": __("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": 'Employee'
		},
		{
			"label": __("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			// "default": frappe.datetime.get_today(),
		},

	],
	onload: (report) => {
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Employee%20Punch%20Error", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() {
			var date = frappe.query_report.get_filter_value('date');
			var employeeId = frappe.query_report.get_filter_value('employee');
			frappe.query_report.set_filter_value({
				"date": date,
				"employee": employeeId
			});
		}).addClass("btn-primary");

		report.page.add_inner_button(__("Mark as Attendance"), function() {
			var filters = report.get_values();
			console.log(filters);
			var employeeId = filters.employee;
			var date = filters.date;
			// var punchdate = frappe.datetime.str_to_user(date);
			// console.log(punchdate);

			frappe.new_doc("Manual Punch", {
				doctype: "Manual Punch",
				date: date,
				employee: employeeId
			});
			
			// frappe.set_route('Form', 'Manual Punch');
		}).addClass("btn-second")
	}
};
