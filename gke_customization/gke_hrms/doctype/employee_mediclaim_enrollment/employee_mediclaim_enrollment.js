// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Mediclaim Enrollment", {
  refresh(frm) {},
  punch_id(frm) {
    if (frm.doc.punch_id) {
      frappe.db.get_value(
        "Employee",
        { old_punch_id: frm.doc.punch_id },
        "name",
        (r) => {
          if (r.name) {
            frm.set_value("employee", r.name);
          }
        },
      );
    }
  },
  insured_by_company(frm) {
    calculate_total(frm);
  },
  additional_insured(frm) {
    calculate_total(frm);
  },
  date_of_birth(frm) {
    if (frm.doc.date_of_birth) {
     let age = calculate_age(frm.doc.date_of_birth);
     frm.set_value("age", age);
    }
  },
});

function calculate_total(frm) {

    let company_cover = flt(frm.doc.insured_by_company) || 0;
    let additional_cover = 0;

    if (frm.doc.additional_insured) {

        // Extract number from "5 Lakh"
        let match = frm.doc.additional_insured.match(/\d+/);

        if (match) {
            additional_cover = parseInt(match[0]) * 100000;
        }
    }
    frm.set_value("total", company_cover + additional_cover);
}



frappe.ui.form.on("Employee Mediclaim Table", {
  date_of_birth(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (!row.date_of_birth) {
      frappe.model.set_value(cdt, cdn, "age", 0 );
      return;
    }

    let age = calculate_age(row.date_of_birth);

    frappe.model.set_value(cdt, cdn, "age", age);
  },

  relation(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (["Son", "Father", "Father In Law"].includes(row.relation)) {
      frappe.model.set_value(cdt, cdn, "gender", "Male");
    }

    if (["Daughter", "Mother", "Mother In Law"].includes(row.relation)) {
      frappe.model.set_value(cdt, cdn, "gender", "Female");
    }
  },
});


function calculate_age(dob) {
    if (!dob) return 0;

    // Convert string to Date object (Frappe date field)
    let dob_date = frappe.datetime.str_to_obj(dob);

    // 31 March of current year
    let currentYear = frappe.datetime.now_date().split("-")[0];
    let end_date = new Date(currentYear, 2, 31); // March = 2 (0-based index)

    let age = end_date.getFullYear() - dob_date.getFullYear();

    // Same logic as Python:
    // ((end_date.month, end_date.day) < (dob.month, dob.day))
    if (
        end_date.getMonth() < dob_date.getMonth() ||
        (end_date.getMonth() === dob_date.getMonth() &&
         end_date.getDate() < dob_date.getDate())
    ) {
        age--;
    }

    return age;
}