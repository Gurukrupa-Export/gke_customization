// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Order Detailed Count"] = {
	"filters": [
		{
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
        },
		{
            fieldname: "order_id",
            label: __("Order"),
            fieldtype: "MultiSelectList",
            options: "Order Form",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Order Form", txt);
            }
        },
		{
            fieldname: "company",
            label: __("Company"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
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
                },
        },

        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            options: "Customer",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Customer", txt);
                },
        },
		{
            fieldname: "diamond_quality",
            label: __("Diamond Quality"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
		
		{
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
	],
	onload: function(report) {
    //     const customText = '<div style="text-align: center; left-padding: 8px; font-weight: bold; font-size: 15px; color:rgb(100, 151, 197) ;">Note: The standard deadline for this process is 2 days.</div>';
        
    //    // const customText = '<div style="text-align: center; padding-left: 8px; font-weight: bold; font-size: 15px; color: rgb(100, 151, 197);">Note: The standard deadline for this process is 2 days.<br>Time Difference = Creation time - Status time.</div>';

    //     $(report.page.wrapper).find('.page-form').after(customText);
        
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
		fetchOptions("Order","diamond_quality", "diamond_quality",true);
		fetchOptions("Order", "workflow_state", "status",true);
	
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
