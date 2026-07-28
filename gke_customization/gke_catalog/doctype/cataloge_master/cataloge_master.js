// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cataloge Master", {
	refresh(frm) {
        // frm.set_query("metal_type", () => {
        //     return {
        //         filters: {
        //             // parent: frm.doc.attribute_name
        //         }
        //     };
        // });
        if (!frm.doc.customer) return;

        // agar table me data hai to kuch mat karo
        if (frm.doc.diamond_quality?.length) return;

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Customer",
                name: frm.doc.customer
            },
            callback: function(r) {

                if (!r.message) return;

                (r.message.diamond_grades || []).forEach(row => {

                    let child = frm.add_child("diamond_quality");

                    child.diamond_quality = row.diamond_quality;
                });

                frm.refresh_field("diamond_quality");

                // Not Saved badge hatane ke liye
                frm.dirty(false);
            }
        });
    }
    
    
});
