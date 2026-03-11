// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Revise Supplier Services Price", {
	setup(frm) {
		console.log("HERE");
		
        var parent_fields = [
			['metal_type', 'Metal Type']];
		set_filters_on_parent_table_fields(frm, parent_fields);
        
        var fields = [
        ['sub_category', 'Item Subcategory'],
		];

		set_filters_on_child_table_fields(frm, fields);
	},
});


function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1]}
			};
		});
	});
};

function set_filters_on_child_table_fields(frm, fields) {
    fields.map(function (field) {
        frm.set_query(field[0], "revise_making_charge_price_item_subcategory", function () {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: { 'item_attribute': field[1] }
            };
        });
    });
};