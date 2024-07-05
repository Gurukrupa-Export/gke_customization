// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Wise Absent Employee"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"mandatory": 1,
		},
	],
	onload: (report) => {
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Department%20Wise%20Absent%20Employee", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() {
			var company = frappe.query_report.get_filter_value('company');
			frappe.query_report.set_filter_value({
				"company": company,
			});
		}).addClass("btn-primary");
	}

};
