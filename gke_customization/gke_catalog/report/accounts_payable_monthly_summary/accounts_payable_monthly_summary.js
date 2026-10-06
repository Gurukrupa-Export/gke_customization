// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Accounts Payable Monthly Summary"] = {
	filters: [],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Aging Summary"), function () {
			frappe.set_route("query-report", "Accounts Payable Aging Summary");
		});
	},
};