// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Design Information Sheet', {
	refresh: function(frm) {
		set_item_attribute_filters_in_bom_diamond_detail_fields(frm);
        set_item_attribute_filters_in_bom_gemstone_detail_fields(frm);
		var parent_fields = [
								['enamel', 'Enamal'],
								['rhodium', 'Rhodium'],
								['chain_type', 'Chain Type'],
								['metal_type', 'Metal Type'],
								['metal_touch', 'Metal Touch'],
								['metal_colour', 'Metal Colour'],
								['metal_purity', 'Metal Purity'],
								['item_category','Titan Item Category'],
								['item_subcategory','Item Subcategory'],
								// ['collection','Collection'],
								['setting_type','Sub Setting Type'],
								['finding_type','Finding Sub-Category'],
							];
		set_filters_on_parent_table_fields(frm, parent_fields);

		frm.set_query("design_code", function(){
			return {
				"filters": [
					["Item", "is_design_code", "=", 1],
				]
			}
		});
		
		frm.set_query("metal_type", function(){
			return {
				"filters": [
					["Attribute Value", "name", "in", ["Gold","Silver","Platinum"]],
				]
			}
		});

		frm.set_query('metal_purity', function () {
			return {
				filters: {
					// 'is_metal_purity': 1,
					'metal_touch':cur_frm.doc.metal_touch
				}
			};
		});

		frm.set_query('item_subcategory', function () {
			return {
				filters: {
					'parent_attribute_value':cur_frm.doc.item_category
				}
			};
		});		

	},
	design_code:function(frm) {
		const arr = []

		frappe.db.get_value("Customer Design Information Sheet", {"design_code": frm.doc.design_code}, "design_code", (r)=> {
			if (r.design_code){
				arr.push(r.design_code)
				// frm.set_value('design_code','')
				frappe.throw(`<b>${arr[0]}</b> already available`)
			}   
		});
		
		// frappe.db.get_value("Item", frm.doc.design_code, "master_bom", (r)=> {
		// 	if (r.master_bom){
		// 		frappe.db.get_list('BOM Finding Detail', {filters: {'parent': r.master_bom},fields: ['finding_category','finding_type'],}).then(function(response) {
		// 			if(response[0].finding_category=="Chains"){
		// 				frm.set_value('chain_type',response[0].finding_type)
		// 				frm.set_value('back_chain','Yes')
		// 				frm.set_value('finding_type','')
		// 			}
		// 			else{
		// 				frm.set_value('chain_type','')
		// 				frm.set_value('back_chain','No')
		// 				frm.set_value('finding_type',response[0].finding_type)
		// 			}
		// 		});
		// 	}
		// 	else{
		// 		frm.set_value('chain_type','')
		// 		frm.set_value('back_chain','No')
		// 		frm.set_value('finding_type','')
		// 	} 
		// })
	},
	// is_set:function(frm){
	// 	// if (frm.doc.is_set==0){

	// 		// frappe.call({
	// 		// 	method: 'gke_customization.gke_order_forms.doctype.titan_design_information_sheet.titan_design_information_sheet.get_value',
	// 		// 	args: {
	// 		// 		'doc': frm.doc,
	// 		// 	},
	// 		// 	callback: function(r) {
	// 		// 		if (!r.exc) {
	// 		// 			console.log(r.message)
	// 		// 		}
	// 		// 	}
	// 		// });
	// 	// } 
	// // 	// frm.set_value('design_code_2','')
	// // 	// frm.set_value('fourteen_digit_set_code','')
	// },
	// serial_no:function(frm){
	// 	frappe.db.get_value("Serial No", frm.doc.serial_no, "item_code", (r)=> {
	// 		if (r.item_code){
	// 			frm.set_value("design_code", r.item_code)
	// 		}   
	// 	})
	// },
	// design_code_2:function(frm){

	// 	frappe.call({
	// 			method: 'gke_customization.gke_order_forms.doctype.titan_design_information_sheet.titan_design_information_sheet.get_value',
	// 			args: {
	// 				'doc': frm.doc,
	// 			},
	// 			callback: function(r) {
	// 				if (!r.exc) {
	// 					console.log(r.message)
	// 				}
	// 			}
	// 		});
	// }
	// design_code:function(frm){
	// 	frappe.call({
	// 		method: 'gke_customization.gke_order_forms.doctype.titan_design_information_sheet.titan_design_information_sheet.get_table_details',
	// 		args: {
	// 			'design_code': frm.doc.design_code,
	// 		},
	// 		callback: function(r) {
	// 			if (!r.exc) {
	// 				console.log(r)
	// 				console.log(r.message);
	// 				var arrayLength = r.message[0].length;
	// 				for (var i = 0; i < arrayLength; i++) {
	// 					let row = frm.add_child('diamond_detail', {
	// 						diamond_type:r.message[0][i]['diamond_type'],
	// 						stone_shape:r.message[0][i]['stone_shape'],
	// 						sub_setting_type:r.message[0][i]['sub_setting_type'],
	// 						diamond_sieve_size:r.message[0][i]['diamond_sieve_size'],
	// 						pcs:r.message[0][i]['pcs'],
	// 						weight_per_pcs:r.message[0][i]['weight_per_pcs'],
	// 						quality:r.message[0][i]['quality'],
	// 						stock_uom:r.message[0][i]['stock_uom'],
	// 						quantity:r.message[0][i]['quantity'],
	// 						size_in_mm:r.message[0][i]['size_in_mm'],

	// 					});
	// 				}
	// 				frm.refresh_field('diamond_detail');

	// 				var arrayLength = r.message[1].length;
	// 				for (var i = 0; i < arrayLength; i++) {
	// 					let row = frm.add_child('gemstone_detail', {
	// 						gemstone_type:r.message[1][i]['gemstone_type'],
	// 						cut_or_cab:r.message[1][i]['cut_or_cab'],
	// 						stone_shape:r.message[1][i]['stone_shape'],
	// 						gemstone_size:r.message[1][i]['gemstone_size'],
	// 						sub_setting_type:r.message[1][i]['sub_setting_type'],
	// 						pcs:r.message[1][i]['pcs'],
	// 						gemstone_quality:r.message[1][i]['gemstone_quality'],
	// 						stock_uom:r.message[1][i]['stock_uom'],
	// 						quantity:r.message[1][i]['quantity'],
	// 					});
	// 				}
	// 				frm.refresh_field('gemstone_detail');
	// 			}
	// 		}
	// 	});
	// }
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

function set_item_attribute_filters_in_bom_diamond_detail_fields(frm) {
	var fields = [  ['diamond_type', 'Diamond Type'],
    		        ['stone_shape', 'Stone Shape'],
    		        ['quality', 'Diamond Quality'],
    		        ['diamond_grade', 'Diamond Grade'],
					['diamond_sieve_size', 'Diamond Sieve Size'],
					['sub_setting_type', 'Sub Setting Type'],
					['setting_type','Setting Type']];
	set_item_attribute_filters_in_bom_detail_fields(frm, fields, 'diamond_detail');
}

function set_item_attribute_filters_in_bom_gemstone_detail_fields(frm) {
	var fields = [  ['gemstone_type', 'Gemstone Type'],
    		        ['stone_shape', 'Stone Shape'],
    		        ['cut_or_cab', 'Cut Or Cab'],
    		        ['gemstone_quality', 'Gemstone Quality'],
    		        ['gemstone_grade', 'Gemstone Grade'],
					['gemstone_size', 'Gemstone Size'],
					['gemstone_pr', 'Gemstone PR'],
					['per_pc_or_per_carat', 'Per Pc or Per Carat'],
					['sub_setting_type', 'Sub Setting Type']];
	set_item_attribute_filters_in_bom_detail_fields(frm, fields, 'gemstone_detail');
}

function set_item_attribute_filters_in_bom_detail_fields(frm, fields, child_table) {
	fields.map(function(field) {
		frm.set_query(field[0], child_table, function() {
			return { 
    			query: 'jewellery_erpnext.query.item_attribute_query',
				filters: {'item_attribute': field[1]}
			};
    	});
	});
}