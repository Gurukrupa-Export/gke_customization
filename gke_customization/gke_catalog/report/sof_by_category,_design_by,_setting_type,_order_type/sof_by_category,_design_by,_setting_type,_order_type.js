// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["SOF By Category, Design By, Setting Type, Order Type"] = {
    filters: [
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            options: ["Category", "Order Type", "Design By", "Setting Type"],  //Customer Group
            default: "Category",
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        // {
        //     fieldname: "company",
        //     label: __("Company"),
        //     fieldtype: "Link",
        //     options: "Company"
        // },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        const group_by = frappe.query_report.get_filter_value("group_by");
        const group_value = data.label;
        const from_date = frappe.query_report.get_filter_value("from_date") || "";
        const to_date = frappe.query_report.get_filter_value("to_date") || "";
        const company = frappe.query_report.get_filter_value("company") || "";
        const branch = frappe.query_report.get_filter_value("branch") || "";

        if (["total_orders", "submitted_orders", "pending_orders", "cancelled_orders"].includes(column.fieldname)) {
            
            let status_filter = "";
            if (column.fieldname === "submitted_orders") status_filter = "&docstatus=1";
            else if (column.fieldname === "pending_orders") status_filter = "&docstatus=0";
            else if (column.fieldname === "cancelled_orders") status_filter = "&docstatus=2";

            let url = `/app/sketch-order-form?view=list`
                + (from_date ? `&from_date=${from_date}` : "")
                + (to_date ? `&to_date=${to_date}` : "")
                + (company ? `&company=${company}` : "")
                + (branch ? `&branch=${branch}` : "");

            if (group_by === "Category") url += `&category=${encodeURIComponent(group_value)}`;
            else if (group_by === "Order Type") url += `&order_type=${encodeURIComponent(group_value)}`;
            else if (group_by === "Design By") url += `&design_by=${encodeURIComponent(group_value)}`;
            else if (group_by === "Setting Type") url += `&setting_type=${encodeURIComponent(group_value)}`;
           // else if (group_by === "Customer Group") url += `&customer_code=${encodeURIComponent(group_value)}`;

           // else url += `&order_type=${encodeURIComponent(group_value)}`;
            //design_by

            url += status_filter;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};

