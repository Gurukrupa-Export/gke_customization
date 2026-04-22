// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Monthly In-Out Log", {
	refresh(frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__("Fetch Latest Data"), function () {
                frm.call({
                    method : "populate_from_attendance",
                    doc: frm.doc,
                    callback: function(r) {
                        // TODO: Handle the response
                        const response = r.message || r.docs || [];
                        console.log(response);
                        if (response.length > 0) {
                            doc_data = response[0];
                            // TODO: Update the form with the response
                            let filed_name = ["net_wrk_hrs", "spent_hrs", "p_out_hrs", "ot_hrs", "in_time", "out_time", "early_hrs", "late_hrs", "late"];
                            filed_name.forEach((field) => {
                                frm.set_value(field, doc_data?.[field] || null);
                            });
                        }
                    }
                })
            })
        }
	},
});
