frappe.ui.form.on('Sketch Order Form', {
    setup: function(frm) {
        set_item_attribute_filters_in_sketch_order_form_detail_fields(frm);
        set_item_attribute_filters_in_sketch_order_form_setting_type(frm);
        set_item_attribute_filters_in_sketch_order_form_colour_stone(frm);
        set_filters_for_design_attributes(frm)
		frm.set_query('subcategory', 'order_details', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
                filters: {
                    'parent_attribute_value' : d.category
                }
            };
        });
		frm.set_query('subsetting_type', 'order_details', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
                filters: {
                    'parent_attribute_value' : d.setting_type
                }
            };
        });
		frm.set_query("tag__design_id","order_details", function(doc, cdt, cdn) {
			return {
				filters: {
					"is_design_code": 1
				}
			}
		});
        set_filter_for_design_n_serial(frm, [["reference_designid","reference_tagid"]],"order_details")
    },
    delivery_date: function(frm){
        validate_dates(frm, frm.doc, "delivery_date")
		set_dates_in_table(frm, "order_details", "delivery_date");
        set_due_days_from_delivery_date_and_order_date(frm); 
    },
    
    estimated_duedate: function(frm){
        validate_dates(frm, frm.doc, "estimated_duedate")
        set_dates_in_table(frm, "order_details", "estimated_duedate");
    },

    due_days: function(frm){ 
        set_delivery_date_from_order_date_and_due_days(frm); 
    }, 

    validate: function(frm){ 
        validate_delivery_date_with_order_date(frm);
    },
    
    concept_image: function(frm) {
        refresh_field('image_preview');
    }
});

frappe.ui.form.on('Sketch Order Form Detail', {
    order_details_add: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        row.delivery_date = frm.doc.delivery_date;
        row.estimated_duedate = frm.doc.estimated_duedate
        refresh_field("order_details");
    },
    
    tag_id(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        fetch_item_from_serial(d, "tag_id", "tag__design_id")
        if (d.tag_id) {
			frappe.db.get_value("BOM",{"tag_no": d.tag_id},'name', (r)=>{
				frappe.model.set_value(cdt, cdn, 'master_bom_no', r.name)
			})
		}
    },

	reference_tagid: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn]
		if (!d.reference_designid && d.reference_tagid) {
			frappe.db.get_value("Serial No", d.reference_tagid, "item_code", (r)=> {
				frappe.model.set_value(cdt, cdn, "reference_designid", r.item_code)
			})
		}
	},

    delivery_date(frm, cdt,cdn) {
        let doc = locals[cdt][cdn]
        validate_dates(frm, doc, "delivery_date")
    },

    estimated_duedate(frm, cdt,cdn) {
        let doc = locals[cdt][cdn]
        validate_dates(frm, doc, "estimated_duedate")
    },

    tag__design_id: function(frm,cdt,cdn) {
        var d = locals[cdt][cdn];
		if (d.tag__design_id) {
			frappe.db.get_value("Item", { "name": d.tag__design_id }, ["image", "item_category", "item_subcategory", "setting_type", "master_bom"], function (value) {
				d.design_image = value.image;
				d.image = value.image;
				d.category = value.item_category;
				d.subcategory = value.item_subcategory;
				d.setting_type = value.setting_type;
				refresh_field('order_details');
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
    
    design_image: function(frm, cdt, cdn){
        refresh_field("order_details");
    },
    
    sketch_image: function(frm, cdt, cdn){
        refresh_field("order_details");
    },
    
    design_type: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        frappe.model.set_value(row.doctype, row.name, 'category','');
        frappe.model.set_value(row.doctype, row.name, 'subcategory','');
        frappe.model.set_value(row.doctype, row.name, 'setting_type','');
        frappe.model.set_value(row.doctype, row.name, 'sub_setting_type','');
        frappe.model.set_value(row.doctype, row.name, 'gold_target','');
        frappe.model.set_value(row.doctype, row.name, 'diamond_target','');
        frappe.model.set_value(row.doctype, row.name, 'product_size','');
        frappe.model.set_value(row.doctype, row.name, '','');
        frappe.model.set_value(row.doctype, row.name, 'reference_tagdesignid','');
        frappe.model.set_value(row.doctype, row.name, 'design_image','');
        frappe.model.set_value(row.doctype, row.name, 'image','');
        frappe.model.set_value(row.doctype, row.name, 'tag__design_id','');
        frappe.model.set_value(row.doctype, row.name, 'item_code','');
    },
});


function fetch_item_from_serial(doc, fieldname, itemfield) {
	if (doc[fieldname]) {
		frappe.db.get_value("Serial No", doc[fieldname], 'item_code', (r) => {
			frappe.model.set_value(doc.doctype, doc.name, itemfield, r.item_code)
		})
	}
}

function set_due_days_from_delivery_date_and_order_date(frm){
    frm.set_value('due_days', frappe.datetime.get_day_diff(frm.doc.delivery_date, frm.doc.order_date));
}

function set_delivery_date_from_order_date_and_due_days(frm){
    frm.set_value('delivery_date', frappe.datetime.add_days(frm.doc.order_date, frm.doc.due_days));
}

function validate_delivery_date_with_order_date(frm) {
    if (frm.doc.delivery_date < frm.doc.order_date) {
        frappe.msgprint(__("You can not select past date in Delivery Date"));
        frappe.validated = false;
    }
}

function set_filter_for_salesman_name(frm) {
    frm.set_query("salesman_name", function() {
        return {
            "filters": { "designation": "Sales Person" }
        };
    });
}

function set_item_attribute_filters_in_sketch_order_form_detail_fields(frm) {
    var fields = [  ['category', 'Item Category'],
                    ['subcategory', 'Item Subcategory'],
                    ['setting_type', 'Setting Type'],
                    ['subsetting_type', 'Sub Setting Type'],
                    ['sub_setting_type2', 'Sub Setting Type'],
                    ['gemstone_type1', 'Gemstone Type1'],
                    ['gemstone_type2', 'Gemstone Type2'],
                    ['gemstone_type3', 'Gemstone Type3'],
                    ['gemstone_type4', 'Gemstone Type4'],
                    ['gemstone_type5', 'Gemstone Type5'],
                    ['gemstone_type6', 'Gemstone Type6'],
                    ['gemstone_type7', 'Gemstone Type7'],
                    ['gemstone_type8', 'Gemstone Type8']
                   
                    ];
    set_filters_on_child_table_fields(frm, fields, 'order_details');
}

function set_item_attribute_filters_in_sketch_order_form_setting_type(frm) {
    var fields = [  ['setting_type', 'Setting Type']];
    set_filters_on_child_table_fields(frm, fields, 'setting_type');
}

function set_item_attribute_filters_in_sketch_order_form_colour_stone(frm) {
    var fields = [  ['color_stone', 'Gemstone Type']];
    set_filters_on_child_table_fields(frm, fields, 'colour_stone');
}

//set delivery date in all order detail rows from delivery date in parent doc
function set_delivery_date_in_order_details(frm) {
    $.each(frm.doc.order_details || [], function(i, d) {
        d.delivery_date = frm.doc.delivery_date;
    });
    refresh_field("order_details");
}

function set_dates_in_table(frm, table, fieldname) {
	$.each(frm.doc[table] || [], function(i, d) {
		d[fieldname] = frm.doc[fieldname];
    });
    refresh_field(table);
}

function set_filters_on_child_table_fields(frm, fields, child_table) {
  fields.map(function(field){
    frm.set_query(field[0], child_table, function() {
      return {
        query: 'jewellery_erpnext.query.item_attribute_query',
        filters: {'item_attribute': field[1]}
      };
    });
  });
}

function set_filters_on_child_table_fields_with_parent_attribute_value(frm, fields, child_table) {
    fields.map(function(field){
        frm.set_query(field[0], "order_details", function() {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {'item_attribute': field[1],
                          'parent_attribute_value' : field[2]}
             };
        });
    });
    frm.refresh_field("order_details");
}

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}

function set_filter_for_design_n_serial(frm, fields, table) {
	fields.map(function (field) {
		frm.set_query(field[0], table, function (doc, cdt, cdn) {
			return {
				filters: {
					"is_design_code": 1
				}
			}
		});
		frm.set_query(field[1], table, function (doc, cdt, cdn) {
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

function set_filters_for_design_attributes(frm) {
    
		frm.set_query('design_attributes', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : 'Design Attributes',
                }
            };
        });
		frm.set_query('design_attribute_value_1', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_2', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_3', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_4', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_5', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_6', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_7', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
		frm.set_query('design_attribute_value_8', 'design_attributes', function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return{
				query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {
                    'item_attribute' : d.design_attributes,
                }
            };
        });
}