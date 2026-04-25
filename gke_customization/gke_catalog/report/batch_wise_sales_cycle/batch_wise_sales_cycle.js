frappe.query_reports["Batch Wise Sales Cycle"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
		},
		{
			fieldname: "delivery_note",
			label: __("Delivery Note"),
			fieldtype: "Link",
			options: "Delivery Note",
		},
		{
			fieldname: "sales_invoice",
			label: __("Sales Invoice"),
			fieldtype: "Link",
			options: "Sales Invoice",
		},
		{
			fieldname: "batch_no",
			label: __("Batch No"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		if (data.is_total_row) {
			return `<span style="font-weight:700;">${value || ""}</span>`;
		}

		if (["dn_id", "si_id", "si_ret_id"].includes(column.fieldname) && value) {
			return `<span style="font-weight:600;">${value}</span>`;
		}

		if (column.fieldname === "dn_si_diff_qty" && data.dn_si_diff_qty) {
			return `<span style="font-weight:600; color:#c0392b;">${value}</span>`;
		}

		return value;
	},
};