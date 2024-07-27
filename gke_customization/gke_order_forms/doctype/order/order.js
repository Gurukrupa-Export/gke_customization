// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt


frappe.ui.form.on('Order', {
	after_workflow_action(frm){
		if(frm.doc.workflow_state == "Designing - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}
		if(frm.doc.workflow_state == "Sent to QC - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "Creating BOM - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "Updating BOM - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "BOM QC - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
	},
	refresh(frm) {		
		frm.refresh_field("update_reason");
	},
	onload(frm) {		
		show_attribute_fields_for_subcategory(frm)
		frm.get_field('designer_assignment').grid.cannot_add_rows = true;
	},
	subcategory(frm) {
		show_attribute_fields_for_subcategory(frm)
	},
	est_delivery_date(frm) {
		validate_dates(frm, frm.doc, "est_delivery_date")
		frm.set_value('est_due_days', frappe.datetime.get_day_diff(frm.doc.est_delivery_date, frm.doc.order_date));
	},
	designer(frm){
		show_designer_dialog(frm);
	},
	// onload(frm) {
	// 	console.log(frm.doc.workflow_state);
    //     if (frm.doc.workflow_state === 'Designing') { 
	// 		frappe.prompt([
	// 			{
	// 				label: 'Designer',
	// 				fieldname: 'designer',
	// 				fieldtype: 'Link',
	// 				options: 'Employee',
	// 				get_query(){
	// 					return {
	// 						"filters": [                                    
	// 							["Employee", "designation", "=", "Designer"],    
	// 						]
	// 					}
	// 				}
	// 			},
	// 		], (values) => {
	// 			let v = {designer: values.designer,};		
	// 			let new_row = frm.add_child("designer_assignment");
	// 			$.extend(new_row, v);
	// 			frm.refresh_field("designer_assignment");
	// 			if (frm.doc.designer_assignment.length >1) {
	// 				frm.set_value("workflow_state","Assigned")
	// 				frm.save()
	// 			}
	// 		});	
    //     }
    // },
	// validate: function(frm){
	// 	calculate_total(frm)
	// }
	
});

function show_designer_dialog(frm){
	frappe.prompt([
		{
			label: 'Designer',
			fieldname: 'designer',
			fieldtype: 'Link',
			options: 'Employee',
			get_query(){
				return {
					"filters": [                                    
						["Employee", "designation", "=", "Designer"],    
					]
				}
			}
		},
	], (values) => {
		let designer_exists = frm.doc.designer_assignment.some(row => row.designer === values.designer);
		
		if (designer_exists) {
            frappe.msgprint(__('Designer already assigned.'));
		}
		else{
			let v = {designer: values.designer,};		
			let new_row = frm.add_child("designer_assignment");
			$.extend(new_row, v);
			frm.refresh_field("designer_assignment");
			frm.set_df_property("designer_assignment", "read_only", 1);

			if (frm.doc.designer_assignment.length >1) {
				frm.set_value("workflow_state","Assigned")
				frm.save()
			}
		}

	});
}

function update_fields_in_child_table(designer) {
	$.each(frm.doc.designer_assignment || [], function (i, d) {
		d["designer"] = designer;
	});
	refresh_field("designer_assignment");
};

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

frappe.ui.form.on("BOM Metal Detail", {
	cad_weight: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.cad_weight && d.cad_to_finish_ratio) {
			frappe.model.set_value(
				d.doctype,
				d.name,
				"quantity",
				flt((d.cad_weight * d.cad_to_finish_ratio) / 100)
			);
		}
	},
	cad_to_finish_ratio: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.cad_weight && d.cad_to_finish_ratio) {
			frappe.model.set_value(
				d.doctype,
				d.name,
				"quantity",
				flt((d.cad_weight * d.cad_to_finish_ratio) / 100)
			);
		}
	},

	quantity: function (frm) {
		calculate_total(frm);
	},
});

frappe.ui.form.on("BOM Diamond Detail", {
	diamond_sieve_size: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		frappe.db.get_value("Attribute Value", d.diamond_sieve_size, "weight_in_cts").then((r) => {
			frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", r.message.weight_in_cts);
		});
		let filter_value = {
			parent: d.diamond_sieve_size,
			diamond_shape: d.stone_shape,
		};
		frappe.call({
			method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.check_diamond_sieve_size_tolerance_value_exist",
			args: {
				filters: filter_value,
			},
			callback: function (r) {
				console.log(r.message);
				if (r.message.length == 0 && d.stone_shape == "Round") {
					frappe.msgprint(
						__("Please Insert Diamond Sieve Size Tolerance at Attribute Value")
					);
					frappe.validated = false;
				}
			},
		});
	},
	pcs: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.quantity == 0.0) {
			let filter_value = {
				name: d.diamond_sieve_size,
			};
			frappe.call({
				method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_weight_in_cts_from_attribute_value",
				args: {
					filters: filter_value,
				},
				callback: function (r) {
					if (r.message) {
						let weight_in_cts = r.message[0].weight_in_cts;
						console.log(weight_in_cts);
						frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", weight_in_cts);
						frappe.model.set_value(
							d.doctype,
							d.name,
							"quantity",
							flt(d.pcs * weight_in_cts)
						);
					}
				},
			});
		}
	},
	quantity: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.pcs > 0) {
			var cal_a = flt(d.quantity / d.pcs, 4);
			console.log(cal_a);
		} else {
			frappe.msgprint(__("Please set PCS value"));
			frappe.validated = false;
		}
		if (d.quantity > 0 && d.stone_shape == "Round" && d.quality) {
			let filter_quality_value = {
				parent: d.diamond_sieve_size,
				diamond_shape: d.stone_shape,
				diamond_quality: d.quality,
			};
			frappe.call({
				method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_quality_diamond_sieve_size_tolerance_value",
				args: {
					filters: filter_quality_value,
				},
				callback: function (r) {
					console.log(r.message);
					let records = r.message;
					if (records) {
						for (let i = 0; i < records.length; i++) {
							let fromWeight = flt(records[i].from_weight);
							let toWeight = flt(records[i].to_weight);
							if (cal_a >= fromWeight && cal_a <= toWeight) {
								// The cal_a value is within the range, do nothing
								frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
								return;
							} else {
								frappe.msgprint(
									`Calculated value ${cal_a} is outside the allowed tolerance range ${fromWeight} to ${toWeight}`
								);
								frappe.validated = false;
								frappe.model.set_value(d.doctype, d.name, "quantity", null);
								return;
							}
						}
					} else {
						frappe.msgprint(__("Tolerance range record not found"));
						frappe.validated = false;
						frappe.model.set_value(d.doctype, d.name, "quantity", null);
						return;
					}
					frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
				},
			});
		}
		if (d.quantity > 0 && d.stone_shape == "Round" && !d.quality) {
			let filter_universal_value = {
				parent: d.diamond_sieve_size,
				for_universal_value: 1,
			};
			// Get records Universal Attribute Value Diamond Sieve Size
			frappe.call({
				method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_records_universal_attribute_value",
				args: {
					filters: filter_universal_value,
				},
				callback: function (r) {
					console.log(r.message);
					let records = r.message;
					if (records) {
						for (let i = 0; i < records.length; i++) {
							let fromWeight = flt(records[i].from_weight);
							let toWeight = flt(records[i].to_weight);
							if (cal_a >= fromWeight && cal_a <= toWeight) {
								// The cal_a value is within the range, do nothing
								frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
								return;
							} else {
								frappe.msgprint(
									`Calculated value ${cal_a} is outside the allowed tolerance range ${fromWeight} to ${toWeight}`
								);
								frappe.validated = false;
								frappe.model.set_value(d.doctype, d.name, "quantity", null);
								return;
							}
						}
					} else {
						// If no range includes cal_a for both specific and universal Diamond Sieve Size, throw an error
						frappe.msgprint(__("Tolerance range record not found"));
						frappe.validated = false;
						frappe.model.set_value(d.doctype, d.name, "quantity", null);
						return;
					}
					frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
				},
			});
		}
	},
});

frappe.ui.form.on("BOM Gemstone Detail", {
	quantity: function (frm) {
		calculate_total(frm);
	},
	pcs: function (frm) {
		calculate_total(frm);
	},
});

frappe.ui.form.on("BOM Finding Detail", {
	quantity: function (frm) {
		calculate_total(frm);
	},
});

function calculate_total(frm) {
	let total_metal_weight = 0;
	let diamond_weight = 0;
	let total_gemstone_weight = 0;
	let finding_weight = 0;
	let total_diamond_pcs = 0;
	let total_gemstone_pcs = 0;

	if (frm.doc.metal_detail) {
		frm.doc.metal_detail.forEach(function (d) {
			total_metal_weight += d.quantity;
		});
	}
	if (frm.doc.diamond_detail) {
		frm.doc.diamond_detail.forEach(function (d) {
			diamond_weight += d.quantity;
			total_diamond_pcs += d.pcs;
		});
	}
	if (frm.doc.gemstone_detail) {
		frm.doc.gemstone_detail.forEach(function (d) {
			total_gemstone_weight += d.quantity;
			total_gemstone_pcs += d.pcs;
		});
	}
	if (frm.doc.finding_detail) {
		frm.doc.finding_detail.forEach(function (d) {
			if (d.finding_category != "Chains") {
				finding_weight += d.quantity;
			}
		});
	}
	frm.set_value("total_metal_weight", total_metal_weight);

	frm.set_value("total_diamond_pcs", total_diamond_pcs);
	frm.set_value("diamond_weight", diamond_weight);
	frm.set_value("total_diamond_weight", diamond_weight);

	frm.set_value("total_gemstone_pcs", total_gemstone_pcs);
	frm.set_value("gemstone_weight", total_gemstone_weight);
	frm.set_value("total_gemstone_weight", total_gemstone_weight);

	frm.set_value("finding_weight", finding_weight);
	frm.set_value("metal_and_finding_weight", frm.doc.total_metal_weight + frm.doc.finding_weight);
	if (frm.doc.metal_and_finding_weight) {
		frm.set_value(
			"gold_to_diamond_ratio",
			frm.doc.metal_and_finding_weight / frm.doc.diamond_weight
		);
	}
	if (frm.doc.total_diamond_pcs) {
		frm.set_value("diamond_ratio", frm.doc.diamond_weight / frm.doc.total_diamond_pcs);
	}
}