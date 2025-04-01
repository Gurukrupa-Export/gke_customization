// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Order Form', {
	// get quotation button for proto type
	refresh(frm){
		frm.add_custom_button(__("Get Quotation"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_quotation",			
				source_doctype: "Quotation",
                target: frm,
                setters: [
                    {
                        label: "Customer",
                        fieldname: "party_name",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        // default: frm.doc.customer_code || undefined
                    },
                ],
                // get_query_filters: {
                    // docstatus: 1,
					// cad_order_form: frappe.db.get_list('Order Form')
                // }
            })
        }, __("Get Quotation"))
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

// function update_fields_in_child_table(frm, fieldname) {
// 	$.each(frm.doc.customer_order_form_detail || [], function (i, d) {
// 		d[fieldname] = frm.doc[fieldname];
// 	});
// 	refresh_field("customer_order_form_detail");
// };

frappe.ui.form.on('Customer Order Form Detail', {
	customer_order_form_detail_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(!row.quotation){
			row.customer_name = frm.doc.customer_name;
			row.customer_code = frm.doc.customer_code;
		}
		
		refresh_field("customer_order_form_detail");
	},
	// digit14_code: function (frm, cdt, cdn) {
	// 	var d = locals[cdt][cdn];
	// 	frappe.call({
	// 		method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_14code_detail",
	// 		args: {
	// 			"digit14_code": d.digit14_code,
	// 			"customer" : d.customer_code
	// 		},
	// 		callback(r) {
	// 			// console.log(r.message);
	// 			d.theme_code = r.message.theme_code; 
				
	// 			if(!d.quotation){

	// 				d.design_code = r.message.design_code;
	// 				d.design_code_bom = r.message.bom;
	// 				d.category = r.message.item_category;
	// 				d.subcategory = r.message.item_subcategory;
	// 				d.setting_type = r.message.setting_type;
	// 				d.metal_type = r.message.metal_type;
	// 				d.metal_touch = r.message.metal_touch;
	// 				d.metal_colour = r.message.metal_colour;
	// 				d.diamond_quality = r.message.stone_data;
	// 				d.finding = r.message.finding_data;
	// 				d.product_size = r.message.size_data;
	// 				d.image = r.message.design_image; 
	// 				d.serial_no = r.message.serial_no; 
	// 			}
				
	// 			refresh_field('customer_order_form_detail');
	// 		}
	// 	})
	// },
	// digit18_code: function (frm, cdt, cdn) {
	// 	var d = locals[cdt][cdn];
	// 	frappe.call({
	// 		method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_18code_detail",
	// 		args: {
	// 			"digit18_code": d.digit18_code,
	// 			"customer" : d.customer_code
	// 		},
	// 		callback(r) {
	// 			// console.log(r.message);
	// 			d.theme_code = r.message.theme_code; 
							
	// 			if(!d.quotation){
	// 				d.design_code = r.message.design_code;
	// 				d.design_code_bom = r.message.bom;
	// 				d.category = r.message.item_category;
	// 				d.subcategory = r.message.item_subcategory;
	// 				d.setting_type = r.message.setting_type;
	// 				d.metal_type = r.message.metal_type;
	// 				d.metal_touch = r.message.metal_touch;
	// 				d.metal_colour = r.message.metal_color;
	// 				d.diamond_quality = r.message.stone_data;
	// 				d.finding = r.message.finding_data;
	// 				d.product_size = r.message.size_data;
	// 				d.image = r.message.design_image; 
	// 				d.serial_no = r.message.serial_no;
	// 			}

	// 			refresh_field('customer_order_form_detail');
	// 		}
	// 	})
	// },
	// digit15_code: function (frm, cdt, cdn) {
	// 	var d = locals[cdt][cdn];
	// 	frappe.call({
	// 		method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_15code_detail",
	// 		args: {
	// 			"digit15_code": d.digit15_code,
	// 			"customer" : d.customer_code
	// 		},
	// 		callback(r) {
	// 			// console.log(r.message);
	// 			if(!d.quotation){
	// 				d.theme_code = r.message.theme_code; 
	// 				d.product_type = r.message.product_type;
	// 				d.design_code = r.message.design_code;
	// 				d.design_code_bom = r.message.bom;
	// 				d.category = r.message.item_category;
	// 				d.subcategory = r.message.item_subcategory;
	// 				d.setting_type = r.message.setting_type;
	// 				d.metal_type = r.message.metal_type;
	// 				d.metal_touch = r.message.metal_touch;
	// 				d.metal_colour = r.message.metal_color;
	// 				d.diamond_quality = r.message.stone_data;
	// 				d.finding = r.message.finding_data;
	// 				d.product_size = r.message.size_data;
	// 				d.image = r.message.design_image; 
	// 				d.serial_no = r.message.serial_no;
	// 			}

	// 			refresh_field('customer_order_form_detail');
	// 		}
	// 	})
	// },

		
});


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