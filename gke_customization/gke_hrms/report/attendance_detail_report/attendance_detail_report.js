// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Attendance Detail Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			reqd: 1,
		},
		{
			"label": __("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"mandatory": 0,
		},
		{
			"label": __("Status"),
			"fieldname": "status",
			"fieldtype": "Select",
			"options": ["", "Present", "Absent", "On Leave", "Half Day", "Work From Home"],
			"mandatory": 0,
		},
		{
			fieldname: "employee",
			label: __("employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "shift",
			label: __("Shift Type"),
			fieldtype: "Link",
			options: "Shift Type",
		}

	]
};
