// // Copyright (c) 2025, Gurukrupa Export and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Customer Master Update", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Customer Master Update', {
    customer_data: function (frm) {
        // if (frm.doc.type == "Existing") {
        //     frappe.db.get_value('Customer', 
        //         { 'name': frm.doc.customer_data }, 
        //         [
        //             'customer_name', 
        //             'custom_sequence', 
        //             'naming_series', 
        //             'salutation', 
        //             'custom_customer_code', 
        //             'customer_group', 
        //             'customer_type',
        //             "gst_category",
        //             "export_type",
        //             "old_customer_code",
        //             "custom_customer_grade",
        //             "territory",
        //             "custom_territory_code",
        //             "gender",
        //             "vendor_code",
        //             "lead_name",
        //             "opportunity_name",
        //             "prospect_name",
        //             "account_manager",
        //             "image",
        //             "custom_certification_charges",
        //             "custom_ignore_po_creation_for_certification",
        //             "default_price_list", 
        //             "default_bank_account",
        //             "default_currency",
        //             "is_internal_customer",
        //             "represents_company",
        //             "market_segment",
        //             "industry",
        //             "website",
        //             "language",
        //             "customer_details",
        //             "custom_gemstone_price_multiplier",
        //             "customer_primary_contact",
        //             "mobile_no",
        //             "email_id",
        //             "tax_id",
        //             "tax_category",
        //             "tax_withholding_category",
        //             "pan",
        //             "payment_terms",
        //             "loyalty_program",
        //             "loyalty_program_tier",
        //             "default_sales_partner",
        //             "default_commission_rate",
        //             "so_required",
        //             "dn_required",
        //             "is_frozen",
        //             "disabled"
 
        //         ], 
        //         function (r) {
        //             if (r) {
        //                 console.log(r)
        //                 frm.set_value('customer_name', r.customer_name); 
        //                 frm.set_value('sequence', r.custom_sequence); 
        //                 frm.set_value('naming_series', r.naming_series); 
        //                 frm.set_value('salutation', r.salutation); 
        //                 frm.set_value('customer_codes', r.custom_customer_code); 
        //                 frm.set_value('customer_group', r.customer_group || "All Customer Groups"); 
        //                 frm.set_value('customer_type', r.customer_type || "Individual");
        //                 frm.set_value('gst_category', r.gst_category);
        //                 frm.set_value('export_type', r.export_type); 
        //                 frm.set_value('old_customer_code', r.old_customer_code);
        //                 frm.set_value('customer_grade', r.custom_customer_grade);
        //                 frm.set_value('territory', r.territory);
        //                 frm.set_value('territory_code', r.custom_territory_code);
        //                 frm.set_value('gender', r.gender); 
        //                 frm.set_value('vendor_code', r.vendor_code); 
        //                 frm.set_value('from_lead', r.lead_name);
        //                 frm.set_value('from_opportunity', r.opportunity_name);  
        //                 frm.set_value('from_prospect', r.prospect_name);  
        //                 frm.set_value('account_manager', r.account_manager);  
        //                 frm.set_value('image', r.image);  
        //                 frm.set_value('certification_charges', r.custom_certification_charges);  
        //                 frm.set_value('ignore_po_creation_for_certification', r.custom_ignore_po_creation_for_certification);  
        //                 frm.set_value('default_price_list', r.default_price_list);  
        //                 frm.set_value('default_company_bank_account', r.default_bank_account);  
        //                 frm.set_value('billing_currency', r.default_currency);  
        //                 frm.set_value('is_internal_customer', r.is_internal_customer);  
        //                 frm.set_value('represents_company', r.represents_company);  
        //                 frm.set_value('is_customer_exempted_from_sales_tax', r.exempt_from_sales_tax);  
        //                 frm.set_value('market_segment', r.market_segment);  
        //                 frm.set_value('industry', r.industry);  
        //                 frm.set_value('customer_pos_id', r.customer_pos_id);  
        //                 frm.set_value('website', r.website); 
        //                 frm.set_value('print_language', r.language); 
        //                 frm.set_value('customer_details', r.customer_details); 
        //                 frm.set_value('gemstone_price_multiplier', r.custom_gemstone_price_multiplier); 
        //                 frm.set_value('customer_primary_contact', r.customer_primary_contact);   
        //                 frm.set_value('mobile_no', r.mobile_no); 
        //                 frm.set_value('email_id', r.email_id);
        //                 frm.set_value('tax_id', r.tax_id); 
        //                 frm.set_value('tax_category', r.tax_category);
        //                 frm.set_value('tax_withholding_category', r.tax_withholding_category);
        //                 frm.set_value('gstin__uin', r.gstin);
        //                 frm.set_value('pan', r.pan);
        //                 frm.set_value('default_payment_terms_template', r.payment_terms);
        //                 frm.set_value('loyalty_program', r.loyalty_program);
        //                 frm.set_value('loyalty_program_tier', r.loyalty_program_tier);
        //                 frm.set_value('sales_partner', r.default_sales_partner);
        //                 frm.set_value('commission_rate', r.default_commission_rate);
        //                 frm.set_value('allow_sales_invoice_creation_without_sales_order', r.so_required);
        //                 frm.set_value('allow_sales_invoice_creation_without_delivery_note', r.dn_required);
        //                 frm.set_value('is_frozen', r.is_frozen);
        //                 frm.set_value('disabled', r.disabled);
                        
        //             }
        //         }
        //     );
        // }
    },
    refresh(frm) {
    //     if(frm.doc.other_cust_address){        
    //         frm.add_custom_button(
    //             __("Customer Address"),
    //             function () {
    //                 frappe.model.open_mapped_doc({
    //                     method: "gke_customization.gke_hrms.doctype.customer_master_update.customer_master_update.create_customer_address",
    //                     frm: frm,
    //                 });
    //             },
    //             __("Create"),
    //         );
    //     }
    //     if(frm.doc.other_cust_contact){        
    //         frm.add_custom_button(
    //             __("Customer Contact"),
    //             function () {
    //                 frappe.model.open_mapped_doc({
    //                     method: "gke_customization.gke_hrms.doctype.customer_master_update.customer_master_update.create_customer_contact",
    //                     frm: frm,
    //                 });
    //             },
    //             __("Create"),
    //         );
    //     }
	// },
    // setup(frm){
    //     frappe.db.get_value("Address", 
    //         {
    //             "address_title":frm.doc.address_title,
    //             "address_type": frm.doc.address_type
    //         }, 
    //         ["name"]).then((r) => {
    //             frm.set_value("customer_primary_address", r.message.name);
    //             frm.save()
    //     }); 
    //     frappe.db.get_value("Contact", 
    //         {
    //             "company_name":frm.doc.customer_name, 
    //             "mobile_no": frm.doc.phone,
    //             "email_id": frm.doc.email_address
    //         }, 
    //         ["name"]).then((r) => {
    //             frm.set_value("customer_primary_contact", r.message.name);
    //             frm.save()
    //     })
    }
});



























