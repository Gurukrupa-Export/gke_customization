// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation", {
	refresh: function (frm) {
		if (frm.doc.workflow_state == "Approved") {
			frm.add_custom_button(
				__("Employee Separation"),
				function () {
					frappe.model.open_mapped_doc({
						method: "gke_customization.gke_hrms.doctype.employee_resignation.employee_resignation.create_employee_resignation",
						frm: frm,
					});
				},
				__("Create")
			);
		}
	},
});
