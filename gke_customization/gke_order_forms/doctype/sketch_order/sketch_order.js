// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sketch Order', {
	setup(frm) {
        var child_fields = [['category','Item Category'],
                            ['setting_type', 'Setting Type']];
        set_filters_on_child_table_fields(frm, child_fields);
		// frm.fields_dict['designer_assignment'].grid.add_custom_button("Testt",function() {

		// });
	},
	refresh(frm) {
		frm.set_query('sub_category', 'final_sketch_approval_cmo', function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return{
				filters: {
					'parent_attribute_value' : d.category
				}
			};
		});
	},
	validate(frm) {
		// if (frm.doc.__islocal) {
		// 	frm.clear_table("rough_sketch_approval")
		// 	frm.clear_table("final_sketch_approval")
		// 	frm.clear_table("final_sketch_approval_cmo")
		// 	frm.refresh_field(["rough_sketch_approval", "final_sketch_approval", "final_sketch_approval_cmo"])
		// }

		/*  moved to client script */
		// $.each(frm.doc.designer_assignment || [], function(i,d) {
		// 	if (!d.count_1) {
		// 		frappe.throw(__("Row #{0}: Assigned Qty is cannot be 0",[d.idx]))
		// 	}
		// 	if (!in_list(['Unassigned','On Hold'], frm.doc.workflow_state)) {
		// 		if (flt(d.count_1) != flt(d.rs_count)) {
		// 			frappe.throw("Assigned Qty(Designer Assignment) does not match with accepted & rejected qty in Rough Sketch Approval (HOD)")
		// 		}
		// 	}
		// })
		// if (!in_list(['Unassigned','Assigned','On Hold', 'On Hold - Assigned', 'Final Assigned', 'On Hold - Final Assigned'], frm.doc.workflow_state)) {
		// 	$.each(frm.doc.rough_sketch_approval || [], function(i,d) {
		// 		if (flt(d.approved) != flt(d.fs_count)) {
		// 			frappe.throw("Approved Qty(Rough Sketch Approval) does not match with accepted & rejected qty in Final Sketch Approval (HOD)")
		// 		}
		// 	})
		// }
		// if (!in_list(['Unassigned','Assigned','On Hold', 'On Hold - Assigned', 'Final Assigned', 'On Hold - Final Assigned','Rough Sketch Approval (HOD)','On Hold - Rough Sketch Approval'], frm.doc.workflow_state)) {
		// 	$.each(frm.doc.final_sketch_approval || [], function(i, d){
		// 		d.cmo_count = frm.doc.final_sketch_approval_cmo.filter(r=>r.designer==d.designer).length
		// 		// if (d.cmo_count != d.approved) frappe.msgprint("Rows in Final Sketch Approval (CMO / CPO) are lesser than approved qty")
		// 	})
		// 	frm.refresh_field("final_sketch_approval")
		// }
	},
	est_delivery_date(frm) {
		validate_dates(frm, frm.doc, "est_delivery_date")
		frm.set_value('est_due_days', frappe.datetime.get_day_diff(frm.doc.est_delivery_date, frm.doc.order_date));
	}
})

frappe.ui.form.on("Rough Sketch Approval", {
	approved(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "designer_assignment", "rs_count")
	},
	reject(frm,cdt,cdn) {
		update_approved_qty_in_prev_table(frm, cdt, cdn, "designer_assignment", "rs_count")
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

function set_filters_on_child_table_fields(frm, fields) {
    fields.map(function(field){
        frm.set_query(field[0], "final_sketch_approval_cmo", function() {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {'item_attribute': field[1]}
            }
        })
    })
}

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}