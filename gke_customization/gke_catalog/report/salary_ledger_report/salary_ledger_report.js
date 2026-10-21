// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

// Financial year (April to March) that contains today
function sl_fy_dates() {
	const today = moment();
	const startYear = today.month() >= 3 ? today.year() : today.year() - 1;
	return {
		from: `${startYear}-04-01`,
		to: `${startYear + 1}-03-31`,
	};
}

// Employee field that holds the Punch ID (change here if the site uses a custom field)
const SL_PUNCH_ID_FIELD = "attendance_device_id";

// Fill the read-only employee detail fields when an Employee is selected
function sl_fill_employee_details() {
	const qr = frappe.query_report;
	const employee = qr.get_filter_value("employee");
	const clear = {
		employee_name: "",
		designation: "",
		employee_department: "",
		employee_branch: "",
		punch_id: "",
	};
	if (!employee) {
		qr.set_filter_value(clear);
		return;
	}
	frappe.db
		.get_value("Employee", employee, ["employee_name", "designation", "department", "branch", SL_PUNCH_ID_FIELD])
		.then((r) => {
			const e = r.message || {};
			qr.set_filter_value({
				employee_name: e.employee_name || "",
				designation: e.designation || "",
				employee_department: e.department || "",
				employee_branch: e.branch || "",
				punch_id: e[SL_PUNCH_ID_FIELD] || "",
			});
		});
}

frappe.query_reports["Salary Ledger Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: sl_fy_dates().from,
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: sl_fy_dates().to,
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company: company } : {} };
			},
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company: company } : {} };
			},
			on_change: () => sl_fill_employee_details(),
		},
		// Second line: details of the selected employee (filled automatically, read-only)
		{ fieldname: "employee_name", label: __("Employee Name"), fieldtype: "Data", read_only: 1 },
		{ fieldname: "designation", label: __("Designation"), fieldtype: "Data", read_only: 1 },
		{ fieldname: "employee_department", label: __("Employee Department"), fieldtype: "Data", read_only: 1 },
		{ fieldname: "employee_branch", label: __("Employee Branch"), fieldtype: "Data", read_only: 1 },
		{ fieldname: "punch_id", label: __("Punch ID"), fieldtype: "Data", read_only: 1 },
		{
			fieldname: "include_draft",
			label: __("Include Draft Salary Slips"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (["gross_pay", "net_pay"].includes(column.fieldname)) {
			return `<b>${value}</b>`;
		}
		return value;
	},
};