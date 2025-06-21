// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Update Customer Diamond Criteria", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Update Customer Diamond Criteria', {
    customer: function (frm) {
        if (!frm.doc.customer) return;

        frappe.db.get_doc('Customer', frm.doc.customer).then(doc => {
            if (!doc.diamond_grades || !doc.diamond_grades.length) {
                frappe.msgprint(__('No diamond grades found for this customer.'));
                return;
            }

            // Clear existing child table first
            frm.clear_table('diamond_grades');


            // Add each row from customer's diamond_grades
            doc.diamond_grades.forEach(row => {
                let child = frm.add_child('diamond_grades');
                child.diamond_quality = row.diamond_quality;
                child.diamond_grade_1 = row.diamond_grade_1;
                child.diamond_grade_2 = row.diamond_grade_2;
                child.diamond_grade_3 = row.diamond_grade_3;
                child.diamond_grade_4 = row.diamond_grade_4;
            });

            frm.refresh_field('diamond_grades');
        });
    }
});

frappe.ui.form.on('Update Customer Diamond Criteria', {
    setup(frm) {
        frm.set_query('diamond_quality', 'diamond_grades', function () {
            return {
                filters: {
                    is_customer_diamond_quality: 1
                }
            };
        });

        const grade_fields = [
            'diamond_grade_1',
            'diamond_grade_2',
            'diamond_grade_3',
            'diamond_grade_4'
        ]

        grade_fields.forEach((field) => {
            frm.set_query(field, 'diamond_grades', function () {
                return {
                        query: 'jewellery_erpnext.query.item_attribute_query',
                        filters: { 'item_attribute': "Diamond Grade"}
                    };
            });

        })
    }
});

