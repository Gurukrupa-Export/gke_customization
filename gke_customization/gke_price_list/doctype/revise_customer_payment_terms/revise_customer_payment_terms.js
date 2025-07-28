// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.ui.form.on("Revise Customer Payment Terms", {
    customer: function (frm) {
        if (frm.doc.customer) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Customer Payment Terms",
                    filters: {
                        customer: frm.doc.customer
                    },
                    // limit_page_length: 1,
                    fields: ["name"]
                },
                callback: function (res) {
                    if (res.message && res.message.length > 0) {
                        let docname = res.message[0].name;
                        frappe.call({
                            method: "frappe.client.get",
                            args: {
                                doctype: "Customer Payment Terms",
                                name: docname
                            },
                            callback: function (r) {
                                if (r.message) {
                                    let full_doc = r.message;
                                    frm.clear_table("customer_payment_details");
                                    if (full_doc.customer_payment_details && full_doc.customer_payment_details.length > 0) {
                                        full_doc.customer_payment_details.forEach(function (row) {
                                            frm.add_child("customer_payment_details", {
                                                due_days: row.due_days,
                                                due_months: row.due_months,
                                                item_type: row.item_type,
                                                payment_term: row.payment_term,
                                                due_date_based_on: row.due_date_based_on,
                                            });
                                        });
                                        frm.refresh_field("customer_payment_details");
                                    }

                                    frm.doc.customer_payment_terms_name = docname;
                              
                                }
                            }
                        });

                    } else {
                        frappe.throw("Customer Payment Terms not found for this customer");
                    }
                }
            });
        }
    },

    // validate: function (frm) {
    //     if (frm.doc.customer_payment_terms_name) {
    //         return frappe.call({
    //             method: "gke_customization.gke_price_list.doctype.revise_customer_payment_terms.revise_customer_payment_terms.update_customer_payment_details",
    //             args: {
    //                 customer_payment_terms_name: frm.doc.customer_payment_terms_name,
    //                 new_details: JSON.stringify(frm.doc.customer_payment_details)
    //             },
    //             callback: function (r) {
    //                 frappe.msgprint("Customer Payment Terms updated successfully.");
    //             }
    //         });
    //     }
    // }

});




