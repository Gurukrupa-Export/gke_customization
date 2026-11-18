// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Personal Out Entry", {
	approve: function (frm) {
		update_fields_in_child_table(frm, "approve");
	},
});

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.checkin_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("checkin_details");
}
