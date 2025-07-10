// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Personal Out Entry", {
	// onload(frm) {
	// 	let start = frappe.datetime.month_start(frappe.datetime.get_today())
	// 	let end = frappe.datetime.month_end(frappe.datetime.get_today())
	// 	frm.set_value({"from_date":start,"to_date":end})
	// },
	// after_save: function(frm) {
	// 	frm.call("get_checkin_details",{"from_log":true})
	// }, 
	approve: function(frm){
		update_fields_in_child_table(frm, "approve");
	}
});

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.checkin_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("checkin_details");
}