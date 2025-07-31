// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('User Permission Request', {
    task_id: function(frm) {
        if (!frm.doc.task_id) return;

        frappe.call({
            method: 'gke_customization.gke_hrms.doctype.user_permission_request.user_permission_request.get_task_data',
            args: {
                task_id: frm.doc.task_id
            },
            callback: function(r) {
                if (!r.exc && r.message) {
                    const data = r.message;
                    frm.set_value('job_applicant', data.job_applicant);
                    frm.set_value('employee_name', data.employee_name);
                    frm.set_value('department', data.department);
                    frm.set_value('designation', data.designation);
                    frm.set_value('company', data.company);
                    frm.set_value('first_name', data.first_name);
                    frm.set_value('last_name', data.last_name);
                    frm.set_value('branch', data.branch);
                    frm.set_value('username', data.username);
                    frm.set_value('employee', data.employee)
                    // frm.set_value('operation', data.operation)
                }
            }
        });
    },
    before_workflow_action: function(frm) {
        if (frm.selected_workflow_action == "Update Employee") {
            frappe.call({
                method: 'gke_customization.gke_hrms.doctype.user_permission_request.user_permission_request.update_employee',
                args: {
                    job_applicant: frm.doc.job_applicant,
                    username: frm.doc.username
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint('Employee updated successfully!');
                    }
                }
            });
        }
    }
});
