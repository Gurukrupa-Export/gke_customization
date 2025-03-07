// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pre Order Form", {
	setup(frm){
		var parent_fields = [
			['diamond_quality', 'Diamond Quality']];
		set_filters_on_parent_table_fields(frm, parent_fields);

		var fields = [
			['mod_reason', 'Mod Reason'],]
			set_filters_on_child_table_fields(frm, fields);
	},
    due_days(frm) {
		delivery_date(frm);
	},
    delivery_date(frm) {
		validate_dates(frm, frm.doc, "delivery_date")
		calculate_due_days(frm);
	},
    customer_code(frm){
		frm.doc.service_type = [];
        if(frm.doc.customer_code){
			frappe.model.with_doc("Customer", frm.doc.customer_code, function() {
				let customer_doc = frappe.model.get_doc("Customer", frm.doc.customer_code);
				$.each(customer_doc.service_type, function(index, row){
					let d = frm.add_child("service_type");
					d.service_type1 = row.service_type1;
				});
				refresh_field("service_type");
			});
        }
		
	},
});


function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1], "customer_code": doc.customer_code }
			};
		});
	});
};

// Auto calculate due days from delivery date    
function calculate_due_days(frm) {
	frm.set_value('due_days', frappe.datetime.get_day_diff(frm.doc.delivery_date, frm.doc.order_date));
};

// Auto Calculate delivery date from due days
function delivery_date(frm) {
	frm.set_value('delivery_date', frappe.datetime.add_days(frm.doc.order_date, frm.doc.due_days));
};

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
};

function set_filters_on_child_table_fields(frm, fields) {
	fields.map(function (field) {
	frm.set_query(field[0], "pre_order_form_details", function () {
		return {
			query: 'jewellery_erpnext.query.item_attribute_query',
			filters: { 'item_attribute': field[1] }
		};
	});
});
};