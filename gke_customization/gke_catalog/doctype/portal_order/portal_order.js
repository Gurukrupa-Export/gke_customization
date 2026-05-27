// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Portal Order", {
	after_workflow_action(frm) { 
        setTimeout(() => {
            if (frm.doc.workflow_state === "Ordered") {
                // frm.set_value('status', 'Ordered');
                frm.refresh_field("items")
                frm.save();
            }
            if (frm.doc.workflow_state === "Cancel Order" ) {
            // if (frm.doc.workflow_state === "Cancel Order" || frm.doc.workflow_state === "Ordered") {
                // frm.set_value('status', 'Cancel Order');
                frm.refresh_field("items")
                frm.save();
            }
            
        }, 100);
	},
});

// function apply_status_to_child(frm) {
//     let status = frm.doc.status;
//     frm.doc.items.forEach(item => {
//         if (item.status === "Cancelled") {
//             return;  // skip only this item
//         }
//         item.status = status;
//     });
// }