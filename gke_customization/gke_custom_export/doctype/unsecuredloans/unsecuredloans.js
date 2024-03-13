// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Unsecuredloans", {
	// refresh(frm) {
    //     // select * from `tabContact Email` where parent = 'Vishal'
    //     // select * from `tabContact Phone` where parent = 'Vishal'
    //     borrower_name = cur_frm.doc.unsecuredloans_name;
    //     frappe.db.get_value('Contact Email', {parent :'borrower_name'},['email_id'], (r) =>{
    //         console.log(r);
    //     })
	// },
    unsecuredloans_name: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.unsecuredloans.unsecuredloans.get_email_id',
			args: {
				'unsecuredloans_name': frm.doc.unsecuredloans_name,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
                    frm.set_value("email_address", r.message[0].email_id);				
				}
			}
		});
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.unsecuredloans.unsecuredloans.get_phone',
			args: {
				'unsecuredloans_name': frm.doc.unsecuredloans_name,
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
