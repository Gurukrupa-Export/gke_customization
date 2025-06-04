// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Email Segmentation", {
	after_workflow_action(frm) {
        if (frm.doc.workflow_state === "On Hold") {
            frappe.prompt([
                    {
                        label: 'Reason For Hold',
                        fieldname: 'remark',
                        fieldtype: 'Data',
                        // options: reasonOptions,
                        reqd: 1
                    },
                ], (values) => {
                    frm.set_value("remark", values.remark).then(() => {
                        frm.save();
                    });
            });		
        }
	},
});
