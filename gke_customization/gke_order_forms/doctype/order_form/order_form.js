frappe.ui.form.on('Order Form', {
	delivery_date: function (frm) {
		validate_dates(frm, frm.doc, "delivery_date")
		update_fields_in_child_table(frm, "delivery_date")
		calculate_due_days(frm);
	},
	estimated_duedate(frm) {
		validate_dates(frm, frm.doc, "estimated_duedate")
		update_fields_in_child_table(frm, "estimated_duedate")
	},
	// custom_cad_finish_date(frm) {
	// 	validate_dates(frm, frm.doc, "delivery_date")
	// 	// update_fields_in_child_table(frm, "delivery_date")
	// 	calculate_due_days(frm);
	// },
	system_due_date(frm) {
		validate_dates(frm, frm.doc, "system_due_date")
	},
	branch(frm) {
		update_fields_in_child_table(frm, "branch")
	},
	project(frm) {
		update_fields_in_child_table(frm, "project")
	},
	setup: function (frm, cdt, cdn) {
		var parent_fields = [['diamond_quality', 'Diamond Quality']];
		set_filters_on_parent_table_fields(frm, parent_fields);

		var fields = [['category', 'new Item subcategory1'],
		['subcategory', 'Item Subcategory'],
		['setting_type', 'Setting Type'],
		['metal_type', 'Metal Type'],
		['metal_purity', 'Metal Purity'],
		['diamond_quality', 'Diamond Quality'],
		['metal_touch', 'Metal Touch'],
		['metal_colour', 'Metal Colour'],
		['sizer_type', 'Sizer Type'],
		['enamal', 'Enamal'],
		['rhodium', 'Rhodium'],
		// ['gemstone_type', 'Gemstone Type'],
		['gemstone_quality', 'Gemstone Quality'],
		['stone_changeable', 'Stone Changeable'],
		['hinges', 'Hinges'],
		['back_belt_patti', 'Back Belt'],
		['vanki_type', 'Vanki Type'],
		['black_beed', 'Black Beed'],
		['screw_type', 'Screw Type'],
		['hook_type', 'Hook Type'],
		['lock_type', 'Lock Type'],
		['two_in_one', 'Two in One'],
		['kadi_type', 'Kadi Type'],
		['chain', 'Chain'],
		['chain_type', 'Chain Type'],
		['customer_chain', 'Customer Chain'],
		['detachable', 'Detachable'],
		['back_chain', 'Back Chain'],
		['nakshi_from', 'Nakshi From'],
		['nakshi', 'Nakshi'],
		['customer_sample', 'Customer Sample'],
		['certificate_place', 'Certificate Place'],
		['breadth', 'Breadth'],
		['width', 'Width'],
		['back_belt', 'Back Belt'],
		['back_belt_length', 'Back Belt Length'],
		['gemstone_type1', 'Gemstone Type1'],
		['sub_setting_type1', 'Sub Setting Type'],
		['sub_setting_type2', 'Sub Setting Type'],
		['gemstone_quality', 'Gemstone Quality'],
		['changeable_type', 'Changeable Type'],
		['feature', 'Feature'],
		['mod_reason', 'Mod Reason'],
		];

		set_filters_on_child_table_fields(frm, fields);
		// set_filter_for_salesman_name(frm);

		let design_fields = [["design_id", "tag_no"], ["reference_designid", "reference_serial_no_1"],
		["reference_design_id_2", "reference_serial_no_2"], ["reference_design_id_3", "reference_serial_no_3"]]
		set_filter_for_design_n_serial(frm, design_fields)
		// frm.set_query("parcel_place", function (doc) {
		// 	return {
		// 		query: "jewellery_erpnext.query.get_parcel_place",
		// 		filters: {
		// 			"customer_code": doc.customer_code
		// 		}
		// 	}
		// })
		frm.set_query('sub_setting_type1', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.setting_type
				}
			};
		});
		frm.set_query('sub_setting_type2', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.setting_type
				}
			};
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
		if (frm.doc.order_details) {
			frm.doc.order_details.forEach(function (d) {
				show_attribute_fields_for_subcategory(frm, d.doctype, d.name, d);
			})
		}
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
	concept_image: function (frm) {
		refresh_field('image_preview');
	},
	design_by: function (frm) { set_order_type_from_design_by(frm); },
	customer_code: function(frm){
		frm.doc.service_type = [];
        if(frm.doc.customer_code){
         frappe.model.with_doc("Customer", frm.doc.customer_code, function() {
          let customer_doc = frappe.model.get_doc("Customer", frm.doc.customer_code);
          $.each(customer_doc.service_type, function(index, row){
            let d = frm.add_child("service_type");
            d.service_type1 = row.service_type1;
          });
		  refresh_field("service_type");
         });
        }
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
		if (frm.doc.order_details) {
			frm.doc.order_details.forEach(function (d) {
				show_attribute_fields_for_subcategory(frm, d.doctype, d.name, d);
			})
		}
		// if(frm.doc.customer_code=='CU0010'){
		// 	frm.fields_dict['order_details'].grid.get_field('screw_type').get_query = function(doc, cdt, cdn) {
		// 		console.log('HERE')
		// 		var d = locals[cdt][cdn];
		// 		return { visible: 1 };
		// 	};
		// }
   	},
    refresh:function(frm) {
		frm.add_custom_button(__("Customer Order"), function(){
				erpnext.utils.map_current_doc({
					method: "jewellery_erpnext.gurukrupa_exports.doctype.order_form.order_form.make_order_form",
					source_doctype: "Customer Order Form",
					target: me.frm,
					setters: [
						{
							label: "Customer Name",
							fieldname: "customer_code",
							fieldtype: "Link",
							options: "Customer",
							reqd: 1,
							read_only:1,
							default: frm.doc.customer_code || undefined
							
						},
						{
							label: "Item Category",
							fieldname: "item_category",
							fieldtype: "Link",
							options: "Attribute Value",
							get_query: function(doc, cdt, cdn) {
								return {
									query: 'jewellery_erpnext.query.item_attribute_query',
									filters: { 'item_attribute': "Item Category"}
								};
							}
							
						},
						{
							label: "Metal Touch",
							fieldname: "metal_touch",
							fieldtype: "Link",
							options: "Attribute Value",
							get_query: function(doc, cdt, cdn) {
								return {
									query: 'jewellery_erpnext.query.item_attribute_query',
									filters: { 'item_attribute': "Metal Touch"}
								};
							}
							
						}
					],
					get_query_filters: {
						// customer_code: ['=', cur_frm.doc.customer_code],
						docstatus: 1
					}
				})
			}, __("Get Order From"))
	},
});

frappe.ui.form.on('Order Form Detail', {
	form_render(frm, cdt, cdn) {
		let order_detail = locals[cdt][cdn];
		if (order_detail.subcategory) {
			set_field_visibility(frm, cdt, cdn)
		}
	},

	tag_no(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "tag_no", "design_id")
		if (d.tag_no) {
			frappe.db.get_value("BOM",{"tag_no": d.tag_no},'name', (r)=>{
				frappe.model.set_value(cdt, cdn, 'bom', r.name)
			})
		}
	},

	reference_serial_no_1(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "reference_serial_no_1", "reference_designid")
	},

	reference_serial_no_2(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "reference_serial_no_2", "reference_design_id_2")
	},

	reference_serial_no_3(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "reference_serial_no_3", "reference_design_id_3")
	},

	design_id: function (frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.design_id) {
			let list_of_attributes = [];
			frappe.call({
				method: "gke_customization.gke_order_forms.doctype.order_form.order_form.get_bom_details",
				args: {
					"design_id": d.design_id,
				},
				callback(r) {
					if(r.message) {

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
		
						d.metal_target = r.message.metal_target
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
		} else {
			d.design_image = "";
			d.image = "";
			d.category = "";
			d.subcategory = "";
			d.setting_type = "";
			d.bom = "";
			refresh_field('order_details');
		}
	},

	subcategory: function (frm, cdt, cdn) {
		set_field_visibility(frm, cdt, cdn)
	},

	order_details_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.delivery_date = frm.doc.delivery_date;
		row.diamond_quality = frm.doc.diamond_quality;
		row.estimated_duedate = frm.doc.estimated_duedate;
		row.branch = frm.doc.branch
		row.project = frm.doc.project
		row.customer_code = frm.doc.customer_code
		refresh_field("order_details");
	},

	design_image: function (frm, cdt, cdn) {
		refresh_field("order_details");
	},

	design_type: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(row.doctype, row.name, 'category', '');
		frappe.model.set_value(row.doctype, row.name, 'subcategory', '');
		frappe.model.set_value(row.doctype, row.name, 'setting_type', '');
		frappe.model.set_value(row.doctype, row.name, 'metal_purity', '');
		frappe.model.set_value(row.doctype, row.name, 'gemstone_price', '');
		frappe.model.set_value(row.doctype, row.name, 'reference_tagdesignid', '');
		frappe.model.set_value(row.doctype, row.name, 'design_image', '');
		frappe.model.set_value(row.doctype, row.name, 'image', '');
		frappe.model.set_value(row.doctype, row.name, 'tag_no', '');
		frappe.model.set_value(row.doctype, row.name, 'item', '');
		frappe.model.set_value(row.doctype, row.name, 'bom', '');
		frappe.model.set_value(row.doctype, row.name, 'design_id', '');
	},

	design_by: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.design_by == "Customer Design") {
			frappe.model.set_value(row.doctype, row.name, 'design_type', 'New Design');
		} else {
			frappe.model.set_value(row.doctype, row.name, 'design_type', '');
		}
	},

	category: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(row.doctype, row.name, 'subcategory', '');
	},

	serial_no_bom(frm, cdt, cdn) {
		set_metal_properties_from_bom(frm, cdt, cdn)
	},

	bom(frm, cdt, cdn) {
		set_metal_properties_from_bom(frm, cdt, cdn)
	},
	// metal_colour(frm,cdt,cdn){
	// 	var row = locals[cdt][cdn];
	// 	if (row.design_type=='Mod'){
	// 		// var row = locals[cdt][cdn];
			
	// 		frappe.call({
	// 			method: 'catalog.catalog.doctype.cad_order_form.cad_order_form.get_metal_color_varinat',
	// 			args: {
	// 				'metal_colour': row.metal_colour,
	// 				'design_id':row.design_id
	// 			},
	// 			callback: function(r) {
	// 				if (!r.exc) {
	// 					if (r.message){
	// 						console.log(r.message)
	// 						row.design_id = r.message
	// 						frm.refresh_field('order_details')
	// 					}
	// 				}
	// 			}
	// 		});
	// 	}
	// }

});

function set_metal_properties_from_bom(frm, cdt, cdn) {
	let row = locals[cdt][cdn]
	if (row.design_type == "Mod" && (row.serial_no_bom || row.bom)) {
		frappe.db.get_value("BOM", row.serial_no_bom || row.bom, ["metal_touch","metal_type","metal_colour","metal_purity"], (r)=> {
			frappe.model.set_value(cdt, cdn, r)
		})
	}
}



function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}

function fetch_item_from_serial(doc, fieldname, itemfield) {
	if (doc[fieldname]) {
		frappe.db.get_value("Serial No", doc[fieldname], 'item_code', (r) => {
			frappe.model.set_value(doc.doctype, doc.name, itemfield, r.item_code)
		})
	}
}

function set_field_visibility(frm, cdt, cdn) {
	hide_all_subcategory_attribute_fields(frm, cdt, cdn);
	var order_detail = locals[cdt][cdn];
	show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail);
};

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
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1], "customer_code": doc.customer_code }
			};
		});
	});
}

//public function to set order type 
function set_order_type_from_design_by(frm) {
	if (cur_frm.doc.design_by == "Customer Design")
		cur_frm.doc.order_type = "Customer Order";
	else
		cur_frm.doc.order_type = "Stock Order";
	cur_frm.refresh_field("order_type");
}

//public function to show item attribute fields based on the selected subcategory
function show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail) {
	if (order_detail.subcategory) {
		frappe.model.with_doc("Attribute Value", order_detail.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", order_detail.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					$.each(subcategory_attribute_value.item_attributes, function (index, row) {
						if (row.in_cad == 1)
							show_field(frm, cdt, cdn, row.item_attribute);
					});
				}
			}
		});
	}
}

//private function to hide all subcategory related fields in order details
function hide_all_subcategory_attribute_fields(frm, cdt, cdn) {
	// var subcategory_attribute_fields = ['Hinges', 'Back Belt', 'Vanki Type',
	// 'Black Beed', 'Black Beed Line', 'Lock Type',
	// '2 in 1', 'Chain', 'Chain Type', 'Customer Chain', 'Chain Length',
	// 'Total Length', 'Chain Weight', 'Back Chain', 'Back Chain Size',
	// 'Back Side Size', 'Chain Thickness', 'Total Mugappu', 'Kadi to Mugappu',
	// 'Space between Mugappu', 'Nakshi', 'Nakshi From', 'Breadth', 'Width', 'Back Belt', 'Back Belt Length'];
	
	var subcategory_attribute_fields = ['Lock Type','Back Chain','Back Chain Size','Back Belt','Back Belt Length','Black Beed','Black Beed Line',
	'Back Side Size','Hinges','Back Belt Patti','Vanki Type','Total Length','Chain','Chain Type','Chain From','Chain Weight',
	'Chain Length','Number of Ant','Distance Between Kadi To Mugappu','Space between Mugappu','Two in One']

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
	//     //console.log(field.toLowerCase().replace(/\s+/g, '_'));
	//     //console.log(df.hidden);
	//     df.hidden = hidden;
	//    // console.log(df.hidden);
	//     if (df.hidden===0) df.reqd = 0;
	// }
	var field_name = field.toLowerCase().replace(/\s+/g, '_')
	var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
	if (df) {
		df.hidden = hidden;
		if (df.hidden == 0) df.reqd = 0;
	}
	frm.refresh_field("order_details");
}

// Auto calculate due days from delivery date    
function calculate_due_days(frm) {
	frm.set_value('due_days', frappe.datetime.get_day_diff(frm.doc.delivery_date, frm.doc.order_date));
}

// Auto Calculate delivery date from due days
function delivery_date(frm) {
	frm.set_value('delivery_date', frappe.datetime.add_days(frm.doc.order_date, frm.doc.due_days));
}

function set_filter_for_salesman_name(frm) {
	frm.set_query("salesman_name", function () {
		return {
			"filters": { "designation": "Sales Person" }
		};
	});
}

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.order_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("order_details");
}

function set_filter_for_design_n_serial(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], "order_details", function (doc, cdt, cdn) {
			return {
				filters: {
					"is_design_code": 1,
					"is_stock_item":1
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