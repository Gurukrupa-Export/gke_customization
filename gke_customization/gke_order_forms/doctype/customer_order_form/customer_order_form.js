// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Order Form', {
	titan_code(frm){
		if (cur_frm.doc.titan_code){
			frappe.call({
				method: 'gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.set_customer_code_logic',
				args: {
					'titan_code': cur_frm.doc.titan_code,
					'customer_code': cur_frm.doc.customer_code,
				},
				callback: function(r) {
					if (!r.exc) {
						console.log(r.message)
						frm.set_value('metal_type',r.message['metal_type'])
						frm.set_value('metal_colour',r.message['metal_colour'])
						frm.set_value('metal_touch',r.message['metal_touch'])
						frm.set_value('productivity',r.message['productivity'])
						frm.set_value('design_code',r.message['design_code'])
						frm.set_value('product_size',r.message['size_data'])
						// frm.set_value('chain',r.message['chain'])
						frm.set_value('stone',r.message['stone_data'])
						frm.set_value('finding',r.message['finding_data'])
						frm.set_value('design_code_2',r.message['design_code_2'])
						// frm.set_value('enamal',r.message['enamal'])
						// frm.set_value('rhodium',r.message['rhodium'])
						// frm.set_value('diamond_quality',r.message['diamond_quality'])
						// frm.set_value('product_size',r.message['size'])
						// frm.set_value('qty',r.message['qty'])
						// frm.set_value('gemstone_type',r.message['stone_type'])stone
						// frm.set_value('gemstone_quality',r.message['stone_quality'])

					}
				}
			});
			if (cur_frm.doc.titan_code.length >= 7 && cur_frm.doc.titan_code.charAt(6) === '2') {
				frm.toggle_display('section_break_oortm', true);
            }
			else{
				frm.toggle_display('section_break_oortm', false);
				frm.set_value('design_code_2','')
			}
		}
		else{
			frm.set_value('metal_type','')
			frm.set_value('metal_colour','')
			frm.set_value('metal_touch','')
			frm.set_value('metal_purity','')
			frm.set_value('design_code','')
			frm.set_value('product_size','')
			frm.set_value('stone','')
			frm.set_value('finding','')
			frm.set_value('productivity','')
			// frm.set_value('gemstone_type','')
			// frm.set_value('gemstone_quality','')
		}	
	},
	item_category(frm){
		if(frm.doc.item_category=='Bangle'){
			frm.set_value('qty',2)
		}
		else{
			frm.set_value('qty',1)
		}
	},
	design_code(frm){
		frappe.db.get_value("Titan Design Information Sheet", {"design_code": frm.doc.design_code}, ["design_code_2","is_set"], (r)=> {
			if (r.design_code_2){
				frm.set_value('design_code_2',r.design_code_2)
			}
		})
	},
	refresh(frm){
		frm.add_custom_button(__("Get Quotation"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_quotation",			
				source_doctype: "Quotation",
                target: frm,
                setters: [
					// {
                    //     label: "Amended From",
                    //     fieldname: "amended_from",
                    //     fieldtype: "Link",
                    //     options: "Sales Invoice"
                    // },
                    // {
                    //     label: "Quotation",
                    //     fieldname: "quotation",
                    //     fieldtype: "Link",
                    //     options: "Quotation"
                    // },
                    {
                        label: "Customer",
                        fieldname: "customer_code",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        // default: frm.doc.customer_code || undefined
                    },
                    // {
                    //     label: "Project",
                    //     fieldname: "project",
                    //     fieldtype: "Link",
                    //     options: "Project",
                    //     // reqd: 1,
                    //     // default: frm.doc.order_type || undefined
                    // }
                ],
                // get_query_filters: {
                    // docstatus: 1,
					// cad_order_form: frappe.db.get_list('Order Form')
                // }
            })
        }, __("Get Quotation"))
	}

});


// frappe.ui.form.on('Customer Order Form Detail', {
// 	design_code: function(frm, cdt, cdn){
// 		var d = locals[cdt][cdn];
// 		frappe.call({
// 			method: "gke_customization.gke_order_forms.doctype.customer_order_form.customer_order_form.get_order_form_detail",
// 			args: {
// 				"design_code": d.design_code,
// 				// "doc":d
// 			},
// 			callback(r) {
// 				// console.log(r.message[0].metal_type);
// 				d.metal_type = r.message[0].metal_type ;
// 				d.metal_touch = r.message[0].metal_touch ;
// 				d.metal_target = r.message[0].metal_target ;
// 				d.metal_colour = r.message[0].metal_colour ;
// 				d.feature = r.message[0].feature;
// 				d.diamond_target = r.message[0].diamond_target ;
// 				d.diamond_quality = r.message[0].diamond_quality ;
// 				d.gemstone_type = r.message[0].gemstone_type1;
// 				d.gemstone_quality = r.message[0].gemstone_quality;
// 				d.product_size = r.message[0].product_size;
// 				d.enamal = r.message[0].enamal;
// 				d.no_of_pcs = r.message[0].qty;
// 				d.rhodium = r.message[0].rhodium_ ;

// 				refresh_field('customer_order_form_detail');
// 			}
// 		})
// 	}
// });


// 5027612QYABA08
// 502761nqyaaa08
// 502761dqyaba08
// 2761nqy
// 2761dqy
// 5027612QY