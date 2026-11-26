const DIAMOND_BROKEN_LOST_REPORT_NAME = "Diamond Broken-Lost Report";

frappe.query_reports[DIAMOND_BROKEN_LOST_REPORT_NAME] = {
    onload(report) {
        dbl_setup_prepared_report_loader(report);
        dbl_init_user_dept_permissions(report);
    },

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(
                frappe.datetime.get_today(),
                -6
            )
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            on_change: function(report) {
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let department = frappe.query_report.get_filter_value("department");

                let filters = {};
                if (department) {
                    filters.department = department;
                }

                return {
                    filters: filters
                };
            }
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacturer"),
            fieldtype: "Link",
            options: "Manufacturer"
        }
    ]
};

function dbl_init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: ["department"]
        },
        callback(r) {
            if (!r.message) return;

            if (r.message.department && report.get_filter("department")) {
                report.get_filter("department").set_value(r.message.department);
            }

            setTimeout(() => report.refresh(), 500);
        }
    });
}

/* ---------------- Prepared report loader ---------------- */

function dbl_setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._dbl_loader_ready) return;
    report._dbl_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function () {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== DIAMOND_BROKEN_LOST_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                dbl_start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };

    report.refresh = function () {
        if (this.report_name === DIAMOND_BROKEN_LOST_REPORT_NAME && this._dbl_loading) {
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
        if (report._dbl_loading && data && data.name === report._dbl_loading) {
            dbl_stop_prepared_report_loader(report, "Completed");
        }
    });
}

function dbl_start_prepared_report_loader(report, prepared_report_name) {
    report._dbl_loading = prepared_report_name;
    dbl_show_prepared_report_overlay(report);

    clearInterval(report._dbl_poll);
    report._dbl_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== DIAMOND_BROKEN_LOST_REPORT_NAME) {
            dbl_stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    dbl_stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => dbl_stop_prepared_report_loader(report));
    }, 4000);
}

function dbl_stop_prepared_report_loader(report, status, error_message) {
    if (!report._dbl_loading) return;
    clearInterval(report._dbl_poll);
    report._dbl_loading = null;
    dbl_hide_prepared_report_overlay(report);

    if (report.report_name !== DIAMOND_BROKEN_LOST_REPORT_NAME) return;

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

function dbl_show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".dbl-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="dbl-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes dbl-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:dbl-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function dbl_hide_prepared_report_overlay(report) {
    report.page.main.find(".dbl-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}