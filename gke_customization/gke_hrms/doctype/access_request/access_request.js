// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('Access Request', {
    request_purpose: function(frm) {
        frappe.call({
            method: 'gke_customization.gke_hrms.doctype.access_request.access_request.auto_department',
            args: {
                user_id: frm.doc.requester,
                request_purpose: frm.doc.request_purpose
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('department', r.message);
                } 
            }
        });
    },
    setup(frm) {
        frm.set_query("designation", "role_mapping", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                query: "gke_customization.gke_hrms.doctype.access_request.access_request.get_designation_query",
                filters: {
                    department: row.department
                }
            };
        });
    }
});
