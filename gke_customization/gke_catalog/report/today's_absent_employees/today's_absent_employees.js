// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Today's Absent Employees"] = {
	"filters": [
		// {
		// 	fieldname: "company",
		// 	label: __("Company"),
		// 	fieldtype: "Link",
		// 	options: "Company",
		// 	default: frappe.defaults.get_user_default("Company"),
		// 	reqd: 1,
		// },
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],
};