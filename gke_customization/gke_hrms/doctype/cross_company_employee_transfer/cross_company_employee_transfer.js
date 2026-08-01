// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Cross Company Employee Transfer", {
// 	refresh(frm) {

// 	},
// });

// frappe.ui.form.on("Cross Company Employee Transfer", {
// 	setup(frm) {
// 		frm.set_query("employee", function () {
// 			return {
// 				filters: {
// 					status: "Active",
// 				},
// 			};
// 		});
// 	},

// 	refresh(frm) {
// 		setup_property_dropdown(frm);
// 	}
// });


// function setup_property_dropdown(frm) {

// 	let grid = frm.fields_dict.transfer_details.grid;

// 	if (!grid)
// 		return;


// 	frappe.model.with_doctype("Employee", () => {

// 		let options = [""];

// 		let exclude_fields = [
// 			"employee",
// 			"employee_name",
// 			"status",
// 			"naming_series",
// 			"first_name",
// 			"middle_name",
// 			"last_name",
// 			"image",
// 			"date_of_birth",
// 			"date_of_joining",
// 			"lft",
// 			"rgt"
// 		];


// 		frappe.get_meta("Employee").fields.forEach(df => {

// 			if (
// 				df.fieldtype != "HTML" &&
// 				df.fieldtype != "Section Break" &&
// 				df.fieldtype != "Column Break" &&
// 				df.fieldtype != "Table" &&
// 				!exclude_fields.includes(df.fieldname) &&
// 				!df.hidden &&
// 				!df.read_only
// 			) {

// 				options.push(__(df.label));

// 			}

// 		});


// 		grid.update_docfield_property(
// 			"property",
// 			"options",
// 			options.join("\n")
// 		);

//         grid.refresh(); 


// 	});

// }


// frappe.ui.form.on("Cross Employee Transfer Details", {

// 	property(frm, cdt, cdn){

// 		let row = locals[cdt][cdn];

//         console.log("lkjhjrtxycgvhbknk")
// 		if(!row.property || !frm.doc.employee)
// 			return;


// 		// label se fieldname nikalna
// 		frappe.model.with_doctype("Employee", ()=>{

// 			let df = frappe.get_meta("Employee").fields.find(
// 				f => __(f.label) == row.property
// 			);


// 			if(!df)
// 				return;


// 			frappe.call({

// 				method:"hrms.hr.utils.get_employee_field_property",

// 				args:{
// 					employee: frm.doc.employee,
// 					fieldname: df.fieldname
// 				},

// 				callback(r){

// 					if(r.message){

// 						frappe.model.set_value(
// 							cdt,
// 							cdn,
// 							"fieldname",
// 							df.fieldname
// 						);


// 						frappe.model.set_value(
// 							cdt,
// 							cdn,
// 							"current",
// 							r.message.value
// 						);


// 						// New field ko dynamic banana
// 						let grid_row = frm.fields_dict.transfer_details.grid.get_row(cdn);

// 						let new_control = frappe.ui.form.make_control({
// 							df:{
// 								fieldtype:r.message.datatype,
// 								fieldname:"new",
// 								options:r.message.options || "",
// 								label:"New"
// 							},
// 							parent:grid_row.grid_form.fields_dict.new.wrapper,
// 							render_input:true
// 						});


// 					}
// 				}

// 			});

// 		});
// 	}

// });


// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cross Company Employee Transfer", {
	setup(frm) {
		frm.set_query("employee", function () {
			return {
				filters: {
					status: "Active",
				},
			};
		});
	},

	onload(frm) {
		// options ko ek baar load karke cache kar lo, taaki har refresh pe API call na ho
		setup_property_dropdown(frm);
		// set_site_defaults(frm)
	},

    refresh(frm) {
		restrict_add_row_without_employee(frm); // 👈 ab refresh me daala
	},


	employee(frm) {
        // toggle_transfer_details_table(frm);
		// employee change hone par cache clear karo taaki current value fresh fetch ho
		(frm.doc.transfer_details || []).forEach(row => {
			frappe.model.set_value(row.doctype, row.name, "current", "");
		});
	}
});


function setup_property_dropdown(frm) {

	let grid = frm.fields_dict.transfer_details.grid;
	if (!grid) return;

	frappe.model.with_doctype("Employee", () => {

		let options = [""]; // blank option — taaki empty select allowed rahe

		let exclude_fields = [
			"employee", "employee_name", "status", "naming_series",
			"first_name", "middle_name", "last_name", "image",
			"date_of_birth", "date_of_joining", "lft", "rgt"
		];

		frappe.get_meta("Employee").fields.forEach(df => {
			if (
				df.fieldtype != "HTML" &&
				df.fieldtype != "Section Break" &&
				df.fieldtype != "Column Break" &&
				df.fieldtype != "Table" &&
				!exclude_fields.includes(df.fieldname) &&
				!df.hidden &&
				!df.read_only
			) {
				options.push(__(df.label));
			}
		});

		// grid ke docfield ka options property update karo
		grid.update_docfield_property("property", "options", options.join("\n"));

		// har already-open grid row ka control bhi refresh karo
		grid.grid_rows.forEach(row => {
			if (row.grid_form && row.grid_form.fields_dict.property) {
				row.grid_form.fields_dict.property.df.options = options.join("\n");
				row.grid_form.fields_dict.property.refresh();
			}
		});

		grid.refresh();
	});
}


frappe.ui.form.on("Cross Employee Transfer Details", {

	property(frm, cdt, cdn) {

		let row = locals[cdt][cdn];

		if (!row.property || !frm.doc.employee) return;

        let duplicate = (frm.doc.transfer_details || []).some(
			r => r.property === row.property && r.name !== row.name
		);

        if (duplicate) {
			frappe.msgprint(__("Property '{0}' is already selected in another row.", [row.property]));
			frappe.model.set_value(cdt, cdn, "property", ""); // field ko clear kardo
			return; // aage ka logic mat chalao
		}

		frappe.model.with_doctype("Employee", () => {

			let df = frappe.get_meta("Employee").fields.find(
				f => __(f.label) == row.property
			);

			if (!df) return;

			frappe.call({
				method: "hrms.hr.utils.get_employee_field_property",
				args: {
					employee: frm.doc.employee,
					fieldname: df.fieldname
				},
				callback(r) {
					if (!r.message) return;

					frappe.model.set_value(cdt, cdn, "fieldname", df.fieldname);
					frappe.model.set_value(cdt, cdn, "current", r.message.value);

					// "New" field ko dynamic banana
					let grid_row = frm.fields_dict.transfer_details.grid.get_row(cdn);

					if (grid_row && grid_row.grid_form) {
						let wrapper = grid_row.grid_form.fields_dict.new.wrapper;
						$(wrapper).empty(); // purana control hatao warna duplicate ban jayega

						frappe.ui.form.make_control({
							df: {
								fieldtype: r.message.datatype,
								fieldname: "new",
								options: r.message.options || "",
								label: "New"
							},
							parent: wrapper,
							render_input: true
						});
					}
				}
			});
		});
	}
});


function restrict_add_row_without_employee(frm) {

	let grid = frm.fields_dict.transfer_details.grid;
	if (!grid) return;

	// pehle se overridden hai to dobara wrap na karo (double wrapping se bug ban sakta hai)
	frm.doc.transfer_details = (frm.doc.transfer_details || []).filter(row => row.property);
	frm.refresh_field("transfer_details");

    if (grid._add_row_restricted) return;

	let original_add_new_row = grid.add_new_row.bind(grid);

	grid.add_new_row = function (...args) {
		if (!frm.doc.employee) {
			frappe.msgprint(__("Please select an Employee first."));
			return;
		}
		return original_add_new_row(...args);
	};

	grid._add_row_restricted = true; // flag lagado taaki dobara wrap na ho
}


// function set_site_defaults(frm) {

// 	// value sirf tabhi set karo jab khaali ho (naya document ho)
// 	if (!frm.doc.source_site) {
// 		frm.set_value("source_site", "https://gkexport.frappe.cloud/");
// 	}

// 	if (!frm.doc.target_site) {
// 		frm.set_value("target_site", "https://kggk-prod.frappe.cloud/");
// 	}

// 	// dono fields read-only bana do
// 	frm.set_df_property("source_site", "read_only", 1);
// 	frm.set_df_property("target_site", "read_only", 1);

// 	frm.refresh_field("source_site");
// 	frm.refresh_field("target_site");
// }