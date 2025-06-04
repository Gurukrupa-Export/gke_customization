// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee B Record", {
	// employee(frm) {
    //     frappe.call({
	// 		method: 'gke_customization.gke_hrms.doctype.employee_b_record.employee_b_record.get_salary_slip',
	// 		args: {
	// 			'employee': frm.doc.employee,
	// 		},
	// 		callback: function(r) {
	// 			if (!r.exc) {
	// 				// console.log(r.message)
	// 				cur_frm.clear_table('employee_b_record_details');
	// 				var arrayLength = r.message.length;
	// 				for (var i = 0; i < arrayLength; i++) {
	// 					let row = frm.add_child('employee_b_record_details', {
	// 						salary_slip: r.message[i].name,
	// 						date: r.message[i].start_date,
	// 						net_days: r.message[i].payment_days,
	// 						net_pay_inr: r.message[i].net_pay,
	// 						working_days: r.message[i].total_working_days,
    //                         // bond_amount: (r.message[i].total_working_days / frm.doc.bond_amount) * r.message[i].payment_days
	// 					});
	// 				}
	// 				frm.refresh_field('employee_b_record_details');
                    
	// 			}
	// 		}
	// 	});
	// },
    // bond_amount(frm){
    //     update_fields_in_child_table(frm, "bond_amount")
    // }
});

// function update_fields_in_child_table(frm, fieldname) {
// 	$.each(frm.doc.employee_b_record_details || [], function (i, d) {
// 		// d[fieldname] = frm.doc[fieldname];
//         let bond_amt = frm.doc[fieldname] / d["working_days"] * d["net_days"];
// 		d["bond_amount"] = Math.round(bond_amt)
        
// 	});
// 	refresh_field("employee_b_record_details");
//     calculate_amount(frm);
// }

// function calculate_amount(frm){
//     let total_amount = 0

//     if(frm.doc.employee_b_record_details){
// 		frm.doc.employee_b_record_details.forEach(function(d){	
// 			total_amount += d.bond_amount
// 		})
// 	};
      
//     frm.set_value("summary_amount", total_amount)
// }