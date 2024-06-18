// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Repair Order Form', {
	delivery_date: function (frm) {
		validate_dates(frm, frm.doc, "delivery_date")
		update_fields_in_child_table(frm, "delivery_date")
		calculate_due_days(frm);
	},
	estimated_duedate(frm) {
		validate_dates(frm, frm.doc, "estimated_duedate")
		update_fields_in_child_table(frm, "estimated_duedate")
	},
	system_due_date(frm) {
		validate_dates(frm, frm.doc, "system_due_date")
	},
	diamond_quality: function (frm) {
		$.each(frm.doc.order_details || [], function (i, d) {
			d.diamond_quality = frm.doc.diamond_quality;
		});
		refresh_field("order_details");
	},
	customer_code: function (frm) {
		frm.doc.service_type = [];
		if (frm.doc.customer_code) {
			frappe.model.with_doc("Customer", frm.doc.customer_code, function () {
				let customer_doc = frappe.model.get_doc("Customer", frm.doc.customer_code);
				$.each(customer_doc.service_type, function (index, row) {
					let d = frm.add_child("service_type");
					d.service_type1 = row.service_type1;
				});
				refresh_field("service_type");
			});
		}
	},
	setup: function (frm) {
		frm.set_query("department", function(){
			return {
				"filters": [
					["Department", "company", "=", frm.doc.company],
				]
			}
		});
		frm.set_query("branch", function(){
			return {
				"filters": [
					["Branch", "company", "=", frm.doc.company],
				]
			}
		});
		frm.set_query("diamond_quality", function (doc) {
			if (!doc.customer_code) {
				frappe.throw("Please select customer code.")
			}
			return {
				query: 'jewellery_erpnext.query.diamond_grades_query',
				filters: {
					"customer": doc.customer_code
				}
			}
		});
		frm.set_query('subcategory', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.category
				}
			};
		});
		frm.set_query('diamond_quality','order_details', function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': "Diamond Quality", "customer_code": doc.customer_code }
			};
		});
		frm.set_query('bom', 'order_details', function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'item': d.item
				}
			};
		});
		if (frm.doc.order_details) {
			frm.doc.order_details.forEach(function (d) {
				show_attribute_fields_for_subcategory(frm, d.doctype, d.name, d);
			})
		};

		var fields = [['category', 'Item Category'],
		['subcategory', 'Item Subcategory'],
		['diamond_quality', 'Diamond Quality'],
		['metal_touch', 'Metal Touch'],
		['metal_type', 'Metal Type'],
		['metal_purity', 'Metal Purity'],
		['metal_colour', 'Metal Colour'],
		['setting_type', 'Setting Type'],
		['sub_setting_type1', 'Sub Setting Type'],
		['sub_setting_type2', 'Sub Setting Type'],
		['sizer_type', 'Sizer Type'],
		['enamal', 'Enamal'],
		['rhodium', 'Rhodium'],
		['gemstone_type1', 'Gemstone Type1'],
		['gemstone_quality', 'Gemstone Quality'],
		['stone_changeable', 'Stone Changeable'],
		['back_belt_patti', 'Back Belt Patti'],
		['vanki_type', 'Vanki Type'],
		['black_beed', 'Black Beed'],
		['lock_type', 'Lock Type'],
		['2_in_1', '2 in 1'],
		['chain', 'Chain'],
		['chain_type', 'Chain Type'],
		['customer_chain', 'Customer Chain'],
		['detachable', 'Detachable'],
		['back_chain', 'Back Chain'],
		['nakshi_from', 'Nakshi From'],
		['customer_sample', 'Customer Sample'],
		['customer_sample', 'Customer Good'],
		['certificate_place', 'Certificate Place'],
		['back_belt', 'Back Belt'],
		['repair_type', 'Repair Type'],
		['product_type','Product Type'],
		];
		set_filters_on_child_table_fields(frm, fields);

		let design_fields = [["item", "tag_no"]]
		set_filter_for_design_n_serial(frm, design_fields)
		
		
	},
	due_days: function (frm) {
		delivery_date(frm);
	},
	validate: function (frm) {
		if (frm.doc.delivery_date < frm.doc.order_date) {
			frappe.msgprint(__("You can not select past date in Delivery Date"));
			frappe.validated = false;
		}
	},
	// concept_image: function (frm) {
	// 	refresh_field('image_preview');
	// },
	// design_by: function (frm) {
	// 	set_order_type_from_design_by(frm);
	// },
	scan_serial_no: function (frm) {
		if (frm.doc.scan_serial_no) {
			frappe.call({
				method: "erpnext.selling.page.point_of_sale.point_of_sale.search_for_serial_or_batch_or_barcode_number",
				args: {
					'search_value': frm.doc.scan_serial_no
				},

				callback: function (r) {
					if (r.message.item_code) {
						let d = frm.add_child('order_details');
						d.item = r.message.item_code;
						d.delivery_date = frm.doc.delivery_date;
						d.diamond_quality = frm.doc.diamond_quality;
						frappe.model.with_doc("Item", r.message.item_code, function (m) {
							var doc = frappe.model.get_doc("Item", r.message.item_code);
							if (doc.attributes) {
								$.each(doc.attributes, function (index, row) {
									var field = row.attribute.toLowerCase().replace(/\s+/g, '_');
									d[field] = row.attribute_value;
								});
							}
						});
						frm.set_value('scan_serial_no', '');
					} else {
						frappe.msgprint('Cannot find Item with this barcode');
					}
					frm.refresh_field('order_details');
				}
			});
		}
	}
});

frappe.ui.form.on('Repair Order Form Detail', {
	form_render: function (frm, cdt, cdn) {
		let order_detail = locals[cdt][cdn];
		if (order_detail.subcategory) {
			set_field_visibility(frm, cdt, cdn)
		}
	},

	tag_no(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "tag_no", "item")
		if (d.tag_no) {
			frappe.db.get_value("BOM",{"tag_no": d.tag_no},'name', (r)=>{
				frappe.model.set_value(cdt, cdn, 'bom', r.name)
			})
			// frappe.call({
			// 	method: 'frappe.client.get_value',
			// 	args: {
			// 		'doctype': 'Item',
			// 	},
			// 	callback: function(r) {
			// 		if (!r.exc) {
			// 			// code snippet
			// 		}
			// 	}
			// });

			frappe.db.get_value("BOM",{"tag_no": d.tag_no},'gross_weight', (r)=>{
				frappe.model.set_value(cdt, cdn, 'bom_weight', r.gross_weight)
			})
		}
	},

	item: function (frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.item) {
			frappe.call({
				method: "gke_customization.gke_order_forms.doctype.repair_order_form.repair_order_form.get_bom_details",
				args: {
					"design_id": d.item,
				},
				callback(r) {
					if(r.message) {
						d.bom_weight = r.message.gross_weight
						d.category = r.message.item_category;
						d.subcategory = r.message.item_subcategory;
						d.setting_type = r.message.setting_type;
						d.sub_setting_type1 = r.message.sub_setting_type1
						d.sub_setting_type2 = r.message.sub_setting_type2
						d.bom = r.message.master_bom;

						d.qty = r.message.qty
						d.metal_type = r.message.metal_type
						d.metal_touch = r.message.metal_touch
						d.metal_purity = r.message.metal_purity
						d.metal_colour = r.message.metal_colour
						
						
						// d.metal_target = r.message.metal_target
						d.metal_target = r.message.custom_metal_target
						d.diamond_target = r.message.diamond_target
						d.product_size = r.message.product_size
						d.sizer_type = r.message.sizer_type
		
						d.length = r.message.length
						d.height = r.message.height
						d.width = r.message.width
						
						d.stone_changeable = r.message.stone_changeable
						d.detachable = r.message.detachable

						d.lock_type = r.message.lock_type
						d.feature = r.message.feature
						
						d.back_chain = r.message.back_chain
						d.back_chain_size = r.message.back_chain_size
						d.back_belt = r.message.back_belt
						d.back_belt_length = r.message.back_belt_length
						d.black_beed = r.message.black_beed
						d.black_beed_line = r.message.black_beed_line
						d.back_side_size = r.message.back_side_size
						
						d.back_belt_patti = r.message.back_belt_patti
						d.vanki_type = r.message.vanki_type
						d.rhodium = r.message.rhodium

						d.chain = r.message.chain
						d.chain_type = r.message.chain_type
						d.customer_chain = r.message.customer_chain
						d.chain_weight = r.message.chain_weight
						d.chain_length = r.message.chain_length

						d.number_of_ant = r.message.number_of_ant
						d.distance_between_kadi_to_mugappu = r.message.distance_between_kadi_to_mugappu
						d.space_between_mugappu = r.message.space_between_mugappu
						d.two_in_one = r.message.two_in_one

						d.rhodium = r.message.rhodium
						d.enamal = r.message.enamal

						d.gemstone_type1 = r.message.gemstone_type1
						d.gemstone_quality = r.message.gemstone_quality
				
						refresh_field('order_details');
						set_field_visibility(frm, cdt, cdn)
					}
				}
			});
		}
		else {
			d.bom_weight = ""
			d.category = ""
			d.subcategory = ""
			d.setting_type = ""
			d.sub_setting_type1 = ""
			d.sub_setting_type2 = ""
			d.bom = ""

			d.qty = ""
			d.metal_type = ""
			d.metal_touch = ""
			d.metal_purity = ""
			d.metal_colour = ""

			// d.metal_target = ""
			d.metal_target = ""
			d.diamond_target = ""
			d.product_size = ""
			d.sizer_type = ""

			d.length = ""
			d.height = ""
			d.width = ""
			
			d.stone_changeable = ""
			d.detachable = ""

			d.lock_type = ""
			d.feature = ""
			
			d.back_chain = ""
			d.back_chain_size = ""
			d.back_belt = ""
			d.back_belt_length = ""
			d.black_beed = ""
			d.black_beed_line = ""
			d.back_side_size = ""
			
			d.back_belt_patti = ""
			d.vanki_type = ""
			d.rhodium = ""

			d.chain = ""
			d.chain_type = ""
			d.customer_chain = ""
			d.chain_weight = ""
			d.chain_length = ""

			d.number_of_ant = ""
			d.distance_between_kadi_to_mugappu = ""
			d.space_between_mugappu = ""
			d.two_in_one = ""

			d.rhodium = ""
			d.enamal = ""
			d.gemstone_type1 = ""
			d.gemstone_quality = ""
			refresh_field('order_details');
		}
	},
	// bom: function (frm, cdt, cdn) {
	// 	var d = locals[cdt][cdn];

	// 	if (d.bom) {
	// 		frappe.db.get_value("BOM", { "name": d.bom }, "metal_purity", function (value) {
	// 			d.purity = value.metal_purity;
	// 			refresh_field('order_details');

	// 		});
	// 	}
	// 	else {
	// 		d.purity = "";
	// 		refresh_field('order_details');

	// 	}
	// },
	subcategory: function (frm, cdt, cdn) {
		set_field_visibility(frm, cdt, cdn)
	},
	order_details_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.delivery_date = frm.doc.delivery_date;
		row.diamond_quality = frm.doc.diamond_quality;
		// row.estimated_duedate = frm.doc.estimated_duedate;
		// row.branch = frm.doc.branch
		// row.project = frm.doc.project
		refresh_field("order_details");
	},
	// design_image: function (frm, cdt, cdn) {
	// 	refresh_field("order_details");
	// },

	// design_type: function (frm, cdt, cdn) {
	// 	var row = locals[cdt][cdn];
	// 	frappe.model.set_value(row.doctype, row.name, 'category', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'subcategory', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'setting_type', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'purity', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'gemstone_price', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'design_image', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'image', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'tag_no', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'item', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'bom', '');
	// 	frappe.model.set_value(row.doctype, row.name, 'design_id', '');
	// },

	category: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(row.doctype, row.name, 'subcategory', '');
	}
});

function set_field_visibility(frm, cdt, cdn) {
	hide_all_subcategory_attribute_fields(frm, cdt, cdn);
	var order_detail = locals[cdt][cdn];
	show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail);
};

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}

//public function to set item attribute filters on child doctype
function set_filters_on_child_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], "order_details", function () {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1] }
			};
		});
	});
}

//public function to set item attribute filters on parent doctype
function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function () {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1] }
			};
		});
	});
}

//public function to show item attribute fields based on the selected subcategory
function show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail) {
	if (order_detail.subcategory) {
		frappe.model.with_doc("Attribute Value", order_detail.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", order_detail.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					$.each(subcategory_attribute_value.item_attributes, function (index, row) {
						show_field(frm, cdt, cdn, row.item_attribute);
					});
				}
			}
		});
	}
}

//private function to hide all subcategory related fields in order details
function hide_all_subcategory_attribute_fields(frm, cdt, cdn) {

	var subcategory_attribute_fields = ['Lock Type','Back Chain','Back Belt','Black Beed','Back Side Size','Hinges','Back Belt Patti','Chain Type',
		'Vanki','Total Length','Number of Ant','Distance Between Kadi To Mugappu','Space between Mugappu','Two in One']
	show_hide_fields(frm, cdt, cdn, subcategory_attribute_fields, 1);
}


//private function to show single child table field
function show_field(frm, cdt, cdn, field_name) {
	show_hide_field(frm, cdt, cdn, field_name, 0);
}

//private function to show or hide multiple child table fields
function show_hide_fields(frm, cdt, cdn, fields, hidden) {
	fields.map(function (field) {
		show_hide_field(frm, cdt, cdn, field, hidden);
	});
}

//private function to show or hide single child table fields
function show_hide_field(frm, cdt, cdn, field, hidden) {
	// var df = frappe.meta.get_docfield(cdt, field.toLowerCase().replace(/\s+/g, '_'), cdn);
	// if (df) {
	//     df.hidden = hidden;
	//     if (df.hidden===0) df.reqd = 0;
	// }

	var field_name = field.toLowerCase().replace(/\s+/g, '_')
	var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
	if (df) {
		df.hidden = hidden;
		if (df.hidden == 0) df.reqd = 0;
	}
	cur_frm.refresh_field("order_details");
}

// Auto calculate due days from delivery date 
function calculate_due_days(frm) {
	frm.set_value('due_days', frappe.datetime.get_day_diff(frm.doc.delivery_date, frm.doc.order_date));
}

// Auto Calculate delivery date from due days
function delivery_date(frm) {
	frm.set_value('delivery_date', frappe.datetime.add_days(frm.doc.order_date, frm.doc.due_days));
}

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.order_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("order_details");
}

function fetch_item_from_serial(doc, fieldname, itemfield) {
	if (doc[fieldname]) {
		frappe.db.get_value("Serial No", doc[fieldname], 'item_code', (r) => {
			frappe.model.set_value(doc.doctype, doc.name, itemfield, r.item_code)
		})
	}
}

function set_filter_for_design_n_serial(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], "order_details", function (doc, cdt, cdn) {
			return {
				filters: {
					"is_design_code": 1
				}
			}
		});
		frm.set_query(field[1], "order_details", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn]
			if (d[field[0]]) {
				return {
					filters: {
						"item_code": d[field[0]]
					}
				}
			}
			return {}
		})
	});
}