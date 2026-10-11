// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Bom Dashboard Script"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{
			fieldname: "category",
			label: __("Category"),
			fieldtype: "Link",
			options: "Attribute Value",
			get_query: () => ({
				query: "jewellery_erpnext.query.item_attribute_query",
				filters: { item_attribute: "Item Category" },
			}),
		},
		{ fieldname: "workflow_state", label: __("Workflow State"), fieldtype: "Link", options: "Workflow State" },
		{ fieldname: "setting_type", label: __("Setting Type"), fieldtype: "Data" },
		{ fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User" },
	],
};