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
	designer(frm){
		// show_designer_dialog(frm);
	},
	view_item(frm){
		if (frm.doc.__islocal) {
			frappe.throw("Please save document to edit the View Item.");
		}

		let order_form_data = [];

		const order_form_fields = [				
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden:1 },			
			
				{
					label: "Item Category",
					fieldname: "item_category",
					fieldtype: "Data",
					fieldtype: "Link",
					options: "Attribute Value",
					in_list_view: 1,
					read_only: 1,
					columns: 1,
				},
				{
					label: "Setting Type",
					fieldname: "setting_type",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					columns: 1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Metal Type",
					fieldname: "metal_type",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					columns: 1,					
					// depends_on: ' eval: in_list(["Addigai Necklace", "Anklet", "Ball Mugappu", "Band Bracelet", "Belt", "Buttons", "Chain Armlet", "Chain Bracelet", "Chandbali", "Chandeliers", "Charm Bracelet", "Charm Necklace", "Charms", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Mugappu", "Cocktail Studs", "Collar Necklace", "Crown", "Cuban Bracelet", "Cuban Chain", "Cufflinks", "Dangler Earrings", "Drop Earrings", "Drop Nose Pin", "Earcuff Earrings", "Eternity Bangles", "Fancy Accessory", "Fancy Armlet", "Fancy Bangles", "Fancy Box", "Fancy Bracelet", "Fancy Earrings", "Fancy Mangalsutra", "Fancy Mugappu", "Fancy Necklace", "Fancy Nose Pin", "Fancy Oddiyanam", "Fancy Ring", "Flexible Bracelet", "Front Back Earrings", "God Bangles", "God Bracelet", "God Earrings", "God Mangalsutra", "God Mugappu", "God Oddiyanam", "God Pendant", "God Vanki", "God Vanki/Armlet", "Goggles", "Golusu Bangles", "Hair Pin", "Haram Necklace", "Hoops & Huggies Earrings", "J Nose Pin", "Jada", "Jada Billa", "Jumkhi", "Jumpring Earrings", "Kada Bangles", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Bangles", "Kids Bracelet", "Kids Earrings", "Kids Hair Pin", "Kids Necklace", "Kids Oddiyanam", "Kids Ring", "Kids Vanki", "Kids Vanki/Armlet", "Kuppu Earrings", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Maang Tikka", "Magdi Necklace", "Mala Necklace", "Mangalsutra Bracelet", "Mangalsutra Chains", "Mangalsutra Pendant", "Mangalsutra Ring", "Matal-Sahara", "Matha Patti", "Mismatch Earrings", "Money Accessory", "Nakshi Armlet", "Nakshi Bangles", "Nakshi Bracelet", "Nakshi Chain", "Nakshi Chandbalis", "Nakshi Choker", "Nakshi Earrings", "Nakshi Haram", "Nakshi Jada", "Nakshi Jada Billa", "Nakshi Jumkhi", "Nakshi Maang Tikka", "Nakshi Mugappu", "Nakshi Necklace", "Nakshi Oddiyanam", "Nakshi Pendant", "Nakshi Ring", "Nakshi Thali/Tanmaniya", "O Nose Pin", "Oddiyanam", "Oval Bracelet", "Pacheli Bangles", "Padhakam Necklace", "Passa", "Pen", "Round Bangles", "Sculpture", "Short Necklace", "Slider Pendant", "Solitaire Bangles", "Solitaire Bracelet", "Solitaire Earrings", "Solitaire Mangalsutra", "Solitaire Mugappu", "Solitaire Necklace", "Solitaire Pendant", "Spiral Mugappu", "Spiral Ring", "Station Necklace", "Stud Nose Pin", "Tennis Bracelet", "Tennis Necklace", "Thali/Tanmaniya", "Threaders", "Tie Clip", "Tube Armlet", "V/U Vanki", "Vanki", "Watch Charms", "Watches"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "lock_type" })[0].depends_on
				},
				{
					label: "Diamond Target",
					fieldname: "diamond_target",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					// default: row.diamond_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
				},
				{
					label: "Gemstone Type",
					fieldname: "gemstone_type",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					// default: row.gemstone_type1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "gemstone_type1" })[0].depends_on
				},
				{
					label: "Rhodium",
					fieldname: "rhodium",
					fieldtype: "Data",
					read_only: 1,
					// default: row.rhodium,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},	
				{
					label: "Detachable",
					fieldname: "detachable",
					fieldtype: "Data",
					read_only: 1,
					// default: row.detachable,
					depends_on: ' eval:in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam","Cocktail Pendant", "Casual Pendant", "Fancy Pendant", "God Pendant","Kid Pendant", "Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Charm Necklace","Chik Chokar", "Choker Necklace", "Collar Necklace", "Fancy Necklace","Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain","Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace","Short Necklace", "Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu","Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya","Hair pin", "Jada", "Jada Billa", "Kids Hair Pin", "Maang Tikka","Matal-Sahara", "Matha Patti", "Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Chandeliers", "Cocktail Studs","Casual Earrings", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings","Fancy Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings", "Mismatch Earrings","Nakshi Jumkhi", "Threaders", "Nakshi Chandbalis", "Nakshi Earrings","Fancy Bracelet", "Nakshi Bracelet", "Chain Armlet", "Fancy Armlet","God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet","Vanki", "Nakshi Armlet", "Charms", "Sculpture", "Fancy Accessory", "Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "detachable" })[0].depends_on
				},
				{
					label: "Chain Type",
					fieldname: "chain_type",
					fieldtype: "Data",
					read_only: 1,
					// default: row.chain_type,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam","Kids Oddiyanam", "Cocktail Ring", "Casual Ring", "Fancy Ring","Mangalsutra Ring", "Adjustable/Bolo Ring", "Cocktail Pendant","Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant","Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram","Charm Necklace", "Chik Chokar", "Choker Necklace","Collar Necklace", "Fancy Necklace", "Haram Necklace","Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace","Nakshi Chain", "Nakshi Choker", "Nakshi Haram","Nakshi Necklace", "Padhakam Necklace", "Short Necklace","Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu","Nakshi Mugappu", "Fancy Mangalsutra", "God Mangalsutra","Mangalsutra Chains", "Mangalsutra Pendant", "Thali/Tanmaniya","Nakshi Thali/Tanmaniya", "Hair pin", "Jada", "Jada Billa","Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti","Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Dangler Earrings","Earcuff Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings","Mismatch Earrings", "Threaders", "Band Bracelet","Chain Bracelet", "Charm Bracelet", "Cuban Bracelet","Fancy Bracelet", "Flexible Bracelet", "God Bracelet","Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet","Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles","God Bangles", "Kada Bangles", "Pacheli Bangles","Chain Armlet", "Fancy Armlet", "God Vanki/Armlet","Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons","Charms", "Crown", "Cufflinks", "Goggles", "Money Accessory","Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_type" })[0].depends_on
				},
				{
					label: "Distance Between Kadi To Mugappu",
					fieldname: "distance_between_kadi_to_mugappu",
					read_only: 1,
					fieldtype: "Data",
					// default: row.distance_between_kadi_to_mugappu,
					depends_on: ' eval:in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "distance_between_kadi_to_mugappu" })[0].depends_on
				},
				{
					label: "Number of Ant",
					fieldname: "number_of_ant",
					read_only: 1,
					fieldtype: "Data",
					// default: row.number_of_ant,
					depends_on: '  eval: in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "number_of_ant" })[0].depends_on
				},
				{
					label: "Back Belt",
					fieldname: "back_belt",
					read_only: 1,
					fieldtype: "Data",
					// default: row.back_belt,
					// 	depends_on: 'eval:in_list(["Fancy Oddiyanam","God Oddiyanam","Kids Oddiyanam","Nakshi Oddiyanam","Oddiyanam"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt" })[0].depends_on
				},
				{
					label: "Back Chain",
					fieldname: "back_chain",
					fieldtype: "Data",
					read_only: 1,
					// default: row.back_chain,
					depends_on: 'eval: in_list(["Addigai Necklace", "Chain Armlet", "Chain Pendant", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Cocktail Pendant", "Collar Necklace", "Casual Pendant", "Fancy Armlet", "Fancy Necklace", "Fancy Pendant", "God Pendant", "God Vanki", "God Vanki/Armlet", "Haram Necklace", "Kantha/Hasli Necklace", "Kid Pendant", "Kids Necklace", "Kids Vanki", "Kids Vanki/Armlet", "Lariat Necklace", "Layered Necklace", "Locket Pendant", "Magdi Necklace", "Mala Necklace", "Nakshi Armlet", "Nakshi Chain", "Nakshi Choker", "Nakshi Haram", "Nakshi Necklace", "Nakshi Pendant", "Padhakam Necklace", "Short Necklace", "Slider Pendant", "Station Necklace", "Tennis Necklace", "Tube Armlet", "V/U Vanki", "Vanki"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_chain" })[0].depends_on
				},
				{
					label: "two_in_one",
					fieldname: "two_in_one",
					read_only: 1,
					fieldtype: "Data",
					// default: row.two_in_one,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
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
					in_list_view: 1,
					columns: 1,
				},
				{
					label: "Sub Setting Type1",
					fieldname: "sub_setting_type1",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					columns: 1,
					// default: row.sub_setting_type1,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Metal Colour",
					fieldname: "metal_colour",
					read_only: 1,
					fieldtype: "Data",
					// in_list_view: 1,
					// default: row.metal_colour,
					// depends_on: ' eval: in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Casual Mugappu", "Eternity Bangles", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
				},
				{
					label: "Metal Target",
					fieldname: "metal_target",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					// default: row.metal_target,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "metal_target" })[0].depends_on					
				},
				{
					label: "Gemstone Quality",
					fieldname: "gemstone_quality",
					fieldtype: "Data",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					// default: row.gemstone_quality,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "rhodium" })[0].depends_on
				},
				{
					label: "Enamal",
					fieldname: "enamal",
					fieldtype: "Data",
					read_only: 1,
					// default: row.enamal,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "enamal" })[0].depends_on
				},
				{
					label: "Lock Type",
					fieldname: "lock_type",
					fieldtype: "Data",
					read_only: 1,
					// default: row.lock_type,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain", "Nakshi Oddiyanam","Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam", "Cocktail Pendant", "Casual Pendant","Fancy Pendant", "God Pendant", "Kid Pendant", "Locket Pendant", "Nakshi Pendant","Slider Pendant", "Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram","Charm Necklace", "Chik Chokar", "Choker Necklace", "Collar Necklace", "Fancy Necklace","Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain", "Nakshi Choker","Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace","Tennis Necklace", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya", "Hair pin", "Jada","Jada Billa", "Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada","Passa", "Nakshi Maang Tikka", "Nakshi Jada Billa", "Nakshi Jumkhi", "Threaders","Band Bracelet", "Chain Bracelet", "Charm Bracelet", "Cuban Bracelet", "Fancy Bracelet","Flexible Bracelet", "God Bracelet", "Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet","Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles", "God Bangles", "Golusu Bangles","Kada Bangles", "Kids Bangles", "Nakshi Bangles", "Pacheli Bangles", "Chain Armlet","Fancy Armlet", "God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons", "Charms", "Crown", "Cufflinks","Goggles", "Money Accessory", "Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "lock_type" })[0].depends_on
				},
				{
					label: "Chain Length",
					fieldname: "chain_length",
					fieldtype: "Data",
					read_only: 1,
					// default: row.chain_length,
					depends_on: ' eval:in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain","Nakshi Oddiyanam", "Fancy Oddiyanam", "God Oddiyanam","Kids Oddiyanam", "Cocktail Ring", "Casual Ring", "Fancy Ring","Mangalsutra Ring", "Adjustable/Bolo Ring", "Cocktail Pendant","Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant", "Locket Pendant", "Nakshi Pendant", "Slider Pendant","Addigai Necklace", "Cocktail Chain", "Cocktail Chain Haram", "Charm Necklace", "Chik Chokar", "Choker Necklace","Collar Necklace", "Fancy Necklace", "Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace","Nakshi Chain", "Nakshi Choker", "Nakshi Haram","Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace", "Tennis Necklace", "Cocktail Mugappu","Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Hair pin", "Jada", "Jada Billa","Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada", "Passa", "Nakshi Maang Tikka","Nakshi Jada Billa", "Chandbali", "Dangler Earrings", "Earcuff Earrings", "Front Back Earrings", "God Earrings","Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings", "Mismatch Earrings", "Threaders", "Band Bracelet","Chain Bracelet", "Charm Bracelet", "Cuban Bracelet", "Fancy Bracelet", "Flexible Bracelet", "God Bracelet","Kids Bracelet", "Mangalsutra Bracelet", "Casual Bracelet", "Tennis Bracelet", "Nakshi Bracelet", "Fancy Bangles","God Bangles", "Kada Bangles", "Pacheli Bangles", "Chain Armlet", "Fancy Armlet", "God Vanki/Armlet","Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki", "Nakshi Armlet", "Anklet", "Belt", "Brooch", "Buttons","Charms", "Crown", "Cufflinks", "Goggles", "Money Accessory", "Pen", "Sculpture", "Tie Clip", "Watches", "Fancy Accessory","Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_length" })[0].depends_on
				},
				{
					label: "Space between Mugappu",
					fieldname: "space_between_mugappu",
					read_only: 1,
					fieldtype: "Data",
					// default: row.space_between_mugappu,
					depends_on: '  eval: in_list(["Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu",], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "space_between_mugappu" })[0].depends_on
				},	
				// {
				// 	label: "Charm",
				// 	fieldname: "charm",
				// 	read_only: 1,
				// 	fieldtype: "Data",
				// 	// default: row.charm,					
				// 	// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				// },
				{
					label: "Back Belt Length",
					fieldname: "back_belt_length",
					read_only: 1,
					fieldtype: "Data",
					// default: row.back_belt_length,
					depends_on: " eval:doc.back_belt == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_belt_length" })[0].depends_on
				},
				{
					label: "Black Bead",
					fieldname: "black_bead",
					read_only: 1,
					fieldtype: "Data",
					// default: row.black_beed,
					depends_on: ' eval: in_list(["Mangalsutra Bracelet", "Mangalsutra Ring", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains", "Mangalsutra Pendant", "Nakshi Thali/Tanmaniya", "Thali/Tanmaniya"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_bead" })[0].depends_on
				},
				{
					label: "Chain Thickness",
					fieldname: "chain_thickness",
					read_only: 1,
					fieldtype: "Data",
					// default: row.chain_thickness,
					depends_on: ' eval:in_list(["Kodi Chain", "Snake Chain", "Runway", "Box Chain (Big)", "Box Chain (Small)", "Anchor Chain", "Black Bead Chain", "Shiva Chain", "Sadak Chain", "Highway Chain", "Mesh Chain", "Milan Chain", "Flat Ghop Chain", "Round Ghop Chain", "Nakshi Chain", "Fancy Chain"], doc.chain_type) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain_thickness" })[0].depends_on
				},

				{
					fieldtype: "Column Break",
				},
				
				{
					label: "No. of Pcs",
					fieldname: "qty",
					fieldtype: "Data",
					read_only: 1, 
					in_list_view: 1,
					columns: 1,
					// default: row.qty,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "diamond_target" })[0].depends_on					
				},	
				{
					label: "Sub Setting Type2",
					fieldname: "sub_setting_type2",
					fieldtype: "Data",
					read_only: 1, 
					// in_list_view: 1,
					// default: row.sub_setting_type2,
					depends_on: ' eval:doc.setting_type == "Open" '
				},
				{
					label: "Metal Touch",
					fieldname: "metal_touch",
					read_only: 1,
					fieldtype: "Data",
					in_list_view: 1,
					columns: 1,
					// default: row.metal_colour,
					// depends_on: ' eval: in_list(["Ant Mugappu", "Ball Mugappu", "Cocktail Mugappu", "Casual Mugappu", "Eternity Bangles", "Fancy Mugappu", "God Mugappu", "Nakshi Mugappu", "Solitaire Mugappu", "Spiral Mugappu"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "number_of_ant" })[0].depends_on
				},
				{
					label: "Feature",
					fieldname: "feature",
					fieldtype: "Data",
					read_only: 1,
					// default: row.feature,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "feature" })[0].depends_on
				},		
				{
					label: "Product Size",
					fieldname: "product_size",
					read_only: 1,
					fieldtype: "Data",
					// default: row.product_size,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "product_size" })[0].depends_on
				},	
				{
					label: "Stone Changeable",
					fieldname: "stone_changeable",
					fieldtype: "Data",
					read_only: 1,
					// default: row.stone_changeable,
					depends_on: ' eval: in_list(["Belt Armlet", "Belt Oddiyanam", "Chain Oddiyanam", "Cuban Chain", "Nakshi Oddiyanam","Fancy Oddiyanam", "God Oddiyanam", "Kids Oddiyanam", "Cocktail Ring", "Fancy Ring","Cocktail Pendant", "Casual Pendant", "Fancy Pendant", "God Pendant", "Kid Pendant","Locket Pendant", "Nakshi Pendant", "Slider Pendant", "Addigai Necklace", "Cocktail Chain","Cocktail Chain Haram", "Charm Necklace", "Chik Chokar", "Choker Necklace", "Collar Necklace","Fancy Necklace", "Haram Necklace", "Kantha/Hasli Necklace", "Kids Necklace", "Lariat Necklace","Layered Necklace", "Magdi Necklace", "Mala Necklace", "Nakshi Chain", "Nakshi Choker","Nakshi Haram", "Nakshi Necklace", "Padhakam Necklace", "Short Necklace", "Station Necklace","Tennis Necklace", "Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "God Mugappu","Nakshi Mugappu", "Fancy Mangalsutra", "God Mangalsutra", "Mangalsutra Chains","Mangalsutra Pendant", "Thali/Tanmaniya", "Nakshi Thali/Tanmaniya", "Hair pin", "Jada","Jada Billa", "Kids Hair Pin", "Maang Tikka", "Matal-Sahara", "Matha Patti", "Nakshi Jada","Passa", "Nakshi Maang Tikka", "Nakshi Jada Billa", "Chandbali", "Chandeliers", "Cocktail Studs","Casual Earrings", "Dangler Earrings", "Drop Earrings", "Earcuff Earrings", "Fancy Earrings","Front Back Earrings", "God Earrings", "Hoops & Huggies Earrings", "Jumkhi", "Jumpring Earrings","Kids Earrings", "Mismatch Earrings", "Nakshi Jumkhi", "Threaders", "Nakshi Chandbalis","Nakshi Earrings", "Band Bracelet", "Chain Bracelet", "Charm Bracelet", "Cuban Bracelet","Fancy Bracelet", "Flexible Bracelet", "God Bracelet", "Kids Bracelet", "Mangalsutra Bracelet","Casual Bracelet", "Nakshi Bracelet", "Fancy Bangles", "God Bangles", "Golusu Bangles","Kada Bangles", "Kids Bangles", "Nakshi Bangles", "Pacheli Bangles", "Chain Armlet","Fancy Armlet", "God Vanki/Armlet", "Kids Vanki/Armlet", "Nakshi Vanki", "Tube Armlet", "Vanki","Nakshi Armlet", "Anklet", "Brooch", "Crown", "Cufflinks", "Goggles", "Sculpture","Fancy Accessory", "Fancy Box"], doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "stone_changeable" })[0].depends_on
				},
				{
					label: "Sizer Type",
					fieldname: "sizer_type",
					fieldtype: "Data",
					read_only: 1,
					// default: row.sizer_type,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "sizer_type" })[0].depends_on
					
				},
				{
					label: "Chain",
					fieldname: "chain",
					fieldtype: "Data",
					read_only: 1,
					// default: row.chain,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "chain" })[0].depends_on
				},
				{
					label: "Count of Spiral Turns",
					fieldname: "count_of_spiral_turns",
					read_only: 1,
					fieldtype: "Data",
					// default: row.count_of_spiral_turns,
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "count_of_spiral_turns" })[0].depends_on
				},
				{
					label: "Cap/Ganthan",
					fieldname: "capganthan",
					read_only: 1,
					fieldtype: "Data",
					// default: row.capganthan,					
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "cap_ganthan" })[0].depends_on
				},
				{
					label: "Back Side Size",
					fieldname: "back_side_size",
					read_only: 1,
					fieldtype: "Data",
					// default: row.back_side_size,
					depends_on: 'eval: in_list(["Belt Oddiyanam", "Fancy Mugappu", "Nakshi Mugappu", "Cocktail Mugappu", "Casual Mugappu", "Fancy Mugappu", "Fancy Oddiyanam", "God Mugappu", "God Oddiyanam", "Kids Oddiyanam", "Nakshi Mugappu", "Nakshi Oddiyanam","Chain Oddiyanam"], doc.subcategory)'
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "back_side_size" })[0].depends_on
				},
				{
					label: "Black Beed",
					fieldname: "black_beed",
					read_only: 1,
					fieldtype: "Data",
					// default: row.black_beed_line,
					depends_on: ' eval: in_list(["Mangalsutra Ring","Mangalsutra Bracelet"],doc.subcategory) '
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_beed_line" })[0].depends_on
				},	
				{
					label: "Black Beed Line",
					fieldname: "black_beed_line",
					read_only: 1,
					fieldtype: "Data",
					// default: row.black_beed_line,
					depends_on: " eval:doc.black_beed == 'Yes' "
					// depends_on: frappe.utils.filter_dict(cur_frm.fields_dict["order_details"].grid.grid_rows_by_docname[cdn].docfields, { "fieldname": "black_beed_line" })[0].depends_on
				},	
			]

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
					fieldtype: "Column Break",
				},
				{
					label: "Item Code",
					fieldname: "item",
					// fieldtype: "Data",
					fieldtype: "Link",
					options: "Item",
					default: frm.doc.item,
					read_only: 1,
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
					default: frm.doc.new_bom,
				},				
				{
					fieldtype: "Section Break",
					// label: "Variants",
				},
				{
					label: "Order Form Detail",
					fieldname: "order_form_detail",
					fieldtype: "Table",
					cannot_add_rows: true,
					cannot_delete_rows: true,
					// in_place_edit: true,
					data: order_form_data,
					get_data: () => {
						return order_form_data;
					},
					fields: order_form_fields,
				},
							
			],
			// primary_action: function () {				
			// 	refresh_field("order_details");
			// },
			primary_action_label: (""),
			
		});
				
		if(dialog.get_value("cad_order_form")) {
			// set item_code variants value in the given dialog box
			edit_item_documents(
				frm,
				dialog,
				dialog.get_value("cad_order_form"),
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
	}
	
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



let edit_item_documents = (frm,dialog,cad_order_form,order_form_data) => {
	var doc = frappe.get_doc("Order Form", cad_order_form);
	console.log(doc);
	if (!doc) {
		frappe.call({
			method: "frappe.client.get",
			freeze: true,
			args: {
				doctype: "Order Form",
				name: cad_order_form,
			},
			callback(r) {
				if (r.message) {
					console.log(r.message);
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


let set_edit_order_form_detail = (frm,doc,dialog) => {
	// clearing all tables
	dialog.fields_dict.order_form_detail.df.data = [];
	dialog.fields_dict.order_form_detail.grid.refresh();
	
	$.each(doc.order_details, function (index, d) {
				
		if(d.name == frm.doc.cad_order_form_detail){
			dialog.fields_dict.order_form_detail.df.data.push({
				docname: d.name,
				item_category: d.category,
				item_subcategory: d.subcategory ,
				setting_type: d.setting_type ,
				sub_setting_type1: d.sub_setting_type1 ,
				sub_setting_type2: d.sub_setting_type2 ,
				metal_type: d.metal_type ,
				metal_colour: d.metal_colour ,
				qty: d.qty ,
				diamond_target: d.diamond_target ,
				gemstone_type: d.gemstone_type ,
				rhodium: d.rhodium ,
				gemstone_quality: d.gemstone_quality ,
				feature: d.feature ,
				lock_type: d.lock_type ,
				chain: d.chain ,
				distance_between_kadi_to_mugappu: d.distance_between_kadi_to_mugappu ,
				number_of_ant: d.number_of_ant ,
				back_belt: d.back_belt ,
				metal_target: d.metal_target ,
				sizer_type: d.sizer_type ,
				detachable: d.detachable ,
				chain_type: d.chain_type ,
				back_chain: d.back_chain ,
				space_between_mugappu: d.space_between_mugappu ,
				black_bead: d.black_bead ,
				black_beed_line: d.black_beed_line ,
				back_belt_length: d.back_belt_length ,
				enamal: d.enamal ,
				stone_changeable: d.stone_changeable ,
				chain_length: d.chain_length ,
				product_size: d.product_size ,
				count_of_spiral_turns: d.count_of_spiral_turns ,
				charm: d.charm ,
				two_in_one: d.two_in_one ,
				capganthan: d.capganthan ,
				chain_thickness: d.chain_thickness ,
				back_side_size: d.back_side_size 
				
			});
		}
		order_form_data = dialog.fields_dict.order_form_detail.df.data;
		dialog.fields_dict.order_form_detail.grid.refresh();
	});

	// $.each(doc.attributes, function (index, d) {
	// 	var field_name = d.attribute.toLowerCase().replace(/\s+/g, '_');
	// 	console.log(field_name);
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
	// diamond_sieve_size: function (frm, cdt, cdn) {
	// 	let d = locals[cdt][cdn];
	// 	frappe.db.get_value("Attribute Value", d.diamond_sieve_size, "weight_in_cts").then((r) => {
	// 		frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", r.message.weight_in_cts);
	// 	});
	// 	let filter_value = {
	// 		parent: d.diamond_sieve_size,
	// 		diamond_shape: d.stone_shape,
	// 	};
	// 	frappe.call({
	// 		method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.check_diamond_sieve_size_tolerance_value_exist",
	// 		args: {
	// 			filters: filter_value,
	// 		},
	// 		callback: function (r) {
	// 			console.log(r.message);
	// 			if (r.message.length == 0 && d.stone_shape == "Round") {
	// 				frappe.msgprint(
	// 					__("Please Insert Diamond Sieve Size Tolerance at Attribute Value")
	// 				);
	// 				frappe.validated = false;
	// 			}
	// 		},
	// 	});
	// },
	pcs: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		d.quantity = d.pcs*d.weight_per_pcs
		frm.refresh_field("diamond_detail")
	},
	// quantity: function (frm, cdt, cdn) {
	// 	let d = locals[cdt][cdn];
	// 	if (d.pcs > 0) {
	// 		var cal_a = flt(d.quantity / d.pcs, 4);
	// 		console.log(cal_a);
	// 	} else {
	// 		frappe.msgprint(__("Please set PCS value"));
	// 		frappe.validated = false;
	// 	}
	// 	if (d.quantity > 0 && d.stone_shape == "Round" && d.quality) {
	// 		let filter_quality_value = {
	// 			parent: d.diamond_sieve_size,
	// 			diamond_shape: d.stone_shape,
	// 			diamond_quality: d.quality,
	// 		};
	// 		frappe.call({
	// 			method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_quality_diamond_sieve_size_tolerance_value",
	// 			args: {
	// 				filters: filter_quality_value,
	// 			},
	// 			callback: function (r) {
	// 				console.log(r.message);
	// 				let records = r.message;
	// 				if (records) {
	// 					for (let i = 0; i < records.length; i++) {
	// 						let fromWeight = flt(records[i].from_weight);
	// 						let toWeight = flt(records[i].to_weight);
	// 						if (cal_a >= fromWeight && cal_a <= toWeight) {
	// 							// The cal_a value is within the range, do nothing
	// 							frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
	// 							return;
	// 						} else {
	// 							frappe.msgprint(
	// 								`Calculated value ${cal_a} is outside the allowed tolerance range ${fromWeight} to ${toWeight}`
	// 							);
	// 							frappe.validated = false;
	// 							frappe.model.set_value(d.doctype, d.name, "quantity", null);
	// 							return;
	// 						}
	// 					}
	// 				} else {
	// 					frappe.msgprint(__("Tolerance range record not found"));
	// 					frappe.validated = false;
	// 					frappe.model.set_value(d.doctype, d.name, "quantity", null);
	// 					return;
	// 				}
	// 				frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
	// 			},
	// 		});
	// 	}
	// 	if (d.quantity > 0 && d.stone_shape == "Round" && !d.quality) {
	// 		let filter_universal_value = {
	// 			parent: d.diamond_sieve_size,
	// 			for_universal_value: 1,
	// 		};
	// 		// Get records Universal Attribute Value Diamond Sieve Size
	// 		frappe.call({
	// 			method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_records_universal_attribute_value",
	// 			args: {
	// 				filters: filter_universal_value,
	// 			},
	// 			callback: function (r) {
	// 				console.log(r.message);
	// 				let records = r.message;
	// 				if (records) {
	// 					for (let i = 0; i < records.length; i++) {
	// 						let fromWeight = flt(records[i].from_weight);
	// 						let toWeight = flt(records[i].to_weight);
	// 						if (cal_a >= fromWeight && cal_a <= toWeight) {
	// 							// The cal_a value is within the range, do nothing
	// 							frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
	// 							return;
	// 						} else {
	// 							frappe.msgprint(
	// 								`Calculated value ${cal_a} is outside the allowed tolerance range ${fromWeight} to ${toWeight}`
	// 							);
	// 							frappe.validated = false;
	// 							frappe.model.set_value(d.doctype, d.name, "quantity", null);
	// 							return;
	// 						}
	// 					}
	// 				} else {
	// 					// If no range includes cal_a for both specific and universal Diamond Sieve Size, throw an error
	// 					frappe.msgprint(__("Tolerance range record not found"));
	// 					frappe.validated = false;
	// 					frappe.model.set_value(d.doctype, d.name, "quantity", null);
	// 					return;
	// 				}
	// 				frappe.model.set_value(d.doctype, d.name, "weight_per_pcs", cal_a);
	// 			},
	// 		});
	// 	}
	// },
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