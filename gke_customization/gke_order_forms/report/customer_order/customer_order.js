// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Order"] = {
	"filters": [
		{
			"label": __("Item Code"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": 'Item',
			// "reqd": 1
		},
		{
			"label": __("Serial Number"),
			"fieldname": "tag_no",
			"fieldtype": "Link",
			"options": 'Serial No',
			// "reqd": 1
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (in_list(["bm_finish_metal", "bm_finish_gross_weight","bm_finish_diamond"], column.id) ) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("color", "blue");
			value = $value.wrap("<p></p>").parent().html();
		}
		return value;
	},
	onload: (report) => {
		
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Customer%20Order", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() { 
			var item = frappe.query_report.get_filter_value('item');
			frappe.query_report.set_filter_value({				 
				"item": item
			});
		}).addClass("btn-primary");
	}
};
