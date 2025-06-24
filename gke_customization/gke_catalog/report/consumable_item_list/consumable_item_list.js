// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Consumable Item List"] = {
  filters: [
     
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
		// {
     
    ],

    onload: function(report) {


     let company = report.get_filter_value("company");
		let branch_filter = report.get_filter("branch");
		if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
			branch_filter.df.hidden = 0;
			branch_filter.toggle(true);
		} else {
			branch_filter.df.hidden = 1;
			branch_filter.toggle(false);
		}

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
}
}







