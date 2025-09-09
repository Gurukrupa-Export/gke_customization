// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Order Item Detail"] = {
    "filters": [
{
    fieldname: "item_group",
    label: __("Item Group"),
    fieldtype: "MultiSelectList",
    get_data: function(txt) {
        return frappe.db.get_list("Item Group", {
            fields: ["name as value", "parent_item_group as description"],
            filters: [["name", "like", "%" + txt + "%"]],
        });
    }
},
{
    fieldname: "item",
    label: __("Item"),
    fieldtype: "MultiSelectList",
    get_data: function(txt) {
        return frappe.db.get_list("Item", {
            fields: ["name as value", "item_group as description"],
            filters: [["name", "like", "%" + txt + "%"]],
        });
    }
},
{
    fieldname: "sketch_order",
    label: __("Sketch Order"),
    fieldtype: "Link",
    options:"Sketch Order",
    //hidden: 1
}

    ],

onload: function(report) {


    report.page.add_inner_button(__("← Back"), function () {
            frappe.set_route("query-report", "Sketch Order Detail");
        });

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

    document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") {
        document.querySelectorAll(".custom-image-modal").forEach(modal => {
            modal.style.display = "none";
        });
    }
});  

    const params = frappe.query_string;
    if (params.sketch_order) {
        // Filter the Item field using sketch_order
        frappe.db.get_list("Item", {
            fields: ["name"],
            filters: {
                custom_sketch_order_id: params.sketch_order
            }
        }).then(items => {
            let item_names = items.map(d => d.name);
            report.set_filter_value("item", item_names);
        });
    }
    
    
 
}
};
