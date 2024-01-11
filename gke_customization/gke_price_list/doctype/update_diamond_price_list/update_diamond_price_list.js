// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('Update Diamond Price List', {
	// refresh: function(frm) {

	// }
});


frappe.ui.form.on('Update Diamond Price List Details', {
	revised_rate:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		d.difference = d.revised_rate - d.rate_per_carat
		refresh_field('update_diamond_price_list_details')
	}
})

frappe.ui.form.on('Update Diamond Price List Details Sieve Size Range', {
	revised_rate:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		d.difference = d.revised_rate - d.rate_per_carat
		refresh_field('update_diamond_price_list_details_sieve_size_range')
		
	}
})


frappe.ui.form.on('Update Diamond Price List Details Size in MM', {
	revised_rate:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		d.difference = d.revised_rate - d.rate_per_carat
		refresh_field('update_diamond_price_list_details_size_in_mm')
		
	}
})