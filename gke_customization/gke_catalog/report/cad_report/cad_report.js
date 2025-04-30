// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["CAD Report"] = {
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
            options: "Order",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Order", txt);
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
            get_data: function(txt) {
                return frappe.db.get_list("Branch", {
                    fields: ["branch_name as value", "name as description"],  
                    filters: {
                        "branch_name": ["like", `%${txt}%`]
                    },
                    limit: 20
                });
            }
        },

        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            options: "Customer",
            reqd: 0,
            get_data: function (txt) {
                return frappe.db.get_list("Customer", {
                    fields: ["name as value", "customer_name as description"], 
                    filters: {
                        "customer_name": ["like", `%${txt}%`]
                    },
                });
            }
        },
		{
            fieldname: "setting_type",
            label: __("Setting Type"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Order", {
                    fields: ["distinct setting_type as value"],
                    filters: [
                        ["setting_type", "not in", ["Close Setting", "Close", " "]],
                        ["setting_type", "like", `%${txt}%`]
                    ],
                    limit: 20
                }).then(r => {
                    return r.map(d => {
                        return {
                            value: d.value,
                            description: ""  // manually adding empty description
                        }
                    });
                });
            }
        },
     
		
        {
            fieldname: "employee",
            label: __("User"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                const allowed_ids = [
                    "HR-EMP-00968",
                    "HR-EMP-00222",
                    "HR-EMP-00957",
                    "HR-EMP-00254",
                    "HR-EMP-00935",
                    "HR-EMP-02452"
                ];
        
                return frappe.db.get_list("Employee", {
                    fields: ["employee_name as value","name as description"],
                    filters: [
                        ["name", "in", allowed_ids],
                        ["employee_name", "like", `%${txt}%`]
                    ],
                    limit: 20
                });
            }
        },
        
		
		{
            fieldname: "status",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Order", {
                    fields: ["distinct workflow_state as value"],
                }).then(r => {
                    return r.map(d => {
                        return {
                            value: d.value,
                            description: ""  // manually adding empty description
                        }
                    });
                });
            }
        },

        {
        fieldname: "workflow_type",
        label: __("Workflow Type"),
        fieldtype: "MultiSelectList",
        options: [],
        reqd: 0,
        get_data: function(txt) {
            return frappe.db.get_list("Order", {
                fields: ["distinct workflow_type as value"],
            }).then(r => {
                return r.map(d => {
                    return {
                        value: d.value,
                        description: ""  // manually adding empty description
                    }
                });
            });
        }
    },
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
		fetchOptions("Order", "workflow_state", "status",true);
      //  fetchOptions("Order Form", "po_no", "customer_po",true);
	    fetchOptions("Order", "setting_type", "setting_type",false)
        fetchOptions("Order", "workflow_type", "workflow_type",true);;




	
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
