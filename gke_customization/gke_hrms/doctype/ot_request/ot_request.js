// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("OT Request", {
	refresh(frm) {
        frm.add_custom_button(__("Get Employees"), function () {            
            frappe.call({
                method: "gke_customization.gke_hrms.doctype.ot_request.ot_request.fill_employee_details",
                args: {
                    'department' : frm.doc.department
                },
                callback: function(r) {
                    if (!r.exc) {                        
                        cur_frm.clear_table('order_request');
                        var arrayLength = r.message.length;

                        for (var i = 0; i < arrayLength; i++) {
                            let row = frm.add_child('order_request', {
                                employee_id : r.message[i].name,
                                employee_name : r.message[i].employee_name,
                                ot_hours: ''
                            });
                        }                        
                        frm.refresh_field('order_request');
                    }
                }
            });
        }).toggleClass("btn-second", !(frm.doc.employees || []).length);
    
	},
    ot_hours:function(frm){
        update_fields_in_child_table(frm, "ot_hours")
    }
    
});

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.order_request || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
		});
	refresh_field("order_request");
}