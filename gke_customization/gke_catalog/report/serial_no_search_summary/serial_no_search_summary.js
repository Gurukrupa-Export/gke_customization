// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No Search Summary"] = {
	filters: [
		{
			fieldname: "search_mode",
			label: __("Search Mode"),
			fieldtype: "Select",
			options: ["Bulk", "Single"],
			default: "Bulk",
			reqd: 0,
		},
		{
			fieldname: "serial_no",
			label: __("Serial No"),
			fieldtype: "Link",
			options: "Serial No",
			width: 200,
			reqd: 0,
			depends_on: "eval:doc.search_mode=='Single'",
		},
		{
			fieldname: "search_text",
			label: __("Search Serial No"),
			fieldtype: "Small Text",
			reqd: 0,
			width: 400,
			depends_on: "eval:doc.search_mode=='Bulk'",
			description: __("Paste Serial Nos and/or Item Codes. Supports newline, comma, semicolon, or space.")
		}
	],

	onload: function(report) {
		if (frappe.route_options) {
			if (frappe.route_options.search_mode) {
				report.set_filter_value("search_mode", frappe.route_options.search_mode);
			}
			if (frappe.route_options.serial_no) {
				report.set_filter_value("serial_no", frappe.route_options.serial_no);
			}
			if (frappe.route_options.search_text) {
				report.set_filter_value("search_text", frappe.route_options.search_text);
			}
		}
	}
};