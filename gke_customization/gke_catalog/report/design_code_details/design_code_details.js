// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Design Code Details"] = {
	"filters": [
        //    {
        //     fieldname: "item_name",
        //     label: __("Item"),
        //     fieldtype: "Link",
        //     options: "Item",
        //     reqd: 0
        // },

        // {
		// 	fieldname: "item_name",
		// 	label: __("Item"),
		// 	fieldtype: "Link",
		// 	options: "Item",
		// 	default:"NP00128",
		// 	reqd: 0,
		// 	get_query: () => {
		// 		return {
		// 			filters: {
		// 				has_variants: 1
		// 			}
		// 		};
		// 	}
		// },


        {
            fieldname: "item_name",
            label: __("Item"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function (txt) {
                return frappe.call({
                    method: "frappe.desk.search.search_link",
                    args: {
                        doctype: "Item",
                        txt: txt,
                        filters: {
                            has_variants: 1
                        },
                        page_length: 20
                    }
                }).then(r => {
                    return (r.message || []).map(item => ({
                        value: item.value,
                        description: item.description
                    }));
                });
            }
        },



        // {
        //     fieldname: "item_name",
        //     label: __("Item"),
        //     fieldtype: "MultiSelectList",
        //     reqd: 0,
        //     get_data: function (txt) {
        //         return frappe.db.get_list("Item", {
        //             fields: ["name", "item_name", "item_group"],
        //             filters: {
        //                 name: ["like", `%${txt}%`],
        //                 has_variants: 1
        //             },
        //             distinct: true,
        //             limit: 20
        //         }).then(items => {
        //             return items
        //                 .filter(item => item.name)
        //                 .map(item => ({
        //                     value: item.name,
        //                     description: `${item.item_name || ''}, ${item.item_group || ''}`
        //                 }));
        //         });
        //     }
        // }


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

	}

};
