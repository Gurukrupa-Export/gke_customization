// Copyright (c) 2024, Gurukrupa Export Private Limited and contributors
// For license information, please see license.txt

const DIAMOND_ASSORTMENT_REPORT_NAME = "Diamond Assortment Report";

frappe.query_reports[DIAMOND_ASSORTMENT_REPORT_NAME] = {
    onload: function (report) {
        dar_setup_prepared_report_loader(report);
    },

    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        }
    ]
};

/* ---------------- Prepared report loader ---------------- */

function dar_setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._dar_loader_ready) return;
    report._dar_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function () {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== DIAMOND_ASSORTMENT_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                dar_start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };

    report.refresh = function () {
        if (this.report_name === DIAMOND_ASSORTMENT_REPORT_NAME && this._dar_loading) {
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
        if (report._dar_loading && data && data.name === report._dar_loading) {
            dar_stop_prepared_report_loader(report, "Completed");
        }
    });
}

function dar_start_prepared_report_loader(report, prepared_report_name) {
    report._dar_loading = prepared_report_name;
    dar_show_prepared_report_overlay(report);

    clearInterval(report._dar_poll);
    report._dar_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== DIAMOND_ASSORTMENT_REPORT_NAME) {
            dar_stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    dar_stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => dar_stop_prepared_report_loader(report));
    }, 4000);
}

function dar_stop_prepared_report_loader(report, status, error_message) {
    if (!report._dar_loading) return;
    clearInterval(report._dar_poll);
    report._dar_loading = null;
    dar_hide_prepared_report_overlay(report);

    if (report.report_name !== DIAMOND_ASSORTMENT_REPORT_NAME) return;

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

function dar_show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".dar-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="dar-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes dar-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:dar-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function dar_hide_prepared_report_overlay(report) {
    report.page.main.find(".dar-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}