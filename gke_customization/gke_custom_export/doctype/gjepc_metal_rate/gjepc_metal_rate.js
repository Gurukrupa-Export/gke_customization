// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('GJEPC Metal Rate', {
	onload: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.gjepc_metal_rate.gjepc_metal_rate.get_gjepc_rate',
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
					frm.set_value('rate_in_ounce',r.message[0][1])
					
					cur_frm.clear_table('gjepc_metal_rate_details');
					var arrayLength = r.message.length;
					for (var i = 0; i < arrayLength; i++) {
						let row = frm.add_child('gjepc_metal_rate_details', {
							metal_touch:r.message[i][0],
							rate_in_usd:r.message[i][1],
						});
					}
					frm.refresh_field('gjepc_metal_rate_details');
				}
			}
		});
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.gjepc_metal_rate.gjepc_metal_rate.get_today_date',
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('date',r.message)
				}
			}
		});

		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.gjepc_metal_rate.gjepc_metal_rate.get_gjepc_file',
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('file_name',r.message)
				}
			}
		});
	}
});
