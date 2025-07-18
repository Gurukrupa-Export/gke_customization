// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Customer Scorecard Period", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("Customer Scorecard Period", {
	onload: function (frm) {
		let criteria_grid = frm.get_field("criteria").grid;
		criteria_grid.toggle_enable("criteria_name", false);
		criteria_grid.toggle_enable("weight", false);
		criteria_grid.toggle_display("max_score", true);
		criteria_grid.toggle_display("formula", true);
		criteria_grid.toggle_display("score", true);
	},
});
