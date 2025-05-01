// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt


frappe.ui.form.on('Order', {
	after_workflow_action(frm){
		if(frm.doc.workflow_state == "Designing - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}
		if(frm.doc.workflow_state == "Sent to QC - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "Creating BOM - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "Updating BOM - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
		if(frm.doc.workflow_state == "BOM QC - On-Hold"){
			frappe.prompt([
				{
					label: 'Reason For Hold',
					fieldname: 'update_reason',
					fieldtype: 'Select',
					options: ['', 'Shift is Over', 'Issue Other Urgent Work', 'Order Clarity Pending']					
				},
			], (values) => { 
				frm.refresh_field("update_reason");
				frm.set_value("update_reason", values.update_reason);
				frm.save();							
		
			});
		}		
	},
	refresh(frm) {		
		frm.refresh_field("update_reason");
	},
	onload(frm) {		
		show_attribute_fields_for_subcategory(frm)
		frm.get_field('designer_assignment').grid.cannot_add_rows = true;
	},
	subcategory(frm) {
		show_attribute_fields_for_subcategory(frm)
	},
	est_delivery_date(frm) {
		validate_dates(frm, frm.doc, "est_delivery_date")
		frm.set_value('est_due_days', frappe.datetime.get_day_diff(frm.doc.est_delivery_date, frm.doc.order_date));
	},
	// designer(frm){
	// 	// show_designer_dialog(frm);
	// },
	view_item(frm){
		if (frm.doc.__islocal) {
			frappe.throw("Please save document to edit the View Item.");
		}

		let order_form_data = [];
		const order_form_fields = [				
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden:1 },			
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
			title: __("Order View"),
			fields: [
				{
					label: "Order Form ID",
					fieldname: "cad_order_form",
					fieldtype: "Link",
					options: "Order Form",
					read_only: 1,
					default: frm.doc.cad_order_form,
				},
				{
					label: "Item Category",
					fieldname: "item_category",
					fieldtype: "Data", 
					in_list_view: 1,
					read_only: 1,
					default: frm.doc.category
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: "Item Code",
					fieldname: "item",
					// fieldtype: "Data",
					fieldtype: "Link",
					options: "Item",
					default: frm.doc.design_id,
					read_only: 1,
				},
				{
					label: "Item Subcategory",
					fieldname: "item_subcategory",
					fieldtype: "Data", 
					in_list_view: 1,
					read_only: 1,
					default: frm.doc.subcategory
					
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: "BOM",
					fieldname: "new_bom",
					fieldtype: "Link",
					options: "BOM",
					read_only: 1,
					default: frm.doc.bom,
				},	
				{
					label: "No. of Pcs",
					fieldname: "qty",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default: frm.doc.qty,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
				},	
				{
					fieldtype: "Section Break",
					// label: "Variants",
				},
				{
					label: "Order Form Detail",
					fieldtype: "Table",
					fieldname: "order_form_detail",
					cannot_add_rows: true,
					cannot_delete_rows: true,
					// in_place_edit: true,
					data: order_form_data,
					get_data: () => {
						return order_form_data;
					},
					fields: order_form_fields,
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
					default: frm.doc.setting_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Sub Setting Type1",
					fieldname: "sub_setting_type1",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default:  frm.doc.sub_setting_type1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Sub Setting Type2",
					fieldname: "sub_setting_type2",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					default:  frm.doc.sub_setting_type2,
					depends_on: ' eval:doc.setting_type == "Open" '
				},
				{
					label: "Feature",
					fieldname: "feature",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.feature,
					in_list_view: 1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "feature" })[0].depends_on
				},	
				{
					label: "Metal Target",
					fieldname: "metal_target",
					fieldtype: "Data",
					// read_only: 1,
					in_list_view: 1,
					default: frm.doc.metal_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "metal_target" })[0].depends_on					
				},
				{
					label: "Diamond Target",
					fieldname: "diamond_target",
					fieldtype: "Data",
					// read_only: 1,
					// in_list_view: 1,
					default: frm.doc.diamond_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
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
					default: frm.doc.metal_type,
				},					
				{
					label: "Metal Touch",
					fieldname: "metal_touch",
					read_only: 1,
					fieldtype: "Data",
					in_list_view: 1,
					default: frm.doc.metal_touch,	
				},	
				{
					label: "Metal Colour",
					fieldname: "metal_colour",
					fieldtype: "Data",
					// in_list_view: 1,
					default: frm.doc.metal_colour,
					// read_only: 1,
				},
				{
					label: "Gemstone Type",
					fieldname: "gemstone_type",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					default: frm.doc.gemstone_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Gemstone Quality",
					fieldname: "gemstone_quality",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					default: frm.doc.gemstone_quality,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: "Product Size",
					fieldname: "product_size",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.product_size,
					in_list_view: 1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "product_size" })[0].depends_on
				},
				{
					label: "Rhodium",
					fieldname: "rhodium",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.rhodium_,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},	
				{
					label: "Detachable",
					fieldname: "detachable",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.detachable,
					depends_on: ' eval:in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam","Cocktail Pendant", "Casual Pendant", "Fancy Pendant", "God Pendant","Kid Pendant", "Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Charm Necklace","Chik Chokar", "Choker Necklace", "Collar Necklace", "Fancy Necklace","Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain","Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace","Short Necklace", "Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu","Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya","Hair pin", "Jada", "Jada Billa", "Kids Hair Pin", "Maang Tikka","Matal-Sahara", "Matha Patti", "Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Chandeliers", "Cocktail Studs","Casual Earrings", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings","Fancy Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings", "Mismatch Earrings","Nakshi Jumkhi", "Threaders", "Nakshi Chandbalis", "Nakshi Earrings","Fancy Bracelet", "Nakshi Bracelet", "Chain Armlet", "Fancy Armlet","God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet","Vanki", "Nakshi Armlet", "Charms", "Sculpture", "Fancy Accessory", "Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "detachable" })[0].depends_on
				},
				{
					label: "Chain Type",
					fieldname: "chain_type",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.chain_type,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam","Kids Oddiyanam", "Cocktail Ring", "Casual Ring", "Fancy Ring","Mangalsutra Ring", "Adjustable/Bolo Ring", "Cocktail Pendant","Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant","Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram","Charm Necklace", "Chik Chokar", "Choker Necklace","Collar Necklace", "Fancy Necklace", "Haram Necklace","Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace","Nakshi Chain", "Nakshi Choker", "Nakshi Haram","Nakshi Necklace", "Padhakam Necklace", "Short Necklace","Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu","Nakshi Mugappu", "Fancy Mangalsutra", "God Mangalsutra","Mangalsutra Chains", "Mangalsutra Pendant", "Thali/Tanmaniya","Nakshi Thali/Tanmaniya", "Hair pin", "Jada", "Jada Billa","Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti","Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Dangler Earrings","Earcuff Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings","Mismatch Earrings", "Threaders", "Band Bracelet","Chain Bracelet", "Charm Bracelet", "Cuban Bracelet","Fancy Bracelet", "Flexible Bracelet", "God Bracelet","Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet","Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles","God Bangles", "Kada Bangles", "Pacheli Bangles","Chain Armlet", "Fancy Armlet", "God Vanki/Armlet","Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons","Charms", "Crown", "Cufflinks", "Goggles", "Money Accessory","Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_type" })[0].depends_on
				},
				{
					label: "Distance Between Kadi To Mugappu",
					fieldname: "distance_between_kadi_to_mugappu",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.distance_between_kadi_to_mugappu,
					depends_on: ' eval:in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "distance_between_kadi_to_mugappu" })[0].depends_on
				},
				{
					label: "Number of Ant",
					fieldname: "number_of_ant",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.number_of_ant,
					depends_on: '  eval: in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "number_of_ant" })[0].depends_on
				},
				{
					fieldtype: "Section Break",
				},
				{
					label: "Back Belt",
					fieldname: "back_belt",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.back_belt,
					// 	depends_on: 'eval:in_list(["Fancy Oddiyanam","God Oddiyanam","Kids Oddiyanam","Nakshi Oddiyanam","Oddiyanam"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt" })[0].depends_on
				},
				{
					label: "Back Chain",
					fieldname: "back_chain",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.back_chain,
					depends_on: 'eval: in_list(["Addigai Necklace", "Chain Armlet", "Chain Pendant", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Pendant", "Collar Necklace", "Casual Pendant", "Fancy Armlet", "Fancy Necklace", "Fancy Pendant", "God Pendant", "God Vanki", "God Vanki/Armlet", "Haram Necklace", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Necklace", "Kids Vanki", "Kids Vanki/Armlet", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Magdi Necklace", "Mala Necklace", "Nakshi Armlet", "Nakshi Chain", "Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Nakshi Pendant", "Padhakam Necklace", "Short Necklace", "Slider Pendant", "Station Necklace", "Tennis Necklace", "Tube Armlet", "V/U Vanki", "Vanki"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_chain" })[0].depends_on
				},
				{
					label: "two_in_one",
					fieldname: "two_in_one",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.two_in_one,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "Enamal",
					fieldname: "enamal",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.enamal,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "enamal" })[0].depends_on
				},
				{
					label: "Cap/Ganthan",
					fieldname: "capganthan",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.capganthan,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "Lock Type",
					fieldname: "lock_type",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.lock_type,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain", "Nakshi Oddiyanam","Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam", "Cocktail Pendant", "Casual Pendant","Fancy Pendant", "God Pendant", "Kid Pendant", "Locket Pendant", "Nakshi Pendant","Slider Pendant", "Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram","Charm Necklace", "Chik Chokar", "Choker Necklace", "Collar Necklace", "Fancy Necklace","Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain", "Nakshi Choker","Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace","Tennis Necklace", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya", "Hair pin", "Jada","Jada Billa", "Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada","Passa", "Nakshi Maang Tikka", "Nakshi Jada Billa", "Nakshi Jumkhi", "Threaders","Band Bracelet", "Chain Bracelet", "Charm Bracelet", "Cuban Bracelet", "Fancy Bracelet","Flexible Bracelet", "God Bracelet", "Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet","Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles", "God Bangles", "Golusu Bangles","Kada Bangles", "Kids Bangles", "Nakshi Bangles", "Pacheli Bangles", "Chain Armlet","Fancy Armlet", "God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons", "Charms", "Crown", "Cufflinks","Goggles", "Money Accessory", "Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "lock_type" })[0].depends_on
				},
				{
					fieldtype: "Column Break",
				},							
				{
					label: "Sizer Type",
					fieldname: "sizer_type",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.sizer_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "sizer_type" })[0].depends_on
					
				},
				{
					label: "Chain Length",
					fieldname: "chain_length",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.chain_length,
					depends_on: ' eval:in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam","Kids Oddiyanam", "Cocktail Ring", "Casual Ring", "Fancy Ring","Mangalsutra Ring", "Adjustable/Bolo Ring", "Cocktail Pendant","Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant", "Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Charm Necklace", "Chik Chokar", "Choker Necklace","Collar Necklace", "Fancy Necklace", "Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace","Nakshi Chain", "Nakshi Choker", "Nakshi Haram","Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Hair pin", "Jada", "Jada Billa","Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Dangler Earrings", "Earcuff Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings", "Mismatch Earrings", "Threaders", "Band Bracelet","Chain Bracelet", "Charm Bracelet", "Cuban Bracelet", "Fancy Bracelet", "Flexible Bracelet", "God Bracelet","Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet", "Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles","God Bangles", "Kada Bangles", "Pacheli Bangles", "Chain Armlet", "Fancy Armlet", "God Vanki/Armlet","Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki", "Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons","Charms", "Crown", "Cufflinks", "Goggles", "Money Accessory", "Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_length" })[0].depends_on
				},
				{
					label: "Space between Mugappu",
					fieldname: "space_between_mugappu",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.space_between_mugappu,
					depends_on: '  eval: in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu",], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "space_between_mugappu" })[0].depends_on
				},	 
				{
					label: "Back Belt Length",
					fieldname: "back_belt_length",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.back_belt_length,
					depends_on: " eval:doc.back_belt == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt_length" })[0].depends_on
				},
				{
					label: "Black Bead",
					fieldname: "black_bead",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.black_beed,
					depends_on: ' eval: in_list(["Mangalsutra Bracelet", "Mangalsutra Ring", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains", "Mangalsutra Pendant", "Nakshi Thali/Tanmaniya", "Thali/Tanmaniya"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_bead" })[0].depends_on
				},
				{
					label: "Chain Thickness",
					fieldname: "chain_thickness",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.chain_thickness,
					depends_on: ' eval:in_list(["Kodi Chain", "Snake Chain", "Runway", "Box Chain (Big)", "Box Chain (Small)", "Anchor Chain", "Black Bead Chain", "Shiva Chain", "Sadak Chain", "Highway Chain", "Mesh Chain", "Milan Chain", "Flat Ghop Chain", "Round Ghop Chain", "Nakshi Chain", "Fancy Chain"], doc.chain_type) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_thickness" })[0].depends_on
				},
				{
					fieldtype: "Column Break",
				},	
				
				{
					label: "Stone Changeable",
					fieldname: "stone_changeable",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.stone_changeable,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain", "Nakshi Oddiyanam","Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam", "Cocktail Ring", "Fancy Ring","Cocktail Pendant", "Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant","Locket Pendant", "Nakshi Pendant", "Slider Pendant", "Addigai Necklace", "Cocktail Chain","Cocktail Chain Haram", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Collar Necklace","Fancy Necklace", "Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain", "Nakshi Choker","Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace","Tennis Necklace", "Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu","Nakshi Mugappu", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya", "Hair pin", "Jada","Jada Billa", "Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada","Passa", "Nakshi Maang Tikka", "Nakshi Jada Billa", "Chandbali", "Chandeliers", "Cocktail Studs","Casual Earrings", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings", "Fancy Earrings","Front Back Earrings", "God Earrings", "Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings","Kids Earrings", "Mismatch Earrings", "Nakshi Jumkhi", "Threaders", "Nakshi Chandbalis","Nakshi Earrings", "Band Bracelet", "Chain Bracelet", "Charm Bracelet", "Cuban Bracelet","Fancy Bracelet", "Flexible Bracelet", "God Bracelet", "Kids Bracelet", "Mangalsutra Bracelet","Casual Bracelet", "Nakshi Bracelet", "Fancy Bangles", "God Bangles", "Golusu Bangles","Kada Bangles", "Kids Bangles", "Nakshi Bangles", "Pacheli Bangles", "Chain Armlet","Fancy Armlet", "God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Brooch", "Crown", "Cufflinks", "Goggles", "Sculpture","Fancy Accessory", "Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "stone_changeable" })[0].depends_on
				},
				{
					label: "Chain",
					fieldname: "chain",
					fieldtype: "Data",
					read_only: 1,
					default: frm.doc.chain,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain" })[0].depends_on
				},
				{
					label: "Count of Spiral Turns",
					fieldname: "count_of_spiral_turns",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.count_of_spiral_turns,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "count_of_spiral_turns" })[0].depends_on
				},
				{
					label: "Back Side Size",
					fieldname: "back_side_size",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.back_side_size,
					depends_on: 'eval: in_list(["Belt Oddiyanam", "Fancy Mugappu", "Nakshi Mugappu", "Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "Fancy Oddiyanam", "God Mugappu", "God Oddiyanam", "Kids Oddiyanam", "Nakshi Mugappu", "Nakshi Oddiyanam","Chain Oddiyanam"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_side_size" })[0].depends_on
				},
				{
					label: "Black Beed",
					fieldname: "black_beed",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.black_beed_line,
					depends_on: ' eval: in_list(["Mangalsutra Ring","Mangalsutra Bracelet"],doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_beed_line" })[0].depends_on
				},	
				{
					label: "Black Beed Line",
					fieldname: "black_beed_line",
					read_only: 1,
					fieldtype: "Data",
					default: frm.doc.black_beed_line,
					depends_on: " eval:doc.black_beed == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_beed_line" })[0].depends_on
				},	
					
							
			],
			// primary_action: function () {				
			// 	refresh_field("order_details");
			// },
			primary_action_label: (""),
			
		});
				
		if(dialog.get_value("item")) {
			// set item_code variants value in the given dialog box
			edit_item_documents(
				frm,
				dialog,
				dialog.get_value("item"),
				order_form_data 
			);
		};

		dialog.show();

		dialog.$wrapper.find(".modal-dialog").css("max-width", "90%");
		dialog.$wrapper.find('.modal-footer .btn-primary').hide();

		// hide update button
		if (cur_frm.doc.docstatus == 1) {
			dialog.$wrapper.find(".btn-modal-primary").remove();
		} 
	},
	navratna(frm){
		if (cur_frm.doc.navratna == 1){
		    frm.get_field('gemstone_detail').grid.cannot_delete_rows = true;

            // Hiding the grid remove icons
            $('*[data-fieldname="gemstone_detail"] .grid-remove-rows').hide();
            $('*[data-fieldname="gemstone_detail"] .grid-remove-all-rows').hide();
            $('*[data-fieldname="gemstone_detail"] .grid-delete-row').hide();
            
			const arr = ["Ruby","Pearl","Coral","Emerald","Yellow Shappire","Blue Shappire","Hessonite","Cat's Eye"]
			var arrayLength = arr.length;
			for (var i = 0; i < arrayLength; i++) {
				let row = frm.add_child('gemstone_detail', {
					gemstone_type: arr[i],
					navratna:'navratna'
				});
			}
			frm.refresh_field('gemstone_detail');
		}	
		if(cur_frm.doc.navratna == 0){
			const arr = ["Ruby","Pearl","Coral","Emerald","Yellow Shappire","Blue Shappire","Hessonite","Cat's Eye"]
			var tbl = cur_frm.doc.gemstone_detail || [];
			var i = tbl.length;
			while (i--)
			{	
				
				if(tbl[i].navratna == 'navratna')
				{
					cur_frm.get_field("gemstone_detail").grid.grid_rows[i].remove();
				}
			}
			cur_frm.refresh();
		}
	},
	
});


frappe.ui.form.on('Order BOM Metal Detail', {
	cad_weight(frm, cdt,cdn) {
		var row = locals[cdt][cdn]
		if (!row.cad_weight) return
		frappe.call({
			method: "gke_customization.gke_order_forms.doctype.order.order.calculate_item_wt_details",
			args: {
				doc: row,
				bom: frm.doc.master_bom,
				item: frm.doc.name
			},
			callback:function(r) {
				console.log(r.message)
				frappe.model.sync(r.message)
				frm.refresh()
			}
		})
	},
});

// bom table calculation
frappe.ui.form.on("Order BOM Metal Detail", {
	cad_weight: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.cad_weight && d.cad_to_finish_ratio) {
			frappe.model.set_value(
				d.doctype,
				d.name,
				"quantity",
				flt((d.cad_weight * d.cad_to_finish_ratio) / 100)
			);
		}
		
		if (!d.cad_weight) return
		frappe.call({
			method: "gke_customization.gke_order_forms.doctype.order.order.calculate_item_wt_details",
			args: {
				doc: d,
				bom: frm.doc.master_bom,
				item: frm.doc.name
			},
			callback:function(r) {
				frappe.model.sync(r.message)
				frm.refresh()
			}
		})
	},
	cad_to_finish_ratio: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.cad_weight && d.cad_to_finish_ratio) {
			frappe.model.set_value(
				d.doctype,
				d.name,
				"quantity",
				flt((d.cad_weight * d.cad_to_finish_ratio) / 100)
			);
		}
	},

	quantity: function (frm) {
		calculate_total(frm);
	},
	finish_product_weight:function(frm,cdt,cdn){
		let d = locals[cdt][cdn];
		d.finish_loss_grams = d.casting_weight - d.finish_product_weight
		d.finish_loss_percentage = ((d.finish_product_weight - d.casting_weight)/d.casting_weight)*100
		frm.refresh_field("metal_detail")
	}
});

frappe.ui.form.on("Order BOM Diamond Detail", {
	pcs: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		d.quantity = d.pcs*d.weight_per_pcs
		frm.refresh_field("diamond_detail")
	},
	size_in_mm: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(d.stone_shape=='Round'){
			let size = d.size_in_mm.replace(" MM","")
			frappe.db.get_value("Attribute Value", {"diameter":size}, ["name","sieve_size_range","weight_in_cts"]).then((r) => {
						frappe.model.set_value(d.doctype, d.name, "diamond_sieve_size", r.message.name);
						frappe.model.set_value(d.doctype, d.name, "sieve_size_range", r.message.sieve_size_range);
						frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", r.message.weight_in_cts);
						
					});
		}
	},
});

frappe.ui.form.on("Order BOM Gemstone Detail", {
	quantity: function (frm) {
		calculate_total(frm);
	},
	pcs: function (frm) {
		calculate_total(frm);
	},
});

frappe.ui.form.on("Order BOM Finding Detail", {
	quantity: function (frm) {
		calculate_total(frm);
	},
});

let edit_item_documents = (frm,dialog,design_id,order_form_data) => {
	var doc = frappe.get_doc("Item", design_id);
	
	if (!doc) {
		frappe.call({
			method: "frappe.client.get",
			freeze: true,
			args: {
				doctype: "Item",
				name: design_id,
			},
			callback(r) {
				if (r.message) {
					// console.log(r.message);
					set_edit_order_form_detail(
						frm,
						r.message,
						dialog,
						order_form_data
					);
				}
			},
		});
	} else {
		set_edit_order_form_detail(frm,doc,dialog,order_form_data);
	}
};

let set_edit_order_form_detail = (frm,item_doc,dialog) => {
	// clearing all tables
	dialog.fields_dict.order_form_detail.df.data = [];
	item_attributes = item_doc.attributes
	
	item_attributes.forEach(attr => {
		const fieldname = attr.attribute.toLowerCase().replace(/\s+/g, '_');
		const order_value = frm.doc[fieldname] || "";
		// console.log(item_doc , fieldname, order_value);
		
		dialog.fields_dict.order_form_detail.df.data.push({
			attribute: attr.attribute,
			attribute_value: attr.attribute_value,
			new_attribute: order_value || ""
		});
	});
	dialog.fields_dict.order_form_detail.grid.refresh();
	
	// $.each(item_doc.attributes, function (index, d) {
	// 	var field_name = d.attribute.toLowerCase().replace(/\s+/g, '_');
	// 	dialog.set_df_property(field_name, "hidden", 1);
	// });
};

function show_designer_dialog(frm){
	frappe.prompt([
		{
			label: 'Designer',
			fieldname: 'designer',
			fieldtype: 'Link',
			options: 'Employee',
			get_query(){
				return {
					"filters": [                                    
						["Employee", "designation", "=", "Computer Aided Designing - GEPL"],    
						["Employee", "designation", "=", "Executive"],
					]
				}
			}
		},
	], (values) => {
		let designer_exists = frm.doc.designer_assignment.some(row => row.designer === values.designer);
		
		if (designer_exists) {
            frappe.msgprint(__('Designer already assigned.'));
		}
		else{
			let v = {designer: values.designer,};		
			let new_row = frm.add_child("designer_assignment");
			$.extend(new_row, v);
			frm.refresh_field("designer_assignment");
			frm.set_df_property("designer_assignment", "read_only", 1);

			if (frm.doc.designer_assignment.length >1) {
				frm.set_value("workflow_state","Assigned")
				frm.save()
			}
		}

	});
}

function update_fields_in_child_table(designer) {
	$.each(frm.doc.designer_assignment || [], function (i, d) {
		d["designer"] = designer;
	});
	refresh_field("designer_assignment");
};

function show_attribute_fields_for_subcategory(frm) {
	if (frm.doc.subcategory) {
		frappe.model.with_doc("Attribute Value", frm.doc.subcategory, function (r) {
			var subcategory_attribute_value = frappe.model.get_doc("Attribute Value", frm.doc.subcategory);
			if (subcategory_attribute_value.is_subcategory == 1) {
				if (subcategory_attribute_value.item_attributes) {
					let fields = subcategory_attribute_value.item_attributes.map((r) => { if (r.in_cad == 1) return r.item_attribute.toLowerCase().replace(/\s+/g, '_') })
					frm.toggle_display(fields, 1)
					frm.refresh_fields()
				}
			}
		});
	}
}

function hide_all_subcategory_attribute_fields(frm) {
	var fields = [
		"length", "height", "stone_type",
		"gemstone_type", "gemstone_quality", "stone_changeable",
		"changeable", "hinges", "back_belt", "vanki_type", "black_beed",
		"black_beed_line", "screw_type", "hook_type", "lock_type", "2_in_1",
		"kadi_type", "chain", "chain_type", "customer_chain", "chain_length",
		"total_length", "chain_weight", "detachable", "back_chain", "back_chain_size",
		"back_side_size", "chain_thickness", "total_mugappu", "kadi_to_mugappu",
		"space_between_mugappu", "nakshi", "nakshi_from", "customer_sample",
		"certificate_place", "breadth", "width", "back_belt", "back_belt_length" ];
		frm.toggle_display(fields, 0)
		frm.refresh_fields()
}

function validate_dates(frm, doc, dateField) {
    let order_date = frm.doc.order_date
    if (doc[dateField] < order_date) {
        frappe.model.set_value(doc.doctype, doc.name, dateField, frappe.datetime.add_days(order_date,1))
    }
}



function calculate_total(frm) {
	let total_metal_weight = 0;
	let diamond_weight = 0;
	let total_gemstone_weight = 0;
	let finding_weight = 0;
	let total_diamond_pcs = 0;
	let total_gemstone_pcs = 0;

	if (frm.doc.metal_detail) {
		frm.doc.metal_detail.forEach(function (d) {
			total_metal_weight += d.quantity;
		});
	}
	if (frm.doc.diamond_detail) {
		frm.doc.diamond_detail.forEach(function (d) {
			diamond_weight += d.quantity;
			total_diamond_pcs += d.pcs;
		});
	}
	if (frm.doc.gemstone_detail) {
		frm.doc.gemstone_detail.forEach(function (d) {
			total_gemstone_weight += d.quantity;
			total_gemstone_pcs += d.pcs;
		});
	}
	if (frm.doc.finding_detail) {
		frm.doc.finding_detail.forEach(function (d) {
			if (d.finding_category != "Chains") {
				finding_weight += d.quantity;
			}
		});
	}
	frm.set_value("total_metal_weight", total_metal_weight);

	frm.set_value("total_diamond_pcs", total_diamond_pcs);
	frm.set_value("diamond_weight", diamond_weight);
	frm.set_value("total_diamond_weight", diamond_weight);

	frm.set_value("total_gemstone_pcs", total_gemstone_pcs);
	frm.set_value("gemstone_weight", total_gemstone_weight);
	frm.set_value("total_gemstone_weight", total_gemstone_weight);

	frm.set_value("finding_weight", finding_weight);
	frm.set_value("metal_and_finding_weight", frm.doc.total_metal_weight + frm.doc.finding_weight);
	if (frm.doc.metal_and_finding_weight) {
		frm.set_value(
			"gold_to_diamond_ratio",
			frm.doc.metal_and_finding_weight / frm.doc.diamond_weight
		);
	}
	if (frm.doc.total_diamond_pcs) {
		frm.set_value("diamond_ratio", frm.doc.diamond_weight / frm.doc.total_diamond_pcs);
	}
}