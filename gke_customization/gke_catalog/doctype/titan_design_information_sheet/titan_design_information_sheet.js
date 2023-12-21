// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Titan Design Information Sheet', {
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
		frappe.db.get_value("Titan Design Information Sheet", {"design_code": frm.doc.design_code}, "design_code", (r)=> {
			if (r.design_code){
				arr.push(r.design_code)
				frm.set_value('design_code','')
				frappe.throw(`<b>${arr[0]}</b> already available`)
			}   
		})
	},
	is_set:function(frm){
		frm.set_value('design_code_2','')
	},
	serial_no:function(frm){
		frappe.db.get_value("Serial No", frm.doc.serial_no, "item_code", (r)=> {
			if (r.item_code){
				frm.set_value("design_code", r.item_code)
			}   
		})
	},
	design_code:function(frm){
		
		frappe.call({
			method: 'catalog.catalog.doctype.titan_design_information_sheet.titan_design_information_sheet.get_table_details',
			args: {
				'design_code': frm.doc.design_code,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r)
					var arrayLength = r.message[1].length;
					for (var i = 0; i < arrayLength; i++) {
						let row = frm.add_child('gemstone_detail', {
							cut_or_cab:r.message[1][i]['cut_or_cab'],

						});
					}
					frm.refresh_field('gemstone_detail');
				}
			}
		});
	}
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