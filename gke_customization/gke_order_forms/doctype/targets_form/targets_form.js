// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Targets Form", {
//     setup(frm) {
//         const current = new Date();
//         const today = current.toISOString().split('T')[0];
//         const currentMonthIndex = current.getMonth(); // 0 = Jan, 4 = May
//         const currentYear = current.getFullYear();

//         const currentMonthName = current.toLocaleString('default', { month: 'long' });

//         frm.set_value('date', today);
//         frm.set_value('month', currentMonthName);
            
//         if (frm.is_new() && !frm.doc.order_target_detail.length) {
//             const entries = [
//                 { setting_type: "Open", nature: "Outright" },
//                 { setting_type: "Open", nature: "Outwork" },
//                 { setting_type: "Close", nature: "Outright" },
//                 { setting_type: "Close", nature: "Outwork" }
//             ];

//             // Financial year start: April (month index 3)
//             const fy_start_month = 3; // April
//             const fy_months = 12;

//             for (let i = 0; i < fy_months; i++) {
//                 let monthIndex = fy_start_month + i;
//                 let year = currentYear;

//                 if (monthIndex >= 12) {
//                     monthIndex -= 12;
//                     year += 1;
//                 }

//                 const monthYear = new Date(year, monthIndex, 1).toLocaleString('default', {
//                     month: 'long',
//                     year: 'numeric'
//                 });

//                 entries.forEach(entry => {
//                     let row = frm.add_child("order_target_detail");
//                     row.setting_type = entry.setting_type;
//                     row.nature = entry.nature;
//                     row.month = monthYear;
//                 });
//             }

//             frm.refresh_field("order_target_detail");
//         }
//     }
// });

// frappe.ui.form.on("Order Target Detail", {
//     form_render(frm, cdt, cdn) {
//         const row = locals[cdt][cdn];

//         const [rowMonthName, rowYear] = row.month.split(" ");
//         const rowMonthIndex = new Date(`${rowMonthName} 1, ${rowYear}`).getMonth();
//         const rowYearInt = parseInt(rowYear);
//         const rowDate = new Date(rowYearInt, rowMonthIndex, 1);

//         const current = new Date();
//         const currentMonthIndex = current.getMonth();
//         const currentYear = current.getFullYear();
//         const currentDate = new Date(currentYear, currentMonthIndex, 1);

//         const is_past_or_current = rowDate <= currentDate;

//         const grid_row = frm.fields_dict["order_target_detail"].grid.grid_rows_by_docname[cdn];

//         ["target_1", "target_2", "target_3", "target_4", "target_5"].forEach(field => {
//             const is_value_filled = !!row[field];
//             const make_read_only = is_past_or_current || is_value_filled;

//             grid_row.toggle_editable(field, !make_read_only);
//         });

//         const $row = $(grid_row.row);
//         if (is_past_or_current) {
//             $row.attr("title", "You cannot edit targets for past or current months.");
//         } else {
//             $row.removeAttr("title");
//         }
//     }
// });



// frappe.ui.form.on("Order Target Detail", {
//     target_1(frm, cdt, cdn) { toggleFieldReadonly(frm, cdt, cdn, "target_1"); },
//     target_2(frm, cdt, cdn) { toggleFieldReadonly(frm, cdt, cdn, "target_2"); },
//     target_3(frm, cdt, cdn) { toggleFieldReadonly(frm, cdt, cdn, "target_3"); },
//     target_4(frm, cdt, cdn) { toggleFieldReadonly(frm, cdt, cdn, "target_4"); },
//     target_5(frm, cdt, cdn) { toggleFieldReadonly(frm, cdt, cdn, "target_5"); },
// });

// function toggleFieldReadonly(frm, cdt, cdn, field) {
//     let row = locals[cdt][cdn];
//     if (row[field]) {
//         frm.fields_dict.order_target_detail.grid.grid_rows_by_docname[cdn].toggle_editable(field, false);
//     }
// }

// frappe.ui.form.on("Targets Form", {
//     setup(frm) {
//         const current = new Date();
//         const today = current.toISOString().split('T')[0];
//         const currentMonthName = current.toLocaleString('default', { month: 'long' });
//         const currentYear = current.getFullYear();

//         frm.set_value('date', today);
//         frm.set_value('month', currentMonthName);
            
//         if (frm.is_new() && !frm.doc.order_target_detail.length) {
//             const entries = [
//                 { setting_type: "Open", nature: "Outright" },
//                 { setting_type: "Open", nature: "Outwork" },
//                 { setting_type: "Close", nature: "Outright" },
//                 { setting_type: "Close", nature: "Outwork" }
//             ];

//             const fy_start_month = 3; // April
//             const fy_months = 12;

//             for (let i = 0; i < fy_months; i++) {
//                 let monthIndex = fy_start_month + i;
//                 let year = currentYear;

//                 if (monthIndex >= 12) {
//                     monthIndex -= 12;
//                     year += 1;
//                 }

//                 const monthYear = new Date(year, monthIndex, 1).toLocaleString('default', {
//                     month: 'long',
//                     year: 'numeric'
//                 });

//                 entries.forEach(entry => {
//                     let row = frm.add_child("order_target_detail");
//                     row.setting_type = entry.setting_type;
//                     row.nature = entry.nature;
//                     row.month = monthYear;
//                 });
//             }

//             frm.refresh_field("order_target_detail");
//         }
//     }
// });


// frappe.ui.form.on("Order Target Detail", {
//     form_render(frm, cdt, cdn) {
//         updateFieldAccessibility(frm, cdt, cdn);
//     },

//     target_1(frm, cdt, cdn) {
//         toggleFieldReadonly(frm, cdt, cdn, "target_1");
//         updateFieldAccessibility(frm, cdt, cdn);
//     },
//     target_2(frm, cdt, cdn) {
//         toggleFieldReadonly(frm, cdt, cdn, "target_2");
//         updateFieldAccessibility(frm, cdt, cdn);
//     },
//     target_3(frm, cdt, cdn) {
//         toggleFieldReadonly(frm, cdt, cdn, "target_3");
//         updateFieldAccessibility(frm, cdt, cdn);
//     },
//     target_4(frm, cdt, cdn) {
//         toggleFieldReadonly(frm, cdt, cdn, "target_4");
//         updateFieldAccessibility(frm, cdt, cdn);
//     },
//     target_5(frm, cdt, cdn) {
//         toggleFieldReadonly(frm, cdt, cdn, "target_5");
//         updateFieldAccessibility(frm, cdt, cdn);
//     }
// });


// function toggleFieldReadonly(frm, cdt, cdn, field) {
//     let row = locals[cdt][cdn];
//     if (row[field]) {
//         frm.fields_dict.order_target_detail.grid.grid_rows_by_docname[cdn].toggle_editable(field, false);
//     }
// }

// function updateFieldAccessibility(frm, cdt, cdn) {
//     const row = locals[cdt][cdn];

//     const [rowMonthName, rowYear] = row.month.split(" ");
//     const rowMonthIndex = new Date(`${rowMonthName} 1, ${rowYear}`).getMonth();
//     const rowYearInt = parseInt(rowYear);
//     const rowDate = new Date(rowYearInt, rowMonthIndex, 1);

//     const current = new Date();
//     const currentMonthIndex = current.getMonth();
//     const currentYear = current.getFullYear();
//     const currentDate = new Date(currentYear, currentMonthIndex, 1);

//     const is_past_or_current = rowDate <= currentDate;
//     const grid_row = frm.fields_dict["order_target_detail"].grid.grid_rows_by_docname[cdn];

//     const targets = ["target_1", "target_2", "target_3", "target_4", "target_5"];

//     for (let i = 0; i < targets.length; i++) {
//         const field = targets[i];

//         const is_filled = !!row[field];
//         const previous_filled = i === 0 || !!row[targets[i - 1]];

//         const can_edit = !is_past_or_current && previous_filled && !is_filled;

//         grid_row.toggle_editable(field, can_edit);
//     }

//     const $row = $(grid_row.row);
//     if (is_past_or_current) {
//         $row.attr("title", "You cannot edit targets for past or current months.");
//     } else {
//         $row.removeAttr("title");
//     }
// }
