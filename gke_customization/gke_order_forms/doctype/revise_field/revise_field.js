frappe.ui.form.on("Revise Field", {
	item: function(frm) {
		if (!frm.doc.item) {
			frm.fields_dict["item_attributes"].$wrapper.html("<div style='color: red;'>Please select an Item</div>");
			return;
		}

		frappe.call({
			method: "gke_customization.gke_order_forms.doctype.revise_field.revise_field.get_filtered_item_attributes",
			args: {
				item_code: frm.doc.item
			},
			callback: function(r) {
				if (r.message) {
					const attribute_map = r.message;

					let attribute_to_field = {
						"Metal Colour": "metal_colour",
						"Diamond Target": "diamond_target",
						"Stone Changeable": "stone_changeable",
						"Gemstone Type": "gemstone_type",
						"Chain Type": "chain_type",
						"Chain Length": "chain_length",
						"Feature": "feature",
						"Rhodium": "rhodium",
						"Enamal": "enamal",
						"Detachable": "detachable",
						"Cap/Ganthan": "capganthan",
						"Two in One": "two_in_one",
						"Product Size": "product_size",
						"Sizer Type": "sizer_type",
						"Lock Type": "lock_type",
						"Black Bead Line": "black_bead_line",
						"Charm": "charm",
						"Count of Spiral Turns": "count_of_spiral_turns",
						"Number of Ant": "number_of_ant",
						"Back Side Size": "back_side_size",
						"Space between Mugappu": "space_between_mugappu",
						"Distance Between Kadi To Mugappu": "distance_between_kadi_to_mugappu",
						"Back Belt": "back_belt",
						"Back Belt Length": "back_belt_length"
					};

					let values_to_set = {};

					for (let [attribute, value] of Object.entries(attribute_map)) {
						let fieldname = attribute_to_field[attribute];

						if (fieldname && frm.fields_dict[fieldname]) {
							let current_val = frm.doc[fieldname];

							// Use string comparison to avoid mismatch due to types
							if (String(current_val ?? "") !== String(value ?? "")) {
								let df = frm.fields_dict[fieldname].df;

								if (df.fieldtype === "Select" && df.options && !df.options.includes(value)) {
									df.options += `\n${value}`;
									frm.refresh_field(fieldname);
								}

								values_to_set[fieldname] = value;
							}
						}
					}

					if (Object.keys(values_to_set).length > 0) {
						frm.set_value(values_to_set);
					}
				}
			}
		});
	},

	onload: function(frm) {
		// Safe load trigger
		if (frm.doc.item) {
			frappe.call({
				method: "gke_customization.gke_order_forms.doctype.revise_field.revise_field.get_filtered_item_attributes",
				args: {
					item_code: frm.doc.item
				},
				callback: function(r) {
					if (r.message) {
						const attribute_map = r.message;
						let attribute_to_field = {
							"Metal Colour": "metal_colour",
							"Diamond Target": "diamond_target",
							"Stone Changeable": "stone_changeable",
							"Gemstone Type": "gemstone_type",
							"Chain Type": "chain_type",
							"Chain Length": "chain_length",
							"Feature": "feature",
							"Rhodium": "rhodium",
							"Enamal": "enamal",
							"Detachable": "detachable",
							"Cap/Ganthan": "capganthan",
							"Two in One": "two_in_one",
							"Product Size": "product_size",
							"Sizer Type": "sizer_type",
							"Lock Type": "lock_type",
							"Black Bead Line": "black_bead_line",
							"Charm": "charm",
							"Count of Spiral Turns": "count_of_spiral_turns",
							"Number of Ant": "number_of_ant",
							"Back Side Size": "back_side_size",
							"Space between Mugappu": "space_between_mugappu",
							"Distance Between Kadi To Mugappu": "distance_between_kadi_to_mugappu",
							"Back Belt": "back_belt",
							"Back Belt Length": "back_belt_length"
						};

						let values_to_set = {};

						for (let [attribute, value] of Object.entries(attribute_map)) {
							let fieldname = attribute_to_field[attribute];
							if (fieldname && frm.fields_dict[fieldname]) {
								let current_val = frm.doc[fieldname];

								if (String(current_val ?? "") !== String(value ?? "")) {
									values_to_set[fieldname] = value;
								}
							}
						}

						if (Object.keys(values_to_set).length > 0) {
							frm.set_value(values_to_set);
						}
					}
				}
			});
		}
	}
});
