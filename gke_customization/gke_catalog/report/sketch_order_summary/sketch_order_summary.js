
// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sketch Order Summary"] = {
       filters: [
       {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
            reqd: 0
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0
        },
         {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
           // default: frappe.defaults.get_user_default("branch")
        },
        {
            fieldname: "customer_group",
            label: __("Customer Group"),
            fieldtype: "Link",
            options: "Customer Group"
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        }
    ],

 formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (column.fieldname === "customer_codes") {
        return "";
    }

    const drill_fields = [
        "sof_draft", "sof_submitted", "sof_cancelled",
        "so_draft", "so_submitted", "so_cancelled"
    ];

    if (!drill_fields.includes(column.fieldname)) {
        return value;
    }

    if (!value || parseInt(value) === 0) {
        return value;
    }

    const params = new URLSearchParams();
    const filter_keys = ["from_date", "to_date", "branch"];
    filter_keys.forEach(key => {
        const filter_value = frappe.query_report.get_filter_value(key);
        if (filter_value) {
            params.append(key, filter_value);
        }
    });

if (column.fieldname === "sof_draft" || column.fieldname === "sof_cancelled") {
    params.append("docstatus", column.fieldname === "sof_draft" ? 0 : 2);

    const from = frappe.query_report.get_filter_value("from_date");
    const to = frappe.query_report.get_filter_value("to_date");
    if (from && to) {
        params.append("order_date", JSON.stringify(["Between", [from, to]]));
    }

    if (data.customer_codes) {
        const customers = data.customer_codes
            .split(',')
            .map(c => c.trim())
            .filter(Boolean);

        if (customers.length > 0) {
            params.append("customer_code", JSON.stringify(["in", customers]));
        }
    }

    const url = `/app/sketch-order-form?${params.toString()}`;
    return `<a href="${url}" target="_blank" style="text-decoration: inherit; color: inherit;">${value}</a>`;
}


    const report_name = "Sketch Order Detail";

    if (data.customer_codes) {
        params.append("customer", data.customer_codes);
    }

 //   if (column.fieldname === "sof_submitted") params.append("docstatus", 1);
    if (column.fieldname === "so_draft") params.append("docstatus", 0);
    if (column.fieldname === "so_submitted") params.append("docstatus", 1);
    if (column.fieldname === "so_cancelled") params.append("workflow_state", "Cancelled");

    const url = `/app/query-report/${encodeURIComponent(report_name)}?${params.toString()}`;
    return `<a href="${url}" target="_blank" style="text-decoration: inherit; color: inherit;">${value}</a>`;
},

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
},
// formatter: function (value, row, column, data, default_formatter) {
//     // Only make clickable links for non-zero values
//     if (value > 0) {
//         return `<a href="/app/query-report/Sketch Order Detail">${value}</a>`;
//     }

//     return default_formatter(value, row, column, data);
// }};
}



