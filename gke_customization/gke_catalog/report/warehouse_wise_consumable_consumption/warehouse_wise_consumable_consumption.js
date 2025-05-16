// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse wise Consumable Consumption"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            // default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            // default: frappe.datetime.get_today()
        },
        // {
        //     fieldname: "t_warehouse",
        //     label: __("Department"),
        //     fieldtype: "Link",
        //     options: "Warehouse"
        // },

        {
    fieldname: "t_warehouse",
    label: __("Warehouse"),
    fieldtype: "MultiSelectList",
    get_data: function(txt) {
        return frappe.db.get_list("Warehouse", {
            fields: ["name as value"],
            // limit_page_length: 1000, 
            filters: txt ? [["name", "like", `%${txt}%`]] : undefined
        }).then(r => {
            return r.map(d => ({
                value: d.value,
                description: ""
            }));
        });
    }
},

		  {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_list("Item Group", {
                    fields: ["name as value", "parent_item_group as description"],
                    filters: { "parent_item_group": "Consumable" }
                });
            }
        }
	
    ],
	onload: function (report) {
   
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
