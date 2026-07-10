frappe.query_reports["Batch Wise Purchase Cycle"] = {
    filters: [
        {
            fieldname: "material_request_id",
            label: __("MR ID"),
            fieldtype: "Link",
            options: "Material Request",
        },
        {
            fieldname: "po_id",
            label: __("PO ID"),
            fieldtype: "Link",
            options: "Purchase Order",
        },
        {
            fieldname: "pr_id",
            label: __("PR ID"),
            fieldtype: "Link",
            options: "Purchase Receipt",
        },
        {
            fieldname: "pi_id",
            label: __("PI ID"),
            fieldtype: "Link",
            options: "Purchase Invoice",
        },
        {
            fieldname: "item",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "batch_no",
            label: __("Batch No"),
            fieldtype: "Link",
            options: "Batch",
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
        },
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
    ],

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (column.fieldname === "pi_id" && data.pi_id) {
            return `<span style="font-weight:600;">${value}</span>`;
        }

        if (column.fieldname === "pr_id" && data.pr_id) {
            return `<span style="font-weight:600;">${value}</span>`;
        }

        return value;
    }
};
