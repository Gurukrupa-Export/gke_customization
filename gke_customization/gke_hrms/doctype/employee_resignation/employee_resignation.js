// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation", {
	// refresh(frm) {
    //     if(frm.doc.waive_off_notice_period == 'Yes'){
    //         let update_notice_days = frm.doc.reduce_notice_days;

    //         let resignationDate = new Date(frm.doc.date_resignation);
    //         let noticeDays = parseInt(update_notice_days);
            
    //         resignationDate.setDate(resignationDate.getDate() + noticeDays);
    //         let formattedDate = resignationDate.toISOString().split('T')[0];
            
    //         console.log(formattedDate);
            
    //         frm.set_value("last_working_day", formattedDate);
    //         frm.refresh_field("last_working_day");
    //     }
	// },

    refresh: function (frm) {
        if(frm.doc.workflow_state == 'Approved'){
            frm.add_custom_button(
				__("Employee Separation"),
				function () {
                    frappe.model.open_mapped_doc({
                        method: "gke_customization.gke_hrms.doctype.employee_resignation.employee_resignation.create_employee_resignation",
                        frm: frm,
                    });
                },
				__("Create"),
			);
        }
    }
});
