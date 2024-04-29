// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Update Item Variant", {
	item(frm) {
        frappe.call({
            method: 'gke_customization.gke_order_forms.doctype.update_item_variant.update_item_variant.get_all_attribute',
            args: {
                'item': frm.doc.item,
            },
            callback: function(r) {
                if (!r.exc) {
                    
                    for (let i = 0; i < r.message.length; i++) {
                        frm.set_value(r.message[i]['attribute'].replace(' ','_').toLowerCase(),r.message[i]['attribute_value'])

                      }
                }	
				set_field_visibility(frm)
            }
        });

	},
	// validate(frm) {
    //     frappe.call({
    //         method: 'gke_customization.gke_order_forms.doctype.update_item_variant.update_item_variant.before_insert',
    //         args: {
    //             'item': frm.doc.item,
    //         },
    //         callback: function(r) {
    //             if (!r.exc) {
                    
    //                 for (let i = 0; i < r.message.length; i++) {
	// 					if(frm.doc.get(r.message[i]['attribute'].replace(' ','_').toLowerCase())){
	// 						frm.set_value(r.message[i]['attribute'].replace(' ','_').toLowerCase(),r.message[i]['attribute_value'])
	// 					}

    //                   }
    //             }
    //         }
    //     });

	// },
	form_render(frm) {
		if (frm.subcategory) {
			set_field_visibility(frm)
		}
	},
	onload(frm) {
		if (frm.subcategory) {
			set_field_visibility(frm)
		}
	},
	refresh(){
		if (frm.subcategory) {
			set_field_visibility(frm)
		}
	},
	setup(frm){
		show_attribute_fields_for_subcategory(frm);
		if (frm.subcategory) {
			set_field_visibility(frm)
		}
	},
	subcategory(frm) {
		set_field_visibility(frm)
	},
});


function set_field_visibility(frm) {
	hide_all_subcategory_attribute_fields(frm);
	show_attribute_fields_for_subcategory(frm);
};

function show_attribute_fields_for_subcategory(frm) {
	if (frm.doc.item) {
		frappe.model.with_doc("Attribute Value", frm.doc.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", frm.doc.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					$.each(subcategory_attribute_value.item_attributes, function (index, row) {
						if (row.in_item_variant == 1)
							show_field(frm, row.item_attribute);
					});
				}
			}
		});
	}
}


function show_field(frm, field_name) {
	show_hide_field(frm, field_name, 0);
}

function show_hide_field(frm, field, hidden) {
	var field_name = field.toLowerCase().replace(/\s+/g, '_')
	if (field_name) {
		frm.set_df_property(field_name, 'hidden', 0)
	}
}


function hide_all_subcategory_attribute_fields(frm) {	
	var subcategory_attribute_fields = ['Lock Type','Back Chain','Back Chain Size','Back Belt','Back Belt Length','Black Beed','Black Beed Line',
	'Back Side Size','Hinges','Back Belt Patti','Vanki Type','Total Length','Chain','Chain Type','Chain From','Chain Weight',
	'Chain Length','Number of Ant','Distance Between Kadi To Mugappu','Space between Mugappu','Two in One']

	show_hide_fields(frm,subcategory_attribute_fields, 1);
}

function show_hide_fields(frm, fields, hidden) {
	fields.map(function (field) {
		show_hide_field(frm, field, hidden);
	});
}