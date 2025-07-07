
frappe.ui.form.on('Update Customer Diamond Criteria', {
    // customer: function (frm) {
    //     if (!frm.doc.customer) return;
    //      frappe.call({
    //         method:"gke_customization.gke_price_list.doctype.update_customer_diamond_criteria.update_customer_diamond_criteria.get_customer_diamond_criteria",
    //         args: {
    //             customer: frm.doc.customer
    //         },
    //         callback: function (r) {
    //             if (!r.message || !r.message.diamond_grades || !r.message.diamond_grades.length) {
    //                 frappe.msgprint(__('No diamond grades found for this customer.'));
    //                 return;
    //             }
    //             frm.clear_table('diamond_grades');

    //             r.message.diamond_grades.forEach(row => {
    //                 let child = frm.add_child('diamond_grades');
    //                 child.diamond_quality = row.diamond_quality;
    //                 child.diamond_grade_1 = row.diamond_grade_1;
    //                 child.diamond_grade_2 = row.diamond_grade_2;
    //                 child.diamond_grade_3 = row.diamond_grade_3;
    //                 child.diamond_grade_4 = row.diamond_grade_4;
    //             });

    //             frm.refresh_field('diamond_grades');
    //         }
    //     });
    // },
   //  setup(frm) {
   //      frm.set_query('diamond_quality', 'diamond_grades', function () {
   //          return {
   //              filters: {
   //                  is_customer_diamond_quality: 1
   //              }
   //          };
   //      });

   //      var fields = [
			// ['diamond_grade_1', 'Diamond Grade'],
   //          ['diamond_grade_2', 'Diamond Grade'],
   //          ['diamond_grade_3', 'Diamond Grade'],
   //          ['diamond_grade_4', 'Diamond Grade'],]

   //      set_filters_on_child_table_fields(frm, fields);
   //  }
});

function set_filters_on_child_table_fields(frm, fields) {
    fields.map(function (field) {
        frm.set_query(field[0], "diamond_grades", function () {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: { 'item_attribute': field[1] }
            };
        });
    });
};
