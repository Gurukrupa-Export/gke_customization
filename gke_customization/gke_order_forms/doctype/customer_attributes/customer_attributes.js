// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer Attributes", {
	refresh(frm) {
        set_filters_ct_fields(frm);
	},
});
function set_filters_ct_fields(frm) {
	var filter_for_metal = [];
	var filter_for_diamond = [];
    
	frappe.db
		.get_list("Tolerance Weight Type", {
			fields: ["name", "metal", "diamond", "gemstone"],
		})
		.then((records) => {
			records.forEach((record) => {
				if (record.metal === 1) {
					filter_for_metal.push(record.name);
				}
				if (record.diamond === 1) {
					filter_for_diamond.push(record.name);
				}
				
			});
			frm.fields_dict["metal_tolerance_table"].grid.get_field("weight_type").get_query =
				function (doc, cdt, cdn) {
					return {
						filters: [[`name`, `in`, filter_for_metal]],
					};
				};
			frm.fields_dict["diamond_tolerance_table"].grid.get_field("weight_type").get_query =
				function (doc, cdt, cdn) {
					return {
						filters: [[`name`, `in`, filter_for_diamond]],
					};
				};
			
		});
}
frappe.ui.form.on("Metal Tolerance Table", {
	range_type: function (frm, cdt, cdn) {
		toggle_metal_table_field(frm, cdt, cdn);
	},
});
frappe.ui.form.on("Diamond Tolerance Table", {
	weight_type: function (frm, cdt, cdn) {
		toggle_diamond_table_field(frm, cdt, cdn);
	},
});

function toggle_metal_table_field(frm, cdt, cdn) {
	let d = locals[cdt][cdn];
	let percentage_fields = ["plus_percent", "minus_percent"];
	let weight_range_fields = ["from_weight", "to_weight"];
	if (d.range_type == "Percentage") {
		$.each(weight_range_fields || [], function (i, field) {
			frm.fields_dict.metal_tolerance_table.grid.toggle_display(field, false);
		});
		frm.refresh_fields();
	} else {
		$.each(weight_range_fields || [], function (i, field) {
			frm.fields_dict.metal_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	}
	if (d.range_type == "Weight Range") {
		$.each(percentage_fields || [], function (i, field) {
			frm.fields_dict.metal_tolerance_table.grid.toggle_display(field, false);
		});
		frm.refresh_fields();
	} else {
		$.each(percentage_fields || [], function (i, field) {
			frm.fields_dict.metal_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	}
}

function toggle_diamond_table_field(frm, cdt, cdn) {
	let d = locals[cdt][cdn];
	let mm_size_wise = [
		"diamond_type",
		"sieve_size",
		"from_diamond",
		"to_diamond",
		"plus_percent",
		"minus_percent",
	];
	let group_size_wise = [
		"diamond_type",
		"sieve_size_range",
		"from_diamond",
		"to_diamond",
		"plus_percent",
		"minus_percent",
	];
	let weight_wise = [
		"diamond_type",
		"from_diamond",
		"to_diamond",
		"plus_percent",
		"minus_percent",
	];
	let universal = ["plus_percent", "minus_percent"];
	let all_field = [
		"diamond_type",
		"sieve_size",
		"sieve_size_range",
		"from_diamond",
		"to_diamond",
		"plus_percent",
		"minus_percent",
	];
	$.each(all_field || [], function (i, field) {
		frm.fields_dict.diamond_tolerance_table.grid.toggle_display(field, false);
	});
	frm.refresh_fields();
	if (d.weight_type == "MM Size wise") {
		$.each(mm_size_wise || [], function (i, field) {
			frm.fields_dict.diamond_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	} else if (d.weight_type == "Group Size wise") {
		$.each(group_size_wise || [], function (i, field) {
			frm.fields_dict.diamond_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	} else if (d.weight_type == "Weight wise") {
		$.each(weight_wise || [], function (i, field) {
			frm.fields_dict.diamond_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	} else if (d.weight_type == "Universal") {
		$.each(universal || [], function (i, field) {
			frm.fields_dict.diamond_tolerance_table.grid.toggle_display(field, true);
		});
		frm.refresh_fields();
	}
}