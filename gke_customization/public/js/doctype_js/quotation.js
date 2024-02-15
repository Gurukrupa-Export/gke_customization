frappe.ui.form.on('Quotation', {
    refresh(frm) {
        frm.add_custom_button(__("Order"), function () {
            erpnext.utils.map_current_doc({
              method: "gke_customization.gke_order_forms.doctype.order.order.make_quotation",
              source_doctype: "Order",
              target: frm,
              setters: [
                {
                  label: "Order Form",
                  fieldname: "cad_order_form",
                  fieldtype: "Link",
                  options: "Order Form"
                },
                {
                  label: "Customer",
                  fieldname: "customer_code",
                  fieldtype: "Link",
                  options: "Customer",
                  reqd: 1,
                  default: frm.doc.party_name || undefined
                },
                {
                  label: "Order Type",
                  fieldname: "order_type",
                  fieldtype: "Select",
                  options: ["Sales", "Stock Order"],
                  reqd: 1,
                  default: frm.doc.order_type || undefined
                }
              ],
      
              get_query_filters: {
                item: ['is', 'set'],
                docstatus: 1
              }
            })
            frm.set_df_property('party_name', 'read_only', 1);
          }, __("Get Items From"))
      
          frm.add_custom_button(__("Repair Order"), function () {
            erpnext.utils.map_current_doc({
              method: "gke_customization.gke_order_forms.doctype.repair_order.repair_order.make_quotation",
              source_doctype: "Repair Order",
              target: frm,
              setters: [
                {
                  label: "Repair Order Form",
                  fieldname: "serial_and_design_code_order_form",
                  fieldtype: "Link",
                  options: "Repair Order Form"
                },
                {
                  label: "Customer",
                  fieldname: "customer_code",
                  fieldtype: "Link",
                  options: "Customer",
                  reqd: 1,
                  default: frm.doc.party_name || undefined
                },
                {
                  label: "Order Type",
                  fieldname: "order_type",
                  fieldtype: "Select",
                  options: ["Sales", "Stock Order"],
                  reqd: 1,
                  default: frm.doc.order_type || undefined
                }
              ],
              get_query_filters: {
                item: ['is', 'set'],
                docstatus: 1
              }
            })
          }, __("Get Items From"))
    }
})