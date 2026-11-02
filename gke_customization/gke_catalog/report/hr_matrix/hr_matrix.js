// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["HR Matrix"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_end(),
			"reqd": 1
		},
		{
			"fieldname": "status",
			"label": __("Employee Status"),
			"fieldtype": "Select",
			"options": "\nActive\nInactive",
			"default": ""
		}
	]
	
};
