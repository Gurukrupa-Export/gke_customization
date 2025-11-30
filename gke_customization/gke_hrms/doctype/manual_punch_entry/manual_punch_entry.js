// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Manual Punch Entry", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2023, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manual Punch Entry', {
	refresh(frm){
		// frm.set_intro("Existing Personal Out and OT records will be cancelled on save")
		// frm.add_custom_button(__("Mark Attendance"), () => {

		// 	frappe.call({ 
        //         method: "gke_customization.gke_hrms.doctype.manual_punch_entry.manual_punch_entry.process_attendance",
        //         args: {
        //             employee: frm.doc.employee,
        //             shift_type: frm.doc.shift_name,
        //             date: frm.doc.date
        //         },
        //         freeze: true,
        //         callback: () => {
        //             frappe.msgprint("Attendance marked using manual punch entries.");
        //         }
        //     });
		// });
	},
	 
	after_workflow_action(frm) { 
        if (frm.doc.workflow_state === "Create Attendance") {
			frm.set_df_property('date', 'read_only', 1);
		}
	},
	date: function(frm) {
		frm.set_value("new_punch", frm.doc.date)
	},
	// employee: function(frm) {
	// 	if (frm.doc.employee) {
	// 		frappe.db.get_value("Shift Assignment", {
	// 			"employee": frm.doc.employee,
	// 			"start_date": ["<=", frm.doc.date],
	// 			// "end_date": [">=", frm.doc.date || null],
	// 			"docstatus": 1
	// 		}, ["name", "shift_type"]).then(shift_res => {
	// 			console.log(shift_res);
				
	// 			if (shift_res && shift_res.message && shift_res.message.shift_type) {
	// 				// Valid shift assignment found
	// 				console.log("Shift Assignment:", shift_res.message.name);
	// 				frm.set_value("shift_name", shift_res.message.shift_type);
	// 			} else {
	// 				// No shift assignment, fallback to default_shift
	// 				frappe.db.get_value("Employee", frm.doc.employee, ["default_shift"])
	// 					.then(emp_res => {
	// 						console.log(emp_res);
							
	// 						if (emp_res && emp_res.message) {
	// 							console.log("Fallback to default_shift:", emp_res.message.default_shift);
	// 							frm.set_value("shift_name", emp_res.message.default_shift);
	// 						}
	// 					});
	// 			}
	// 		});
			
	// 		frappe.db.get_value("Employee",frm.doc.employee, ["attendance_device_id"], (r) => {
	// 			frm.set_value("punch_id", r.attendance_device_id)  
	// 			console.log("Shift attendance_device_id:", r.attendance_device_id);
	// 		})
			
	// 	}
	// },
	employee: function(frm) {
		if (frm.doc.employee) {

			frappe.db.get_list("Shift Assignment", {
				fields: ["name", "shift_type"],
				filters: [
					["employee", "=", frm.doc.employee],
					["start_date", "<=", frm.doc.date],
					["docstatus", "=", 1],
					["end_date", "is", "not set"],
					
				],
				limit: 1
			}).then(assignments => {
				
				if (assignments.length > 0) {
					frm.set_value("shift_name", assignments[0].shift_type);
				} 
				else {
					// Second query: where end_date IS not NULL
					frappe.db.get_list("Shift Assignment", {
						fields: ["name", "shift_type"],
						filters: [
							["employee", "=", frm.doc.employee],
							["start_date", "<=", frm.doc.date],
							["end_date", "is", "set"],
							["docstatus", "=", 1]
						],
						limit: 1
					}).then(null_end_assign => {
						if (null_end_assign.length > 0) {
							frm.set_value("shift_name", null_end_assign[0].shift_type);
						} 
						else {
							// Fallback to default shift
							frappe.db.get_value("Employee", frm.doc.employee, ["default_shift"])
								.then(emp_res => {
									frm.set_value("shift_name", emp_res.message.default_shift);
								});
						}
					});
				}
			});

			// Punch ID
			frappe.db.get_value("Employee", frm.doc.employee, ["attendance_device_id"], r => {
				frm.set_value("punch_id", r.attendance_device_id);
			});
		} 
	},
	search: function(frm) {
		frm.call({
			method: "search_checkin",
			doc: frm.doc,
			callback: function(r) {
				var checkins = r.message
				console.log(checkins)
				$.each(checkins || [], function(i,d) {
					if (!d.source) {
						d.source = "Employee Checkin"
					}
					d.type = i%2==0 ? "IN":"OUT"
					frm.add_child("details", d)
				})
				frm.refresh_field("details")
			}
		})
	},
	add_new_punch(frm) {
		if (!frm.doc.date || !frm.doc.employee) {
			frappe.throw(__("Filters missing"));
		}
		if (frm.doc.new_punch) {
			frappe.run_serially([
				()=>frm.call("validate_punch"),
				()=>add_punch(frm, frm.doc.new_punch),
				()=>frm.refresh_field("details")
			])
		}
		frm.refresh_field("details")
	}
});

frappe.ui.form.on("Manual Punch Details", {
	before_details_remove(frm, cdt, cdn) {
		var row = locals[cdt][cdn]
		if (!row.employee_checkin) return
		var to_be_deleted = frm.doc.to_be_deleted ? frm.doc.to_be_deleted.split(',') : []
		to_be_deleted.push(row.employee_checkin)
		frm.set_value("to_be_deleted", to_be_deleted.join())
	}
})

function validate_dates(frm) {
        var date = frm.doc.date;
        var datetime = frm.doc.new_punch;
        
        if (date && datetime) {
            var dateObj = moment(date);
            var datetimeObj = moment(datetime);
            
            if (!datetimeObj.isSame(dateObj, 'day')) {
                frappe.throw(__('The New Punch must be on the same day as the date field.'));
            }
        }
}

function add_punch(frm,time) {
	let new_punch = {
		"date": frm.doc.date,
		"time": time,
		"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
	} 
	var checkins = frm.doc.details || []
	checkins.push(new_punch)
	checkins.sort((a,b)=>{
		return moment(a.time).diff(b.time, 'second')
	})
	frm.doc.details = []
	$.each(checkins || [], function(i,d) {
		d.type = i%2==0 ? "IN":"OUT"
		frm.add_child("details", d)
	})
}