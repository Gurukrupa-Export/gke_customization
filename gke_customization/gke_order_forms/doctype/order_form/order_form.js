frappe.ui.form.on('Order Form', {
	setup(frm) {
		// Ensure default time is 11:00:00 AM on load too if needed
		if (frm.doc.delivery_date) {
			set_11am_time_on_date(frm, 'delivery_date');
		}
	},
	
	delivery_date(frm) {
		set_11am_time_on_date(frm, 'delivery_date');
		validate_dates(frm, frm.doc, "delivery_date")
		update_fields_in_child_table(frm, "delivery_date")
		calculate_due_days(frm);
	},
	is_finding_order(frm) {
		update_fields_in_child_table(frm, "is_finding_order")
	},
	estimated_duedate(frm) {
		validate_dates(frm, frm.doc, "estimated_duedate")
		update_fields_in_child_table(frm, "estimated_duedate")
	},
	system_due_date(frm) {
		validate_dates(frm, frm.doc, "system_due_date")
	},
	branch(frm) {
		update_fields_in_child_table(frm, "branch")
	},
	project(frm) {
		update_fields_in_child_table(frm, "project")
	},
	setup(frm, cdt, cdn) {
		var parent_fields = [
			['diamond_quality', 'Diamond Quality']];
		set_filters_on_parent_table_fields(frm, parent_fields);

		var fields = [
			['design_type', 'Design Type'],
		['category', 'Item Category'],
		['subcategory', 'Item Subcategory'],
		['setting_type', 'Setting Type'],
		['metal_type', 'Metal Type'],
		// ['metal_purity', 'Metal Purity'],
		['diamond_quality', 'Diamond Quality'],
		['metal_touch', 'Metal Touch'],
		['metal_colour', 'Metal Colour'],
		['sizer_type', 'Sizer Type'],
		['enamal', 'Enamal'],
		['rhodium', 'Rhodium'],
		// ['gemstone_type', 'Gemstone Type'],
		['gemstone_quality', 'Gemstone Quality'],
		['stone_changeable', 'Stone Changeable'],
		['hinges', 'Hinges'],
		['back_belt_patti', 'Back Belt'],
		['vanki', 'Vanki'],
		['black_beed', 'Black Beed'],
		['screw_type', 'Screw Type'],
		['hook_type', 'Hook Type'],
		['lock_type', 'Lock Type'],
		['two_in_one', 'Two in One'],
		['kadi_type', 'Kadi Type'],
		// ['chain', 'Chain'],
		['chain_type', 'Chain Type'],
		['customer_chain', 'Chain From'],
		['detachable', 'Detachable'],
		['back_chain', 'Back Chain'],
		['nakshi_from', 'Nakshi From'],
		['nakshi', 'Nakshi'],
		['customer_sample', 'Customer Sample'],
		['certificate_place', 'Certificate Place'],
		['breadth', 'Breadth'],
		['width', 'Width'],
		['back_belt', 'Back Belt'],
		['back_belt_length', 'Back Belt Length'],
		['gemstone_type', 'Gemstone Type'],
		['sub_setting_type1', 'Sub Setting Type'],
		['sub_setting_type2', 'Sub Setting Type'],
		['gemstone_quality', 'Gemstone Quality'],
		['changeable_type', 'Changeable Type'],
		['feature', 'Feature'],
		['mod_reason', 'Mod Reason'],
		['capganthan', 'Cap/Ganthan'],
		['charm', 'Charm'],
		['finding_category', 'Finding Category'],
		['finding_subcategory', 'Finding Sub-Category'],
		['finding_size', 'Finding Size'],
		];

		set_filters_on_child_table_fields(frm, fields);
		set_filter_for_salesman_name(frm);

		frm.set_query('sub_setting_type1', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.setting_type
				}
			};
		});
		frm.set_query('sub_setting_type2', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.setting_type
				}
			};
		});
		frm.set_query('subcategory', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.category
				}
			};
		});
		frm.set_query('finding_subcategory', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					'parent_attribute_value': d.finding_category
				}
			};
		});
		frm.set_query('diamond_quality','order_details', function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': "Diamond Quality", "customer_code": doc.customer_code }
			};
		});
		frm.set_query('metal_touch','order_details', function (doc) {
			return {
				query: 'gke_customization.gke_order_forms.doctype.order_form.order_form.item_attribute_query',
				filters: { 'item_attribute': "Metal Touch", "customer_code": doc.customer_code }
			};
		});
		frm.set_query('design_id', 'order_details', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			if (d.design_type == 'Sketch Design'){
				return {
					filters: {
						"has_variants": 1,
						"variant_of": ["=", ""],
						"item_category": ["!=", ""],
						"order_form_type":"Sketch Order"
					}
				};
			}
		});
	},
	due_days(frm) {
		delivery_date(frm);
	},
	validate(frm) {
		if (frm.doc.delivery_date < frm.doc.order_date) {
			frappe.msgprint(__("You can not select past date in Delivery Date"));
			frappe.validated = false;
		}
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
		frm.set_query('diamond_quality','order_details', function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': "Diamond Quality", "customer_code": doc.customer_code }
			};
		});
		frm.set_query('metal_touch','order_details', function (doc) {
			return {
				query: 'gke_customization.gke_order_forms.doctype.order_form.order_form.item_attribute_query',
				filters: { 'item_attribute': "Metal Touch", "customer_code": doc.customer_code }
			};
		});

		frappe.call({
			method: "gke_customization.gke_order_forms.doctype.order_form.order_form.get_customer_orderType",
			args: {
				customer_code: frm.doc.customer_code,
			},
			callback: function (r) {
				if (!r.exc) {
					var arrayLength = r.message.length;
					if (arrayLength === 1) {
						frm.set_value("order_type", r.message[0].order_type);
						frm.set_df_property("order_type", "read_only", 1);
					} else {
						frm.set_value("order_type", "");
						frm.set_df_property("order_type", "read_only", 0);
					}
				}
			},
		});
		
		// if (frm.doc.order_details) {
		// 	frm.doc.order_details.forEach(function (d) {
		// 		show_attribute_fields_for_subcategory(frm, d.doctype, d.name, d);
		// 	})
		// }
		// if(frm.doc.customer_code=='CU0010'){
		// 	frm.fields_dict['order_details'].grid.get_field('screw_type').get_query = function(doc, cdt, cdn) {
		// 		var d = locals[cdt][cdn];
		// 		return { visible: 1 };
		// 	};
		// }
	},
	refresh(frm){
		frm.add_custom_button(__("Get Customer Order Form"), function(){
            erpnext.utils.map_current_doc({
                method: "gke_customization.gke_order_forms.doctype.order_form.order_form.get_customer_order_form",			
				source_doctype: "Customer Order Form",
                target: frm,
                setters: [
					// {
                    //     label: "Amended From",
                    //     fieldname: "amended_from",
                    //     fieldtype: "Link",
                    //     options: "Sales Invoice"
                    // },
                    {
                        label: "Customer Order Form",
                        fieldname: "customer_order_form",
                        fieldtype: "Link",
                        options: "Customer Order Form"
                    },
                    {
                        label: "Customer",
                        fieldname: "customer_code",
                        fieldtype: "Link",
                        options: "Customer",
                        // reqd: 1,
                        // default: frm.doc.design_code || undefined
                    },
                    // {
                    //     label: "Project",
                    //     fieldname: "project",
                    //     fieldtype: "Link",
                    //     options: "Project",
                    //     // reqd: 1,
                    //     // default: frm.doc.order_type || undefined
                    // }
                ],
                // get_query_filters: {
                    // docstatus: 1,
					// cad_order_form: frappe.db.get_list('Order Form')
                // }
            })
        }, __("Get Order"))
		frm.add_custom_button(__("Pre Order Form"), function () {
			erpnext.utils.map_current_doc({
				method: "gke_customization.gke_order_forms.doctype.order_form.order_form.make_from_pre_order_form",
				source_doctype: "Pre Order Form",
				target: frm,
				setters: [
				{
					label: "Pre Order Form",
					fieldname: "name",
					fieldtype: "Link",
					options: "Pre Order Form"
				},
				{
					label: "Date",
					fieldname: "date",
					fieldtype: "Date",
				},
				// {
				//   label: "Order Type",
				//   fieldname: "order_type",
				//   fieldtype: "Select",
				//   options: ["Sales", "Stock Order"],
				//   reqd: 1,
				//   default: frm.doc.order_type || undefined
				// }
				],
		
				get_query_filters: {
				// item: ['is', 'set'],
                workflow_state:['in',['Approved','Creating Item & BOM']],
				order_form_id:['is','not set'],
                // docstatus: 1
				}
			})
			frm.set_df_property('party_name', 'read_only', 1);
			}, __("Get Order"))
		if(frm.doc.workflow_state=='Validate Rows' && frm.doc.name && !frm.doc.__islocal){
			frm.add_custom_button('Validate Rows', function () {
				frappe.call({
					method: "gke_customization.gke_order_forms.doctype.order_form.order_form.validate_rows",
					args: {
						docname: frm.doc.name
					},
					callback(r) {
						if (r.message) {
							frappe.msgprint(r.message);
							console.log(r.message);
							
							if (r.message == "No duplicates found"){
								frm.reload_doc();

							}
						}
					}
				});
			});
		}
	},
	order_type(frm){
		if(frm.doc.order_type=='Purchase'){
			$.each(frm.doc.order_details || [], function (i, d) {
				d.design_by = frm.doc.order_type;
				d.design_type = 'New Design';
			});
			refresh_field("order_details");
		}
	}

});

frappe.ui.form.on('Order Form Detail', {
	form_render(frm, cdt, cdn) {
		let order_detail = locals[cdt][cdn];

		var fields = ['design_id'];
		if (order_detail.design_type == 'Sketch Design'){
			set_filter_for_sketch_design_n_serial(frm,fields)
		}
		// else{
		// 	set_filter_for_design_n_serial(frm,fields)
		// }
	},

	tag_no(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		fetch_item_from_serial(d, "tag_no", "design_id")
		if (d.tag_no) {
			frappe.db.get_value("BOM",{"tag_no": d.tag_no},'name', (r)=>{
				frappe.model.set_value(cdt, cdn, 'bom', r.name)
			})
		}
	},

	design_id: function(frm, cdt, cdn) {
		handle_design_id_change(frm, cdt, cdn);
    },

	order_details_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.delivery_date = frm.doc.delivery_date;
		row.diamond_quality = frm.doc.diamond_quality;
		row.estimated_duedate = frm.doc.estimated_duedate;
		row.branch = frm.doc.branch
		row.project = frm.doc.project
		row.customer_code = frm.doc.customer_code
		row.is_finding_order = frm.doc.is_finding_order
		var fields = ['design_id'];
		if (row.design_type == 'Sketch Design'){
			set_filter_for_sketch_design_n_serial(frm,fields)
		}
		// else{
		// 	set_filter_for_design_n_serial(frm,fields)
		// }
		if (frm.doc.order_type === 'Purchase') {
			var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "design_type" })[0];
			if (df) {
				df.read_only = 1
				row.design_type = "New Design"
			}
			var df1 = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "design_by" })[0];
			if (df1) {
				df1.read_only = 1
				row.design_by = "Purchase"
			}
        }
		refresh_field("order_details");
	},

	design_type: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		var fields = ['design_id'];
		if (row.design_type == 'Sketch Design'){
			set_filter_for_sketch_design_n_serial(frm,fields)
		}
	},

	category: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(row.doctype, row.name, 'subcategory', '');
	},

	// button to view item variants
	update_item:function(frm,cdt,cdn){
		var row = locals[cdt][cdn];

		if (frm.doc.__islocal) {
			frappe.throw("Please save document to edit the View Item.");
		}

		let item_data = [];

		const item_fields = [				
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, columns: 1,hidden:1 },			
			{
				fieldtype: "Link",
				fieldname: "attribute",
				label: __("Attribute"),
				// reqd: 1,
				read_only: 1,
				columns: 4,
				in_list_view: 1,
				options: "Item Attribute",
			},
			{
				fieldtype: "Data",
				fieldname: "attribute_value",
				label: __("Attribute Value"),
				// reqd: 1,
				read_only: 1,
				columns: 3,
				in_list_view: 1,
			},
			{
				fieldtype: "Data",
				fieldname: "new_attribute",
				label: __("New Attribute Value"),
				// reqd: 1,
				read_only: 1,
				columns: 3,
				in_list_view: 1,
			},
		];

		const dialog = new frappe.ui.Dialog({
			title: __("Item Variants View"),
			fields: [
				{
					label: "Item Code",
					fieldname: "item_code",
					fieldtype: "Link",
					options: "Item",
					// read_only: 1,
					default: row.design_id,
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: "Item Category",
					fieldname: "item_category",
					fieldtype: "Data",
					fieldtype: "Link",
					options: "Attribute Value",
					default: row.category,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: "Item Subcategory",
					fieldname: "item_subcategory",
					fieldtype: "Link",
					options: "Attribute Value",
					read_only: 1,
					default: row.subcategory,
				},				
				{
					fieldtype: "Section Break",
					// label: "Variants",
				},
				{
					fieldname: "item_detail",
					fieldtype: "Table",
					label: "Item Variants Value",
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					data: item_data,
					get_data: () => {
						return item_data;
					},
					fields: item_fields,
				},
								
				{
					fieldtype: "Section Break",
				},

				{
					label: "Setting Type",
					fieldname: "setting_type",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: row.setting_type,
				},
				{
					label: "Sub Setting Type1",
					fieldname: "sub_setting_type1",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: row.sub_setting_type1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Sub Setting Type2",
					fieldname: "sub_setting_type2",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: row.sub_setting_type2,
					depends_on: ' eval:doc.setting_type == "Open" '
				},
				{
					fieldtype: "Column Break",
				},				
				{
					label: "Metal Type",
					fieldname: "metal_type",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: row.metal_type,
					// depends_on: ' eval: in_list(["Addigai Necklace", "Anklet", "Ball Mugappu", "Band Bracelet", "Belt", "Buttons", "Chain Armlet", "Chain Bracelet", "Chandbali", "Chandeliers", "Charm Bracelet", "Charm Necklace", "Charms", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Mugappu", "Cocktail Studs", "Collar Necklace", "Crown", "Cuban Bracelet", "Cuban Chain", "Cufflinks", "Dangler Earrings", "Drop Earrings", "Drop Nose Pin", "Earcuff Earrings", "Eternity Bangles", "Fancy Accessory", "Fancy Armlet", "Fancy Bangles", "Fancy Box", "Fancy Bracelet", "Fancy Earrings", "Fancy Mangalsutra", "Fancy Mugappu", "Fancy Necklace", "Fancy Nose Pin", "Fancy Oddiyanam", "Fancy Ring", "Flexible Bracelet", "Front Back Earrings", "God Bangles", "God Bracelet", "God Earrings", "God Mangalsutra", "God Mugappu", "God Oddiyanam", "God Pendant", "God Vanki", "God Vanki/Armlet", "Goggles", "Golusu Bangles", "Hair Pin", "Haram Necklace", "Hoops & Huggies Earrings", "J Nose Pin", "Jada", "Jada Billa", "Jumkhi", "Jumpring Earrings", "Kada Bangles", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Bangles", "Kids Bracelet", "Kids Earrings", "Kids Hair Pin", "Kids Necklace", "Kids Oddiyanam", "Kids Ring", "Kids Vanki", "Kids Vanki/Armlet", "Kuppu Earrings", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Maang Tikka", "Magdi Necklace", "Mala Necklace", "Mangalsutra Bracelet", "Mangalsutra Chains", "Mangalsutra Pendant", "Mangalsutra Ring", "Matal-Sahara", "Matha Patti", "Mismatch Earrings", "Money Accessory", "Nakshi Armlet", "Nakshi Bangles", "Nakshi Bracelet", "Nakshi Chain", "Nakshi Chandbalis", "Nakshi Choker", "Nakshi Earrings", "Nakshi Haram", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Jumkhi", "Nakshi Maang Tikka", "Nakshi Mugappu", "Nakshi Necklace", "Nakshi Oddiyanam", "Nakshi Pendant", "Nakshi Ring", "Nakshi Thali/Tanmaniya", "O Nose Pin", "Oddiyanam", "Oval Bracelet", "Pacheli Bangles", "Padhakam Necklace", "Passa", "Pen", "Round Bangles", "Sculpture", "Short Necklace", "Slider Pendant", "Solitaire Bangles", "Solitaire Bracelet", "Solitaire Earrings", "Solitaire Mangalsutra", "Solitaire Mugappu", "Solitaire Necklace", "Solitaire Pendant", "Spiral Mugappu", "Spiral Ring", "Station Necklace", "Stud Nose Pin", "Tennis Bracelet", "Tennis Necklace", "Thali/Tanmaniya", "Threaders", "Tie Clip", "Tube Armlet", "V/U Vanki", "Vanki", "Watch Charms", "Watches"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "lock_type" })[0].depends_on
				},				
				
				{
					fieldtype: "Column Break",
				},
				{
					label: "Metal Colour",
					fieldname: "metal_colour",
					read_only: 1,
					fieldtype: "Data",
					in_list_view: 1,
					default: row.metal_colour,
					// depends_on: ' eval: in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Daily Wear Mugappu", "Eternity Bangles", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "number_of_ant" })[0].depends_on
				},
				{
					label: "No. of Pcs",
					fieldname: "qty",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: row.qty,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
				},		
				{
					fieldtype: "Section Break",
				},
				{
					label: "Diamond Target",
					fieldname: "diamond_target",
					fieldtype: "Data",
					read_only: 1,
					default: row.diamond_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
				},
				{
					label: "Gemstone Type1",
					fieldname: "gemstone_type1",
					fieldtype: "Data",
					read_only: 1,
					hidden: 1,
					default: row.gemstone_type1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Gemstone Type",
					fieldname: "gemstone_type",
					fieldtype: "Data",
					read_only: 1,
					default: row.gemstone_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Rhodium",
					fieldname: "rhodium",
					fieldtype: "Data",
					read_only: 1,
					default: row.rhodium,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Gemstone Quality",
					fieldname: "gemstone_quality",
					fieldtype: "Data",
					read_only: 1,
					default: row.gemstone_quality,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Feature",
					fieldname: "feature",
					fieldtype: "Data",
					read_only: 1,
					default: row.feature,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "feature" })[0].depends_on
				},
				{
					label: "Lock Type",
					fieldname: "lock_type",
					fieldtype: "Data",
					read_only: 1,
					default: row.lock_type,
					// depends_on: ' eval: in_list(["Addigai Necklace", "Anklet", "Ball Mugappu", "Band Bracelet", "Belt", "Buttons", "Chain Armlet", "Chain Bracelet", "Chandbali", "Chandeliers", "Charm Bracelet", "Charm Necklace", "Charms", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Mugappu", "Cocktail Studs", "Collar Necklace", "Crown", "Cuban Bracelet", "Cuban Chain", "Cufflinks", "Dangler Earrings", "Drop Earrings", "Drop Nose Pin", "Earcuff Earrings", "Eternity Bangles", "Fancy Accessory", "Fancy Armlet", "Fancy Bangles", "Fancy Box", "Fancy Bracelet", "Fancy Earrings", "Fancy Mangalsutra", "Fancy Mugappu", "Fancy Necklace", "Fancy Nose Pin", "Fancy Oddiyanam", "Fancy Ring", "Flexible Bracelet", "Front Back Earrings", "God Bangles", "God Bracelet", "God Earrings", "God Mangalsutra", "God Mugappu", "God Oddiyanam", "God Pendant", "God Vanki", "God Vanki/Armlet", "Goggles", "Golusu Bangles", "Hair Pin", "Haram Necklace", "Hoops & Huggies Earrings", "J Nose Pin", "Jada", "Jada Billa", "Jumkhi", "Jumpring Earrings", "Kada Bangles", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Bangles", "Kids Bracelet", "Kids Earrings", "Kids Hair Pin", "Kids Necklace", "Kids Oddiyanam", "Kids Ring", "Kids Vanki", "Kids Vanki/Armlet", "Kuppu Earrings", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Maang Tikka", "Magdi Necklace", "Mala Necklace", "Mangalsutra Bracelet", "Mangalsutra Chains", "Mangalsutra Pendant", "Mangalsutra Ring", "Matal-Sahara", "Matha Patti", "Mismatch Earrings", "Money Accessory", "Nakshi Armlet", "Nakshi Bangles", "Nakshi Bracelet", "Nakshi Chain", "Nakshi Chandbalis", "Nakshi Choker", "Nakshi Earrings", "Nakshi Haram", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Jumkhi", "Nakshi Maang Tikka", "Nakshi Mugappu", "Nakshi Necklace", "Nakshi Oddiyanam", "Nakshi Pendant", "Nakshi Ring", "Nakshi Thali/Tanmaniya", "O Nose Pin", "Oddiyanam", "Oval Bracelet", "Pacheli Bangles", "Padhakam Necklace", "Passa", "Pen", "Round Bangles", "Sculpture", "Short Necklace", "Slider Pendant", "Solitaire Bangles", "Solitaire Bracelet", "Solitaire Earrings", "Solitaire Mangalsutra", "Solitaire Mugappu", "Solitaire Necklace", "Solitaire Pendant", "Spiral Mugappu", "Spiral Ring", "Station Necklace", "Stud Nose Pin", "Tennis Bracelet", "Tennis Necklace", "Thali/Tanmaniya", "Threaders", "Tie Clip", "Tube Armlet", "V/U Vanki", "Vanki", "Watch Charms", "Watches"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "lock_type" })[0].depends_on
				},
				{
					label: "Chain",
					fieldname: "chain",
					fieldtype: "Data",
					read_only: 1,
					default: row.chain,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain" })[0].depends_on
				},
				{
					label: "Distance Between Kadi To Mugappu",
					fieldname: "distance_between_kadi_to_mugappu",
					read_only: 1,
					fieldtype: "Data",
					default: row.distance_between_kadi_to_mugappu,
					// 	depends_on: ' eval:in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Daily Wear Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "distance_between_kadi_to_mugappu" })[0].depends_on
				},
				{
					label: "Number of Ant",
					fieldname: "number_of_ant",
					read_only: 1,
					fieldtype: "Data",
					default: row.number_of_ant,
					// 	depends_on: ' eval: in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Daily Wear Mugappu", "Eternity Bangles", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "number_of_ant" })[0].depends_on
				},
				{
					label: "Back Belt",
					fieldname: "back_belt",
					read_only: 1,
					fieldtype: "Data",
					default: row.back_belt,
					// 	depends_on: 'eval:in_list(["Fancy Oddiyanam","God Oddiyanam","Kids Oddiyanam","Nakshi Oddiyanam","Oddiyanam"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt" })[0].depends_on
				},
				{
					fieldtype: "Column Break",
				},				
				{
					label: "Metal Target",
					fieldname: "metal_target",
					fieldtype: "Data",
					read_only: 1,
					default: row.metal_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "metal_target" })[0].depends_on					
				},
				{
					label: "Sizer Type",
					fieldname: "sizer_type",
					fieldtype: "Data",
					read_only: 1,
					default: row.sizer_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "sizer_type" })[0].depends_on
					
				},	
				{
					label: "Detachable",
					fieldname: "detachable",
					fieldtype: "Data",
					read_only: 1,
					default: row.detachable,
					// 	depends_on: ' eval:in_list(["Addigai Necklace", "Ant Mugappu", "Ball Mugappu", "Chain Armlet", "Chain Pendant", "Chandbali", "Chandeliers", "Charm Necklace", "Charms", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Mugappu", "Cocktail Pendant", "Cocktail Studs", "Collar Necklace", "Cuban Chain", "Daily Wear Earrings", "Daily Wear Mugappu", "Daily Wear Pendant", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings", "Eternity Bangles", "Fancy Accessory", "Fancy Armlet", "Fancy Box", "Fancy Bracelet", "Fancy Earrings", "Fancy Mangalsutra", "Fancy Mugappu", "Fancy Necklace", "Fancy Oddiyanam", "Fancy Pendant", "Front Back Earrings", "God Earrings", "God Mangalsutra", "God Mugappu", "God Oddiyanam", "God Pendant", "God Vanki/Armlet", "Hair Pin", "Haram Necklace", "Hoops & Huggies Earrings", "Jada", "Jada Billa", "Jumkhi", "Jumpring Earrings", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Earrings", "Kids Hair Pin", "Kids Necklace", "Kids Oddiyanam", "Kids Vanki/Armlet", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Maang Tikka", "Magdi Necklace", "Mala Necklace", "Mangalsutra Chains", "Mangalsutra Pendant", "Matal-Sahara", "Matha Patti", "Mismatch Earrings", "Nakshi Armlet", "Nakshi Chain", "Nakshi Chandbalis", "Nakshi Choker", "Nakshi Earrings", "Nakshi Haram", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Jumkhi", "Nakshi Maang Tikka", "Nakshi Mugappu", "Nakshi Necklace", "Nakshi Oddiyanam", "Nakshi Pendant", "Nakshi Thali/Tanmaniya", "Oddiyanam", "Padhakam Necklace", "Passa", "Sculpture", "Short Necklace", "Slider Pendant", "Solitaire Bracelet", "Solitaire Earrings", "Solitaire Mangalsutra", "Solitaire Mugappu", "Solitaire Necklace", "Solitaire Pendant", "Spiral Mugappu", "Station Necklace", "Tennis Necklace", "Thali/Tanmaniya", "Threaders", "Tube Armlet", "Vanki"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "detachable" })[0].depends_on
				},
				{
					label: "Chain Type",
					fieldname: "chain_type",
					fieldtype: "Data",
					read_only: 1,
					default: row.chain_type,
					// 	depends_on: ' eval: in_list(["Nakshi Bracelet", "Chain Pendant", "Round Bangles", "Kada Bangles", "God Bangles", "Fancy Bangles", "Hair Pin", "Jada", "Maang Tikka", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Maang Tikka", "Passa", "Matha Patti", "Matal-Sahara", "Kids Hair Pin", "Jada Billa", "Belt", "Brooch", "Cufflinks", "Goggles", "Pen", "Sculpture", "Tie Clip", "Watches", "Buttons", "Money Accessory", "Fancy Accessory", "Fancy Box", "Anklet", "Charms", "Nakshi Armlet", "Vanki", "Tube Armlet", "Kids Vanki/Armlet", "God Vanki/Armlet", "Fancy Armlet", "Chain Armlet", "God Oddiyanam", "Oddiyanam", "Kids Oddiyanam", "Fancy Oddiyanam", "Nakshi Oddiyanam", "God Mugappu", "Solitaire Mugappu", "Spiral Mugappu", "Nakshi Mugappu", "Fancy Mugappu", "Daily Wear Mugappu", "Cocktail Mugappu", "Ball Mugappu", "Ant Mugappu", "Nakshi Thali/Tanmaniya", "Thali/Tanmaniya", "Solitaire Mangalsutra", "Mangalsutra Pendant", "Mangalsutra Chains", "God Mangalsutra", "Fancy Mangalsutra", "Cuban Chain", "Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Fancy Necklace", "Collar Necklace", "Choker Necklace", "Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Charm Necklace", "Chik Chokar", "Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace", "Layered Necklace", "Magdi Necklace", "Mala Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace", "Tennis Necklace", "Solitaire Necklace", "Nakshi Chain", "Cuban Bracelet", "Solitaire Bracelet", "Tennis Bracelet", "Oval Bracelet", "Mangalsutra Bracelet", "Kids Bracelet", "God Bracelet", "Flexible Bracelet", "Fancy Bracelet", "Charm Bracelet", "Chain Bracelet", "Band Bracelet", "Crown", "God Pendant", "Solitaire Pendant", "Slider Pendant", "Nakshi Pendant", "Locket Pendant", "Kid Pendant", "Fancy Pendant", "Daily Wear Pendant", "Cocktail Pendant", "Threaders", "Jumkhi", "Chandbali", "Mismatch Earrings", "Jumpring Earrings", "Hoops & Huggies Earrings", "God Earrings", "Front Back Earrings", "Fancy Earrings", "Earcuff Earrings", "Dangler Earrings", "Chandeliers", "Adjustable/Bolo Ring", "Mangalsutra Ring", "Fancy Ring", "Daily Wear Ring", "Cocktail Ring", "Band Ring"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_type" })[0].depends_on
				},
				{
					label: "Back Chain",
					fieldname: "back_chain",
					fieldtype: "Data",
					read_only: 1,
					default: row.back_chain,
					// 	depends_on: 'eval: in_list(["Addigai Necklace", "Chain Armlet", "Chain Pendant", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Pendant", "Collar Necklace", "Daily Wear Pendant", "Fancy Armlet", "Fancy Necklace", "Fancy Pendant", "God Pendant", "God Vanki", "God Vanki/Armlet", "Haram Necklace", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Necklace", "Kids Vanki", "Kids Vanki/Armlet", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Magdi Necklace", "Mala Necklace", "Nakshi Armlet", "Nakshi Chain", "Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Nakshi Pendant", "Padhakam Necklace", "Short Necklace", "Slider Pendant", "Solitaire Necklace", "Solitaire Pendant", "Station Necklace", "Tennis Necklace", "Tube Armlet", "V/U Vanki", "Vanki"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_chain" })[0].depends_on
				},
				{
					label: "Space between Mugappu",
					fieldname: "space_between_mugappu",
					read_only: 1,
					fieldtype: "Data",
					default: row.space_between_mugappu,
					// 	depends_on: ' eval: in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Daily Wear Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "space_between_mugappu" })[0].depends_on
				},
				{
					label: "Black Bead",
					fieldname: "black_bead",
					read_only: 1,
					fieldtype: "Data",
					default: row.black_beed,
					// 	depends_on: ' eval: in_list(["Mangalsutra Bracelet", "Mangalsutra Ring", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains", "Mangalsutra Pendant", "Nakshi Thali/Tanmaniya", "Solitaire Mangalsutra", "Thali/Tanmaniya"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_bead" })[0].depends_on
				},
				{
					label: "Black Beed Line",
					fieldname: "black_beed_line",
					read_only: 1,
					fieldtype: "Data",
					default: row.black_beed_line,
					depends_on: " eval:doc.black_beed == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_beed_line" })[0].depends_on
				},
				{
					label: "Back Belt Length",
					fieldname: "back_belt_length",
					read_only: 1,
					fieldtype: "Data",
					default: row.back_belt_length,
					depends_on: " eval:doc.back_belt == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt_length" })[0].depends_on
				},
				
				{
					fieldtype: "Column Break",
				},
				
				{
					label: "Metal Colour",
					fieldname: "metal_colour",
					fieldtype: "Data",
					read_only: 1, 
					default: row.metal_colour,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "metal_colour" })[0].depends_on
				},
				{
					label: "Enamal",
					fieldname: "enamal",
					fieldtype: "Data",
					read_only: 1,
					default: row.enamal,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "enamal" })[0].depends_on
				},
				{
					label: "Stone Changeable",
					fieldname: "stone_changeable",
					fieldtype: "Data",
					read_only: 1,
					default: row.stone_changeable,
					// depends_on: ' eval: in_list(["Addigai Necklace", "Anklet", "Ant Mugappu", "Ball Mugappu", "Band Bracelet", "Chain Armlet", "Chain Bracelet", "Chain Pendant", "Chandbali", "Chandeliers", "Charm Bracelet", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Mugappu", "Cocktail Pendant", "Cocktail Ring", "Cocktail Studs", "Collar Necklace", "Crown", "Cuban Bracelet", "Cuban Chain", "Cufflinks", "Daily Wear Earrings", "Daily Wear Mugappu", "Daily Wear Pendant", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings", "Engagement Ring", "Eternity Bangles", "Fancy Accessory", "Fancy Armlet", "Fancy Bangles", "Fancy Box", "Fancy Bracelet", "Fancy Earrings", "Fancy Mangalsutra", "Fancy Mugappu", "Fancy Necklace", "Fancy Oddiyanam", "Fancy Pendant", "Fancy Ring", "Flexible Bracelet", "Front Back Earrings", "God Bangles", "God Bracelet", "God Earrings", "God Mangalsutra", "God Mugappu", "God Oddiyanam", "God Pendant", "God Vanki/Armlet", "Goggles", "Golusu Bangles", "Hair Pin", "Haram Necklace", "Hoops & Huggies Earrings", "Jada", "Jada Billa", "Jumkhi", "Jumpring Earrings", "Kada Bangles", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Bangles", "Kids Bracelet", "Kids Earrings", "Kids Hair Pin", "Kids Necklace", "Kids Oddiyanam", "Kids Vanki/Armlet", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Maang Tikka", "Magdi Necklace", "Mala Necklace", "Mangalsutra Bracelet", "Mangalsutra Chains", "Mangalsutra Pendant", "Matal-Sahara", "Matha Patti", "Mismatch Earrings", "Nakshi Armlet", "Nakshi Bangles", "Nakshi Bracelet", "Nakshi Chain", "Nakshi Chandbalis", "Nakshi Choker", "Nakshi Earrings", "Nakshi Haram", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Jumkhi", "Nakshi Maang Tikka", "Nakshi Mugappu", "Nakshi Necklace", "Nakshi Oddiyanam", "Nakshi Pendant", "Nakshi Thali/Tanmaniya", "Oddiyanam", "Oval Bracelet", "Pacheli Bangles", "Padhakam Necklace", "Passa", "Round Bangles", "Sculpture", "Short Necklace", "Slider Pendant", "Solitaire Bangles", "Solitaire Bracelet", "Solitaire Earrings", "Solitaire Mangalsutra", "Solitaire Mugappu", "Solitaire Necklace", "Solitaire Pendant", "Solitaire Ring", "Spiral Mugappu", "Station Necklace", "Tennis Necklace", "Thali/Tanmaniya", "Threaders", "Tube Armlet", "Vanki"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "stone_changeable" })[0].depends_on
				},
				{
					label: "Chain Length",
					fieldname: "chain_length",
					fieldtype: "Data",
					read_only: 1,
					default: row.chain_length,
					// depends_on: ' eval:in_list(["Kodi Chain", "Snake Chain", "Runway", "Box Chain (Big)", "Box Chain (Small)", "Anchor Chain", "Black Bead Chain", "Shiva Chain", "Sadak Chain", "Highway Chain", "Mesh Chain", "Milan Chain", "Flat Ghop Chain", "Round Ghop Chain", "Nakshi Chain", "Fancy Chain"], doc.chain_type) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_length" })[0].depends_on
				},	
				{
					label: "Product Size",
					fieldname: "product_size",
					read_only: 1,
					fieldtype: "Data",
					default: row.product_size,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "product_size" })[0].depends_on
				},
				{
					label: "Count of Spiral Turns",
					fieldname: "count_of_spiral_turns",
					read_only: 1,
					fieldtype: "Data",
					default: row.count_of_spiral_turns,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "count_of_spiral_turns" })[0].depends_on
				},
				{
					label: "Charm",
					fieldname: "charm",
					read_only: 1,
					fieldtype: "Data",
					default: row.charm,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "two_in_one",
					fieldname: "two_in_one",
					read_only: 1,
					fieldtype: "Data",
					default: row.two_in_one,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "Cap/Ganthan",
					fieldname: "capganthan",
					read_only: 1,
					fieldtype: "Data",
					default: row.capganthan,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "Chain Thickness",
					fieldname: "chain_thickness",
					read_only: 1,
					fieldtype: "Data",
					default: row.chain_thickness,
					// depends_on: ' eval:in_list(["Kodi Chain", "Snake Chain", "Runway", "Box Chain (Big)", "Box Chain (Small)", "Anchor Chain", "Black Bead Chain", "Shiva Chain", "Sadak Chain", "Highway Chain", "Mesh Chain", "Milan Chain", "Flat Ghop Chain", "Round Ghop Chain", "Nakshi Chain", "Fancy Chain"], doc.chain_type) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_thickness" })[0].depends_on
				},
				{
					label: "Back Side Size",
					fieldname: "back_side_size",
					read_only: 1,
					fieldtype: "Data",
					default: '0.0',
				},
								
				{
					fieldtype: "Section Break",
				},	
					
				
				
				
			],	
			primary_action: function () {				
				refresh_field("order_details");
			},
			primary_action_label: (""),
			
		});
				
		if(dialog.get_value("item_code")) {
			// set item_code variants value in the given dialog box
			edit_item_documents(
				row,
				dialog,
				dialog.get_value("item_code"),
				item_data 
			);
		};

		dialog.show();

		dialog.$wrapper.find(".modal-dialog").css("max-width", "80%");
		dialog.$wrapper.find('.modal-footer .btn-primary').hide();

		// hide update button
		if (cur_frm.doc.docstatus == 1) {
			dialog.$wrapper.find(".btn-modal-primary").remove();
		} 
	},

});

let edit_item_documents = (row,dialog,item_code,item_data) => {
	var doc = frappe.model.get_doc("Item", item_code);
	if (!doc) {
		frappe.call({
			method: "frappe.client.get",
			freeze: true,
			args: {
				doctype: "Item",
				name: item_code,
			},
			callback(r) {
				if (r.message) {
					set_edit_item_details(row,
						r.message,
						dialog,
						item_data
					);
				}
			},
		});
	} else {
		set_edit_item_details(row,doc,dialog,item_data);
	}
};


let set_edit_item_details = (row,doc,dialog) => {
	// clearing all tables
	dialog.fields_dict.item_detail.df.data = [];
	dialog.fields_dict.item_detail.grid.refresh();
	
	$.each(doc.attributes, function (index, d) {
				
		let matchingValue = row[d.attribute.toLowerCase().replace(/\s+/g, '_')];

		dialog.fields_dict.item_detail.df.data.push({
			// docname: d.index,
			attribute: d.attribute,
			attribute_value: d.attribute_value,
			new_attribute: matchingValue || ""
			
		});
		item_data = dialog.fields_dict.item_detail.df.data;
		dialog.fields_dict.item_detail.grid.refresh();
	});

	$.each(doc.attributes, function (index, d) {
		var field_name = d.attribute.toLowerCase().replace(/\s+/g, '_');
		dialog.set_df_property(field_name, "hidden", 1);
	});
};

function set_metal_properties_from_bom(frm, cdt, cdn) {
	let row = locals[cdt][cdn]
	if (row.design_type == "Mod - Old Stylebio & Tag No" && (row.serial_no_bom || row.bom)) {
		frappe.db.get_value("BOM", row.serial_no_bom || row.bom, ["metal_touch","metal_type","metal_colour","metal_purity"], (r)=> {
			frappe.model.set_value(cdt, cdn, r)
		})
	}
};
function set_11am_time_on_date(frm, fieldname) {
	if (frm.doc[fieldname]) {
		let date_only = frappe.datetime.obj_to_str(frappe.datetime.str_to_obj(frm.doc[fieldname]), 'date');
		let new_datetime = `${date_only} 11:00:00`;
		frm.set_value(fieldname, new_datetime);
	}
};

function validate_dates(frm, doc, dateField) {
	let order_date = frm.doc.order_date;
	let delivery_date = doc[dateField];

	if (!order_date || !delivery_date) return;

	// Ensure order_date and delivery_date are both datetime objects
	const order_dt = frappe.datetime.str_to_obj(order_date);
	const delivery_dt = frappe.datetime.str_to_obj(delivery_date);

	// If delivery date is earlier than order date, reset it to +1 day at 11:00 AM
	if (delivery_dt < order_dt) {
		let new_date = frappe.datetime.add_days(order_date, 1);
		new_date = frappe.datetime.set_time(new_date, '11:00:00');
		frappe.model.set_value(doc.doctype, doc.name, dateField, new_date);
	}
};

function fetch_item_from_serial(doc, fieldname, itemfield) {
	if (doc[fieldname]) {
		frappe.db.get_value("Serial No", doc[fieldname], 'item_code', (r) => {
			frappe.model.set_value(doc.doctype, doc.name, itemfield, r.item_code)
		})
	}
}

function set_field_visibility(frm, cdt, cdn) {
	// hide_all_subcategory_attribute_fields(frm, cdt, cdn);
	// var order_detail = locals[cdt][cdn];
	// show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail);
};

//public function to set item attribute filters on child doctype
function set_filters_on_child_table_fields(frm, fields) {
			fields.map(function (field) {
			frm.set_query(field[0], "order_details", function () {
				return {
					query: 'jewellery_erpnext.query.item_attribute_query',
					filters: { 'item_attribute': field[1] }
				};
			});
		});
};

//public function to set item attribute filters on parent doctype
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

//public function to set order type 
function set_order_type_from_design_by(frm) {
	if (cur_frm.doc.design_by == "Customer Design")
		cur_frm.doc.order_type = "Customer Order";
	else
		cur_frm.doc.order_type = "Stock Order";
	cur_frm.refresh_field("order_type");
};

//public function to show item attribute fields based on the selected subcategory
function show_attribute_fields_for_subcategory(frm, cdt, cdn, order_detail) {
	if (order_detail.subcategory) {
		frappe.model.with_doc("Attribute Value", order_detail.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", order_detail.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					$.each(subcategory_attribute_value.item_attributes, function (index, row) {
							if (row.in_cad == 1){

							}
								// show_field(frm, cdt, cdn, row.item_attribute);					
					});
				}
			}
		});
	}
};

//private function to hide all subcategory related fields in order details
function hide_all_subcategory_attribute_fields(frm, cdt, cdn) {	
	var subcategory_attribute_fields = ['Lock Type','Back Chain','Back Belt','Black Beed',
		'Back Side Size','Hinges','Back Belt Patti','Chain Type',
		'Vanki','Total Length','Number of Ant','Distance Between Kadi To Mugappu',
		'Space between Mugappu','Two in One']

	show_hide_fields(frm, cdt, cdn, subcategory_attribute_fields, 1);
};

//private function to show single child table field
function show_field(frm, cdt, cdn, field_name) {
	show_hide_field(frm, cdt, cdn, field_name, 0);
};

//private function to show or hide multiple child table fields
function show_hide_fields(frm, cdt, cdn, fields, hidden) {
	fields.map(function (field) {
		show_hide_field(frm, cdt, cdn, field, hidden);
	});
};

//private function to show or hide single child table fields
function show_hide_field(frm, cdt, cdn, field, hidden) {
	var field_name = field.toLowerCase().replace(/\s+/g, '_')
	var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
		
	if (df) {
		df.hidden = hidden;
	}
	frm.refresh_field("order_details");
};

//private function to show attribute value fields
function show_field_attribute(frm, cdt, cdn, field) {
	var subcategory_attribute_fields = ['Lock Type','Back Chain','Back Belt','Black Beed',
		'Back Side Size','Hinges','Back Belt Patti','Chain Type',
		'Vanki','Total Length','Number of Ant','Distance Between Kadi To Mugappu',
		'Space between Mugappu','Two in One']
	
	subcategory_attribute_fields.map(function (f) {
		var field_name = f.toLowerCase().replace(/\s+/g, '_')
		var field_name1 = field.toLowerCase().replace(/\s+/g, '_')
		if(field_name == field_name1){
			var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
			
			if (df) {
				df.hidden = 0; 
			}
			frm.refresh_field("order_details");

		}
	});

	var field_name = field.toLowerCase().replace(/\s+/g, '_')
	if(field_name) {
		var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
		if (df) {
			df.reqd = 1;
		}
	}
	frm.refresh_field("order_details");	 
};

//private function to hide attribute value fields -b
function hide_field_attribute(frm, cdt, cdn, field) {
	
	var field_name = field.toLowerCase().replace(/\s+/g, '_') 
	if(field_name) {
		var df = frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": field_name })[0];
		if (df) {
			df.reqd = 1;			
		}
	}
	frm.refresh_field("order_details");	 

};

// Auto calculate due days from delivery date    
function calculate_due_days(frm) {
	if (frm.doc.delivery_date && frm.doc.order_date) {
		const delivery = frappe.datetime.str_to_obj(frm.doc.delivery_date);
		const order = frappe.datetime.str_to_obj(frm.doc.order_date);

		// Get date-only values
		const delivery_date_only = new Date(delivery.getFullYear(), delivery.getMonth(), delivery.getDate());
		const order_date_only = new Date(order.getFullYear(), order.getMonth(), order.getDate());

		const ms_diff = delivery_date_only - order_date_only;
		console.log(ms_diff)
		const days = Math.ceil(ms_diff / (1000 * 60 * 60 * 24));  // ⬅️ Use ceil instead of round

		frm.set_value('due_days', days);
	}
};


function delivery_date(frm) {
	if (frm.doc.order_date && frm.doc.due_days != null) {
		const order_date = frappe.datetime.str_to_obj(frm.doc.order_date);

		// Add due_days to order_date
		let delivery = frappe.datetime.add_days(order_date, frm.doc.due_days);

		// Set time to 11:00:00 AM
		delivery = frappe.datetime.obj_to_str(new Date(
			new Date(delivery).setHours(11, 0, 0)
		));

		frm.set_value('delivery_date', delivery);
	}
};

function set_filter_for_salesman_name(frm) {
	frm.set_query("salesman_name", function () {
		return {
			"filters": { "parent_sales_person": "Sales Team" }
		};
	});
};

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.order_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("order_details");
};

function set_filter_for_sketch_design_n_serial(frm, fields) {
	fields.map(function (field) {
		
		frm.set_query(field, "order_details", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					"has_variants": 1,
					"variant_of": ["=", ""],
					"item_category": ["!=", ""],
					"order_form_type":"Sketch Order"
				}
			}
		});
		// frm.set_query(field[1], "order_details", function (doc, cdt, cdn) {
		// 	var d = locals[cdt][cdn]
		// 	if (d[field[0]]) {
		// 		return {
		// 			filters: {
		// 				"item_code": d[field[0]]
		// 			}
		// 		}
		// 	}
		// 	return {}
		// })
	});
};

function set_filter_for_design_n_serial(frm, fields) {
	fields.map(function (field) {
		
		frm.set_query(field, "order_details", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			if(d.is_finding_order==1){
				return {
					filters: {
						"variant_of": "F",
					}
				}
			}
			else{
				return {
					filters: {
						"is_design_code": 1,
						"is_stock_item":1,
					}
				}
			}
		});
		// frm.set_query(field[1], "order_details", function (doc, cdt, cdn) {
		// 	var d = locals[cdt][cdn]
		// 	if (d[field[0]]) {
		// 		return {
		// 			filters: {
		// 				"item_code": d[field[0]]
		// 			}
		// 		}
		// 	}
		// 	return {}
		// })
	});
};

function handle_design_id_change(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    // your existing code from design_id handler goes here
    if (d.design_id && (['Mod - Old Stylebio & Tag No', 'Sketch Design', 'As Per Design Type'].includes(d.design_type) || d.design_type == '')) {
        let method = d.design_type === 'Sketch Design'
            ? "gke_customization.gke_order_forms.doctype.order_form.order_form.get_sketh_details"
            : "gke_customization.gke_order_forms.doctype.order_form.order_form.get_bom_details";

        frappe.call({
            method: method,
            args: { design_id: d.design_id, doc: d },
            callback: function (r) {
                if (r.message) {
                    $.extend(d, r.message);
                    if (d.metal_type === "Silver") {
                        d.setting_type = "Open";
                        d.diamond_type = "AD";
                        d.metal_touch = "20KT";
                        d.metal_colour = "White";
                    }
                    frm.refresh_field('order_details');
                    frm.fields_dict['order_details'].grid.grid_rows_by_docname[d.name].refresh();
                }
            }
        });
    } else {
        // Clear fields if design_id is empty
        d.design_image = "";
        d.image = "";
        d.category = "";
        d.subcategory = "";
        d.setting_type = "";
        d.bom = "";
        frm.refresh_field('order_details');
        frm.fields_dict['order_details'].grid.grid_rows_by_docname[d.name].refresh();
    }
}

