frappe.query_reports["Advance Bagging For Customer Job Work Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 0
        },
        {
            "fieldname": "bom_id",
            "label": __("BOM ID"),
            "fieldtype": "Link",
            "options": "BOM",
            "reqd": 0
        },
        {
            "fieldname": "design_code",
            "label": __("Design Code"),
            "fieldtype": "Link",
            "options": "Item",
            "reqd": 0
        },
        {
            "fieldname": "item_category",
            "label": __("Item Category"),
            "fieldtype": "MultiSelectList",
            "reqd": 0,
            "get_data": function(txt) {
                return frappe.db.get_list("BOM", {
                    fields: ["distinct item_category as value"],
                    filters: {"bom_type": "Template"}
                }).then(r => {
                    return r
                        .filter(d => d.value)
                        .map(d => {
                            return { value: d.value, description: "" };
                        });
                });
            }
        },
        {
            "fieldname": "item_sub_category",
            "label": __("Item Sub Category"),
            "fieldtype": "MultiSelectList",
            "reqd": 0,
            "get_data": function(txt) {
                return frappe.db.get_list("BOM", {
                    fields: ["distinct item_subcategory as value"],
                    filters: {"bom_type": "Template"}
                }).then(r => {
                    return r
                        .filter(d => d.value)
                        .map(d => {
                            return { value: d.value, description: "" };
                        });
                });
            }
        }
    ],

    onload: function(report) {
        report.page.add_inner_button(__("Clear Filters"), function() {
            report.filters.forEach(function(filter) {
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
};
