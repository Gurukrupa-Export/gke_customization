// Copyright (c) 2023, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Gatepass', {
	refresh: function(frm) {
		// if (frm.doc.docstatus==1) {
		// 	if(frm.has_perm("submit")){
				var currentStatus = frm.doc.status;
				frm.clear_custom_buttons('Status');
				// open status
				if (currentStatus === 'Draft') {
					frm.add_custom_button(__('Open'), function() {
						frm.set_value('status', 'Re Open');
						frm.save();
					}, __('Status'));
				}
				// re open status
				else if (currentStatus === 'Re Open') {
					frm.add_custom_button(__('Close'), function() {
						frm.set_value('status', 'Completed');
						frm.save();
					}, __('Status'));
				} else {
					// open status
					frm.add_custom_button(__('Open'), function() {
						frm.set_value('status', 'Re Open');
						frm.save();
					}, __('Status'));
				}
		// 	}
		// }
	}
});
