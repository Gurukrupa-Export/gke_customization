// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department IR Report"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: __("Issue Date"),
            fieldtype: "Date",
            reqd: 0,
            // default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("Receive Date"),
            fieldtype: "Date",
            reqd: 0,
            // default: frappe.datetime.month_end()
        },
        {
            fieldname: "current_department",
            label: __("From Department"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Department", txt);
            }
        },
        {
            fieldname: "next_department",
            label: __("To Department"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Department", txt);
            }
        },
        // {
        //     fieldname: "manufacturing_work_order_id",
        //     label: __("Manufacturing Work Order"),
        //     fieldtype: "MultiSelectList",
        //     options: "Manufacturing Work Order",
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return new Promise((resolve) => {
        //             frappe.call({
        //                 method: "frappe.desk.search.search_link",
        //                 args: {
        //                     doctype: "Manufacturing Work Order",
        //                     txt: txt,
        //                     page_length: 10
        //                 }
        //             }).then(response => {
        //                 resolve((response.message || []).map(d => ({
        //                     value: d.value,
        //                     label: d.label
        //                 })));
        //             });
        //         });
        //     }
        // },
  
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

        const issueDate = report.get_filter("from_date");
		const receiveDate = report.get_filter("to_date");
	
		function toggleDateFilter(activeField, passiveField) {
			activeField.$wrapper.on("change", function () {
				const activeValue = activeField.get_value();
				passiveField.$wrapper.find("input").prop("disabled", !!activeValue);
			});
		}
	
		toggleDateFilter(issueDate, receiveDate);
		toggleDateFilter(receiveDate, issueDate);
            
        }}