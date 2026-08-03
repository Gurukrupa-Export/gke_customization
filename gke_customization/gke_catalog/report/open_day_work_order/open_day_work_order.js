// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt


frappe.query_reports["Open Day Work Order"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
        },
        {
            fieldname: "operation",
            label: __("Current Process"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_list("Employee IR", {
                    fields: ["operation"],
                    group_by: "operation",
                    filters: {
                        operation: ["is", "set"]
                    },
                    order_by: "operation"
                }).then(r => {
                    return r
                        .filter(d => d.operation)
                        .map(d => ({
                            value: d.operation,
                            description: ""
                        }));
                });
            }
        },
        {
            fieldname: "employee",
            label: __("Worker"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Employee", txt);
            }
        },
        {
            fieldname: "manufacturing_work_order",
            label: __("Manufacturing Work Order"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options(
                    "Manufacturing Work Order",
                    txt
                );
            }
        }
    ],


    formatter: function(value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);


        if (
            column.fieldname === "batch_no" &&
            data.item_image
        ) {

            return `
                <span 
                    class="mwo-image-hover"
                    data-image="${data.item_image}">
                    ${value}
                </span>
            `;
        }

        return value;
    },


    onload: function(report) {


        report.page.add_inner_button(
            __("Clear Filter"),
            function() {

                report.filters.forEach(function(filter) {

                    let field = report.get_filter(filter.fieldname);

                    if (
                        field &&
                        field.df.fieldtype === "MultiSelectList"
                    ) {
                        field.set_value([]);

                    } else if (
                        field &&
                        field.df.default
                    ) {
                        field.set_value(
                            field.df.default
                        );

                    } else if(field) {
                        field.set_value("");
                    }

                });

                report.refresh();
            }
        );


        $(document).on(
            "mouseenter",
            ".mwo-image-hover",
            function() {

                let image = $(this).data("image");

                if (!image)
                    return;


                frappe.ui.tooltip(
                    $(this),
                    `<img src="${image}" 
                    style="max-width:250px;max-height:250px;">`
                );
            }
        );

    }
};