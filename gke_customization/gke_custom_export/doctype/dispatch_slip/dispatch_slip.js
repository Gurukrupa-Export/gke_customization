// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatch Slip', {
	company: function(frm) {
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.dispatch_slip.dispatch_slip.get_company_address',
			args: {
				'company': frm.doc.company,
			},
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('company_address',r.message[0])
					frm.set_value('gst_no',r.message[2])
				}
			}
		});
	},
	customer:function(frm){
		frappe.call({
			method: 'gke_customization.gke_custom_export.doctype.dispatch_slip.dispatch_slip.get_customer_address',
			args: {
				'customer': frm.doc.customer,
			},
			callback: function(r) {
				if (!r.exc) {
					frm.set_value('address',r.message[0])
				}
			}
		});
	},
	refresh(frm) {
		//status
		// var currentStatus = frm.doc.status;
        // frm.clear_custom_buttons('Status');

        // if (currentStatus === 'On Hold') {
        //     frm.add_custom_button(__('Resume'), function() {
        //         frm.set_value('status', 'Draft'); 
        //         frm.save();
        //     }, __('Status'));
        //     frm.add_custom_button(__('Close'), function() {
        //         frm.set_value('status', 'Completed');
        //         frm.save();
        //     }, __('Status'));
        // } else if (currentStatus === 'Completed') {
        //     frm.add_custom_button(__('Re open'), function() {
        //         frm.set_value('status', 'Draft');
        //         frm.save();
        //     }, __('Status'));
        // } else {
        //     // this.frm.add_custom_button(__('Hold'), () => this.hold_sales_order(), __("Status"))
        //     frm.add_custom_button(__('Hold'), function() {
        //         frm.set_value('status', 'On Hold');
        //         hold_sales_order(frm);
        //         frm.save();
        //     }, __('Status'));
		// 	frm.add_custom_button(__('Close'), function() {
        //         frm.set_value('status', 'Completed');
        //         frm.save();
        //     }, __('Status'));
        // }

        frm.add_custom_button(__("Sales Invoice"), function(){
            erpnext.utils.map_current_doc({
                method: "jewellery_erpnext.jewellery_erpnext.doc_events.sales_invoice.get_dispatch_slip",
                source_doctype: "Sales Invoice",
                target: me.frm,
                setters: [
					{
                        label: "Amended From",
                        fieldname: "amended_from",
                        fieldtype: "Link",
                        options: "Sales Invoice"
                    },
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
                        // default: frm.doc.party_name || undefined
                    },
                    {
                        label: "Project",
                        fieldname: "project",
                        fieldtype: "Link",
                        options: "Project",
                        // reqd: 1,
                        // default: frm.doc.order_type || undefined
                    }
                ],
                // get_query_filters: {
                //     item: ['is', 'set'],
                //     docstatus: 1
                // }
            })
        }, __("Get Items From"))
        frm.add_custom_button(__("Stock Entry"), function(){
            erpnext.utils.map_current_doc({
                method: "jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.get_dispatch_slip",
                source_doctype: "Stock Entry",
                target: me.frm,
                setters: [
					{
                        label: "Amended From",
                        fieldname: "amended_from",
                        fieldtype: "Link",
                        options: "Stock Entry"
                    },
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
                        // default: frm.doc.party_name || undefined
                    },
                    {
                        label: "Inventory Type",
                        fieldname: "inventory_type",
                        fieldtype: "Link",
                        options: "Inventory Type",
                        // reqd: 1,
                        default: frm.doc.order_type || undefined
                    }
                ],
                // get_query_filters: {
                //     item: ['is', 'set'],
                //     docstatus: 1
                // }
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
 