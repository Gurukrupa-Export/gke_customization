// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Advance Bagging Report From MR"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 0,
            default:frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 0,
            default:frappe.datetime.month_end(),

        },
        {
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 0
		},
        {
            label: "Material Type",
            fieldname: "material_type",
            fieldtype: "Select",
            options: ["", "Diamond", "Metal", "Gemstone", "Finding", "Others"],
            reqd: 0
        },
        {
            label: "Parent Manufacturing Order",
            fieldname: "manufacturing_order",
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Parent Manufacturing Order", txt);
            }
        },
       {
    fieldname: "item_category",
    label: __("Category"),
    fieldtype: "MultiSelectList",
    options: [],
    reqd: 0,
    get_data: function(txt) {
        return frappe.db.get_list("Parent Manufacturing Order", {
            fields: ["distinct item_category as value"],
        }).then(r => {
            return r
                .filter(d => d.value)  // Removes null, undefined, empty strings
                .map(d => {
                    return {
                        value: d.value,
                        description: ""
                    }
                });
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
                return frappe.db.get_list("Parent Manufacturing Order", {
                    fields: ["distinct setting_type as value"],
                }).then(r => {
            return r
                .filter(d => d.value)  // Removes null, undefined, empty strings
                .map(d => {
                    return {
                        value: d.value,
                        description: ""
                    }
                });
        });
    }
},
    ],
     onload: function(report) {

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
}

