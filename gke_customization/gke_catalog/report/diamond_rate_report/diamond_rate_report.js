// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const DIAMOND_RATE_REPORT_NAME = "Diamond Rate Report";

frappe.query_reports[DIAMOND_RATE_REPORT_NAME] = {
    onload: function (report) {
        drr_setup_prepared_report_loader(report);
    },

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -2)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            on_change: function(report) {
                report.set_filter_value("branch", "");
                report.refresh();
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let filters = {};
                if (company) {
                    filters.company = company;
                }
                return {
                    filters: filters
                };
            }
        }
    ]
};

/* ---------------- Prepared report loader ---------------- */

function drr_setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._drr_loader_ready) return;
    report._drr_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function () {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== DIAMOND_RATE_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                drr_start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };

    report.refresh = function () {
        if (this.report_name === DIAMOND_RATE_REPORT_NAME && this._drr_loading) {
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
        if (report._drr_loading && data && data.name === report._drr_loading) {
            drr_stop_prepared_report_loader(report, "Completed");
        }
    });
}

function drr_start_prepared_report_loader(report, prepared_report_name) {
    report._drr_loading = prepared_report_name;
    drr_show_prepared_report_overlay(report);

    clearInterval(report._drr_poll);
    report._drr_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== DIAMOND_RATE_REPORT_NAME) {
            drr_stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    drr_stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => drr_stop_prepared_report_loader(report));
    }, 4000);
}

function drr_stop_prepared_report_loader(report, status, error_message) {
    if (!report._drr_loading) return;
    clearInterval(report._drr_poll);
    report._drr_loading = null;
    drr_hide_prepared_report_overlay(report);

    if (report.report_name !== DIAMOND_RATE_REPORT_NAME) return;

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

function drr_show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".drr-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="drr-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes drr-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:drr-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function drr_hide_prepared_report_overlay(report) {
    report.page.main.find(".drr-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}