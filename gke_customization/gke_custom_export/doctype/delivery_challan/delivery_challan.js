// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Challan', {
	company_branch: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.delivery_challan.delivery_challan.get_company_address',
			args: {
				'company': frm.doc.company,
                'company_branch': frm.doc.company_branch
			},
			callback: function(r) {
				if (!r.exc) {
                    console.log(r.message);
					frm.set_value('company_address',r.message[0])
					frm.set_value('gst_no',r.message[1])
				}
			}
		});
	},
    company: function(frm){
        if(frm.doc.company == 'Sadguru Diamond'){
            frappe.call({
                method: 'gke_customization.gke_custom_export.doctype.delivery_challan.delivery_challan.get_sd_company_address',
                args: {
                    'company': frm.doc.company, 
                },
                callback: function(r) {
                    if (!r.exc) {
                        console.log(r.message);
                        frm.set_df_property('company_branch', 'hidden',1)
                        frm.set_value('company_address',r.message[0])
                        frm.set_value('gst_no',r.message[1])
                    }
                }
            });
        }

    },
	customer:function(frm){
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.delivery_challan.delivery_challan.get_customer_address',
			args: {
				'customer': frm.doc.customer,
			},
			callback: function(r) {
				if (!r.exc) {
                    // console.log(r.message);
					frm.set_value('address',r.message[0])
					frm.set_value('gst_number',r.message[3])
					frm.set_value('statecode',r.message[4])
				}
			}
		});
	},
    supplier:function(frm){
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.delivery_challan.delivery_challan.get_supplier_address',
			args: {
				'supplier': frm.doc.supplier,
			},
			callback: function(r) {
				if (!r.exc) {
                    // console.log(r.message);
                    frm.set_value('supplier_address',r.message[0])
                    frm.set_value('supplier_gst',r.message[1])
                    frm.set_value('supplier_statecode',r.message[2]) 
				}
			}
		});
	},   
	
	refresh(frm) {
        frm.set_query('company_branch',function () {
			return {
				filters: {
                    company: frm.doc.company
                }
			};
		});

        frm.add_custom_button(__("Sales Invoice"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_customization.doc_events.sales_invoice.get_delivery_challan",
                source_doctype: "Sales Invoice",
                target: frm,
                setters: [ 
                    {
                        label: "Cost Center",
                        fieldname: "cost_center",
                        fieldtype: "Link",
                        options: "Cost Center"
                    },
                    {
                        label: "Customer",
                        fieldname: "customer",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        default: frm.doc.customer || undefined
                    }, 
                ],
                get_query_filters: {
                    company: frm.doc.company,
                //     item: ['is', 'set'],
                    docstatus: 1
                }
            })
        }, __("Get Items From"))
        frm.add_custom_button(__("Stock Entry"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_customization.doc_events.stock_entry.get_delivery_challan",
                source_doctype: "Stock Entry",
                target: frm,
                setters: [ 
                    {
                        label: "Stock Entry Type",
                        fieldname: "stock_entry_type",
                        fieldtype: "Link",
                        options: "Stock Entry Type"
                    },
                    {
                        label: "Customer",
                        fieldname: "customer",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        default: frm.doc.customer || undefined
                    },
                    {
                        label: "Company",
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        default: frm.doc.company || undefined
                    }
                ],
                
                get_query_filters: {
                    company: frm.doc.company,
                    customer: frm.doc.customer,
                    docstatus: 1,
                }
            })
        }, __("Get Items From"))
        frm.add_custom_button(__("Material Transfer to Branch"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_customization.doc_events.stock_entry.get_delivery_challan",
                source_doctype: "Stock Entry",
                target: frm,
                setters: [ 
                    {
                        label: "Stock Entry Type",
                        fieldname: "stock_entry_type",
                        fieldtype: "Data", 
                        default: "Material Transfer to Branch"
                    },
                    {
                        label: "Customer",
                        fieldname: "customer",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        default: frm.doc.customer || undefined
                    },
                    {
                        label: "Company",
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        default: frm.doc.company || undefined
                    }
                ],
                size: "extra-large",
                get_query_filters: {
                    company: frm.doc.company,
                    docstatus: 1,
                    stock_entry_type : "Material Transfer to Branch"
                }
            })
        }, __("Get Items From"))
        frm.add_custom_button(__("Purchase Return"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_customization.doc_events.purchase_receipt.get_delivery_challan1",
                source_doctype: "Purchase Receipt",
                target: frm,
                setters: [ 
                    {
                        label: "Return Against Purchase Receipt",
                        fieldname: "return_against",
                        fieldtype: "Link",
                        options: "Purchase Receipt", 
                    },
                    {
                        label: "Supplier",
                        fieldname: "supplier",
                        fieldtype: "Link",
                        options: "Supplier",
                        default: frm.doc.supplier || undefined
                    }, 
                    {
                        label: "Company",
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        default: frm.doc.company || undefined
                    }
                ],
                // size: "extra-large", 
                get_query_filters: {
                    company: frm.doc.company,
                    is_return: 1 
                }
            })
        }, __("Get Items From"))		        
    }    
});


function hold_sales_order(frm){
    var d = new frappe.ui.Dialog({
        title: __('Reason for Hold'),
        fields: [
            {
                "fieldname": "reason_for_hold",
                "fieldtype": "Text",
                "reqd": 1,
            }
        ],
        primary_action: function() {
            var data = d.get_values();
            frappe.call({
                method: "frappe.desk.form.utils.add_comment",
                args: {
                    reference_doctype: frm.doctype,
                    reference_name: frm.docname,
                    content: __('Reason for hold:') + ' ' + data.reason_for_hold,
                    comment_email: frappe.session.user,
                    comment_by: frappe.session.user_fullname
                },
                callback: function(r) {
                    if(!r.exc) {
                        // frm.update_status('Hold', 'On Hold')
                        console.log(r);
                        d.hide();
                    }
                }
            });
        }
    });
    d.show();
}
 