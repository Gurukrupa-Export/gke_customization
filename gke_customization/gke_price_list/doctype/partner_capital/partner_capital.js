// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

frappe.ui.form.on("Partner Capital", {
	refresh(frm) {
        if (frm.doc.payment_entry_created == 0 && frm.doc.docstatus == 1 && frm.doc.total_interest > 0) {
            frm.add_custom_button(__('Create Journal Entry'), () => {
                frappe.call({
                    method: "gke_customization.gke_price_list.doctype.partner_capital.partner_capital.create_journal_entry",
                    args: {
                        name : frm.doc.name,
                        lender: frm.doc.lender,
                        loan_amount: frm.doc.loan_amount,
                        company: frm.doc.company,
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            // open the new Journal Entry after creation
                            frappe.set_route("Form", "Journal Entry", r.message);
                        }
                    }
                });
                // frappe.new_doc('Journal Entry', {
                //     payment_type: "Receive",
                //     party_type: "Customer",
                //     posting_date: frappe.datetime.nowdate(),
                //     paid_amount: frm.doc.loan_amount,
                //     company: frm.doc.company,
                //     custom_partner_capital:frm.doc.name,
                //     branch:frm.doc.branch
                    
                // });

                // // Set the party field after a short delay
                // console.log();
                
                // setTimeout(function() {
                //     frappe.db.get_value("Business Partner", frm.doc.lender, "customer").then((r)=> {
                //         if(r.message){
                //                 cur_frm.set_value("party", r.message.customer);
                //                 // cur_frm.set_value("paid_to", "50200 - HDFC - SD");
                //             }
                //         });
    
                // }, 1500);
            });
        }
	},
    interest_rate(frm) {
        update_fields_in_child_table(frm, "interest_rate");
    },
    get_total: function(frm) {
        frappe.call({

            method: "gke_customization.gke_price_list.doctype.partner_capital.partner_capital.get_total_interest_upto_today",
            args: {
                name: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    // Reload the whole document to avoid sync issues and reflect db changes
                    frm.reload_doc();
                    frappe.msgprint(__('Total interest and amount updated up to current date.'));
                }
            }
        });
    }
});

frappe.ui.form.on("Partner Capital Repayment Schedule", {
	// partner_capital_repayment_schedule_add(frm, cdt, cdn) {
    //     var row = locals[cdt][cdn];
    //     calculate_due_days(frm);
    //     refresh_field("partner_capital_repayment_schedule");
    // },

    // payment_date: function(frm, cdt, cdn) {
    //     calculate_due_days(frm);
    //     refresh_field("partner_capital_repayment_schedule");
    // },
    make_payment_entry(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.payment_type == 'Pay' && row.payment_entry_created ==0){

            frappe.new_doc('Payment Entry', {
                    payment_type: "Pay",
                    party_type: "Supplier",
                    posting_date: frappe.datetime.nowdate(),
                    paid_amount: row.total_payment,
                    company: frm.doc.company,
                    custom_partner_capital: frm.doc.name,
                    custom_partner_capital_repayment_schedule: row.name
                });
            
                // Set party after a short delay
                setTimeout(function() {
                    frappe.db.get_value("Business Partner", frm.doc.lender, "supplier")
                        .then((r) => {
                            if (r.message) {
                                console.log(r.message)
                                cur_frm.set_value("party", r.message.supplier);
                                cur_frm.set_value("paid_to", r.message.payable_account);
                                
                            }
                        });
                }, 1500);
        }
        if (row.payment_type == 'Receive' && row.payment_entry_created ==0){

            frappe.new_doc('Payment Entry', {
                    payment_type: "Receive",
                    party_type: "Customer",
                    posting_date: frappe.datetime.nowdate(),
                    paid_amount: row.total_payment,
                    company: frm.doc.company,
                    custom_partner_capital: frm.doc.name,
                    custom_partner_capital_repayment_schedule: row.name
                });
            
                // Set party after a short delay
                setTimeout(function() {
                    frappe.db.get_value("Business Partner", frm.doc.lender, "customer")
                        .then((r) => {
                            if (r.message) {
                                console.log(r.message)
                                cur_frm.set_value("party", r.message.customer);
                                cur_frm.set_value("paid_from", r.message.receivable_account);
                                
                            }
                        });
                }, 1500);
        }


    },
});

// function calculate_due_days(frm) {
//     let partner_capital_repayment_schedule = frm.doc.partner_capital_repayment_schedule || [];

//     if (partner_capital_repayment_schedule.length > 1) {
//         let last_row = partner_capital_repayment_schedule[partner_capital_repayment_schedule.length - 1];
//         let prev_row = partner_capital_repayment_schedule[partner_capital_repayment_schedule.length - 2];
//         let due_days = frappe.datetime.get_day_diff(last_row.payment_date, prev_row.payment_date);
//         frappe.model.set_value(last_row.doctype, last_row.name, 'number_of_days', due_days);
//     }
//     else{
//         // let due_days = frappe.datetime.get_day_diff(frm.doc.date, partner_capital_repayment_schedule[0].payment_date);
//         let due_days = 0
//         frappe.model.set_value(partner_capital_repayment_schedule[0].doctype, partner_capital_repayment_schedule[0].name, 'number_of_days', due_days);
//     }
// }

function update_fields_in_child_table(frm, fieldname) {
    $.each(frm.doc.repayment_schedule || [], function (i, d) {
        d[fieldname] = frm.doc[fieldname];
    });
    refresh_field("partner_capital_repayment_schedule");
};