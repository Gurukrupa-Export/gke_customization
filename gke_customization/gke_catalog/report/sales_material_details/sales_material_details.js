// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Material Details"] = {
	"filters": [
		// {
		// 	"fieldname": "company",
		// 	"label": __("Company"),
		// 	"fieldtype": "Link",
		// 	"options": "Company",
		// 	"default": frappe.defaults.get_user_default("Company")
		// },
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "invoice_no",
			"label": __("Invoice No"),
			"fieldtype": "Link",
			"options": "Sales Invoice"
		},
		{
			"fieldname": "invoice_type",
			"label": __("Sales Invoice / Credit Note"),
			"fieldtype": "Select",
			"options": "\nSales Invoice\nCredit Note",
			"default": ""
		},
		{
			"fieldname": "sales_type",
			"label": __("Sales Type"),
			"fieldtype": "Link",
			"options": "Sales Type"
		},
		{
			"fieldname": "summary_view",
			"label": __("Summary View"),
			"fieldtype": "Check",
			"default": 0,
			"hidden": 1
		}
	],

	onload: function(report) {
		let $btn = report.page.add_inner_button(__("Invoice Summary"), function() {
			let is_summary = frappe.query_report.get_filter_value("summary_view");
			frappe.query_report.set_filter_value("summary_view", is_summary ? 0 : 1);
			$btn.text(is_summary ? __("Invoice Summary") : __("Detailed View"));
			report.refresh();
		});
	}
};
