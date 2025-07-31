// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employees Overtime Sheet"] = {
	   filters: [
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            options: ["", 2022, 2023, 2024, 2025, 2026],
            default: new Date().getFullYear().toString(),
            reqd: 1,
        },
		
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: ["", "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"],
            default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).toLocaleString('default', { month: 'long' }),
            reqd: 1,
        },

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Company", txt);
                },
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
            hidden:1,
			get_data: function (txt) {
				return frappe.db.get_link_options("Branch", txt);
			},
            on_change: () => frappe.query_report.refresh()
		},
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            options: [],
            get_data: function (txt) {
                return frappe.db.get_link_options("Department", txt);
                },
            default: "Information Technology - GEPL",
            reqd: 1,
            // default: frappe.defaults.get_user_default("Company"),
        },
    ],

    onload: function (report) {
        if (frappe.query_report.message) {
            const note = frappe.query_report.message;
            frappe.msgprint({
                message: note,
                indicator: 'blue'
            });
        } 
        //company -branch
        let company = report.get_filter_value("company");
		let branch_filter = report.get_filter("branch");
		if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
			branch_filter.df.hidden = 0;
			branch_filter.toggle(true);
		} else {
			branch_filter.df.hidden = 1;
			branch_filter.toggle(false);
		}

		// Code for adding a field in filter options.
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
	
		// Fetch options for filters - first param- doctype name(from where the filter options should be fetched), 
		// 2nd- fieldname, 3rd- filter name
        fetchOptions("Employee","company", "company",true);
    	// fetchOptions("Employee","department","department",true)

    //Function code to add a button on top which will clear all selections from the filter and set it to default values.
        report.page.add_inner_button(__("Clear Filter"), function () {
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
        
    }}
    

