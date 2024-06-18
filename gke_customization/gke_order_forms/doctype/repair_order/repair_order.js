// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt
frappe.ui.form.on('Repair Order', {
	onload(frm) {
		show_attribute_fields_for_subcategory(frm)
	},
	subcategory(frm) {
		hide_all_subcategory_attribute_fields(frm)
		show_attribute_fields_for_subcategory(frm)
	},
	order_form(frm){
		if(frm.doc.order_form){
			console.log('HERE')
			frm.set_df_property('cad', 'hidden', 1)
		}
		else{
			frm.set_df_property('cad', 'hidden', 0)
		}
	},
	est_delivery_date(frm) {
		validate_dates(frm, frm.doc, "est_delivery_date")
		frm.set_value('est_due_days', frappe.datetime.get_day_diff(frm.doc.est_delivery_date, frm.doc.order_date));
	}
});


frappe.ui.form.on("Rough Sketch Approval", {
	approved(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "designer_assignment_sketch", "rs_count")
	},
	reject(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "designer_assignment_sketch", "rs_count")
	}
})

frappe.ui.form.on("Final Sketch Approval HOD", {
	approved(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "rough_sketch_approval", "fs_count")
	},
	reject(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "rough_sketch_approval", "fs_count")
	}
})

function update_approved_qty_in_prev_table(frm,cdt,cdn, table, fieldname) {
	var d = locals[cdt][cdn]
	let row = frm.doc[table].find(r => r.designer == d.designer)
	if (!row) {
		frappe.throw(__("Designer not found in {0}", [table]))
	}
	row[fieldname] = flt(d.approved) + flt(d.reject)
	frm.refresh_field(table)
}

function show_attribute_fields_for_subcategory(frm) {
	if (frm.doc.subcategory) {
		frappe.model.with_doc("Attribute Value", frm.doc.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", frm.doc.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					let fields = subcategory_attribute_value.item_attributes.map((r) => { if (r.in_cad == 1) return r.item_attribute.toLowerCase().replace(/\s+/g, '_') })
					frm.toggle_display(fields, 1)
					frm.refresh_fields()
				}
			}
		});
	}
}

function hide_all_subcategory_attribute_fields(frm) {
	var fields = [
		"metal_target", "diamond_target", "metal_colour", "product_size",
		"length", "height", "sizer_type", "enamal", "rhodium", "stone_type",
		"gemstone_type", "gemstone_quality", "stone_changeable",
		"changeable", "hinges", "back_belt", "vanki_type", "black_beed",
		"black_beed_line", "screw_type", "hook_type", "lock_type", "two_in_one",
		"kadi_type", "chain", "chain_type", "customer_chain", "chain_length",
		"total_length", "chain_weight", "detachable", "back_chain", "back_chain_size",
		"back_side_size", "chain_thickness", "total_mugappu", "kadi_to_mugappu",
		"space_between_mugappu", "nakshi", "nakshi_from", "customer_sample",
		"certificate_place", "breadth", "width", "back_belt", "back_belt_length" ];
		frm.toggle_display(fields, 0)
		frm.refresh_fields()
}

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}