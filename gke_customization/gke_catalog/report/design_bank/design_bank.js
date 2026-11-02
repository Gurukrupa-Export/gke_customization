// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Design Bank"] = {
	filters: [
		{
			fieldname: "item_category",
			label: __("Item Category"),
			fieldtype: "Autocomplete",
			options: [],
		},
		{
			fieldname: "code_status",
			label: __("Code Status"),
			fieldtype: "Select",
			options: ["", "Active", "Deactive"],
		},
	],

	onload: function (report) {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Item",
				fields: ["item_category"],
				filters: [["item_category", "is", "set"]],
				group_by: "item_category",
				order_by: "item_category asc",
				limit_page_length: 0,
			},
			callback: function (r) {
				const categories = (r.message || [])
					.map((d) => d.item_category)
					.filter(Boolean);

				const filter = report.get_filter("item_category");
				filter.df.options = categories;
				filter.set_data(categories);
				filter.refresh();
			},
		});
	},
};