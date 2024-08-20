// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Order', {
	onload(frm) {
		show_attribute_fields_for_subcategory(frm)
	},
	subcategory(frm) {
		// hide_all_subcategory_attribute_fields(frm)
		show_attribute_fields_for_subcategory(frm)
	},
	est_delivery_date(frm) {
		validate_dates(frm, frm.doc, "est_delivery_date")
		frm.set_value('est_due_days', frappe.datetime.get_day_diff(frm.doc.est_delivery_date, frm.doc.order_date));
	}
});

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
		"length", "height", "stone_type",
		"gemstone_type", "gemstone_quality", "stone_changeable",
		"changeable", "hinges", "back_belt", "vanki_type", "black_beed",
		"black_beed_line", "screw_type", "hook_type", "lock_type", "2_in_1",
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

// frappe.ui.form.on('Order', {
//     refresh: function(frm) {
//         frm.fields_dict['status'].$input.on('change', function() {
//             if (frm.doc.status === 'Start Designing') {
//                 // Assuming 'designer_assignment' is the child table
//                 var designerAssignments = frm.doc.designer_assignment;

//                 // Assuming you have a link field 'employee' in the Timesheet
//                 frappe.call({
//                     method: 'jewellery_erpnext.gurukrupa_exports.doctype.cad_order.cad_order.update_timesheet_employee',
//                     args: {
//                         timesheet_name: frm.doc.timesheet,  // Replace with the actual fieldname
//                         designer_assignments: designerAssignments
//                     },
//                     callback: function(response) {
//                         if (response.message) {
//                             frappe.msgprint('Employee data updated in Timesheet.');
//                         } else {
//                             frappe.msgprint('Failed to update employee data in Timesheet.');
//                         }
//                     }
//                 });
//             }
//         });
//     }
// });
