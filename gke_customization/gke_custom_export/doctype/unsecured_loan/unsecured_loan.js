

frappe.ui.form.on("Unsecured Loan", {
    refresh(frm) {
        frm.add_custom_button(__('Create Receive Payment Entry'), function() {
            frappe.new_doc('Payment Entry', {
                payment_type: "Receive",
                party_type: "Customer",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: frm.doc.loan_amount,
                company: frm.doc.company,
                custom_unsecured_loan:frm.doc.name,
                
            });
    
            // Set the party field after a short delay
            setTimeout(function() {
                frappe.db.get_value("Business Partner", frm.doc.lender, "customer").then((r)=> {
                    if(r.message){
                            cur_frm.set_value("party", r.message.customer);
                        }
                    });

            }, 1500);
        }, __('Create'));

        frm.add_custom_button(__('Create Pay Payment Entry'), function() {
            // Find the last repayment row where gl_entry_created is not checked
            const schedule = frm.doc.repayment_schedule || [];
            const target_row = [...schedule].reverse().find(row => !row.gl_entry_created);
        
            if (!target_row) {
                frappe.msgprint("All repayment entries are already linked to GL Entries.");
                return;
            }
        
            frappe.new_doc('Payment Entry', {
                payment_type: "Pay",
                party_type: "Supplier",
                posting_date: frappe.datetime.nowdate(),
                paid_amount: target_row.total_payment,
                received_amount:target_row.total_payment,
                company: frm.doc.company,
                custom_unsecured_loan: frm.doc.name,
                custom_unsecured_loan_repayment_schedule: target_row.name
            });
        
            // Set party after a short delay
            setTimeout(function() {
                frappe.db.get_value("Business Partner", frm.doc.lender, "supplier")
                    .then((r) => {
                        if (r.message.supplier) {
                            cur_frm.set_value("party", r.message.supplier);
                        }
                    });
            }, 1500);
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

