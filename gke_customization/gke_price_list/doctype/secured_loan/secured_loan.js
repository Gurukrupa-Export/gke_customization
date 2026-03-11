// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on('Secured Loan', {
    refresh(frm) {
        // if (frm.doc.payment_entry_created == 0 && frm.doc.docstatus == 1) {
        //     frm.add_custom_button(__('Create Receive Payment Entry'), () => {
        //         frappe.new_doc('Payment Entry', {
        //             payment_type: "Receive",
        //             party_type: "Customer",
        //             posting_date: frappe.datetime.nowdate(),
        //             paid_amount: frm.doc.loan_amount,
        //             company: frm.doc.company,
        //             mode_of_payment: "Cash",
        //             custom_secured_loan: frm.doc.name,
        //         });

        //         // Set the party field after a short delay
        //         setTimeout(function () {
        //             frappe.db.get_value("Business Partner", frm.doc.lender, "customer").then((r) => {
        //                 if (r.message) {
        //                     cur_frm.set_value("party", r.message.customer);
        //                 }
        //             });

        //         }, 1500);
        //     });
        // }

        if (frm.doc.journal_entry_created == 0 && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Create Journal Entry'), () => {
                frappe.call({
                    method: "gke_customization.gke_price_list.doctype.secured_loan.secured_loan.make_jv",
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
            });
        }

    },
});


frappe.ui.form.on('Secured Loan Repayment Schedule', {
    make_payment_entry(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.payment_entry_created == 0) {
            frappe.new_doc('Payment Entry', {
                payment_type: "Pay",
                party_type: "Supplier",
                posting_date: row.payment_date,
                reference_date: row.payment_date,
                paid_amount: row.emi_amount,
                received_amount: row.emi_amount,
                company: frm.doc.company,
                mode_of_payment: "Bank Draft",
                custom_secured_loan: frm.doc.name,
                custom_secured_loan_repayment_schedule: row.name,
                branch : frm.doc.branch
            });


            // Set party after a short delay
            setTimeout(function () {
                frappe.db.get_value("Business Partner", frm.doc.lender, ["supplier", "payable_account"])
                    .then((r) => {
                        if (r.message) {
                            cur_frm.set_value("party", r.message.supplier);
                            // cur_frm.set_value("paid_to", r.message.payable_account);
                        }
                    });
            }, 1500);
        }


    },
    make_journal_entry(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.journal_entry_created == 0) {
            frappe.call({
                    method: "gke_customization.gke_price_list.doctype.secured_loan.secured_loan.make_jv_from_table",
                    args: {
                        name : frm.doc.name,
                        row:row.name,
                        due_date: row.due_date,
                        lender: frm.doc.lender,
                        credit_in_account_currency: (row.emi_amount || 0) - (row.principal_amount || 0),
                        company: frm.doc.company,
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            // open the new Journal Entry after creation
                            frappe.set_route("Form", "Journal Entry", r.message);
                        }
                    }
                });
        } else {
            frappe.msgprint("Journal Entry already processed for this row");
        }
    }
});
