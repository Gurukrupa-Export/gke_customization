frappe.ui.form.on('Quotation', {
    refresh(frm) {
        frm.add_custom_button(__("Order"), function () {
            let dialog = new frappe.ui.form.MultiSelectDialog({
              doctype: "Order",
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
              ],
              add_filters_group: 1,
              get_query() {
                return {
                  query:"gke_customization.gke_order_forms.doctype.order.order.get_orders_for_quotation",
                };
              },
              action(selections) {
                if (!selections || selections.length === 0) return;
        
                frappe.call({
                  method: "gke_customization.gke_order_forms.doctype.order.order.make_quotation_batch",
                  args: {
                    order_names: selections,
                    target_doc: frm.doc
                  },
                  freeze: true,
                  freeze_message: "Mapping orders to quotation...",
                  callback: function (r) {
                    if (r.message) {
                      frappe.model.sync(r.message);
                      frm.refresh();
                      frm.set_df_property('party_name', 'read_only', 1);
                    }
                  }
                });
                dialog.dialog.hide();
              }
            });
          }, __("Get Items From"));

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
