// Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
// For license information, please see license.txt

frappe.ui.form.on('Solitaire Calculator', {
	onload: function(frm) {
        frappe.call({
			method: 'catalog.catalog.doctype.solitaire_calculator.solitaire_calculator.get_usd_inr',
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('usd_to_inr',r.message)
				}
			}
		});

		frappe.call({
			method: 'catalog.catalog.doctype.solitaire_calculator.solitaire_calculator.date_time',
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('date',r.message)
				}
			}
		});

	}
});
