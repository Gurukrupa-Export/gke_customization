// Employee Batch Issue Receive - JavaScript File
// File: employee_batch_issue_receive.js

frappe.query_reports["Employee Batch Issue Receive"] = {
    "filters": [
        // {
        //     "fieldname": "branch",
        //     "label": __("Branch"),
        //     "fieldtype": "Link",
        //     "options": "Branch",
        //     "get_query": function() {
        //         return {
        //             "filters": {
        //                 "company": frappe.query_report.get_filter_value("company")
        //             }
        //         }
        //     }
        // },
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
            "options": "Department",
            "default": frappe.defaults.get_user_default("Department"),
            "read_only": !(frappe.user.has_role("System Manager") || frappe.session.user === "Administrator"),
            "on_change": function() {
                // Clear operation and employee when department changes
                frappe.query_report.set_filter_value("operation", "");
                frappe.query_report.set_filter_value("employee_id", "");
            }
        },
        {
            "fieldname": "operation",
            "label": __("Operation"),
            "fieldtype": "Link",
            "options": "Department Operation",
            "get_query": function() {
                var department = frappe.query_report.get_filter_value("department");

                var filters = {
                    "docstatus": ["!=", 2]
                };

                if (department) {
                    filters["department"] = department;
                }

                return {
                    "filters": filters
                }
            },
            "on_change": function() {
                // Clear employee when operation changes
                frappe.query_report.set_filter_value("employee_id", "");
            }
        },
        {
            "fieldname": "employee_id",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                var department = frappe.query_report.get_filter_value("department");
                var operation = frappe.query_report.get_filter_value("operation");

                // If operation is selected, use custom query
                if (operation && operation !== "") {
                    return {
                        "query": "gke_customization.gke_catalog.report.employee_batch_issue_receive.employee_batch_issue_receive.get_employees_by_operation",
                        "filters": {
                            "department": department,
                            "operation": operation
                        }
                    }
                }

                // Otherwise, use standard filters
                var filters = {
                    "status": "Active"
                };

                if (department) {
                    filters["department"] = department;
                }

                return {
                    "filters": filters
                }
            }
        }
        
    ],

    onload: function(report) {
        setup_prepared_report_loader(report);
    }

};

// Report Loader Function
const Report_Name = "Employee Batch Issue Receive"; // change the Report Name as per the Report you want to update

function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._ebir_loader_ready) return;
    report._ebir_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function() {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== Report_Name || !result || !result.then) {
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
        if (this.report_name === Report_Name && this._ebir_loading) {
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
        if (report._ebir_loading && data && data.name === report._ebir_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}

function start_prepared_report_loader(report, prepared_report_name) {
    report._ebir_loading = prepared_report_name;
    show_prepared_report_overlay(report);

    clearInterval(report._ebir_poll);
    report._ebir_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== Report_Name) {
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
    if (!report._ebir_loading) return;
    clearInterval(report._ebir_poll);
    report._ebir_loading = null;
    hide_prepared_report_overlay(report);

    if (report.report_name !== Report_Name) return;

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
    $main.find(".ebir-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="ebir-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes ebir-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:ebir-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function hide_prepared_report_overlay(report) {
    report.page.main.find(".ebir-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}