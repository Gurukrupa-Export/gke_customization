// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('Custom Packing List', {
	sales_order: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.custom_packing_list.custom_packing_list.get_salesOrder_item',
			args: {
				'sales_order': frm.doc.sales_order,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
					
					frm.clear_table('custom_packing_list_detail');
					var arrayLength = r.message.length;
					for (var i = 0; i < arrayLength; i++) {
						console.log(r.message[i].name)
						let row = frm.add_child('custom_packing_list_detail', {
							serial_number : r.message[i].item,
							product_category : r.message[i].item_category,							
							quantity : r.message[i].quantity,
							gross_weight : r.message[i].gross_weight,							
							// gold weight
							// gold_weight:(r.message[i].gross_weight-((r.message[i].total_diamond_weight+r.message[i].total_cubic_zirconia_in_carat)/5)),
							gold_weight : (r.message[i].gross_weight-((r.message[i].total_diamond_weight)/5)),				
							// gold rate - gjepc
							// gold val 
							total_diamond_pcs : r.message[i].total_diamond_pcs,
							total_diamond_in_carat : r.message[i].total_diamond_weight,
							diamond_rate_in_usd:r.message[i].gold_rate_with_gst,	
							total_diamond_value_in_usd: (r.message[i].gold_rate_with_gst * r.message[i].total_diamond_weight)
						});
					}
					frm.refresh_field('custom_packing_list_detail');
				}
			}
		});

	},
	wastage:function(frm){
		update_fields_in_child_table(frm, "wastage")
	},
	value_addition:function(frm){
		update_fields_in_VA_child_table(frm, "value_addition")
	}

});

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.custom_packing_list_detail || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
		d["gold_wastage"] = d["gold_weight"]*d[fieldname]/100
		d["total_weight"] = d["gold_weight"] + (d["gold_weight"]*d[fieldname]/100)
	});
	refresh_field("custom_packing_list_detail");
}

function update_fields_in_VA_child_table(frm, fieldname) {
	$.each(frm.doc.custom_packing_list_detail || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("custom_packing_list_detail");
}

// frappe.ui.form.on('Custom Packing List Detail', {
// 	wastage (frm, cdt, cdn) {
// 		let list = locals[cdt][cdn];
// 		list.gold_wastage = list.gold_weight * list.wastage/100;
// 		refresh_field('custom_packing_list_detail');
// 	}
// });
