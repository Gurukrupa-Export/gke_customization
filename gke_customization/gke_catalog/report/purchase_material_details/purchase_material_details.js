// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Material Details"] = {
	"filters": [
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
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "purchase_type",
			"label": __("Purchase Type"),
			"fieldtype": "Link",
			"options": "Purchase Type"
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
			"options": "Purchase Invoice"
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
