// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

frappe.ui.form.on("Supplier Update Master", {
    supplier_group(frm){
        if (frm.doc.supplier_group === "Internal Supplier") {
            frm.set_value("is_internal_supplier", 1)
            // frm.save()
        }
    }
    // after_workflow_action(frm) {
    //     if (frm.doc.workflow_state === "On Hold") {
    //         frappe.prompt([
    //                 {
    //                     label: 'Reason For Hold',
    //                     fieldname: 'reason_for_hold',
    //                     fieldtype: 'Data',
    //                     // options: reasonOptions,
    //                     reqd: 1
    //                 },
    //             ], (values) => {
    //                 frm.set_value("reason_for_hold", values.reason_for_hold).then(() => {
    //                     frm.save();
    //                 });
    //         });		
    //     }
	// },
    
});
