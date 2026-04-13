// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on("OT Request", {
    refresh(frm) {
        frm.add_custom_button(__("Get Employees"), function () {
            frappe.call({
                method: "gke_customization.gke_hrms.doctype.ot_request.ot_request.fill_employee_details",
                args: {
                    // 'department': frm.doc.department,
                    'gender': frm.doc.gender || null,
                    'department_head': frm.doc.department_head,
                    'branch': frm.doc.branch
                },
                callback: function (r) {
                    if (!r.exc) {
                        cur_frm.clear_table('order_request');
                        r.message.forEach(emp => {
                            let row = frm.add_child('order_request', {
                                employee_id: emp.name,
                                employee_name: emp.employee_name,
                                ot_hours: frm.doc.ot_hours || '',
                                reason_for_ot: frm.doc.reason_for_ot || '',
                            });
                        });
                        frm.refresh_field('order_request');
                    }
                }
            });
        }).toggleClass("btn-second", !(frm.doc.employees || []).length);

    },

    ot_hours: function (frm) {
        update_fields_in_child_table(frm, "ot_hours");
    },
    reason_for_ot(frm) {
        update_fields_in_child_table(frm, "reason_for_ot")
        if (frm.doc.order_request && frm.doc.order_request.length > 0) {
            let remark_to_set = null;
            frm.doc.order_request.forEach(row => {
                if (row.reason_for_ot) {
                    remark_to_set = row.reason_for_ot;
                }
            });
            if (remark_to_set) {
                frm.doc.order_request.forEach(row => {
                    row.reason_for_ot = remark_to_set;
                });
                frm.refresh_field('order_request');
            }
        }
    },
});

function update_fields_in_child_table(frm, fieldname) {
    (frm.doc.order_request || []).forEach(d => {
        d[fieldname] = frm.doc[fieldname];
    });
    refresh_field("order_request");
}

frappe.ui.form.on('Overtime Request Details', {
    enable_ot_duration(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // If unchecked → clear dates & hours
        if (!row.enable_ot_duration) {
            frappe.model.set_value(cdt, cdn, 'work_start_date', null);
            frappe.model.set_value(cdt, cdn, 'work_end_date', null);
            frappe.model.set_value(cdt, cdn, 'ot_hours', frm.doc.ot_hours);
            return;
        }

        // If checked → try calculating
        calculate_ot_hours(cdt, cdn);
    },

    work_start_date(frm, cdt, cdn) {
        calculate_ot_hours(cdt, cdn);
    },

    work_end_date(frm, cdt, cdn) {
        calculate_ot_hours(cdt, cdn);
    }
});

function calculate_ot_hours(cdt, cdn) {
    const row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'ot_hours', null);

    if (!row.enable_ot_duration) return;
    if (!row.work_start_date || !row.work_end_date) return;

    const start = moment(row.work_start_date);
    const end = moment(row.work_end_date);

    if (!end.isAfter(start)) {
        // frappe.msgprint(__('Work End Date must be greater than Work Start Date'));
        return;
    }

    const diffSeconds = end.diff(start, 'seconds');
    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    const seconds = diffSeconds % 60;

    const pad = (num) => num.toString().padStart(2, '0');
    const formatted_time = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

    frappe.model.set_value(cdt, cdn, 'ot_hours', formatted_time);
}
