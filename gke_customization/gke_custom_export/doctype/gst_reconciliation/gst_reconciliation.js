// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.ui.form.on("GST Reconciliation", {
    get_invoice:function (frm){
		if(!frm.doc.from_date){
			frappe.throw("From Date is not available")
		}
		if(!frm.doc.to_date){
			frappe.throw("To Date is not available")
		}
		if(!frm.doc.invoice_type){
			frappe.throw("Invoice type is not selected")
		}
		if(!frm.doc.company){
			frappe.throw("Company is not selected")
		}
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.gst_reconciliation.gst_reconciliation.get_invoice',
			args: {
				'from_date': frm.doc.from_date,
				'to_date': frm.doc.to_date,
				'invoice_type': frm.doc.invoice_type,
				'company': frm.doc.company,
			},
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('gst_reconciliation', []);
					$.each(r.message, function (i, v) {
						frm.doc.gst_reconciliation = frm.doc.gst_reconciliation.filter((row) => row.invoice);
						let row = frm.add_child("gst_reconciliation"); 
						$.extend(row, v);
					});
					
					refresh_field("gst_reconciliation");
					calculate_total(frm)
				}
			}
		});
		
	}
});

function calculate_total(frm){
	let total_sales = 0 	
	let total_cgst = 0
	let total_sgst = 0
	let total_igst = 0
	let total_amount = 0

	// sales_invoice
	if(frm.doc.gst_reconciliation){
		frm.doc.gst_reconciliation.forEach(function(d){
			total_sales += d.total_taxes_and_charges 
			total_cgst += d.total_cgst 
			total_sgst += d.total_sgst 
			total_igst += d.total_igst 
			total_amount += d.item_total
		})
	}
	frm.set_value('total_sales',total_sales);		
	frm.set_value('total_cgst',total_cgst);
	frm.set_value('total_sgst',total_sgst);
	frm.set_value('total_igst',total_igst);
	frm.set_value('total_amount',total_amount);
	
	// purchase_invoice	
	// let total_purchase = 0 
	// let total_purchase_cgst = 0
	// let total_purchase_sgst = 0
	// let total_purchase_igst = 0
	// let total_purchase_tds = 0
	
	// if(frm.doc.purchase_invoice_gst_reconciliation_table){
	// 	frm.doc.purchase_invoice_gst_reconciliation_table.forEach(function(d){	
	// 		total_purchase += d.total_taxes_and_charges		
	// 		total_purchase_cgst += d.total_cgst 
	// 		total_purchase_sgst += d.total_sgst 
	// 		total_purchase_igst += d.total_igst 
	// 		total_purchase_tds += d.total_tds 
	// 	})
	// }
	
}
