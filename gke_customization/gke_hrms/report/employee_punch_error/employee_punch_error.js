// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Punch Error"] = {
	filters: [
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			label: __("From Date"),
			fieldname: "from_date",
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			label: __("To Date"),
			fieldname: "to_date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			label: __("Department"),
			fieldname: "department",
			fieldtype: "Link",
			options: "Department",
			// "reqd": 1,
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					doctype: "Department",
					filters: { company: company },
				};
			},
		},
		{
			label: __("Employee"),
			fieldname: "employee",
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					doctype: "Employee",
					filters: { company: company },
				};
			},
		},
		{
			label: __("Branch"),
			fieldname: "branch",
			fieldtype: "Link",
			options: "Branch",
		},
	],
	onload: (report) => {
		report.page
			.add_button("Clear Filters", function () {
				["department", "employee", "branch"].forEach((fieldname) => {
					frappe.query_report.set_filter_value(fieldname, "");
				});
				report.refresh();
			})
			.addClass("btn-info");

		report.page
			.add_button("Generate", function () {
				report.refresh();
			})
			.addClass("btn-primary");

		report.page
			.add_inner_button(__("Mark as Attendance"), function () {
				let checkedRowIndexes = frappe.query_report.datatable.rowmanager.getCheckedRows();

				if (!checkedRowIndexes.length) {
					frappe.msgprint(__("Please select a row."));
					return false;
				}

				if (checkedRowIndexes.length > 1) {
					frappe.msgprint(__("Please select only one row."));
					return false;
				}

				let selectedRowData = report.data[checkedRowIndexes[0]];

				if (!selectedRowData) {
					frappe.msgprint(__("Unable to fetch data for the selected row."));
					return false;
				}

				frappe.new_doc("Manual Punch Entry", {
					date: selectedRowData.attendance_date,
					error_date: selectedRowData.attendance_date,
					employee: selectedRowData.employee,
					employee_name: selectedRowData.employee_name,
					department: selectedRowData.department,
					branch: selectedRowData.custom_branch,
				});
			})
			.addClass("btn-default");
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
};
