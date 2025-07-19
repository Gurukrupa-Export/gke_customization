// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on('Secured Loan', {
    refresh(frm) {
        frm.add_custom_button(__('Create Receive Payment Entry'), function() {
            frappe.new_doc('Payment Entry', {
                payment_type: "Receive",
                party_type: "Customer",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: frm.doc.loan_amount,
                company: frm.doc.company,
                mode_of_payment: "Bank Draft",
                custom_secured_loan:frm.doc.name,
            });
    
            // Set the party field after a short delay
            setTimeout(function() {
                frappe.db.get_value("Business Partner", frm.doc.lender, ["customer","receivable_account"]).then((r)=> {
                    if(r.message){
                        console.log(r.message)
                            cur_frm.set_value("party", r.message.customer);
                            cur_frm.set_value("paid_from", r.message.receivable_account);
                        }
                    });

            }, 1500);
        }, __('Create'));


        // Ensure fields are updated in child table
        // update_fields_in_child_table(frm, "interest_rate");
        // update_fields_in_child_table(frm, "loan_amount");
    },
});


frappe.ui.form.on('Secured Loan Repayment Schedule', {
    make_payment_entry(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // frappe.new_doc('Payment Entry', {
        //     payment_type: "Pay",
        //     party_type: frm.doc.lender_type,
        //     posting_date: frappe.datetime.nowdate(),
        //     paid_amount: row.emi_amount,
        //     company: frm.doc.company,
        //     mode_of_payment: "Bank Draft",
        //     secured_loan: frm.doc.name,
        //     secured_loan_repayment_schedule: row.name,
        // });

        // // Set party after a short delay
        // setTimeout(function () {
        //     cur_frm.set_value("party", frm.doc.lender);
        // }, 1500);
        frappe.new_doc('Payment Entry', {
                payment_type: "Pay",
                party_type: "Supplier",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: row.emi_amount,
                company: frm.doc.company,
                mode_of_payment: "Bank Draft",
                custom_secured_loan: frm.doc.name,
                custom_secured_loan_repayment_schedule: row.name
            });
        
            // Set party after a short delay
            setTimeout(function() {
                frappe.db.get_value("Business Partner", frm.doc.lender, ["supplier","payable_account"])
                    .then((r) => {
                        if (r.message) {
                            console.log(r.message)
                            cur_frm.set_value("party", r.message.supplier);
                            cur_frm.set_value("paid_to", r.message.payable_account);
                            
                        }
                    });
            }, 1500);


    },
    grid_row_rendered(frm, cdt, cdn) {
        console.log("grid_row_rendered triggered");
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.secured_loan_repayment_schedule.grid.grid_rows_by_docname[cdn];
        console.log(grid_row.fields_dict)

        if (row.payment_status === 'Unpaid' && grid_row?.fields_dict?.make_payment_entry) {
            const html = `
                <button type="button" class="btn btn-sm btn-primary make-payment-btn" data-idx="${row.idx}">
                    Make Payment
                </button>
            `;
            grid_row.fields_dict.make_payment_entry.$wrapper.html(html);
        }
    }
});




// frappe.ui.form.on('Secured Loan', {
//     refresh(frm) {
//         render_payment_buttons(frm);
//     }
// });

// function render_payment_buttons(frm) {
//     const rows = frm.doc.secured_loan_repayment_schedule || [];

//     if (!rows.length) return;

//     const grid = frm.fields_dict.secured_loan_repayment_schedule.grid;

//     rows.forEach(row => {
//         const grid_row = grid?.grid_rows_by_docname?.[row.name];
//         console.log(grid_row.fields_dict)
//         if (grid_row && grid_row.fields_dict && grid_row.fields_dict.make_payment_entry) {
//             const html = row.payment_status === 'Unpaid'
//                 ? `<button type="button" class="btn btn-sm btn-primary make-payment-btn" data-idx="${row.idx}">
//                             Make Payment
//                        </button>`
//                 : '';

//             // ✅ SAFE injection
//             grid_row.fields_dict.make_payment_entry.$wrapper.html(html);
//             console.log(grid_row.fields_dict.make_payment_entry)
//         }
//     });
// }
