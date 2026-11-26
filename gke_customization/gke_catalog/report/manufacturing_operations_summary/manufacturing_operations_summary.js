// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt
const LOADER_REPORT_NAME = "Manufacturing Operations Summary";
frappe.query_reports["Manufacturing Operations Summary"] = {
    onload: function(report) {
        setup_prepared_report_loader(report);
	},
    filters: [
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "item_category",
            label: __("Item Category"),
            fieldtype: "Link",
            options: "Attribute Value",
        },
        {
            fieldname: "setting_type",
            label: __("Setting Type"),
            fieldtype: "Select",
            options: "\nOpen\nClose\nNova Glow",
        },
        {
            fieldname: "sub_setting_type",
            label: __("Sub Setting Type"),
            fieldtype: "Link",
            options: "Attribute Value",
            get_query: function () {
                return {
                    filters: {
                        is_sub_setting_type: 1
                    }
                };
            },
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
    ],

    // onload: function (report) {
    //     const load_options = () => {
    //         const options = new Set([""]);

    //         (report.data || []).forEach((row) => {
    //             if (row.sub_setting_type && row.sub_setting_type !== "Grand Total") {
    //                 options.add(row.sub_setting_type);
    //             }
    //         });

    //         const f = report.get_filter("setting_type");
    //         if (f) {
    //             f.df.options = Array.from(options).join("\n");
    //             f.refresh();
    //         }
    //     };

    //     load_options();

    //     report.page.wrapper.on("click", ".btn-primary", function () {
    //         setTimeout(load_options, 800);
    //     });
    // },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        const is_dark = document.documentElement.getAttribute("data-theme") === "dark";

        if (data.is_grand_total) {
            const bg = is_dark ? "#14532d" : "#bbf7d0";
            const color = is_dark ? "#dcfce7" : "#14532d";
            value = `<span style="font-weight:700; background-color:${bg}; color:${color}; display:block; padding:2px 6px;">${value}</span>`;
        } else if (data.is_total || data.bold) {
            const bg = is_dark ? "#78350f" : "#fef3c7";
            const color = is_dark ? "#fef3c7" : "#78350f";
            value = `<span style="font-weight:600; background-color:${bg}; color:${color}; display:block; padding:2px 6px;">${value}</span>`;
        }

        return value;
    },
};
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