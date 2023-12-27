// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('Custom Office Invoice', {
	exporter: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.custom_office_invoice.custom_office_invoice.get_exporter_address',
			args: {
				'exporter': frm.doc.exporter,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message);
					frm.set_value('address',r.message[0])
					frm.set_value('place_of_receipt_by_pre_carrier',r.message[1])
					frm.set_value('port_of_loading',r.message[1])
					frm.set_value('gstn',r.message[2])
					frm.set_value('pan_no',r.message[3])
					frm.set_value('iec_code',r.message[4])
				}
			}
		});

		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.custom_office_invoice.custom_office_invoice.get_exporter_bank',
			args: {
				'exporter': frm.doc.exporter,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message);
					frm.set_value('bank',r.message[0][0])
					frm.set_value('account_no',r.message[0][1])
					frm.set_value('ifsc_code',r.message[0][2])
					frm.set_value('ad_code',r.message[0][3])
					frm.set_value('bank_address',r.message[1])
				}
			}
		});
	},
	consignee:function(frm){
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.custom_office_invoice.custom_office_invoice.get_customer_address',
			args: {
				'consignee': frm.doc.consignee,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message);
					frm.set_value('consignee_address',r.message[0])
					frm.set_value('port_of_destination',r.message[1])
					frm.set_value('country_of_final_destination',r.message[2])
					frm.set_value('final_destination',r.message[2])
				}
			}
		});
	},
	onload: function(frm) {
		if (frm.doc.docstatus == 0){
			frappe.call({
				method: 'gke_customization.gke_custom_export.doctype.gjepc_metal_rate.gjepc_metal_rate.get_gjepc_rate',
				callback: function(r) {
					if (!r.exc) {
						frm.set_value('rate_in_ounce',r.message[0][1])
						
						cur_frm.clear_table('gjepc_metal_rate_details');
						var arrayLength = r.message.length;
						for (var i = 0; i < arrayLength; i++) {
							let row = frm.add_child('gjepc_metal_rate_details', {
								metal_touch:r.message[i][0],
								rate_in_usd:r.message[i][1],
							});
						}
						frm.refresh_field('gjepc_metal_rate_details');
					}
				}
			});
			frappe.call({
				method: 'gke_customization.gke_custom_export.doctype.gjepc_metal_rate.gjepc_metal_rate.get_gjepc_file',
				callback: function(r) {
					if (!r.exc) {
						frm.set_value('file_name',r.message)
					}
				}
			});
		}
	},
	get_items_from_packing_list:function(frm){

		erpnext.utils.map_current_doc({
						method: "gke_customization.gke_custom_export.doctype.custom_office_invoice.custom_office_invoice.get_items_from_packing_list",
						source_doctype: "Packing List",
						target: frm,
						setters: {
							customer_name: undefined,
							date: frm.doc.company || undefined,
						},
						// get_query_filters: query_filters,
						size: "extra-large"
					})
	}

});

frappe.ui.form.on('Description of Goods', {
	bom: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn]
		frappe.db.get_value("BOM", {"name": row.bom}, ["quantity","metal_touch","gross_weight","metal_and_finding_weight","diamond_weight",
		"gemstone_weight","total_bom_amount","gold_rate_with_gst","total_bom_amount"], (r)=> {
			if (r){
				row.metal_touch = r.metal_touch
				row.quantity = r.quantity
				row.gross_weight = r.gross_weight
				row.metal_weight = r.metal_and_finding_weight
				row.diamond_weight = r.diamond_weight
				row.gemstone_weight = r.gemstone_weight
				row.total_value = r.total_bom_amount
				row.per_piece_rate = r.total_bom_amount/r.quantity
				row.per_piece_rate = r.gold_rate_with_gst/r.metal_and_finding_weight
				row.total_value = r.total_bom_amount
				frm.refresh_field('description_of_goods_1')
				calculate_total(frm)
			}   
		})
	},
});

function calculate_total(frm){
	let total_pcs = 0
	let total_gross_weight = 0
	let total_gold_weight = 0

	if(frm.doc.description_of_goods_1){
		frm.doc.description_of_goods_1.forEach(function(d){
			total_pcs += d.quantity
			total_gross_weight += d.gross_weight
			total_gold_weight += d.metal_weight
		})
	}
	console.log(total_gross_weight)
	frm.set_value('total_pcs',total_pcs)
	frm.set_value('total_gross_weight',total_gross_weight)
	frm.set_value('total_gold_weight',total_gold_weight)
}



// if (!frm.doc.current_department) {
// 			frappe.throw("Please select current department first")
// 		}
// 		var query_filters = {
// 			"company": frm.doc.company
// 		}
// 		if (frm.doc.type == "Issue") {
// 			query_filters["department_ir_status"] = ["not in", ["In-Transit", "Revert"]]
// 			query_filters["status"] = ["in", ["Not Started"]]
// 			query_filters["employee"] = ["is", "not set"]
// 			query_filters["subcontractor"] = ["is", "not set"]
// 		}
// 		else {
// 			query_filters["department_ir_status"] = "In-Transit"
// 			query_filters["department"] = frm.doc.current_department
// 		}
// 		erpnext.utils.map_current_doc({
// 			method: "jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir.get_manufacturing_operations",
// 			source_doctype: "Manufacturing Operation",
// 			target: frm,
// 			setters: {
// 				manufacturing_work_order: undefined,
// 				company: frm.doc.company || undefined,
// 				department: frm.doc.current_department
// 			},
// 			get_query_filters: query_filters,
// 			size: "extra-large"
// 		})