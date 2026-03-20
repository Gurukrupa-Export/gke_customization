// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt
frappe.provide("erpnext.item");

frappe.ui.form.on("Product Return Form", {
	onload(frm) {
		frm.set_query("credit_note_subtype", function () {
			return {
				filters: {
					"parent_type": frm.doc.credit_note_type
				}
			};
		});
	},
	refresh(frm) {

		frm.add_custom_button(__("Create Return"), function () {
			frm.call("create_return_sales_invoices").then(() => {
				frm.msgprint(__("Return Sales Invoices created successfully"));
			});
		});

		set_tag_no_mandatory(frm);

		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__("Payment"), function () {
				frappe.new_doc("Payment Entry", {
					payment_type: "Pay",
					party_type: "Customer",
					party: frm.doc.customer,
					company: frm.doc.company,
					branch: frm.doc.branch,
					reference_doctype: frm.doc.doctype,
					reference_name: frm.doc.name,
				});

			}, __("Create"));

			frm.add_custom_button(__("Payment Request"), function () {
				frappe.new_doc("Payment Request", {
					party_type: "Customer",
					party: frm.doc.customer,
					company: frm.doc.company,
					branch: frm.doc.branch,
					reference_doctype: frm.doc.doctype,
					reference_name: frm.doc.name,
					grand_total: frm.doc.grand_total || 0
				});
			}, __("Create"));
		}

		// =================================================
		// JEWELEX CREDIT NOTE – 3-STAGE PROCESS BUTTONS
		// =================================================
		if (frm.doc.is_jewlex_credit_note && !frm.is_new() && frm.doc.docstatus === 0) {

			// Stage 1: Draft → Item & BOM Creation
			if (frm.doc.status === "Draft") {
				frm.add_custom_button(__("Send to Item & BOM Creation"), function () {
					frappe.confirm(
						__("This will move the document to Item & BOM Creation stage. Continue?"),
						function () {
							frappe.call({
								method: "gke_customization.gke_price_list.doctype.product_return_form.product_return_form_api.send_to_item_bom_creation",
								args: { docname: frm.doc.name },
								freeze: true,
								freeze_message: __("Updating status..."),
								callback: function (r) {
									if (r.message) {
										frm.reload_doc();
									}
								}
							});
						}
					);
				}).addClass("btn-primary");
			}

			// Stage 2: Item & BOM Creation
			if (frm.doc.status === "Item & BOM Creation") {

				// Button: Update Items from Tag (auto-link items + trigger pricing)
				frm.add_custom_button(__("Update Items from Tag"), function () {
					frappe.confirm(
						__("This will link Items using Tag No, update status to 'Send to Pricing', and run pricing calculation. Continue?"),
						function () {
							frappe.call({
								method: "gke_customization.gke_price_list.doctype.product_return_form.product_return_form_api.update_items_from_tag",
								args: { docname: frm.doc.name },
								freeze: true,
								freeze_message: __("Updating items and calculating pricing..."),
								callback: function (r) {
									if (r.message) {
										frm.reload_doc();
									}
								}
							});
						}
					);
				});
			}
		}
	},
	is_jewlex_credit_note: function (frm) {
		set_tag_no_mandatory(frm);
	},
	company(frm) {
		frm.set_query("branch", function () {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})
	},
	credit_note_type: function (frm) {
		frm.set_query("credit_note_subtype", function () {
			return {
				filters: {
					"parent_type": frm.doc.credit_note_type
				}
			};
		});
	},
	gold_rate_with_gst: function (frm) {
		if (frm.doc.gold_rate_with_gst) {
			let gold_rate = flt(frm.doc.gold_rate_with_gst / 1.03, 3);
			if (gold_rate != flt(frm.doc.gold_rate, 3)) {
				frappe.model.set_value(frm.doc.doctype, frm.doc.name, "gold_rate", gold_rate);
			}
		}
	},
	gold_rate: function (frm) {
		if (frm.doc.gold_rate) {
			let gold_rate_with_gst = flt(frm.doc.gold_rate * 1.03, 3);
			if (gold_rate_with_gst != flt(frm.doc.gold_rate_with_gst, 3)) {
				frappe.model.set_value(
					frm.doc.doctype,
					frm.doc.name,
					"gold_rate_with_gst",
					gold_rate_with_gst
				);
			}
		}
	},

	scan_barcode(frm) {
		// same functionality of serial_no
		if (!frm.doc.scan_barcode) return;

		// Get last row or create new
		let row = frm.add_child("items"); // replace "items" with your child table fieldname

		frappe.model.set_value(row.doctype, row.name, "serial_no", frm.doc.scan_barcode);
		frm.refresh_field("items");
		frm.set_value("scan_barcode", "");
	}

});


frappe.ui.form.on("Product Return Form Item", {
	serial_no(frm, cdt, cdn) {
		let child = locals[cdt][cdn];

		if (!frm.doc.customer || !frm.doc.sales_type) {
			frappe.throw(__("Please select Customer and Sales Type"));
			return;
		}

		if (child.serial_no) {

			frappe.call({
				method: "gke_customization.gke_price_list.doctype.product_return_form.product_return_form.get_sales_bom_nd_invoice",
				args: {
					serial_no: child.serial_no,
					customer: frm.doc.customer,
					sales_type: frm.doc.sales_type
				},
				callback: function (r) {
					if (r.message && r.message.sales_invoice) {

						frappe.model.set_value(cdt, cdn, "bom", r.message.bom);
						frappe.model.set_value(cdt, cdn, "item_code", r.message.item_code);
						frappe.model.set_value(cdt, cdn, "item_name", r.message.sales_invoice.item_name);
						frappe.model.set_value(cdt, cdn, "sales_invoice", r.message.sales_invoice.parent);
						frappe.model.set_value(cdt, cdn, "sales_invoice_item", r.message.sales_invoice.name);
						frappe.model.set_value(cdt, cdn, "qty", r.message.sales_invoice.qty);
						frappe.model.set_value(cdt, cdn, "uom", r.message.sales_invoice.uom);
						frappe.model.set_value(cdt, cdn, "diamond_quality", r.message.sales_invoice.custom_diamond_quality);
						frappe.model.set_value(cdt, cdn, "warehouse", r.message.sales_invoice.warehouse);
						frappe.model.set_value(cdt, cdn, "total_weight", r.message.sales_invoice.total_weight);
						frappe.model.set_value(cdt, cdn, "rate", r.message.sales_invoice.rate);

						if (frm.doc.credit_note_subtype in ["Sale Without Payment-Actual", "QC Fail-Repair", "Finish Goods-Consignment"]) {
							// Amount fields
							frappe.model.set_value(cdt, cdn, "amount", r.message.sales_invoice.amount);
							frappe.model.set_value(cdt, cdn, "base_rate", r.message.sales_invoice.base_rate);
							frappe.model.set_value(cdt, cdn, "base_amount", r.message.sales_invoice.base_amount);
							frappe.model.set_value(cdt, cdn, "metal_amount", r.message.sales_invoice.metal_amount);
							frappe.model.set_value(cdt, cdn, "diamond_amount", r.message.sales_invoice.diamond_amount);
							frappe.model.set_value(cdt, cdn, "gemstone_amount", r.message.sales_invoice.gemstone_amount);
							frappe.model.set_value(cdt, cdn, "finding_amount", r.message.sales_invoice.finding_amount);
							frappe.model.set_value(cdt, cdn, "making_amount", r.message.sales_invoice.making_amount);
							frappe.model.set_value(cdt, cdn, "certification_amount", r.message.sales_invoice.custom_certification_amount);
							frappe.model.set_value(cdt, cdn, "freight_amount", r.message.sales_invoice.custom_freight_amount);
							frappe.model.set_value(cdt, cdn, "other_material_amount", r.message.sales_invoice.other_material_amount);
							frappe.model.set_value(cdt, cdn, "hallmarking_amount", r.message.sales_invoice.custom_hallmarking_amount);
							frappe.model.set_value(cdt, cdn, "custom_duty_amount", r.message.sales_invoice.custom_custom_duty_amount);
							frappe.model.set_value(cdt, cdn, "other_amount", r.message.sales_invoice.custom_other_amount);
						}
					}
				},
				error: function (r) {
					// console.log("ERROR MESSAGE ::: ", r);

					frappe.model.clear_doc(cdt, cdn);
					frm.refresh_field("items");

					// frappe.model.set_value(cdt, cdn, "serial_no", "");
					// frappe.model.set_value(cdt, cdn, "sales_invoice", "");
					// frappe.model.set_value(cdt, cdn, "sales_invoice_item", "");
					// frappe.model.set_value(cdt, cdn, "bom", "");
					// frappe.model.set_value(cdt, cdn, "item_code", "");
				}
			})
		}
	},

	edit_bom: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];

		if (frm.doc.__islocal) {
			frappe.throw(__("Please save document to edit the BOM."));
		}

		if (!row.bom) {
			frappe.throw(__("Please select BOM to edit."));
		}

		if (row.tag_no) { // Jwelex items then disable button
			return
		}

		// child table data variables
		let metal_data = [];
		let diamond_data = [];
		let gemstone_data = [];
		let finding_data = [];
		let other_data = [];

		// Type	Colour	Purity	Weight in gms	Rate	Amount
		const metal_fields = [
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden: 1 },
			{
				fieldtype: "Link",
				fieldname: "metal_type",
				label: __("Metal Type"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Type" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "metal_touch",
				label: __("Metal Touch"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Touch" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "metal_purity",
				label: __("Metal Purity"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Purity" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "customer_metal_purity",
				label: __("Customer Metal Purity"),
				read_only: 1,
				options: "Attribute Value",
			},
			{
				fieldtype: "Link",
				fieldname: "metal_colour",
				label: __("Metal Colour"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Colour" },
					};
				},
			},
			{ fieldtype: "Column Break", fieldname: "clb1" },
			{
				fieldtype: "Float",
				fieldname: "quantity",
				label: __("Weight In Gms"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
				description: __("Weight show Based on precision"),
			},
			{
				fieldtype: "Float",
				fieldname: "actual_quantity",
				label: __("Weight In Gms"),
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "difference_qty",
				label: __("Difference(Based on Roundoff)"),
				hidden: 1,
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "rate",
				label: __("Gold Rate"),
				reqd: 1,
				columns: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "actual_rate",
				label: __("Actual Rate"),
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "amount",
				label: __("Gold Amount"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
			},
			{ fieldtype: "Column Break", fieldname: "clb2" },
			{
				fieldtype: "Float",
				fieldname: "making_rate",
				label: __("Making Rate"),
				reqd: 1,
				columns: 1,
				in_list_view: 1,
			},
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "making_rate_copy",
			// 	read_only: 1,
			// 	label: __("Making Rate"),
			// },
			{
				fieldtype: "Float",
				fieldname: "making_amount",
				label: __("Making Amount"),
				read_only: 1,
				reqd: 1,
				columns: 1,
				in_list_view: 1,
			},
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "wastage_rate",
			// 	label: __("Wastage Rate"),
			// 	columns: 1,
			// },
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "wastage_amount",
			// 	label: __("Wastage Amount"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
			// {
			// 	fieldtype: "Currency",
			// 	fieldname: "difference",
			// 	label: __("Difference(Based on Metal Purity)"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
		];

		const diamond_fields = [
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden: 1 },
			{
				fieldtype: "Link",
				fieldname: "diamond_type",
				label: __("Diamond Type"),
				columns: 1,
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Diamond Type" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "stone_shape",
				label: __("Stone Shape"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Stone Shape" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "diamond_cut",
				label: __("Diamond Cut"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Stone Shape" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "quality",
				label: __("Diamond Quality"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Diamond Quality" },
					};
				},
			},
			{ fieldtype: "Column Break", fieldname: "clb1" },
			{
				fieldtype: "Link",
				fieldname: "sub_setting_type",
				label: __("Sub Setting Type"),
				read_only: 1,
				columns: 1,
				reqd: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Sub Setting Type" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "diamond_sieve_size",
				label: __("Diamond Sieve Size"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Diamond Sieve Size" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "sieve_size_range",
				label: __("Sieve Size Range"),
				columns: 1,
				read_only: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Diamond Sieve Size Range" },
					};
				},
			},
			{
				fieldtype: "Float",
				fieldname: "size_in_mm",
				label: __("Size (in MM)"),
				columns: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{ fieldtype: "Column Break", fieldname: "clb2" },
			{
				fieldtype: "Float",
				fieldname: "pcs",
				label: __("Pcs"),
				reqd: 1,
				in_list_view: 1,
				read_only: 1,
				columns: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "quantity",
				label: __("Weight In Cts"),
				reqd: 1,
				columns: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "weight_per_pcs",
				label: __("Weight Per Piece"),
				read_only: 1,
				columns: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "total_diamond_rate",
				label: __("Rate"),
				columns: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "actual_total_diamond_rate",
				label: __("Actual Rate"),
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "diamond_rate_for_specified_quantity",
				columns: 1,
				read_only: 1,
				label: __("Amount"),
				in_list_view: 1,
			},
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "difference",
			// 	label: __("Difference(Based on Roundoff)"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
		];

		const gemstone_fields = [
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden: 1 },
			{
				fieldtype: "Link",
				fieldname: "gemstone_type",
				label: __("Gemstone Type"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Gemstone Type" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "cut_or_cab",
				label: __("Cut And Cab"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Cut Or Cab" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "stone_shape",
				label: __("Stone Shape"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Stone Shape" },
					};
				},
			},
			{ fieldtype: "Column Break", fieldname: "clb1" },
			{
				fieldtype: "Link",
				fieldname: "gemstone_quality",
				label: __("Gemstone Quality"),
				read_only: 1,
				columns: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Gemstone Quality" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "gemstone_size",
				label: __("Gemstone Size"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Gemstone Size" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "sub_setting_type",
				label: __("Sub Setting Type"),
				columns: 1,
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Sub Setting Type" },
					};
				},
			},
			{ fieldtype: "Column Break", fieldname: "clb2" },
			{
				fieldtype: "Float",
				fieldname: "pcs",
				label: __("Pcs"),
				columns: 1,
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "quantity",
				label: __("Weight In Cts"),
				columns: 1,
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "total_gemstone_rate",
				columns: 1,
				label: __("Total Gemstone Rate"),
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "actual_total_gemstone_rate",
				read_only: 1,
				label: __("Actual Gemstone Rate"),
			},
			{
				fieldtype: "Float",
				fieldname: "gemstone_rate_for_specified_quantity",
				columns: 1,
				label: __("Amount"),
				read_only: 1,
				in_list_view: 1,
			},
			// {
			// 	fieldtype: "Flaot",
			// 	fieldname: "difference",
			// 	label: __("Difference(Based on Roundoff)"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
		];

		const finding_fields = [
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden: 1 },
			{
				fieldtype: "Link",
				fieldname: "metal_type",
				columns: 1,
				label: __("Metal Type"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Type" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "finding_category",
				columns: 1,
				label: __("Category"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Finding Category" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "finding_type",
				columns: 1,
				label: __("Type"),
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Finding Sub-Category" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "metal_touch",
				columns: 1,
				label: __("Metal Touch"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Touch" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "metal_purity",
				columns: 1,
				label: __("Metal Purity"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Purity" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "customer_metal_purity",
				label: __("Customer Metal Purity"),
				read_only: 1,
				options: "Attribute Value",
			},
			{ fieldtype: "Column Break", fieldname: "clb1" },
			{
				fieldtype: "Link",
				fieldname: "finding_size",
				columns: 1,
				label: __("Size"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Finding Size" },
					};
				},
			},
			{
				fieldtype: "Link",
				fieldname: "metal_colour",
				columns: 1,
				label: __("Metal Colour"),
				read_only: 1,
				reqd: 1,
				in_list_view: 1,
				options: "Attribute Value",
				get_query() {
					return {
						query: "jewellery_erpnext.query.item_attribute_query",
						filters: { item_attribute: "Metal Colour" },
					};
				},
			},
			{
				fieldtype: "Float",
				fieldname: "quantity",
				columns: 1,
				label: __("Quantity"),
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
				default: 1,
				description: __("Weight show Based on precision"),
			},
			{
				fieldtype: "Float",
				fieldname: "actual_quantity",
				label: __("Quantity"),
				hidden: 1,
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "difference_qty",
				label: __("Difference(Based on Roundoff)"),
				hidden: 1,
				read_only: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "rate",
				columns: 1,
				label: __("Rate"),
				reqd: 1,
				in_list_view: 1,
				default: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "actual_rate",
				columns: 1,
				label: __("Actual Rate"),
				read_only: 1,
			},
			{ fieldtype: "Column Break", fieldname: "clb2" },
			{
				fieldtype: "Float",
				fieldname: "amount",
				columns: 1,
				label: __("Amount"),
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
				default: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "making_rate",
				label: __("Making Rate"),
				reqd: 1,
				columns: 1,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "making_amount",
				label: __("Making Amount"),
				reqd: 1,
				read_only: 1,
				columns: 1,
				in_list_view: 1,
			},
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "wastage_rate",
			// 	label: __("Wastage Rate"),
			// 	columns: 1,
			// 	in_list_view: 1,
			// },
			// {
			// 	fieldtype: "Float",
			// 	fieldname: "wastage_amount",
			// 	label: __("Wastage Amount"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
			// {
			// 	fieldtype: "Currency",
			// 	fieldname: "difference",
			// 	label: __("Difference(Based on Metal Purity)"),
			// 	columns: 1,
			// 	read_only: 1,
			// 	in_list_view: 1,
			// },
		];

		const other_fields = [
			{ fieldtype: "Data", fieldname: "docname", read_only: 1, hidden: 1 },
			{
				fieldtype: "Link",
				fieldname: "item_code",
				read_only: 1,
				options: "Item",
				columns: 2,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "weight",
				read_only: 1,
				label: __("WT in (GMS)"),
				columns: 2,
				in_list_view: 1,
			},
			{
				fieldtype: "Float",
				fieldname: "qty",
				read_only: 1,
				label: __("Qty"),
				columns: 2,
				in_list_view: 1,
			},
			{
				fieldtype: "Link",
				fieldname: "uom",
				columns: 1,
				read_only: 1,
				label: __("UOM"),
				reqd: 2,
				in_list_view: 1,
				options: "UOM",
			},
		];

		const dialog = new frappe.ui.Dialog({
			title: __("Update"),
			fields: [
				// {
				// 	fieldname: "barcode_scanner",
				// 	fieldtype: "Data",
				// 	label: "Scan Barcode",
				// 	options: "Barcode",
				// 	onchange: (e) => {
				// 		if (!e) {
				// 			return;
				// 		}

				// 		if (e.target.value) {
				// 			scan_api_call(e.target.value, (r) => {
				// 				if (r.message) {
				// 					update_dialog_values(dialog, row.item_code, r, row);
				// 				}
				// 			});
				// 		}
				// 	},
				// },
				{
					fieldname: "gold_rate",
					fieldtype: "Float",
					label: "Gold Rate",
					default: frm.doc.gold_rate,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "serial_no",
					fieldtype: "Link",
					label: "Serial No",
					options: "Serial No",
					read_only: 1,
					default: row.serial_no,
					onchange: (e) => {
						if (e && e.target && e.target.value && dialog.get_value("serial_no")) {
							add_row(dialog.get_value("serial_no"), frm, row)
								.then((row_) => {
									dialog.set_value("bom_no", row_.bom);
								})
								.catch((error) => {
									console.error(error);
								});
						}
					},
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "bom_no",
					fieldtype: "Link",
					label: "BOM-No",
					options: "BOM",
					read_only: 1,
					default: row.bom,
					onchange: () => {
						if (dialog.get_value("bom_no")) {
							edit_bom_documents(
								dialog,
								dialog.get_value("bom_no"),
								metal_data,
								diamond_data,
								gemstone_data,
								finding_data,
								other_data,
								row // current row
							);
						}
					},
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "metal_detail",
					fieldtype: "Table",
					label: "Metal Detail",
					read_only: 1,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					data: metal_data,
					get_data: () => {
						return metal_data;
					},
					fields: metal_fields,
				},
				{
					fieldname: "finding_detail",
					fieldtype: "Table",
					label: "Finding Detail",
					read_only: 1,
					cannot_delete_rows: true,
					cannot_add_rows: true,
					data: finding_data,
					get_data: () => {
						return finding_data;
					},
					fields: finding_fields,
				},
				{
					fieldname: "diamond_detail",
					fieldtype: "Table",
					label: "Diamond Detail",
					read_only: 1,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					data: diamond_data,
					get_data: () => {
						return diamond_data;
					},
					fields: diamond_fields,
				},
				{
					fieldname: "gemstone_detail",
					fieldtype: "Table",
					label: "Gemstone Detail",
					read_only: 1,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					data: gemstone_data,
					get_data: () => {
						return gemstone_data;
					},
					fields: gemstone_fields,
				},
				{
					fieldname: "other_detail",
					fieldtype: "Table",
					label: "Other Detail",
					read_only: 1,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					data: other_data,
					get_data: () => {
						return other_data;
					},
					fields: other_fields,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "gross_weight",
					fieldtype: "Float",
					label: "Gross Weight (In Gram)",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "net_weight",
					fieldtype: "Float",
					label: "Net Weight",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "metal_amount",
					fieldtype: "Currency",
					label: "Metal Amount",
					default: row.metal_amount,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "making_amount",
					fieldtype: "Currency",
					label: "Making Amount",
					default: row.making_amount,
					read_only: 1,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "finding_weight",
					fieldtype: "Float",
					label: "Finding Weight",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "finding_amount",
					fieldtype: "Currency",
					label: "Finding Amount",
					default: row.finding_amount,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "other_weight",
					fieldtype: "Float",
					label: "Other Materials Weight (in Gram)",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "other_material_amount",
					fieldtype: "Currency",
					label: "Other Materials Amount",
					read_only: 1,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "diamond_weight",
					fieldtype: "Float",
					label: "Diamond Weight (in carat)",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "diamond_amount",
					fieldtype: "Currency",
					label: "Diamond Amount",
					default: row.diamond_amount,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "gemstone_weight",
					fieldtype: "Float",
					label: "Gemstone Weight (in carat)",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "gemstone_amount",
					fieldtype: "Currency",
					label: "Gemstone Amount",
					default: row.gemstone_amount,
					read_only: 1,
				},
				// {
				// 	fieldtype: "Section Break",
				// },
				// {
				// 	fieldtype: "Column Break",
				// },
				// {
				// 	fieldname: "wastage_amount",
				// 	fieldtype: "Currency",
				// 	label: "Wastage Amount",
				// 	read_only: 1,
				// },
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "certification_amount",
					fieldtype: "Currency",
					label: "Certification Amount",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "hallmarking_amount",
					fieldtype: "Currency",
					label: "Hallmarking Amount",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "custom_duty_amount",
					fieldtype: "Currency",
					label: "Custom Duty Amount",
					default: row.custom_duty_amount,
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "freight_amount",
					fieldtype: "Currency",
					label: "Freight Amount",
					read_only: 1,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "sale_key",
					fieldtype: "Currency",
					label: "Sale Key",
					onchange: () => {
						if (dialog.get_value("sale_key"))
							dialog.set_value(
								"saleAmount",
								dialog.get_value("sale_amount") / dialog.get_value("sale_key") || 0
							);
					},
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "sale_amount",
					fieldtype: "Currency",
					label: "MRP Sale Amount",
					read_only: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "rate",
					fieldtype: "Currency",
					label: "Rate",
					read_only: 1,
					default: row.rate,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "amount",
					fieldtype: "Currency",
					label: "Amount",
					read_only: 1,
					default: row.amount,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "diamond_inclusive",
					fieldtype: "Currency",
					label: "Diamond Inclusive WT",
					description:
						"Diamond Inclusive = Gross Wt - Stone Wt(in gram) - Finding Wt - Other Wt",
					precision: 3,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "net_wt",
					fieldtype: "Currency",
					label: "Net WT WT",
					description:
						"Net Wt = Gross Wt - Diamond Wt(in gram) - Stone Wt(in gram) - Finding Wt - Other Wt",
					precision: 3,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "saleAmount",
					fieldtype: "Currency",
					label: "Sale Amount",
					read_only: 1,
					hidden: 1,
				},
				// {
				//     fieldtype: "Column Break",
				// },
				{
					fieldname: "other_amount_",
					fieldtype: "Currency",
					label: "Other Amount",
				},
			],
			primary_action: function () {
				const metal_detail = dialog.get_values()["metal_detail"] || [];
				const diamond_detail = dialog.get_values()["diamond_detail"] || [];
				const gemstone_detail = dialog.get_values()["gemstone_detail"] || [];
				const finding_detail = dialog.get_values()["finding_detail"] || [];
				const other_detail = dialog.get_values()["other_detail"] || [];

				// frappe.call({
				// 	method: "jewellery_erpnext.jewellery_erpnext.doc_events.quotation.update_bom_detail",
				// 	freeze: true,
				// 	args: {
				// 		parent_doctype: "BOM",
				// 		parent_doctype_name: dialog.get_value("bom_no") || row.bom,
				// 		metal_detail: metal_detail,
				// 		diamond_detail: diamond_detail,
				// 		gemstone_detail: gemstone_detail,
				// 		finding_detail: finding_detail,
				// 		other_detail: other_detail,
				// 	},
				// 	callback: function (r) {
				// 		frm.is_dirty() ? frm.save() : frm.reload_doc();
				// 	},
				// });
				// dialog.hide();
				refresh_field("items");
			},
			primary_action_label: __("Update"),
		});

		if (row.bom) {
			edit_bom_documents(
				dialog,
				row.bom,
				metal_data,
				diamond_data,
				gemstone_data,
				finding_data,
				other_data,
				row // current row
			);
		}

		// setting bom no if missing from child
		if (!dialog.get_value("bom_no") && dialog.get_value("serial_no")) {
			console.log("in else case");
			frappe.db
				.get_value(
					"BOM",
					{
						tag_no: dialog.get_value("serial_no"),
						is_active: 1,
						customer: frm.doc.customer,
					},
					"name"
				)
				.then((r) => {
					if (r.message && r.message.name) {
						dialog.set_value("bom_no", r.message.name);
					}
				});
		}

		// displaying scan icon
		let scan_btn = dialog.$wrapper.find(".link-btn");
		scan_btn.css("display", "inline");

		dialog.show();

		dialog.$wrapper.find(".modal-dialog").css("max-width", "90%");

		// hide update button
		if (frm.doc.docstatus == 1) dialog.$wrapper.find(".btn-modal-primary").remove();
	},

	qty(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
	},

	rate(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", row.rate * row.qty);
	}
});

function set_tag_no_mandatory(frm) {
	let mandatory = frm.doc.is_jewlex_credit_note ? 1 : 0;

	// Replace 'child_table_fieldname' with your actual child table fieldname
	frm.fields_dict['items'].grid.update_docfield_property(
		'tag_no',
		'reqd',
		mandatory
	);

}


function update_dialog_values(dialog, scanned_item, r, row) {
	const { item_code, barcode, batch_no, serial_no } = r.message;

	dialog.set_value("barcode_scanner", "");
	if (item_code === scanned_item) {
		if (serial_no) {
			dialog.set_value("serial_no", serial_no);
			row.serial_no = serial_no;
		}
	}
}


let edit_bom_documents = (
	dialog,
	bom_no,
	metal_data,
	diamond_data,
	gemstone_data,
	finding_data,
	other_data,
	row // current row
) => {
	frappe.call({
		method: "gke_customization.gke_price_list.doctype.product_return_form.product_return_form.get_credit_note_adjusted_bom",
		freeze: true,
		args: {
			doc: cur_frm.doc,
			invoice_item: row.sales_invoice_item || '',
			bom_name: bom_no,
		},
		callback(r) {
			if (r.message) {
				set_edit_bom_details(
					r.message,
					dialog,
					metal_data,
					diamond_data,
					gemstone_data,
					finding_data,
					other_data
				);
			}
		},
	});
};

let set_edit_bom_details = (
	doc,
	dialog,
	metal_data,
	diamond_data,
	gemstone_data,
	finding_data,
	other_data
) => {
	/*
		function to set fields and child tables values of dialog ui
		args:
			dialog: dialog form
			metal_data, diamond_data, gemstone_data, finding_data, other_data => variables used to append table data
	*/

	// clearing all tables
	dialog.fields_dict.metal_detail.df.data = [];
	dialog.fields_dict.metal_detail.grid.refresh();

	dialog.fields_dict.diamond_detail.df.data = [];
	dialog.fields_dict.diamond_detail.grid.refresh();

	dialog.fields_dict.gemstone_detail.df.data = [];
	dialog.fields_dict.gemstone_detail.grid.refresh();

	dialog.fields_dict.finding_detail.df.data = [];
	dialog.fields_dict.finding_detail.grid.refresh();

	dialog.fields_dict.other_detail.df.data = [];
	dialog.fields_dict.other_detail.grid.refresh();

	// clearing all field values
	dialog.set_value("gross_weight", 0);
	// dialog.set_value("certification_amount", 0)
	// dialog.set_value("hallmarking_amount", 0)
	// dialog.set_value("custom_duty_amount", 0)
	// dialog.set_value("freight_amount", 0)
	// dialog.set_value("sale_amount", 0)

	// dialog.set_value("metal_amount", 0);
	// dialog.set_value("making_amount", 0);
	// dialog.set_value("wastage_amount", 0);
	// dialog.set_value("gemstone_amount", 0);
	// dialog.set_value("diamond_amount", 0);
	dialog.set_value("saleAmount", 0);

	// total amount calculation
	var metal_amount = 0;
	var making_amount = 0;
	var wastage_amount = 0;
	var diamond_amount = 0;
	var finding_amount = 0;
	var gemstone_amount = 0;
	var other_material_amount = 0;

	// metal details table append
	$.each(doc.metal_detail, function (index, d) {
		metal_amount += d.amount;
		making_amount += d.making_amount;
		// wastage_amount += d.wastage_amount;

		dialog.fields_dict.metal_detail.df.data.push({
			docname: d.name,
			metal_type: d.metal_type,
			metal_touch: d.metal_touch,
			metal_purity: d.metal_purity,
			customer_metal_purity: d.customer_metal_purity,
			metal_colour: d.metal_colour,
			amount: d.amount,
			rate: d.rate,
			actual_rate: d.rate,
			quantity: d.quantity,
			actual_quantity: d.actual_quantity,
			difference_qty: d.difference_qty,
			// wastage_rate: d.wastage_rate,
			// wastage_amount: d.wastage_amount,
			making_rate: d.making_rate,
			// making_rate_copy: d.making_rate,
			making_amount: d.making_amount,
			// difference: d.difference,
		});
		metal_data = dialog.fields_dict.metal_detail.df.data;
		dialog.fields_dict.metal_detail.grid.refresh();
	});

	// diamond details table append
	$.each(doc.diamond_detail, function (index, d) {
		diamond_amount += d.diamond_rate_for_specified_quantity;

		dialog.fields_dict.diamond_detail.df.data.push({
			docname: d.name,
			diamond_type: d.diamond_type,
			stone_shape: d.stone_shape,
			quality: d.quality,
			pcs: d.pcs,
			diamond_cut: d.diamond_cut,
			sub_setting_type: d.sub_setting_type,
			diamond_grade: d.diamond_grade,
			diamond_sieve_size: d.diamond_sieve_size,
			sieve_size_range: d.sieve_size_range,
			size_in_mm: d.size_in_mm,
			quantity: d.quantity,
			weight_per_pcs: d.weight_per_pcs,
			total_diamond_rate: d.total_diamond_rate,
			actual_total_diamond_rate: d.total_diamond_rate,
			diamond_rate_for_specified_quantity: d.diamond_rate_for_specified_quantity,
			// difference: d.difference,
		});
		diamond_data = dialog.fields_dict.diamond_detail.df.data;
		dialog.fields_dict.diamond_detail.grid.refresh();
	});

	// gemstone details table append
	$.each(doc.gemstone_detail, function (index, d) {
		gemstone_amount += d.gemstone_rate_for_specified_quantity;

		dialog.fields_dict.gemstone_detail.df.data.push({
			docname: d.name,
			gemstone_type: d.gemstone_type,
			stone_shape: d.stone_shape,
			sub_setting_type: d.sub_setting_type,
			cut_or_cab: d.cut_or_cab,
			pcs: d.pcs,
			gemstone_quality: d.gemstone_quality,
			gemstone_grade: d.gemstone_grade,
			gemstone_size: d.gemstone_size,
			quantity: d.quantity,
			total_gemstone_rate: d.total_gemstone_rate,
			actual_total_gemstone_rate: d.total_gemstone_rate,
			gemstone_rate_for_specified_quantity: d.gemstone_rate_for_specified_quantity,
			// difference: d.difference,
		});
		gemstone_data = dialog.fields_dict.gemstone_detail.df.data;
		dialog.fields_dict.gemstone_detail.grid.refresh();
	});

	// finding details table append
	$.each(doc.finding_detail, function (index, d) {
		finding_amount += d.amount;

		dialog.fields_dict.finding_detail.df.data.push({
			docname: d.name,
			metal_type: d.metal_type,
			finding_category: d.finding_category,
			finding_type: d.finding_type,
			finding_size: d.finding_size,
			metal_touch: d.metal_touch,
			metal_purity: d.metal_purity,
			customer_metal_purity: d.customer_metal_purity,
			amount: d.amount,
			rate: d.rate,
			actual_rate: d.rate,
			metal_colour: d.metal_colour,
			quantity: d.quantity,
			actual_quantity: d.actual_quantity,
			difference_qty: d.difference_qty,
			// wastage_rate: d.wastage_rate,
			// wastage_amount: d.wastage_amount,
			making_rate: d.making_rate,
			making_amount: d.making_amount,
			// difference: d.difference,
		});
		finding_data = dialog.fields_dict.finding_detail.df.data;
		dialog.fields_dict.finding_detail.grid.refresh();
	});

	// other details table append
	$.each(doc.other_detail, function (index, d) {
		dialog.fields_dict.other_detail.df.data.push({
			docname: d.name,
			item_code: d.item_code,
			qty: d.qty,
			weight: d.weight,
			uom: d.uom,
		});
		other_data = dialog.fields_dict.other_detail.df.data;
		dialog.fields_dict.other_detail.grid.refresh();
	});

	// dialog fields value fetch from BOM
	dialog.set_value("gross_weight", doc.gross_weight);
	// dialog.set_value("finding_amount", finding_amount)
	// dialog.set_value("hallmarking_amount", doc.hallmarking_amount)
	// dialog.set_value("custom_duty_amount", doc.custom_duty_amount)
	// dialog.set_value("freight_amount", doc.freight_amount)
	// dialog.set_value("sale_amount", doc.sale_amount)

	dialog.set_value("diamond_inclusive", doc.diamond_inclusive);
	dialog.set_value("net_wt", doc.net_wt);
	// dialog.set_value("metal_amount", metal_amount);
	// dialog.set_value("making_amount", making_amount);
	// dialog.set_value("wastage_amount", wastage_amount);
	// dialog.set_value("gemstone_amount", gemstone_amount);
	// dialog.set_value("diamond_amount", diamond_amount);
	dialog.set_value("net_weight", doc.metal_and_finding_weight || 0);
	dialog.set_value("finding_weight", doc.finding_weight_ || 0);
	dialog.set_value("other_weight", doc.other_weight || 0);
	dialog.set_value("diamond_weight", doc.diamond_weight || 0);
	dialog.set_value("gemstone_weight", doc.gemstone_weight || 0);
	if (dialog.get_value("sale_key"))
		dialog.set_value(
			"saleAmount",
			dialog.get_value("sale_amount") / dialog.get_value("sale_key")
		);
};


let add_row = (serial_no, frm, row) => {
	/*
		function to add row of Sales Invoice Item table using bom details
		args:
			serial_no: link of serail no( to fetch bom using serial)
			frm: current form
			row: current row
	*/
	return new Promise((resolve, reject) => {
		let new_row;
		frappe.call({
			method: "jewellery_erpnext.jewellery_erpnext.doc_events.bom.get_bom_details",
			freeze: true,
			args: {
				serial_no: serial_no,
				customer: frm.doc.customer,
			},
			callback: function (r) {
				if (r.message) {
					let bom = r.message;
					new_row = frm.add_child("items");
					new_row.item_code = bom.item;
					new_row.serial_no = bom.tag_no;
					new_row.bom = bom.name;
					refresh_field("items");
					frm.trigger("item_code", new_row.doctype, new_row.name);
					frm.script_manager.trigger("item_code", new_row.doctype, new_row.name);
					row = new_row;
					resolve(new_row);
				} else {
					reject("Failed to fetch BOM details");
				}
			},
		});
	});
};


function scan_api_call(input, callback) {
	frappe
		.call({
			method: "erpnext.stock.utils.scan_barcode",
			args: {
				search_value: input,
			},
		})
		.then((r) => {
			callback(r);
		});
}