// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Manufacturing Batch Stock Register"] = {

    filters: [
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
            reqd: 1,
        },
    ],

    onload: function (report) {
        // Only System Manager / Administrator can view/change other departments.
        // Everyone else is locked to their own default (Employee) department.
        // Resolved server-side (not via a direct Employee lookup) since most
        // report users don't have read permission on the Employee doctype.
        frappe.call({
            method: "gke_customization.gke_catalog.report.manufacturing_batch_stock_register.manufacturing_batch_stock_register.get_user_department_filter",
            callback: function (r) {
                var res = r.message || {};
                if (res.can_change_department) return;

                var filter = report.get_filter("department");
                if (!filter) return;

                filter.set_value(res.department || "");
                filter.df.read_only = 1;
                filter.df.get_query = null;
                filter.refresh();
            }
        });

        const tabs = [
            { label: "1. Batch Count",   key: "count"   },
            { label: "2. Batch Gold",    key: "gold"    },
            { label: "3. Batch Diamond", key: "diamond" },
            { label: "4. Batch Stone",   key: "stone"   },
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
    const allData = frappe.query_report._all_data;
    if (!allData) return;

    // Map each row's display fields to the selected material type
    frappe.query_report.data = allData.map(row => ({
        ...row,
        opening: row[`${key}_opening`] || 0,
        issue:   row[`${key}_issue`]   || 0,
        receive: row[`${key}_receive`] || 0,
        closing: row[`${key}_closing`] || 0,
    }));

    // Re-render datatable with new values — no server call
    frappe.query_report.render_datatable();
}