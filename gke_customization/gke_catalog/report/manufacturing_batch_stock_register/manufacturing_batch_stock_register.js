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

        report.page.add_inner_button(__("1. Batch Count"), () => _switch_tab("count"));
        report.page.add_inner_button(__("2. Batch Gold"), () => _switch_tab("gold"));
        report.page.add_inner_button(__("3. Batch Diamond"), () => _switch_tab("diamond"));
        report.page.add_inner_button(__("4. Batch Stone"), () => _switch_tab("stone"));
        report.page.add_inner_button(__("5. Batch Finding"), () => _switch_tab("finding"));

        setTimeout(_highlight_tab, 500);
    },

    // Runs after EVERY render — server loads (any filter change / refresh) and
    // tab switches alike. Each row from the server carries all four materials
    // (count_*, gold_*, diamond_*, stone_*, finding_*), so the displayed columns are always
    // re-derived from the rows just loaded; nothing is cached between runs. A
    // fresh server load arrives with Gold in the display columns, so if another
    // tab is active it is re-applied here. Once applied the rows match and this
    // returns without re-rendering again.
    after_datatable_render: function () {
        const data = frappe.query_report.data || [];
        const key = _active_tab();
        if (data.some(row => DISPLAY_FIELDS.some(f => (row[f] ?? null) !== (row[`${key}_${f}`] ?? null)))) {
            _switch_tab(key);
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
// Tabs — pure client-side, no server call
// ---------------------------------------------------------------------------
var DISPLAY_FIELDS = ["opening", "issue", "receive", "closing"];
var TAB_LABELS = {
    count:   "1. Batch Count",
    gold:    "2. Batch Gold",
    diamond: "3. Batch Diamond",
    stone:   "4. Batch Stone",
    finding: "5. Batch Finding",
};

function _active_tab() {
    return frappe.query_report._active_tab || "gold";
}

function _switch_tab(key) {
    const qr = frappe.query_report;
    qr._active_tab = key;
    _highlight_tab();

    if (!qr.data) return;

    // Map each row's display fields to the selected material type, from the
    // rows currently loaded (they keep every material's own fields).
    qr.data = qr.data.map(row => {
        const mapped = { ...row };
        DISPLAY_FIELDS.forEach(f => { mapped[f] = row[`${key}_${f}`] ?? null; });
        return mapped;
    });

    qr.render_datatable();
}

function _highlight_tab() {
    const buttons = frappe.query_report.page.inner_toolbar.find(".btn");
    buttons.css({ "font-weight": "normal", "background": "" });
    buttons
        .filter((_, el) => $(el).text().trim() === __(TAB_LABELS[_active_tab()]))
        .css({ "font-weight": "bold", "background": "#c8e6c9" });
}
