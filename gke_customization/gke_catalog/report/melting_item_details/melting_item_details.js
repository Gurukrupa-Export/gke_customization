// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const MELTING_ITEM_DETAILS_TABS = [
	"Transaction",
	"Serial No Detail",
	"Material Detail",
	"Serial No Wise Detail",
];

frappe.query_reports["Melting Item Details"] = {
	filters: [
		{
			"fieldname": "tab_view",
			"label": __("Tab View"),
			"fieldtype": "Data",
			"default": "Transaction",
			"hidden": 1,
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
		},
		{
			"fieldname": "refining_id",
			"label": __("Refining ID"),
			"fieldtype": "Link",
			"options": "Refining Entry",
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": [
				"",
				"Draft",
				"Physical Verification",
				"Submitted",
				"Received",
				"Classified",
				"Refining In Progress",
				"Recovery Entered",
				"Recovery Verified",
				"Completed",
				"Transferred",
				"Cancelled",
			].join("\n"),
		},
	],

	onload(report) {
		if (report.melting_item_details_tabs_rendered) {
			return;
		}
		report.melting_item_details_tabs_rendered = true;

		const active_tab = report.get_filter_value("tab_view") || "Transaction";
		const $buttons = {};

		const set_active_tab = (tab) => {
			MELTING_ITEM_DETAILS_TABS.forEach((t) => {
				$buttons[t]
					.removeClass("btn-primary btn-default")
					.addClass(t === tab ? "btn-primary" : "btn-default");
			});
		};

		MELTING_ITEM_DETAILS_TABS.forEach((tab) => {
			$buttons[tab] = report.page.add_button(
				__(tab),
				() => {
					if (report.get_filter_value("tab_view") === tab) {
						return;
					}
					report.set_filter_value("tab_view", tab);
					set_active_tab(tab);
				},
				{ btn_class: tab === active_tab ? "btn-primary" : "btn-default" }
			);
		});
	},
};
