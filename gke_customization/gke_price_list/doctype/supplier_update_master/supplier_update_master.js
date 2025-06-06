// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Supplier Update Master", {
//     after_workflow_action(frm) {
//         if (frm.doc.workflow_state === "On Hold") {
//             frappe.prompt([
//                     {
//                         label: 'Reason For Hold',
//                         fieldname: 'reason_for_hold',
//                         fieldtype: 'Data',
//                         // options: reasonOptions,
//                         reqd: 1
//                     },
//                 ], (values) => {
//                     frm.set_value("reason_for_hold", values.reason_for_hold).then(() => {
//                         frm.save();
//                     });
//             });		
//         }
// 	},
// });
