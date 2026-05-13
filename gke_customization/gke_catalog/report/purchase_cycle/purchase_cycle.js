// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Cycle"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 0
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"reqd": 0
		},
		{
			"fieldname": "manufacturer",
			"label": __("Manufacturer"),
			"fieldtype": "Link",
			"options": "Manufacturer",
			"reqd": 0
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 0
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"reqd": 0
		},
		{
			"fieldname": "required_by",
			"label": __("Required By"),
			"fieldtype": "Date",
			"reqd": 0
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Color coding for status columns
		if (column.fieldname == "rfq_status") {
			if (value && value.includes("Not Created")) {
				value = `<span style="color: #d73a49; font-weight: bold;">${value}</span>`;
			} else if (value && value.includes("Submitted")) {
				value = `<span style="color: #28a745;">${value}</span>`;
			}
		}

		if (column.fieldname == "sq_status" && value && value.includes("Submitted")) {
			value = `<span style="color: #28a745;">${value}</span>`;
		}

		if (column.fieldname == "po_status") {
			if (value && (value.includes("To Bill") || value.includes("To Receive"))) {
				value = `<span style="color: #ff8c00;">${value}</span>`;
			} else if (value && value.includes("Completed")) {
				value = `<span style="color: #28a745;">${value}</span>`;
			}
		}

		if (column.fieldname == "pr_status") {
			if (value && value.includes("To Bill")) {
				value = `<span style="color: #ff8c00;">${value}</span>`;
			} else if (value && value.includes("Completed")) {
				value = `<span style="color: #28a745;">${value}</span>`;
			}
		}

		if (column.fieldname == "pi_status") {
			if (value && value.includes("Overdue")) {
				value = `<span style="color: #d73a49; font-weight: bold;">${value}</span>`;
			} else if (value && value.includes("Paid")) {
				value = `<span style="color: #28a745;">${value}</span>`;
			} else if (value && value.includes("To Bill")) {
				value = `<span style="color: #ff8c00;">${value}</span>`;
			}
		}

		return value;
	}
};
