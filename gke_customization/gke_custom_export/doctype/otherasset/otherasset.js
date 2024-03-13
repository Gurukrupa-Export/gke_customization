// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("OtherAsset", {
	otherasset_name: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.otherasset.otherasset.get_email_id',
			args: {
				'otherasset_name': frm.doc.otherasset_name,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
                    frm.set_value("email_address", r.message[0].email_id);				
				}
			}
		});
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.otherasset.otherasset.get_phone',
			args: {
				'otherasset_name': frm.doc.otherasset_name,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
                    frm.set_value("phone", r.message[0].phone);				
				}
			}
		});
	},
});
