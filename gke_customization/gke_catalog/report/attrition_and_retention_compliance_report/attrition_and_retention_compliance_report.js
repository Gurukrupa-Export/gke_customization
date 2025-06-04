// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Attrition and retention compliance report"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 0,
			default: '2025-01-01'
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: '2025-05-31'
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "MultiSelectList",
			options: "Company",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Company", txt);
			}
		},
        {
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "MultiSelectList",
			options: "Branch",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Branch", txt);
			}
		},

		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "MultiSelectList",
			options: "Department",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Department", txt);
			}
		},
    

		// {
		// 	fieldname: "status",
		// 	label: __("Status"),
		// 	fieldtype: "Select",
		// 	reqd: 0
		// }
	],

	onload: function (report) {
		// Clear Filter button setup
		const clearFilterButton = report.page.add_inner_button(__("Clear Filter"), function () {
			report.filters.forEach(function (filter) {
				let field = report.get_filter(filter.fieldname);
				if (field.df.fieldtype === "MultiSelectList") {
					field.set_value([]);
				} else if (field.df.default) {
					field.set_value(field.df.default);
				} else {
					field.set_value("");
				}
			});
		});

		// Fetch distinct options for dropdown filters
		function fetchOptions(doctype, field, filterField, includeBlank = false) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: doctype,
					fields: [`distinct ${field}`],
					order_by: `${field} asc`,
					limit_page_length: 30000,
				},
				callback: function (r) {
					if (r.message) {
						let options = r.message
							.map(row => row[field])
							.filter(value => value && value.trim() !== "");
						if (includeBlank) {
							options.unshift("");
						}
						const filter = report.get_filter(filterField);
						filter.df.options = options;
						filter.refresh();
					}
				},
			});
		}

		// Populate boarding status options
		// fetchOptions("Employee Onboarding", "boarding_status", "status", true);

	}
};
	