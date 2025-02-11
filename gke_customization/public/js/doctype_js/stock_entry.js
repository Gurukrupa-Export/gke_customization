frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus == 0) {
			frm.add_custom_button(
				__("Stock Ledger"),
				function () {
					// Call server-side method
					frappe.call({
						type: "GET",
						method: "gke_customization.gke_customization.doc_events.stock_entry.show_stock_ledger_preview",
						args: {
							company: frm.doc.company,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
						},
						callback: function (response) {
							if (response.message && response.message.sl_columns && response.message.sl_data) {
								make_dialog(
									"Stock Ledger Preview",
									"stock_ledger_preview_html",
									response.message.sl_columns,
									response.message.sl_data
								);
							} else {
								frappe.msgprint(__("No data returned for the stock ledger preview."));
							}
						},
						error: function (error) {
							frappe.msgprint(__("An error occurred while fetching stock ledger data."));
							console.error(error);
						},
					});
				},
				__("Preview")
			);
		}
		function make_dialog(label, fieldname, columns, data) {
			let dialog = new frappe.ui.Dialog({
				size: "extra-large",
				title: __(label),
				fields: [
					{
						fieldtype: "HTML",
						fieldname: fieldname,
					},
				],
			});
		
			// Attach DataTable only after the dialog is fully rendered
			dialog.$wrapper.on("shown.bs.modal", function () {
				let wrapper = dialog.get_field(fieldname).$wrapper;
				wrapper.empty(); // Clean wrapper before rendering
				get_datatable(columns, data, wrapper);
			});
		
			dialog.show();
		}
		
		function get_datatable(columns, data, wrapper) {
			const datatable_options = {
				columns: columns,
				data: data,
				dynamicRowHeight: true,
				checkboxColumn: false,
				inlineFilters: true,
			};
		
			// Ensure DataTable is initialized on a valid DOM element
			if (wrapper[0]) {
				new frappe.DataTable(wrapper[0], datatable_options);
			} else {
				console.error("Error: DataTable wrapper is not attached to DOM.");
			}
		}
		
	},
});
