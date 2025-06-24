// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Fixed Asset Register Report"] = {
	"filters": [
		// {
		// fieldname: "nrv_date",
		// label: __("NRV As On Date"),
		// fieldtype: "Date",
		// default: frappe.datetime.get_today()
		// },
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
			default: '2025-06-30'
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 0,
            on_change: function () {
				let company = frappe.query_report.get_filter_value("company");
				let branch_filter = frappe.query_report.get_filter("branch");
				if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
					branch_filter.df.hidden = 0;
					branch_filter.toggle(true);
				} else {
					branch_filter.df.hidden = 1;
					branch_filter.toggle(false);
				}
                frappe.query_report.refresh();
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
			fieldname: "location",
			label: __("Location"),
			fieldtype: "MultiSelectList",
			options: "Location",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Location", txt);
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
		// 	fieldname: "item",
		// 	label: __("Department"),
		// 	fieldtype: "MultiSelectList",
		// 	options: "Department",
		// 	reqd: 0,
		// 	get_data: function (txt) {
		// 		return frappe.db.get_link_options("Department", txt);
		// 	}
		// },
    

		// {
		// 	fieldname: "status",
		// 	label: __("Status"),
		// 	fieldtype: "Select",
		// 	reqd: 0
		// }
	],

	onload: function (report) {

		//  ##### To set branch filter only visible for gurukrupa filter ############
		let company = report.get_filter_value("company");
		let branch_filter = report.get_filter("branch");
		if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
			branch_filter.df.hidden = 0;
			branch_filter.toggle(true);
		} else {
			branch_filter.df.hidden = 1;
			branch_filter.toggle(false);
		}

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
// 	    frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "User",
//             name: frappe.session.user
//         },
//         callback: function (user_res) {
//             const roles = user_res.message.roles.map(role => role.role);
//             const isSystemManager = roles.includes("System Manager");

//         if (isSystemManager) {
//             // If System Manager, fetch all distinct branches 
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Branch",
//                     fields: ["name"],
//                     limit_page_length: 1000
//                 },
//                 callback: function (branch_res) {
//                     const branches = (branch_res.message || []).map(b => b.name);
//                     const branch_filter = report.get_filter("branch");

//                     if (branch_filter) {
//                         branch_filter.df.options = branches;
//                         branch_filter.refresh();
//                     }
//                 }
//             });
//         } else {
//             // For regular users, fetch branch from Employee record
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Employee",
//                     filters: { user_id: frappe.session.user },
//                     fields: ["branch"]
//                 },
//                 callback: function (emp_res) {
//                     const branches = (emp_res.message || []).map(e => e.branch).filter(b => !!b);
//                     const branch_filter = report.get_filter("branch");

//                     if (branch_filter) {
//                         branch_filter.df.options = branches;
//                         branch_filter.refresh();

//                         if (branches.length === 1) {
//                             branch_filter.set_value(branches[0]);
//                         }
//                     }
//                 }
//             });
//         }
//     }
// });

}
}