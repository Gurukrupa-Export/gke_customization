// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Attrition and Retention Report"] = {
	"filters": [

        {
            fieldname: "from_date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 0,
            default:'2024-01-01',
            // default: frappe.datetime.get_today(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default:'2024-12-31'
            // default: frappe.datetime.month_end(),
        },

        // {
        //     fieldname: "company",
        //     label: __("Company"),
        //     fieldtype: "MultiSelectList",
        //     options: "Company",
        //     reqd: 0,
        //     get_data: function (txt) {
        //         return frappe.db.get_link_options("Company", txt);
        //         },
        //     // default: frappe.defaults.get_user_default("Company"),
        // },
        // {
        //     fieldname: "branch",
        //     label: __("Branch"),
        //     fieldtype: "MultiSelectList",
        //     options: "Branch",
        //     reqd: 0,
        //     get_data: function (txt) {
        //         return frappe.db.get_link_options("Branch", txt);
        //         },
        //     // default: frappe.defaults.get_user_default("Company"),
        // },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            options: "Department",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Department", txt);
                },
            // default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        // {
        //     label: __("Designation"),
        //     fieldname: "designation",
        //     fieldtype: "MultiSelectList",
        //     options: "Designation",
        //     reqd: 0,
        //     get_data: function (txt) {
        //         return frappe.db.get_link_options("Designation", txt);
        //         },

        // }
    ],
    
    onload: function(report) {
        // const customText = '<div style="text-align: center; left-padding: 8px; font-weight: bold; font-size: 15px; color:rgb(100, 151, 197) ;">Note: The standard deadline for this process is 2 days.</div>';
        // $(report.page.wrapper).find('.page-form').after(customText);
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
	
		// Fetch options for filters
		// fetchOptions("Item","item_category", "category",true);
        
        fetchOptions("Employee", "status", "status",true);



	
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
	}
	} ;
