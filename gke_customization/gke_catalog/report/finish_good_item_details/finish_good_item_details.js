frappe.query_reports["Finish Good Item Details"] = {
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
        // {
        //     fieldname: "company",
        //     label: __("Company"),
        //     fieldtype: "Link",
        //     options: "Company",
        //     reqd: 1,
        //     default: frappe.defaults.get_user_default("Company"),
        //     on_change: function(report) {
        //         report.set_filter_value("branch", "");
        //         report.set_filter_value("department", "");
        //         report.refresh();
        //     }
        // },
        // {
        //     fieldname: "branch",
        //     label: __("Branch"),
        //     fieldtype: "Link",
        //     options: "Branch",
        //     get_query: function() {

        //         let company = frappe.query_report.get_filter_value("company");

        //         let filters = {};

        //         if (company) {
        //             filters.company = company;
        //         }

        //         return {
        //             filters: filters
        //         };
        //     },
        //     on_change: function(report) {
        //         report.set_filter_value("department", "");
        //         report.refresh();
        //     }
        // },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            get_query: function() {

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
            fieldname: "serial_no",
            label: __("Serial No"),
            fieldtype: "Link",
            options: "Serial No"
        },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item"
        }
    ],
     onload: function(report) {
        init_user_dept_permissions(report);
        setup_prepared_report_loader(report);
    }   
};
function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback(user_res) {
            const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
            const management_roles = ["Director", "CEO", "System Manager", "Branch Manager", "Department Manager"];
            const is_management = roles.some(r => management_roles.includes(r));

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fieldname: ["company", "branch", "department"]
                },
                callback(r) {
                    if (!r.message) return;

                    if (r.message.company && report.get_filter("company")) {
                        report.get_filter("company").set_value(r.message.company);
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

// Report Loader Function
const Report_Name = "Finish Good Item Details"; // change the Report Name as per the Report you want to update

function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._fgid_loader_ready) return;
    report._fgid_loader_ready = true;

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
        if (this.report_name === Report_Name && this._fgid_loading) {
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
        if (report._fgid_loading && data && data.name === report._fgid_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}

function start_prepared_report_loader(report, prepared_report_name) {
    report._fgid_loading = prepared_report_name;
    show_prepared_report_overlay(report);

    clearInterval(report._fgid_poll);
    report._fgid_poll = setInterval(() => {
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
    if (!report._fgid_loading) return;
    clearInterval(report._fgid_poll);
    report._fgid_loading = null;
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
    $main.find(".fgid-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="fgid-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes fgid-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:fgid-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function hide_prepared_report_overlay(report) {
    report.page.main.find(".fgid-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}