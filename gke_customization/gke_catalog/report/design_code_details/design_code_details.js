// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Design Code Details"] = {
	"filters": [
           {
            fieldname: "item_name",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        }
	],
onload: function(report) {
	 report.page.add_inner_button(__("Clear Filter"), function () {
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);
                if (field.df.fieldtype === "MultiSelectList") {
                    field.set_value([]);
                } else if (field.df.default) {
                    field.set_value(field.df.default);
                } else {
                    field.set_value("");
                }
            });
        });
},
};
