// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on("OT Request", {
    refresh(frm) {
        frm.add_custom_button(__("Get Employees"), function () {            
            frappe.call({
                method: "gke_customization.gke_hrms.doctype.ot_request.ot_request.fill_employee_details",
                args: {
                    'department': frm.doc.department,
                    'gender': frm.doc.gender || null
                },
                callback: function(r) {
                    if (!r.exc) {                        
                        cur_frm.clear_table('order_request');
                        r.message.forEach(emp => {
                            let row = frm.add_child('order_request', {
                                employee_id: emp.name,
                                employee_name: emp.employee_name,
                                ot_hours: ''
                            });
                        });                        
                        frm.refresh_field('order_request');
                    }
                }
            });
        }).toggleClass("btn-second", !(frm.doc.employees || []).length);
    },

    ot_hours: function(frm) {
        update_fields_in_child_table(frm, "ot_hours");
    }
});

function update_fields_in_child_table(frm, fieldname) {
    (frm.doc.order_request || []).forEach(d => {
        d[fieldname] = frm.doc[fieldname];
    });
    refresh_field("order_request");
}

