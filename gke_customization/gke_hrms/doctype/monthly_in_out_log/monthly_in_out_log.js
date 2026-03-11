// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Monthly In-Out Log", {
	refresh(frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__("Fetch Latest Data"), function () {
                frm.call("populate_from_attendance").then(() => {
                    frm.reload_doc();
                })
            })
        }
	},
});
