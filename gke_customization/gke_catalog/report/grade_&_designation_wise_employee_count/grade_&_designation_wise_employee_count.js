// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Grade & Designation wise Employee count"] = {
	"filters": [
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
            hidden:1,
			get_data: function (txt) {
				return frappe.db.get_link_options("Branch", txt);
			},
            on_change: () => frappe.query_report.refresh()
		},

	],


onload: function(report) {
    if (frappe.query_report.message) {
            const note = frappe.query_report.message;
            frappe.msgprint({
                message: note,
                indicator: 'blue'
            });
        } 

        let company = report.get_filter_value("company");
		let branch_filter = report.get_filter("branch");
		if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
			branch_filter.df.hidden = 0;
			branch_filter.toggle(true);
		} else {
			branch_filter.df.hidden = 1;
			branch_filter.toggle(false);
		}
    
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
    
      fetchOptions("Employee", "manufacturer", "manufacturer",true);
    //   fetchOptions("Employee", "custom_operation", "operation",true);

	

       
        
    
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
    



		

