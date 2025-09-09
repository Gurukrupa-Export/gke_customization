// // // Copyright (c) 2025, Gurukrupa Export and contributors
// // // For license information, please see license.txt


// frappe.ui.form.on('Inactive Payroll', {
//     refresh(frm) {
//         if (!frm.is_new()) {
//             frm.add_custom_button(__('Get Employees'), function () {
//                 if (!frm.doc.from_date || !frm.doc.to_date) {
//                     frappe.msgprint("Please set both From Date and To Date.");
//                     return;
//                 }

//                 frappe.call({
//                     method: "gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.get_inactive_employees",
//                     args: {
//                         docname: frm.doc.name
//                     },
//                     callback: function (r) {
//                         if (!r.exc) {
//                             frappe.msgprint("Employees fetched successfully.");
//                             frm.reload_doc();
//                         }
//                     }
//                 });
//             });

//             frm.add_custom_button(__('Make Employees Active'), function () {
//                 frappe.confirm("Are you sure you want to activate all listed employees?",
//                     () => {
//                         frappe.call({
//                             method: 'gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.activate_employees',
//                             args: { docname: frm.doc.name },
//                             callback: function (r) {
//                                 if (!r.exc) {
//                                     frappe.msgprint(r.message);
                                    
//             //                         frm.reload_doc(); 
//             //                     }
//             //                 }
//             //             });
//             //         }
//             //     );
//             // });
//                        if (r.message && r.message.includes('employees marked as Active')) {
//                                 frm.add_custom_button(__('Create Payroll'), () => {
//                                     frappe.confirm(
//                                         'Create payroll entries for all inactive employees listed?',
//                                         () => {
//                                             frappe.call({
//                                                 method: 'gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.create_payroll_entries',
//                                                 args: {
//                                                     docname: frm.doc.name
//                                                 },
//                                                 callback: function (r) {
//                                                     if (!r.exc) {
//                                                         frm.set_value('payroll_entry', r.message);
//                                                         frm.save();
//                                                     }
//                                                 }
//                                             });
//                                         }
//                                     );
//                                 }).addClass('btn-primary');
//                             }

//                             frm.reload_doc();
//                         }
//                     }
//                 });
//             });
//         });
//     }}
// });
// //                 frm.add_custom_button(__('Create Payroll'), () => {
// //                     frappe.confirm(
// //                         'Create payroll entries for all inactive employees listed?',
// //                         () => {
// //                             frappe.call({
// //                                 method: 'gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.create_payroll_entries',
// //                                 args: {
// //                                     docname: frm.doc.name
// //                                 },
// //                                 callback: function (r) {
// //                                     if (!r.exc) {
// //                                         // frappe.msgprint(r.message);
// //                                         frm.set_value('payroll_entry', r.message);
// //                                         frm.save();
// //                                     }
// //                                 }
// //                             });
// //                         }
// //                     );
// //                 });
            
// //         }
// //     }
// // });

// frappe.ui.form.on('Inactive Payroll', {
//     onload(frm) {
//         if (!frm.doc.posting_date) {
//             frm.set_value('posting_date', frappe.datetime.get_today());
//         }
//     }
// });

frappe.ui.form.on('Inactive Payroll', {
    onload(frm) {
        if (!frm.doc.posting_date) {
            frm.set_value('posting_date', frappe.datetime.get_today());
        }
    },

    refresh(frm) {
        if (frm.is_new()) return;

        frm.clear_custom_buttons();

   
        frm.add_custom_button(__('Get Employees'), function () {
            if (!frm.doc.from_date || !frm.doc.to_date) {
                frappe.msgprint("Please set both From Date and To Date.");
                return;
            }

            frappe.call({
                method: "gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.get_inactive_employees",
                args: {
                    docname: frm.doc.name
                },
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint("Employees fetched successfully.");
                        frm.reload_doc();
                    }
                }
            });
        });

        frm.add_custom_button(__('Make Employees Active'), function () {
            frappe.confirm("Are you sure you want to activate all listed employees?", () => {
                frappe.call({
                    method: 'gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.activate_employees',
                    args: { docname: frm.doc.name },
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint(r.message);

                            if (r.message && r.message.includes('employees marked as Active')) {
                                
                                frm.add_custom_button(__('Create Payroll'), () => {
                                    frappe.confirm(
                                        'Create payroll entries for all inactive employees listed?',
                                        () => {
                                            frappe.call({
                                                method: 'gke_customization.gke_hrms.doctype.inactive_payroll.inactive_payroll.create_payroll_entries',
                                                args: {
                                                    docname: frm.doc.name
                                                },
                                                callback: function (r) {
                                                    if (!r.exc) {
                                                        frm.set_value('payroll_entry', r.message);
                                                        frm.save();
                                                    }
                                                }
                                            });
                                        }
                                    );
                                }).addClass('btn-primary');
                            }

                           
                            frm.refresh_field("employee"); 
                        }
                    }
                });
            });
        });
    }
});
