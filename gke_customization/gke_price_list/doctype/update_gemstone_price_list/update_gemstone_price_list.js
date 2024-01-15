// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('Update Gemstone Price List', {
	onload: function(frm) {
		if(frm.doc.name){
			frappe.call({
				method: 'gke_customization.gke_price_list.doctype.update_gemstone_price_list.update_gemstone_price_list.get_value',
				args: {
					'doc': frm.doc,
				},
				callback: function(r) {
					if (!r.exc) {
						// code snippet
					}
				}
			});
		}
	},
	revised_rate: function(frm){
		frm.set_value('difference',frm.doc.revised_rate-frm.doc.rate_per_carat)
	}
});


frappe.ui.form.on('Update Gemstone Price List Details', {
	revised_rate:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		d.difference = d.revised_rate - d.rate_per_carat
		refresh_field('update_gemstone_price_list_details')
	}
})