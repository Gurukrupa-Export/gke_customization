// frappe.ui.form.on("Rewise Filed", {
// 	item: function(frm) {
// 		if (!frm.doc.item) {
// 			frm.fields_dict["item_attributes"].$wrapper.html("<div style='color: red;'>Please select an Item</div>");
// 			return;
// 		}

// 		frappe.call({
// 			method: "gke_customization.gke_order_forms.doctype.rewise_filed.rewise_filed.get_filtered_item_attributes",
// 			args: {
// 				item_code: frm.doc.item
// 			},
// 			callback: function(r) {
// 				if (r.message) {
// 					const attribute_map = r.message;

// 					// Mapping attribute names to fieldnames in Rewise Filed Doctype
// 					let attribute_to_field = {
// 						"Metal Colour": "metal_colour",
// 						"Diamond Target": "diamond_target",
// 						"Stone Changeable": "stone_changeable",
// 						"Gemstone Type": "gemstone_type",
// 						"Chain Type": "chain_type",
// 						"Chain Length": "chain_length",
// 						"Feature": "feature",
// 						"Rhodium": "rhodium",
// 						"Enamal": "enamal",
// 						"Detachable": "detachable",
// 						"Cap/Ganthan": "cap_ganthan",
// 						"Two in One": "two_in_one",
// 						"Product Size": "product_size",
// 						"Sizer Type": "sizer_type",
// 						"Lock Type": "lock_type",
// 						"Black Bead Line": "black_bead_line",
// 						"Charm": "charm",
// 						"Count of Spiral Turns": "count_of_spiral_turns",
// 						"Number of Ant": "number_of_ant",
// 						"Back Side Size": "back_side_size",
// 						"Space between Mugappu": "space_between_mugappu",
// 						"Distance Between Kadi To Mugappu": "distance_kadi_to_mugappu",
// 						"Back Belt": "back_belt",
// 						"Back Belt Length": "back_belt_length"
// 					};

// 					for (let [attribute, value] of Object.entries(attribute_map)) {
// 						let fieldname = attribute_to_field[attribute];
// 						if (fieldname && frm.fields_dict[fieldname]) {
// 							// Optional: if fieldtype is Select, dynamically add option
// 							let df = frm.fields_dict[fieldname].df;
// 							if (df.fieldtype === "Select" && !df.options?.includes(value)) {
// 								df.options += `\n${value}`;
// 								frm.refresh_field(fieldname);
// 							}
// 							frm.set_value(fieldname, value);
// 						}
// 					}
// 				}
// 			}
// 		});
// 	},

// 	onload: function(frm) {
// 		if (frm.doc.item) {
// 			frm.trigger("item");
// 		}
// 	}
// });




// frappe.ui.form.on("Rewise Filed", {
// 	item: function(frm) {
// 		if (!frm.doc.item) {
// 			frm.fields_dict["item_attributes"].$wrapper.html("<div style='color: red;'>Please select an Item</div>");
// 			return;
// 		}

// 		frappe.call({
// 			method: "gke_customization.gke_order_forms.doctype.rewise_filed.rewise_filed.get_filtered_item_attributes",
// 			args: {
// 				item_code: frm.doc.item
// 			},
// 			callback: function(r) {
// 				if (r.message) {
// 					const attribute_map = r.message;

// 					let attribute_to_field = {
// 						"Metal Colour": "metal_colour",
// 						"Diamond Target": "diamond_target",
// 						"Stone Changeable": "stone_changeable",
// 						"Gemstone Type": "gemstone_type",
// 						"Chain Type": "chain_type",
// 						"Chain Length": "chain_length",
// 						"Feature": "feature",
// 						"Rhodium": "rhodium",
// 						"Enamal": "enamal",
// 						"Detachable": "detachable",
// 						"Cap/Ganthan": "cap_ganthan",
// 						"Two in One": "two_in_one",
// 						"Product Size": "product_size",
// 						"Sizer Type": "sizer_type",
// 						"Lock Type": "lock_type",
// 						"Black Bead Line": "black_bead_line",
// 						"Charm": "charm",
// 						"Count of Spiral Turns": "count_of_spiral_turns",
// 						"Number of Ant": "number_of_ant",
// 						"Back Side Size": "back_side_size",
// 						"Space between Mugappu": "space_between_mugappu",
// 						"Distance Between Kadi To Mugappu": "distance_between_kadi_to_mugappu",
// 						"Back Belt": "back_belt",
// 						"Back Belt Length": "back_belt_length"
// 					};
//                     console.log(attribute_to_field)
// 					for (let [attribute, value] of Object.entries(attribute_map)) {
// 						let fieldname = attribute_to_field[attribute];
// 						if (fieldname && frm.fields_dict[fieldname]) {
// 							let df = frm.fields_dict[fieldname].df;
// 							if (df.fieldtype === "Select" && !df.options?.includes(value)) {
// 								df.options += `\n${value}`;
// 								frm.refresh_field(fieldname);
// 							}
// 							frm.set_value(fieldname, value);
// 						}
// 					}
// 				}
// 			}
// 		});
// 	},

// 	onload: function(frm) {
// 		if (frm.doc.item) {
// 			frm.trigger("item");
// 		}
// 	}
// });




frappe.ui.form.on("Rewise Filed", {
	item: function(frm) {
		if (!frm.doc.item) {
			frm.fields_dict["item_attributes"].$wrapper.html("<div style='color: red;'>Please select an Item</div>");
			return;
		}

		frappe.call({
			method: "gke_customization.gke_order_forms.doctype.rewise_filed.rewise_filed.get_filtered_item_attributes",
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
						"Back Belt Length": "back_belt_length",
                        
					};

					console.log("Backend attributes:", attribute_map);

					for (let [attribute, value] of Object.entries(attribute_map)) {
						let fieldname = attribute_to_field[attribute];
						console.log("Attribute:", attribute, " → Fieldname:", fieldname, " → Value:", value);

						if (fieldname && frm.fields_dict[fieldname]) {
							let df = frm.fields_dict[fieldname].df;
							console.log("Field Type of", fieldname, "is", df.fieldtype);

							if (df.fieldtype === "Select" && !df.options?.includes(value)) {
								df.options += `\n${value}`;
								console.log("Added new select option:", value);
								frm.refresh_field(fieldname);
							}
							console.log("Setting value for", fieldname, "=", value);
							frm.set_value(fieldname, value);
						} else {
							console.warn("Field not found for attribute:", attribute);
						}
					}
				}
			}
		});
	},

	onload: function(frm) {
		if (frm.doc.item) {
			frm.trigger("item");
		}
	}
});
