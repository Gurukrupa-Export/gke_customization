// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const LOADER_REPORT_NAME = "Manufacturing Batch Stock Register";
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
        setup_prepared_report_loader(report);
         if (report.prepared_report_doc_name) {
            start_prepared_report_loader(report, report.prepared_report_doc_name);
        }
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

        report.page.add_inner_button(__("1. WO Count"), () => _switch_tab("count"));
        report.page.add_inner_button(__("2. WO Gold"), () => _switch_tab("gold"));
        report.page.add_inner_button(__("3. WO Diamond"), () => _switch_tab("diamond"));
        report.page.add_inner_button(__("4. WO Stone"), () => _switch_tab("stone"));
        report.page.add_inner_button(__("5. WO Finding"), () => _switch_tab("finding"));

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
    count:   "1. WO Count",
    gold:    "2. WO Gold",
    diamond: "3. WO Diamond",
    stone:   "4. WO Stone",
    finding: "5. WO Finding",
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
function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._production_loader_ready) return;
    report._production_loader_ready = true;
 
    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;
 
    report.generate_background_report = function() {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== LOADER_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };
 
    report.refresh = function() {
        if (this.report_name === LOADER_REPORT_NAME && this._production_loading) {
            frappe.show_alert({
                message: __("Report is still generating, please wait..."),
                indicator: "orange"
            }, 5);
            this.page.btn_secondary && this.page.btn_secondary.prop("disabled", true);
            return Promise.resolve();
        }
        return original_refresh.apply(this, arguments);
    };
 
    frappe.realtime.on("report_generated", (data) => {
        if (report._production_loading && data && data.name === report._production_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}
 
function start_prepared_report_loader(report, prepared_report_name) {
    report._production_loading = prepared_report_name;
    show_prepared_report_overlay(report);
 
    clearInterval(report._production_poll);
    report._production_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== LOADER_REPORT_NAME) {
            stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => stop_prepared_report_loader(report));
    }, 4000);
}
 
function stop_prepared_report_loader(report, status, error_message) {
    if (!report._production_loading) return;
    clearInterval(report._production_poll);
    report._production_loading = null;
    hide_prepared_report_overlay(report);
 
    if (report.report_name !== LOADER_REPORT_NAME) return;
 
    if (status === "Completed") {
        frappe.show_alert({ message: __("Report generated"), indicator: "green" }, 5);
        report.refresh();
    } else if (status === "Error") {
        frappe.msgprint({
            title: __("Report Generation Failed"),
            message: error_message || __("Please check the Prepared Report for details."),
            indicator: "red"
        });
    }
}
 
function show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".production-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="production-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes production-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:production-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}
 
function hide_prepared_report_overlay(report) {
    report.page.main.find(".production-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}