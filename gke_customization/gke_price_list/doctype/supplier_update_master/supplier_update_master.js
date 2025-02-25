// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

frappe.ui.form.on("Supplier Update Master", {
    setup(frm){
        // frm.set_query("supplier_primary_contact", function (doc) {
		// 	return {
		// 		query: "erpnext.buying.doctype.supplier.supplier.get_supplier_primary_contact",
		// 		filters: {
		// 			supplier: doc.name,
		// 		},
		// 	};
		// });

		// frm.set_query("supplier_primary_address", function (doc) {
		// 	return {
		// 		filters: {
		// 			link_doctype: "Supplier",
		// 			link_name: doc.name,
		// 		},
		// 	};
		// });
    },     
	
});


// frappe.ui.form.on('Supplier Update Master', {
//     supplier_data: function (frm) {
//         if (frm.doc.type == "Existing") {
//             frappe.db.get_value('Supplier', 
//                 { 'name': frm.doc.supplier_data }, 
//                 [
//                 "naming_series",
//                 "supplier_group",
//                 "supplier_name",
// 				"supplier_type",
// 				"custom_territory",
// 				"gst_category",
// 				"export_type",
// 				"country",
// 				"custom_consider_purchase_receipt_as_customergoods",
// 				// "custom_territory_code",
// 				"gst_transporter_id",
// 				"is_reverse_charge_applicable",
// 				"is_transporter",
// 				"image",
// 				"default_currency",
// 				"default_bank_account",
// 				"default_price_list",
// 				"payment_terms",
// 				"custom_certification_charges",
// 				"is_internal_supplier",
// 				"represents_company",
// 				// "custom_is_external_customer",
// 				"supplier_details",
// 				"website",
// 				"language",
// 				"tax_id",
// 				"irs_1099",
// 				"tax_category",
// 				"tax_withholding_category",
// 				"gstin",
// 				"pan",
// 				"supplier_primary_contact",
// 				"mobile_no",
// 				"email_id",
// 				"supplier_primary_address",
// 				"primary_address",
// 				"allow_purchase_invoice_creation_without_purchase_order",
// 				"allow_purchase_invoice_creation_without_purchase_receipt",
// 				"is_frozen",
// 				"disabled",
// 				"warn_rfqs",
// 				"warn_pos",
// 				"prevent_rfqs",
// 				"prevent_pos",
// 				"on_hold",
// 				"hold_type",
// 				"release_date",
 
//                 ], 
//                 function (r) {
//                     if (r) {
//                         console.log(r)
//                         frm.set_value('naming_series', r.naming_series); 
//                         frm.set_value('supplier_group', r.supplier_group || "All Customer Groups"); 
//                         frm.set_value('supplier_name', r.supplier_name); 
//                         frm.set_value('supplier_type', r.supplier_type); 
//                         frm.set_value('territory', r.custom_territory); 
//                         frm.set_value('gst_category', r.gst_category); 
//                         frm.set_value('export_type', r.export_type); 
//                         frm.set_value('country', r.country); 
//                         // frm.set_value('customer_type', r.customer_type || "Individual");
//                         frm.set_value('gst_category', r.gst_category);
//                         frm.set_value('export_type', r.export_type); 
//                         frm.set_value('consider_purchase_receipt_as_customer', r.custom_consider_purchase_receipt_as_customergoods);
//                         // frm.set_value('territory_code', r.custom_territory_code);
//                         frm.set_value('gst_transporter_id', r.gst_transporter_id);
//                         frm.set_value('reverse_charge_applicable', r.is_reverse_charge_applicable);
//                         frm.set_value('is_transporter', r.is_transporter); 
//                         frm.set_value('image', r.image); 
//                         frm.set_value('billing_currency', r.default_currency);
//                         frm.set_value('default_company_bank_account', r.default_bank_account); 
//                         frm.set_value('price_list', r.default_price_list); 
//                         frm.set_value('default_payment_terms_template', r.payment_terms);  
                          
//                         frm.set_value('certification_charges', r.custom_certification_charges); 
//                         frm.set_value('is_internal_supplier', r.is_internal_supplier);  
//                         frm.set_value('represents_company', r.represents_company);  
//                         // frm.set_value('is_external_customer', r.custom_is_external_customer); 
//                         frm.set_value('supplier_details', r.supplier_details);  
//                         frm.set_value('website', r.website);  
//                         frm.set_value('print_language', r.language);  
//                         frm.set_value('tax_id', r.tax_id);  
//                         frm.set_value('is_irs_1099_reporting_required_for_supplier', r.irs_1099);  
//                         frm.set_value('tax_category', r.tax_category);
//                         frm.set_value('tax_withholding_category', r.tax_withholding_category);
//                         frm.set_value('gstin__uin', r.gstin);
//                         frm.set_value('pan', r.pan);
//                         frm.set_value('supplier_primary_contact', r.supplier_primary_contact);
//                         frm.set_value('mobile_no', r.mobile_no); 
//                         frm.set_value('email_id', r.email_id);
//                         frm.set_value('supplier_primary_address', r.supplier_primary_address);
//                         frm.set_value('primary_address', r.primary_address);
//                         frm.set_value('allow_purchase_invoice_creation_without_purchase_order', r.allow_purchase_invoice_creation_without_purchase_order);
//                         frm.set_value('allow_purchase_invoice_creation_without_purchase_receipt', r.allow_purchase_invoice_creation_without_purchase_receipt);
//                         frm.set_value('is_frozen', r.is_frozen);
//                         frm.set_value('disabled', r.disabled);  
//                         frm.set_value('warn_rfqs', r.warn_rfqs);  
//                         frm.set_value('warn_pos', r.warn_pos);  
//                         frm.set_value('prevent_rfqs', r.prevent_rfqs); 
//                         frm.set_value('prevent_pos', r.prevent_pos); 
//                         frm.set_value('block_supplier', r.on_hold); 
//                         frm.set_value('hold_type', r.hold_type); 
//                         // frm.set_value('customer_primary_contact', r.customer_primary_contact);   
//                         frm.set_value('release_date', r.realease_date); 
                        
                        
                        
//                     }
//                 }
//             );
//         }
//     },
// });

