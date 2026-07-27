// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Manufacturing Operations Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "item_category",
            label: __("Item Category"),
            fieldtype: "Link",
            options: "Item Group",
        },
        {
            fieldname: "setting_type",
            label: __("Setting Type"),
            fieldtype: "Select",
            options: "\nOpen\nClose",
        },
        {
            fieldname: "sub_setting_type",
            label: __("Sub Setting Type"),
            fieldtype: "Link",
            options: "Attribute Value",
            get_query: function () {
                return {
                    filters: {
                        is_sub_setting_type: 1
                    }
                };
            },
        },
    ],

    // onload: function (report) {
    //     const load_options = () => {
    //         const options = new Set([""]);

    //         (report.data || []).forEach((row) => {
    //             if (row.sub_setting_type && row.sub_setting_type !== "Grand Total") {
    //                 options.add(row.sub_setting_type);
    //             }
    //         });

    //         const f = report.get_filter("setting_type");
    //         if (f) {
    //             f.df.options = Array.from(options).join("\n");
    //             f.refresh();
    //         }
    //     };

    //     load_options();

    //     report.page.wrapper.on("click", ".btn-primary", function () {
    //         setTimeout(load_options, 800);
    //     });
    // },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        if (data.is_grand_total) {
            value = `<span style="font-weight:700; background-color:#bbf7d0; display:block; padding:2px 6px;">${value}</span>`;
        } else if (data.is_total || data.bold) {
            value = `<span style="font-weight:600; background-color:#fef3c7; display:block; padding:2px 6px;">${value}</span>`;
        }

        return value;
    },
};