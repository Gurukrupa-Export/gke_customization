frappe.query_reports["SLIP WISE DIAMOND DETAIL REPORT"] = {
    onload(report) {
        init_user_dept_permissions(report);

        $(document).off("click", ".view-details-btn");
        $(document).on("click", ".view-details-btn", function () {
            const main_slip = $(this).data("main-slip");
            const batch_no = $(this).data("batch-no");
            const employee = $(this).data("employee");

            frappe.call({
                method: "gke_customization.gke_catalog.report.slip_wise_diamond_detail_report.slip_wise_diamond_detail_report.get_row_details",
                args: {
                    main_slip: main_slip,
                    batch_no: batch_no,
                    employee: employee
                },
                callback: function (r) {
                    if (r.message) {
                        show_diamond_detail_popup(r.message, main_slip, batch_no, employee);
                    } else {
                        frappe.msgprint(__("No details found."));
                    }
                }
            });
        });
    },

    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
            on_change: function () {
                frappe.query_report.set_filter_value("branch", "");
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            reqd: 0,
            get_query: function () {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            },
            on_change: function () {
                frappe.query_report.set_filter_value("department", "");
            }
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            reqd: 1,
            get_query: function () {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let filters = {};

                if (company) {
                    filters.company = company;
                }
                if (branch) {
                    filters.branch = branch;
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
        },
        {
            fieldname: "main_slip",
            label: __("Main Slip"),
            fieldtype: "Link",
            options: "Main Slip"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "action" && data && data.main_slip) {
            return `<button class="btn btn-xs btn-primary view-details-btn"
                        data-main-slip="${frappe.utils.escape_html(data.main_slip || "")}"
                        data-batch-no="${frappe.utils.escape_html(data.batch_no || "")}"
                        data-employee="${frappe.utils.escape_html(data.employee || "")}">
                        <i class="fa fa-eye"></i> View Details
                    </button>`;
        }

        if (column.fieldtype === "Float" && value !== null && value !== undefined && value !== "") {
            let num = parseFloat(value);
            if (!isNaN(num)) {
                return num.toFixed(3);
            }
        }

        return value;
    }
};


function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback: function (user_res) {
            const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
            const management_roles = [
                "Director",
                "CEO",
                "System Manager",
                "Branch Manager",
                "Department Manager"
            ];
            const is_management = roles.some(role => management_roles.includes(role));

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fieldname: ["company", "branch", "department"]
                },
                callback: function (r) {
                    if (!r.message) return;

                    if (r.message.company && report.get_filter("company")) {
                        report.get_filter("company").set_value(r.message.company);
                        if (!is_management) {
                            report.get_filter("company").df.read_only = 1;
                            report.get_filter("company").refresh();
                        }
                    }

                    if (r.message.branch && report.get_filter("branch")) {
                        report.get_filter("branch").set_value(r.message.branch);
                        if (!is_management) {
                            report.get_filter("branch").df.read_only = 1;
                            report.get_filter("branch").refresh();
                        }
                    }

                    if (r.message.department && report.get_filter("department")) {
                        report.get_filter("department").set_value(r.message.department);
                        if (!is_management) {
                            report.get_filter("department").df.read_only = 1;
                            report.get_filter("department").refresh();
                        }
                    }

                    setTimeout(() => report.refresh(), 500);
                }
            });
        }
    });
}


function show_diamond_detail_popup(data, main_slip, batch_no, employee) {
    let detail_rows = "";
    let extra_rows = "";

    (data.details || []).forEach(function (row) {
        detail_rows += `
            <tr>
                <td>${row.creation_date || ""}</td>
                <td>${row.branch || ""}</td>
                <td>${row.department || ""}</td>
                <td>${row.employee || ""}</td>
                <td>${row.batch_no || ""}</td>
                <td>${row.ir_type || ""}</td>
                <td style="text-align:right;">${format_float(row.diamond_wt)}</td>
            </tr>
        `;
    });

    if (!detail_rows) {
        detail_rows = `
            <tr>
                <td colspan="7" style="text-align:center; color:#777;">No issue/receive details found</td>
            </tr>
        `;
    }

    (data.extra_details || []).forEach(function (row) {
        extra_rows += `
            <tr>
                <td>${row.batch_no || ""}</td>
                <td style="text-align:right;">${format_float(row.mop_qty)}</td>
                <td style="text-align:right;">${format_float(row.mop_consume_qty)}</td>
                <td style="text-align:right;">${format_float(row.extra_issue_wt)}</td>
                <td style="text-align:right;">${format_float(row.extra_receive_wt)}</td>
            </tr>
        `;
    });

    if (!extra_rows) {
        extra_rows = `
            <tr>
                <td colspan="5" style="text-align:center; color:#777;">No extra issue/receive details found</td>
            </tr>
        `;
    }

    const html = `
        <div>
            <div style="margin-bottom: 15px;">
                <p><strong>Main Slip:</strong> ${main_slip || ""}</p>
                <p><strong>Batch No:</strong> ${batch_no || ""}</p>
                <p><strong>Employee:</strong> ${employee || ""}</p>
            </div>

            <h5 style="margin-top: 10px;">Employee IR Details</h5>
            <div style="overflow-x:auto; margin-bottom:20px;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Main Slip Date</th>
                            <th>Branch</th>
                            <th>Department</th>
                            <th>Employee</th>
                            <th>Batch No / MWO</th>
                            <th>Type</th>
                            <th style="text-align:right;">Diamond Wt</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${detail_rows}
                    </tbody>
                </table>
            </div>

            <h5 style="margin-top: 10px;">Extra Issue / Receive Details</h5>
            <div style="overflow-x:auto;">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Batch No</th>
                            <th style="text-align:right;">MOP Qty</th>
                            <th style="text-align:right;">MOP Consume Qty</th>
                            <th style="text-align:right;">Extra Issue Wt</th>
                            <th style="text-align:right;">Extra Receive Wt</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${extra_rows}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    let d = new frappe.ui.Dialog({
        title: __("Diamond Detail View"),
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "details_html"
            }
        ]
    });

    d.fields_dict.details_html.$wrapper.html(html);
    d.show();
}


function format_float(val) {
    let num = parseFloat(val || 0);
    return isNaN(num) ? "0.000" : num.toFixed(3);
}