// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Penalty", {
    refresh(frm) {        
        calculate_total(frm);
    },
});

frappe.ui.form.on("Employee Penalty Detail", {
    penalty_amount(frm, cdt, cdn) {
        calculate_total(frm);
    },
});

function calculate_total(frm) {
    let total_penalty_amount = 0;

    if (frm.doc.penalty_type) {
        frm.doc.penalty_type.forEach(function (d) {
            total_penalty_amount += d.penalty_amount;
        });
    }

    let ctc = frm.doc.cost_to_company_ctc;
    let advanced_cash = ctc - total_penalty_amount;

    frm.set_value('total_penalty_amount', total_penalty_amount);
    frm.set_value('advanced_cash', advanced_cash);
}