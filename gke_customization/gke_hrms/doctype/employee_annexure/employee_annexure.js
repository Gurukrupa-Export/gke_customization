
// frappe.ui.form.on("Employee Annexure", {
//     onload(frm) {
//         set_salary_structure(frm);
//     },
//     employee(frm) {
//         frm.set_query("salary_structure", () => ({
//             filters: {
//                 is_active: "Yes",
//                 docstatus: 1,
//                 company: frm.doc.company,
//                 consider_working_hours: "No"
//             }
//         }));

//         if (frm.doc.company) {
//             frappe.db.get_list('Salary Structure', {
//                 filters: {
//                     is_active: "Yes",
//                     docstatus: 1,
//                     company: frm.doc.company,
//                     consider_working_hours: "No"
//                 },
//                 limit: 1,
//                 fields: ['name']
//             }).then(res => {
//                 if (res.length) {
//                     frm.set_value('salary_structure', res[0].name);
//                 }
//             });
//         }
//     }
// });
frappe.ui.form.on("Employee Annexure", {
    onload(frm) {
        set_salary_structure(frm);
    },

    employee(frm) {
        set_salary_structure(frm);
    }
});

function set_salary_structure(frm) {
    frm.set_query("salary_structure", () => {
        return {
            filters: {
                is_active: "Yes",
                docstatus: 1,
                company: frm.doc.company,
                consider_working_hours: "No"
            }
        };
    });

    if (frm.doc.company) {
        frappe.db.get_list('Salary Structure', {
            filters: {
                is_active: "Yes",
                docstatus: 1,
                company: frm.doc.company,
                consider_working_hours: "No"
            },
            limit: 1,
            fields: ['name']
        }).then(res => {
            if (res.length && !frm.doc.salary_structure) {
                frm.set_value('salary_structure', res[0].name);
            }
        });
    }
}
