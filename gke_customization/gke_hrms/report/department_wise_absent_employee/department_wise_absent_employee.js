// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Wise Absent Employee"] = {
	filters: [
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
		},
	],
	onload: (report) => {
		report.page
			.add_button(__("Clear Filters"), function () {
				window.open("/app/query-report/Department%20Wise%20Absent%20Employee", "_self");
			})
			.addClass("btn-info");
	},
};
