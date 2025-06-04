// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Leave Report"] = {
	"filters": [
      
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
			default: '2025-03-01'
            //default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
			default: '2025-05-31'
            //default: frappe.datetime.month_end(),
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "MultiSelectList",
            options: "Employee",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Employee", txt);
                },
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            options: "Department",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_link_options("Department", txt);
                },
        },

		{
            fieldname: "leave_type",
            label: __("Leave Type"),
            fieldtype: "Select",
            reqd: 0,
        },
		{
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            reqd: 0
        }
    ],
	onload: function (report) {
		//Function code to add a button on top which will clear all selections from the filter and set it to default values.
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
        fetchOptions("Leave Application","status", "status",true);
		fetchOptions("Leave Application", "leave_type", "leave_type",true);
        
		
		/*
        $(clearFilterButton).css({
            "background-color": "#17a2b8",
            "color": "white",
            "border-radius": "5px",
            "margin": "5px",
        });
        */
	}	

};
