// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Monthly Attendance Resigter", {
	refresh(frm) {

	},
    serach: function(frm) {
        frappe.call({
			method: 'gke_customization.gke_hrms.doctype.monthly_attendance_resigter.monthly_attendance_resigter.get_attendance_data',
			args: {  
				'company': frm.doc.company,
				'branch': frm.doc.branch,
				'from_date':frm.doc.from_date,
				'to_date':frm.doc.to_date,
			},
			callback: function(r) {
				if (!r.exc) {
					frm.clear_table('monthly_attendance_resigter_details');
					var arrayLength = r.message.length;
                    console.log('arrayLength', arrayLength);
                    
					for (var i = 0; i < arrayLength; i++) {
						let row = frm.add_child('monthly_attendance_resigter_details', {
							employee: r.message[i]['employee_id'],
							employee_name: r.message[i]['employee_name'],
							branch: r.message[i]['branch'],
							holiday:r.message[i]['holiday_list'],
							in_time: r.message[i]['in_time'],
							out_time: r.message[i]['out_time'],
							status: r.message[i]['status'],
							duration: r.message[i]['dur_min_time'],
							count: r.message[i]['count'],
							att_date: r.message[i]['att_date'].split('T')[0],

						});
					}
					frm.refresh_field('monthly_attendance_resigter_details');
				}
			}
		});
    }
});
