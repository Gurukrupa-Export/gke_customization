// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Order Form', {
	// get quotation button for proto type
	refresh(frm){		
		set_item_attribute_filters_in_child_table(frm);
		// frm.add_custom_button(__("Get Quotation"), function(){
        //     erpnext.utils.map_current_doc({
        //         method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_quotation",			
		// 		source_doctype: "Quotation",
        //         target: frm,
        //         setters: [
        //             {
        //                 label: "Customer",
        //                 fieldname: "party_name",
        //                 fieldtype: "Link",
        //                 options: "Customer",
        //                 // reqd: 1,
        //                 // default: frm.doc.customer_code || undefined
        //             },
        //         ],
        //         // get_query_filters: {
        //             // docstatus: 1,
		// 			// cad_order_form: frappe.db.get_list('Order Form')
        //         // }
        //     })
        // }, __("Get Quotation"))
	},

	customer_code(frm){
		// update_fields_in_child_table(frm, "customer_code")
		// update_fields_in_child_table(frm, "customer_name")
		// frappe.call({
		// 	method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_theme_code",
		// 	args: { 
		// 		customer: frm.doc.customer_code
		// 	},
		// 	callback(r) {
		// 		if(r.message) {
		// 			//console.log(r.message);
		// 			var arrayLength = r.message.length;
		// 			for (var i = 0; i < arrayLength; i++) {						
		// 				let row = frm.add_child('customer_order_form_detail', {
		// 					customer_name : frm.doc.customer_name,
		// 					design_code : r.message[i].item,
		// 					design_code_bom: r.message[i].name,
		// 					theme_code: r.message[i].theme_code,
		// 					category: r.message[i].item_category ,
		// 					subcategory: r.message[i].item_subcategory,
		// 					setting_type: r.message[i].setting_type,
		// 					metal_type: r.message[i].metal_type,
		// 					metal_touch: r.message[i].metal_touch,
		// 					metal_colour: r.message[i].metal_colour,
		// 					feature: r.message[i].feature,
		// 					metal_target: r.message[i].custom_metal_target ,
		// 					diamond_target: r.message[i].diamond_target,
		// 					diamond_quality: r.message[i].diamond_quality,
		// 					gemstone_type: r.message[i].gemstone_type1,
		// 					gemstone_quality: r.message[i].gemstone_quality,
		// 					product_size: r.message[i].product_size,
		// 					enamal: r.message[i].enamal,
		// 					no_of_pcs: r.message[i].qty,
		// 					rhodium: r.message[i].rhodium,
		// 					image: r.message[i].front_view_finish

		// 				});
		// 			}
		// 			frm.refresh_field('customer_order_form_detail');				
		// 		}
		// 	}
		// });
		
	},

});

function set_item_attribute_filters_in_child_table(frm){
	var fields = [  ['category', 'Item Category'],
					['subcategory', 'Item Subcategory'],
					['setting_type', 'Setting Type'],
					['metal_type', 'Metal Type'],
					['metal_touch', 'Metal Touch'],
					['metal_colour', 'Metal Colour'],
					['chain', 'Chain'],
					['rhodium', 'Rhodium'],
					['feature', 'Feature'],
					['diamond_quality', 'Diamond Quality'],
					['chain', 'Chain'],
					['rhodium', 'Rhodium'],

	];
	set_item_attribute_filters_in_child_table_fields(frm, fields, 'customer_order_form_detail');
}

function set_item_attribute_filters_in_child_table_fields(frm, fields, child_table) {
	fields.map(function(field) {
		frm.set_query(field[0], child_table, function() {
			return { 
    			query: 'jewellery_erpnext.query.item_attribute_query',
				filters: {'item_attribute': field[1]}
			};
    	});
	});
}

frappe.ui.form.on('Customer Order Form Detail', {
	customer_order_form_detail_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(!row.quotation){
			row.customer_name = frm.doc.customer_name;
			row.customer_code = frm.doc.customer_code;
			row.flow_type = frm.doc.flow_type;
		}
		
		refresh_field("customer_order_form_detail");
	},
		
});

function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1]}
			};
		});
	});
}


// 5027612QYABA08
// 502761nqyaaa08
// 502761dqyaba08
// 2761nqy
// 2761dqy
// 5027612QY

// titan
// 50 Q4STNAL N A X 01
// 50Q4STNALNAX01
// 50W5PLNIPNAX01

// reliance
// 2GBANAH1901A1B2ABB																	
// 2 G BANAH1901 A1 B2 A BB

// novel
// DEHYA40AANS935
// D E H Y A 40 AANS935
// 0 1 2 3 4 56 78910111213

// caratlane 
// KL01233-1YP600_18
// KL01233 - 1Y P600     _  18
// KL01233 - 1Y P 6 0 0  _  1 8
// 0123456 7 89 10111213 14 1516

// KL01233-YGP600_18
