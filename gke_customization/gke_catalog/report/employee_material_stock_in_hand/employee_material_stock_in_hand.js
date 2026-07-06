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