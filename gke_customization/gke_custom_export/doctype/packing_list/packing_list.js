// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('Packing List', {
	sales_order: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.packing_list.packing_list.get_salesOrder_item',
			args: {
				'sales_order': frm.doc.sales_order,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
					cur_frm.clear_table('packing_list_detail');
					var arrayLength = r.message.length;
					for (var i = 0; i < arrayLength; i++) {
						let row = frm.add_child('packing_list_detail', {
							item_code:r.message[i].item,
							item_category:r.message[i].item_category,							
							quality:r.message[i].quality,
							diamond_pcs:r.message[i].total_diamond_pcs,
							diamond_weight:r.message[i].total_diamond_weight,
							diamond_rate:r.message[i].diamond_bom_rate,							
							gross_weight:r.message[i].gross_weight,
							other_weight:r.message[i].other_weight,
							net_weight:r.message[i].metal_and_finding_weight,	
							stone_weight:r.message[i].gemstone_weight,	
							diamond_amount:r.message[i].diamond_bom_amount,
							gold_amount:r.message[i].gold_bom_amount,
							stone_amount:r.message[i].gemstone_bom_amount,
							total_amount:r.message[i].total_bom_amount,
						});
					}
					frm.refresh_field('packing_list_detail');
				}
			}
		});
	}
});
