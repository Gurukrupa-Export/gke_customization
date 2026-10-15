// Copyright (c) 2026
// Accounts Payable Aging Summary - Script Report
// Asli report HTML (message) me draw hoti hai; yahan sirf default khali grid chhupayi jaati hai.

const AP_AGING_HIDE_CSS =
	".ap-aging-report .datatable, .ap-aging-report .report-summary, .ap-aging-report .chart-wrapper" +
	"{display:none !important;}";

const AP_AGING_REPORT = {
	filters: [
		{
			fieldname: "supplier_type",
			label: __("Supplier Type"),
			fieldtype: "Select",
			options: "All Suppliers\nDiamonds",
			default: "All Suppliers",
		},
	],

	onload: function (report) {
		if (!document.getElementById("ap-aging-summary-style")) {
			$("<style id='ap-aging-summary-style'>").text(AP_AGING_HIDE_CSS).appendTo("head");
		}
		if (report && report.page && report.page.wrapper) {
			report.page.wrapper.addClass("ap-aging-report");
		}
	},

	after_datatable_render: function (datatable) {
		// grid kabhi dikh jaye to seedha chhupa do
		if (datatable && datatable.wrapper) {
			$(datatable.wrapper).hide();
		}
		$(".report-summary, .chart-wrapper").hide();
	},
};

// Report ka naam "Accounts Payable Aging Summary" ho ya "... Report", dono par chalega
frappe.query_reports["Accounts Payable Aging Summary"] = AP_AGING_REPORT;
frappe.query_reports["Accounts Payable Aging Summary Report"] = AP_AGING_REPORT;