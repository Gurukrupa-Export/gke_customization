// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Material Stock In Hand"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
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
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nSubmitted",
            default: "",
        },
    ],

    onload: function (report) {
        setup_prepared_report_loader(report);
        // Remove any previously attached handler to avoid duplicates on refresh
        $(document).off("click.ir_detail_btn");

        // Use document-level delegation — survives DataTable re-renders
        $(document).on("click.ir_detail_btn", ".ir-detail-btn", function () {
            const employee = $(this).data("employee");
            const empname  = $(this).data("empname");
            frappe_show_ir_detail_dialog(employee, empname);
        });
    },
};


// Global so it can also be triggered via inline onclick as a fallback
window.frappe_show_ir_detail_dialog = function (employee, empname) {
    if (!employee) {
        frappe.msgprint(__("Employee not found on button."));
        return;
    }

    frappe.call({
        method: "gke_customization.gke_catalog.report.employee_material_stock_in_hand.employee_material_stock_in_hand.get_employee_ir_details",
        args: { employee: employee },
        freeze: true,
        freeze_message: __("Loading details…"),
        callback: function (r) {
            if (r.exc) {
                frappe.msgprint(__("Error fetching details. Check console for more info."));
                return;
            }

            if (!r.message || !r.message.length) {
                frappe.msgprint(__("No records found for {0}.", [empname || employee]));
                return;
            }

            // Map docstatus integer to label
            const status_label = { 0: "Draft", 1: "Submitted" };

            // Totals
            let totals = { dia_pcs: 0, dia_wt: 0, stone_wt: 0, gold_wt: 0 };
            r.message.forEach(row => {
                totals.dia_pcs  += flt(row.dia_pcs);
                totals.dia_wt   += flt(row.dia_wt);
                totals.stone_wt += flt(row.stone_wt);
                totals.gold_wt  += flt(row.gold_wt);
            });

            const detail_rows = r.message.map(row => `
                <tr>
                    <td><a href="/app/employee-ir/${row.ir_name}" target="_blank">${row.ir_name}</a></td>
                    <td>${row.posting_date || ""}</td>
                    <td>${status_label[row.status] || row.status}</td>
                    <td>${row.Mfg_Work_Order || ""}</td>
                    <td style="text-align:right">${flt(row.dia_pcs,  2)}</td>
                    <td style="text-align:right">${flt(row.dia_wt,   3)}</td>
                    <td style="text-align:right">${flt(row.stone_wt, 3)}</td>
                    <td style="text-align:right">${flt(row.gold_wt,  3)}</td>
                </tr>`).join("");

            const html = `
                <div style="overflow:auto; max-height:65vh;">
                    <table class="table table-bordered table-condensed" style="margin:0; font-size:12px;">
                        <thead style="position:sticky; top:0; background:#fff; z-index:1;">
                            <tr style="background:#f0f4f8;">
                                <th>IR ID</th>
                                <th>Date / Time</th>
                                <th>Status</th>
                                <th>Work Order</th>
                                <th style="text-align:right">Dia Pcs</th>
                                <th style="text-align:right">Dia Wt</th>
                                <th style="text-align:right">Stone Wt</th>
                                <th style="text-align:right">Net Wt</th>
                            </tr>
                        </thead>
                        <tbody>${detail_rows}</tbody>
                        <tfoot>
                            <tr style="font-weight:bold; background:#f5f5f5;">
                                <td colspan="4">Total &nbsp;(${r.message.length} record${r.message.length !== 1 ? "s" : ""})</td>
                                <td style="text-align:right">${flt(totals.dia_pcs,  2)}</td>
                                <td style="text-align:right">${flt(totals.dia_wt,   3)}</td>
                                <td style="text-align:right">${flt(totals.stone_wt, 3)}</td>
                                <td style="text-align:right">${flt(totals.gold_wt,  3)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>`;

            const d = new frappe.ui.Dialog({
                title: __("IR Details — {0} ({1})", [empname || "", employee]),
                fields: [{ fieldtype: "HTML", fieldname: "detail_html" }],
                size: "extra-large",
            });
            d.fields_dict.detail_html.$wrapper.html(html);
            d.show();
        },
    });
};
// Report Loader Function
const Report_Name = "Employee Material Stock In Hand"; // change the Report Name as per the Report you want to update

function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._stock_loader_ready) return;
    report._stock_loader_ready = true;

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
        if (this.report_name === Report_Name && this._stock_loading) {
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
        if (report._stock_loading && data && data.name === report._stock_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}

function start_prepared_report_loader(report, prepared_report_name) {
    report._stock_loading = prepared_report_name;
    show_prepared_report_overlay(report);

    clearInterval(report._stock_poll);
    report._stock_poll = setInterval(() => {
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
    if (!report._stock_loading) return;
    clearInterval(report._stock_poll);
    report._stock_loading = null;
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
    $main.find(".stock-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="stock-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes stock-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:stock-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function hide_prepared_report_overlay(report) {
    report.page.main.find(".stock-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}