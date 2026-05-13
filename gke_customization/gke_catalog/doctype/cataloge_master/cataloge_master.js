// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cataloge Master", {
	refresh(frm) {
        frm.set_query("metal_type", () => {
            return {
                filters: {
                    // parent: frm.doc.attribute_name
                }
            };
        });
	},
});
