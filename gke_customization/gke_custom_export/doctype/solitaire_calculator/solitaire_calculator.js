// Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
// For license information, please see license.txt

frappe.ui.form.on('Solitaire Calculator', {
	onload: function(frm) {
		if(frm.doc.usd_to_inr == 0){
			frappe.call({
				method: 'gke_customization.gke_custom_export.doctype.solitaire_calculator.solitaire_calculator.get_usd_inr',
				callback: function(r) {
					if (!r.exc) {
						console.log(r.message)
						frm.set_value('usd_to_inr',r.message)
					}
				}
			});
		}
	}
});
