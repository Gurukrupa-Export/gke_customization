// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on('Secured Loan Repayment Schedule', {
    make_payment_entry(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        frappe.new_doc('Payment Entry', {
            payment_type: "Pay",
            party_type: frm.doc.lender_type,
            posting_date: frappe.datetime.nowdate(),
            paid_amount: row.outstanding_amount,
            company: frm.doc.company,
            mode_of_payment: "Cash",
            secured_loan: frm.doc.name,
            secured_loan_repayment_schedule: row.name,
        });

        // Set party after a short delay
        setTimeout(function () {
            cur_frm.set_value("party", frm.doc.lender);
        }, 1500);
    }
});



frappe.ui.form.on('Secured Loan Repayment Schedule', {
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
0