// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Order Summary by Branch, Category & Material"] = {
    filters: [
   
     {
      fieldname: "group_by_type",
      label: "Group By",
      fieldtype: "Select",
      options: [" ","Category", "Branch", "Diamond Target Range", "Metal Target Range"],
      reqd: 1
	// default: "Category",
    //   on_change: function (query_report) {
    //     const group_by = frappe.query_report.get_filter_value("group_by_type");
    //     frappe.query_report.toggle_filter_display("subcategory", group_by?.toLowerCase() === "branch");
    //     frappe.query_report.refresh();
    //   }
    },
     {
			fieldname: "subcategory",
			label: __("Sub Category"),
			fieldtype: "MultiSelectList",
			options: [],
			reqd: 0,
			get_data: function(txt) {
				return frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Sketch Order",
						fields: ["subcategory"],
						limit_page_length: 1000,
					}
				}).then(r => {
					const unique = [...new Set(
						(r.message || []).map(d => d.subcategory).filter(v => v && v.trim() !== "")
					)];
					return unique.map(val => ({
						value: val,
						description: ""
					}));
				});
			}
		}
  ],
//    onload: function (report) {
//     const group_by = frappe.query_report.get_filter_value("group_by_type");
//     frappe.query_report.toggle_filter_display("subcategory", group_by?.toLowerCase() === "branch");
//   }
  
      }




