// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Item and BOM Mismatch"] = {
    tree: true,
    name_field: "item_code",
    parent_field: "parent",
    initial_depth: 0,

    filters: [
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
            width: "180px"
        },
        {
            fieldname: "bom_code",
            label: __("BOM Code"),
            fieldtype: "Link",
            options: "BOM",
            width: "180px"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        if (!data) return default_formatter(value, row, column, data);

        // Preserve tree arrow structure
        if (column.fieldname === "item_code") {
            let margin_left = data.indent ? (data.indent * 15) + "px" : "0px";
            return `<span style="margin-left:${margin_left};"></span>` + default_formatter(value, row, column, data);
        }

        // Show image HTML as-is
        if (column.fieldname === "image") {
            return value || "";
        }

        // Show link for BOM ID if not blank
        if (column.fieldname === "bom_name" && value) {
            return `<a href="/app/bom/${encodeURIComponent(value)}" target="_blank" style="color:#00aaff;text-decoration:none;">${value}</a>`;
        }

        // --- Row color styling ---
        let bg = "";
        if (data.indent === 0) {
            // Item row
            bg = "background-color:#1a1a1a;color:#fff;";
        } else if (data.indent === 1) {
            // BOM row
            bg = "background-color:#222;color:#ffcccc;";
        }

        let content = value || default_formatter(value, row, column, data);
        return `<div style="${bg}padding:4px;">${content}</div>`;
    }
};
