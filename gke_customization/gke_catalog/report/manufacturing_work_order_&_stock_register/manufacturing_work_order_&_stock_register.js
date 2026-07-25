// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Manufacturing Work Order & Stock Register"] = {

    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            read_only: frappe.user.has_role("System Manager") ? 0 : 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        
    ],

    onload: function (report) {
        const tabs = [
            { label: "1. WO Count",   key: "count"   },
            { label: "2. WO Gold",    key: "gold"    },
            { label: "3. WO Diamond", key: "diamond" },
            { label: "4. WO Stone",   key: "stone"   },
        ];

        tabs.forEach(tab => {
            report.page.add_inner_button(__(tab.label), () => {
                _switch_tab(tab.key);

                // Highlight active button
                report.page.inner_toolbar.find(".btn").css({ "font-weight": "normal", "background": "" });
                report.page.inner_toolbar.find(".btn")
                    .filter((_, el) => $(el).text().trim() === __(tab.label))
                    .css({ "font-weight": "bold", "background": "#c8e6c9" });
            });
        });

        // Default highlight: Batch Gold
        setTimeout(() => {
            report.page.inner_toolbar.find(".btn")
                .filter((_, el) => $(el).text().trim() === __("2. Batch Gold"))
                .css({ "font-weight": "bold", "background": "#c8e6c9" });
        }, 500);
    },

    // After server loads data — store all values for instant client-side switching
    after_datatable_render: function () {
        if (!frappe.query_report._all_data) {
            frappe.query_report._all_data = frappe.query_report.data.map(r => ({ ...r }));
        }
    },

    formatter: function (value, row, column, data, default_formatter) {
        const count_fields = ["opening", "issue", "receive", "closing"];
        if (frappe.query_report._active_tab === "count" && count_fields.includes(column.fieldname)) {
            return cint(value);
        }

        value = default_formatter(value, row, column, data);
        if (!data || column.fieldname !== "department") return value;

        if ((data.department || "").startsWith("    ")) {
            return `<span style="color:#616161;font-style:italic;padding-left:16px;">${(data.department || "").trim()}</span>`;
        }
        return `<b style="color:#1b5e20;">${data.department || ""}</b>`;
    },
};


// ---------------------------------------------------------------------------
// Switch tab — pure client-side, no server call
// ---------------------------------------------------------------------------
function _switch_tab(key) {
    const report = frappe.query_report;
    const allData = report._all_data;

    if (!allData) return;

    report._active_tab = key;

    report.data = allData.map(row => ({
        ...row,

        opening: row[`${key}_opening`] || 0,
        issue: row[`${key}_issue`] || 0,
        receive: row[`${key}_receive`] || 0,
        closing: row[`${key}_closing`] || 0,

        opening_pure: key === "gold" ? row.gold_opening_pure || 0 : 0,
        issue_pure: key === "gold" ? row.gold_issue_pure || 0 : 0,
        receive_pure: key === "gold" ? row.gold_receive_pure || 0 : 0,
        closing_pure: key === "gold" ? row.gold_closing_pure || 0 : 0,
    }));

    report.render_datatable();

    setTimeout(() => {
        toggle_pure_columns(key);
    }, 100);
}
function toggle_pure_columns(key) {

    const table = frappe.query_report.datatable;

    if (!table) return;

    const pure_fields = [
        "opening_pure",
        "issue_pure",
        "receive_pure",
        "closing_pure"
    ];

    table.columns.forEach((col, index) => {

        if (pure_fields.includes(col.id)) {

            const cells = table.wrapper.querySelectorAll(
                `.dt-cell--col-${index}`
            );

            cells.forEach(cell => {
                cell.style.display = key === "gold" ? "" : "none";
            });

        }
    });
}