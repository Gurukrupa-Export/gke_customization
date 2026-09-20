// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["KGGK Jewelex - ERP Order Tally"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Order Date (From)"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Order Date (To)"),
			fieldtype: "Date",
		},
		{
			fieldname: "jewelex_order_no",
			label: __("Jwelex Order No"),
			fieldtype: "Data",
		},
		{
			fieldname: "jewelex_batch_no",
			label: __("Jwelex Batch No"),
			fieldtype: "Data",
		},
		{
			fieldname: "compare_mode",
			label: __("Compare Mode"),
			fieldtype: "Check",
			default: 0,
			hidden: 1,
		},
	],
	onload: function (report) {
		const compare_btn = report.page.add_inner_button(__("Compare"), function () {
			const is_compare = frappe.query_report.get_filter_value("compare_mode");
			const next_value = is_compare ? 0 : 1;
			frappe.query_report.set_filter_value("compare_mode", next_value);
			compare_btn.text(next_value ? __("Back to Report") : __("Compare"));
		});
	},
};
