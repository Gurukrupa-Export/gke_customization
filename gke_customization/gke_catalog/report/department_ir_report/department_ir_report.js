// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

const DEPARTMENT_IR_REPORT_NAME = "Department IR Report";

frappe.query_reports[DEPARTMENT_IR_REPORT_NAME] = {
    "filters": [
        {
            fieldname: "from_date",
            label: __("Issue Date"),
            fieldtype: "Date",
            reqd: 0,
            // default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("Receive Date"),
            fieldtype: "Date",
            reqd: 0,
            // default: frappe.datetime.month_end()
        },
        {
            fieldname: "current_department",
            label: __("From Department"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Department", txt);
            }
        },
        {
            fieldname: "next_department",
            label: __("To Department"),
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Department", txt);
            }
        },
        // {
        //     fieldname: "manufacturing_work_order_id",
        //     label: __("Manufacturing Work Order"),
        //     fieldtype: "MultiSelectList",
        //     options: "Manufacturing Work Order",
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return new Promise((resolve) => {
        //             frappe.call({
        //                 method: "frappe.desk.search.search_link",
        //                 args: {
        //                     doctype: "Manufacturing Work Order",
        //                     txt: txt,
        //                     page_length: 10
        //                 }
        //             }).then(response => {
        //                 resolve((response.message || []).map(d => ({
        //                     value: d.value,
        //                     label: d.label
        //                 })));
        //             });
        //         });
        //     }
        // },

    ],

    onload: function(report) {
        // Loader for prepared / background report generation
        dir_setup_prepared_report_loader(report);

        report.page.add_inner_button(__("Clear Filter"), function () {
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);
                if (field.df.fieldtype === "MultiSelectList") {
                    field.set_value([]);
                } else if (field.df.default) {
                    field.set_value(field.df.default);
                } else {
                    field.set_value("");
                }
            });
        });

        const issueDate = report.get_filter("from_date");
        const receiveDate = report.get_filter("to_date");

        function toggleDateFilter(activeField, passiveField) {
            activeField.$wrapper.on("change", function () {
                const activeValue = activeField.get_value();
                passiveField.$wrapper.find("input").prop("disabled", !!activeValue);
            });
        }

        toggleDateFilter(issueDate, receiveDate);
        toggleDateFilter(receiveDate, issueDate);
    }
};

/* ---------------- Prepared report loader ---------------- */

function dir_setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._dir_loader_ready) return;
    report._dir_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function () {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== DEPARTMENT_IR_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                dir_start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };

    report.refresh = function () {
        if (this.report_name === DEPARTMENT_IR_REPORT_NAME && this._dir_loading) {
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
        if (report._dir_loading && data && data.name === report._dir_loading) {
            dir_stop_prepared_report_loader(report, "Completed");
        }
    });
}

function dir_start_prepared_report_loader(report, prepared_report_name) {
    report._dir_loading = prepared_report_name;
    dir_show_prepared_report_overlay(report);

    clearInterval(report._dir_poll);
    report._dir_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== DEPARTMENT_IR_REPORT_NAME) {
            dir_stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    dir_stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => dir_stop_prepared_report_loader(report));
    }, 4000);
}

function dir_stop_prepared_report_loader(report, status, error_message) {
    if (!report._dir_loading) return;
    clearInterval(report._dir_poll);
    report._dir_loading = null;
    dir_hide_prepared_report_overlay(report);

    if (report.report_name !== DEPARTMENT_IR_REPORT_NAME) return;

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

function dir_show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".dir-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="dir-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes dir-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:dir-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function dir_hide_prepared_report_overlay(report) {
    report.page.main.find(".dir-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}