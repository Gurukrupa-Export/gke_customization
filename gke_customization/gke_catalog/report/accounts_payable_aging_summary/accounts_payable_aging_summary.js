// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Accounts Payable Aging Summary"] = {
	filters: [],

	// The aging table is rendered by the server as the report message (above this table).
	// This formatter is for the month-wise table.
	formatter: function (value, row, column, data, default_formatter) {
		if (!data) {
			return default_formatter(value, row, column, data);
		}
		if (column.fieldname === "total_amount") {
			value = format_currency(value || 0, data.currency);
		} else {
			value = default_formatter(value, row, column, data);
		}
		return data.bold && value ? `<b>${value}</b>` : value;
	},
};