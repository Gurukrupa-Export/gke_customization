// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Variant Details"] = {
	filters: [
		{
			reqd: 1,
			default: "",
			options: "Item",
			label: __("Item"),
			fieldname: "item",
			fieldtype: "Link",
			get_query: () => {
				return {
					filters: [
                        ["Item", "has_variants", "=", 1],
                        ["Item", "item_subcategory", "!=", ""]
                    ],
				};
			},
		},
	],
};
