
// frappe.ui.form.on("Unsecured Loan", {
//     refresh(frm) {
//         // Add a custom button labeled "Accounting Ledger"
//         frm.add_custom_button("Accounting Ledger", () => {
//             frappe.set_route("query-report", "General Ledger", {
//                 account: frm.doc.account || "",
//                 voucher_no: frm.doc.name, 
//                 company: frm.doc.company || "" 
//             });
//         }, __("View")); 
//     },
//     interest_rate(frm){
//         update_fields_in_child_table(frm, "interest_rate")
//     },
//     loan_amount(frm){
//         console.log("HERE");
//         update_fields_in_child_table(frm, "loan_amount")
//     },
// });

// frappe.ui.form.on("Unsecured Loan Repayment Schedule", {
//     repayment_schedule_add(frm,cdt,cdn) {
//         var row = locals[cdt][cdn];
//         row.interest_rate = frm.doc.interest_rate;
//         row.loan_amount = frm.doc.loan_amount;
//         refresh_field("repayment_schedule");
//     },
// });


// function update_fields_in_child_table(frm, fieldname) {
// 	$.each(frm.doc.repayment_schedule || [], function (i, d) {
// 		d[fieldname] = frm.doc[fieldname];
// 	});
// 	refresh_field("repayment_schedule");
// };




// frappe.ui.form.on("Unsecured Loan", {
//     refresh(frm) {
//         // Add a button under the "View" menu for Accounting Ledger
//         frm.add_custom_button("Accounting Ledger", () => {
//             frappe.set_route("query-report", "General Ledger", {
//                 account: frm.doc.account || "",
//                 voucher_no: frm.doc.name, 
//                 company: frm.doc.company || "" 
//             });
//         }, __("View"));

//         // Ensure fields are updated in child table
//         update_fields_in_child_table(frm, "interest_rate");
//         update_fields_in_child_table(frm, "loan_amount");
//     },

//     interest_rate(frm) {
//         update_fields_in_child_table(frm, "interest_rate");
//     },

//     loan_amount(frm) {
//         console.log("HERE");
//         update_fields_in_child_table(frm, "loan_amount");
//     }
// });

// frappe.ui.form.on("Unsecured Loan Repayment Schedule", {
//     repayment_schedule_add(frm, cdt, cdn) {
//         var row = locals[cdt][cdn];
//         row.interest_rate = frm.doc.interest_rate;
//         row.loan_amount = frm.doc.loan_amount;
//         refresh_field("repayment_schedule");
//     }
// });

// function update_fields_in_child_table(frm, fieldname) {
//     $.each(frm.doc.repayment_schedule || [], function (i, d) {
//         d[fieldname] = frm.doc[fieldname];
//     });
//     refresh_field("repayment_schedule");
// };




frappe.ui.form.on("Unsecured Loan", {
    refresh(frm) {
        // Add a button under the "View" menu for Accounting Ledger
        // frm.add_custom_button("Accounting Ledger", () => {
        //     frappe.set_route("query-report", "General Ledger", {
        //         voucher_no: frm.doc.name, 
        //         company: frm.doc.company || "" 
        //     });
        // }, __("View"));
        // if(frm.doc.parent_gl_entry_created==0){
        //     frm.add_custom_button(__('Create Receive Payment Entry'), function() {
        //         frappe.call({
        //             method: "gke_customization.gke_custom_export.doctype.unsecured_loan.unsecured_loan.create_receive_payment_entry",
        //             args: {
        //                 loan_name: frm.doc.name
        //             },
        //             callback: function(r) {
        //                 if (r.message.status === "success") {
        //                     frappe.msgprint(__('Payment Entry {0} created successfully.', [r.message.payment_entry]));
        //                     // frappe.set_route("Form", "Payment Entry", r.message.payment_entry);
        //                 } else {
        //                     frappe.msgprint(__('Error: {0}', [r.message.message]));
        //                 }
        //             }
        //         });
        //     }, __('Create'));
        // }
    
        // frm.add_custom_button(__('Create Pay Payment Entry'), function() {
        //     frappe.call({
        //         method: "gke_customization.gke_custom_export.doctype.unsecured_loan.unsecured_loan.create_pay_payment_entry",
        //         args: {
        //             loan_name: frm.doc.name
        //         },
        //         callback: function(r) {
        //             if (r.message.status === "success") {
        //                 frappe.msgprint(__('Payment Entry {0} created successfully.', [r.message.payment_entry]));
        //                 // frappe.set_route("Form", "Payment Entry", r.message.payment_entry);
        //             } else {
        //                 frappe.msgprint(__('Error: {0}', [r.message.message]));
        //             }
        //         }
        //     });
        // }, __('Create'));

        frm.add_custom_button(__('Create Receive Payment Entry'), function() {
            frappe.new_doc('Payment Entry', {
                payment_type: "Receive",
                party_type: "Customer",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: frm.doc.loan_amount,
                company: frm.doc.company,
                mode_of_payment: "Cash",
            });
    
            // Set the party field after a short delay
            setTimeout(function() {
                
                frappe.db.get_value("Business Partner", frm.doc.lender, "customer")
    	           .then((r)=> {
                	   if(r.message.customer){
                            cur_frm.set_value("party", r.message.customer);
        	            }
            	});
                cur_frm.set_value("paid_from", "");
                cur_frm.set_value("paid_to", "");
            }, 300);
        }, __('Create'));

        frm.add_custom_button(__('Create Pay Payment Entry'), function() {
            frappe.new_doc('Payment Entry', {
                payment_type: "Receive",
                party_type: "Supplier",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: frm.doc.repayment_schedule[-1]['total_payment'],
                company: frm.doc.company,
                mode_of_payment: "Cash",
            });
    
            // Set the party field after a short delay
            setTimeout(function() {
                
                frappe.db.get_value("Business Partner", frm.doc.lender, "supplier")
    	           .then((r)=> {
                	   if(r.message.supplier){
                            cur_frm.set_value("party", r.message.supplier);
        	            }
            	});
                cur_frm.set_value("paid_from", "");
                cur_frm.set_value("paid_to", "");
            }, 300);
        }, __('Create'));
        

        // Ensure fields are updated in child table
        update_fields_in_child_table(frm, "interest_rate");
        update_fields_in_child_table(frm, "loan_amount");
    },

    interest_rate(frm) {
        update_fields_in_child_table(frm, "interest_rate");
    },

    loan_amount(frm) {
        update_fields_in_child_table(frm, "loan_amount");
    },
    // validate(frm) {
    //     validate_total_payment(frm);
    // }
});

frappe.ui.form.on("Unsecured Loan Repayment Schedule", {
    repayment_schedule_add(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        row.interest_rate = frm.doc.interest_rate;
        row.loan_amount = frm.doc.loan_amount;
        calculate_due_days(frm);
        refresh_field("repayment_schedule");
    },
    payment_date: function(frm, cdt, cdn) {
        calculate_due_days(frm);
        refresh_field("repayment_schedule");
    }
});

function update_fields_in_child_table(frm, fieldname) {
    $.each(frm.doc.repayment_schedule || [], function (i, d) {
        d[fieldname] = frm.doc[fieldname];
    });
    refresh_field("repayment_schedule");
};


function calculate_due_days(frm) {
    let repayment_schedule = frm.doc.repayment_schedule || [];

    if (repayment_schedule.length === 1) {
        let due_days = frappe.datetime.get_day_diff(frm.doc.payment_date, repayment_schedule[0].payment_date);
        frappe.model.set_value(repayment_schedule[0].doctype, repayment_schedule[0].name, 'number_of_days', due_days);
    } else if (repayment_schedule.length > 1) {
        let last_row = repayment_schedule[repayment_schedule.length - 1];
        let prev_row = repayment_schedule[repayment_schedule.length - 2];
        let due_days = frappe.datetime.get_day_diff(last_row.payment_date, prev_row.payment_date);
        frappe.model.set_value(last_row.doctype, last_row.name, 'number_of_days', due_days);
    }
}

function validate_total_payment(frm) {
    let repayment_schedule = frm.doc.repayment_schedule || [];
    let total_payment_amount = 0;

    repayment_schedule.forEach(row => {
        total_payment_amount += row.repay_loan_amount || 0;
    });

    if (total_payment_amount > frm.doc.loan_amount) {
        frappe.throw(`Total Payment Amount (${total_payment_amount}) cannot exceed Loan Amount (${frm.doc.loan_amount}).`);
        throw new Error("IF");
    }
    else{
        console.log(total_payment_amount);
        frappe.throw("HERE");
        
        
    }
}

