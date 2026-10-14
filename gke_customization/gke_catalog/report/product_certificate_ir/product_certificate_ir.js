// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Product Certificate IR"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "receive_status",
			label: __("Receive Status"),
			fieldtype: "Select",
			options: "\nNot Received\nPartially Received\nFully Received",
		},
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Select",
			options: "\nHall Marking Service\nDiamond Certificate service\nFire Assy Service\nXRF Services",
		},
		// {
		// 	fieldname: "customer",
		// 	label: __("Reference Customer"),
		// 	fieldtype: "Link",
		// 	options: "Customer",
		// },
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "serial_no",
			label: __("Serial No"),
			fieldtype: "Link",
			options: "Serial No",
		},
	],
};
