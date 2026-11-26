frappe.query_reports["Worker Wise Performance Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },

        /*
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            on_change: function(report) {
                report.set_filter_value("branch", "");
                report.set_filter_value("department", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        */

        /*
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");

                let filters = {};
                if (company) filters.company = company;

                return {
                    filters: filters
                };
            },
            on_change: function(report) {
                report.set_filter_value("department", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        */

        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            on_change: function() {
                // Clear employee when department changes
                frappe.query_report.set_filter_value("employee", "");
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
                if (department) filters.department = department;

                return {
                    filters: filters
                };
            }
        },

        {
            fieldname: "touch",
            label: __("Touch"),
            fieldtype: "Select",
            options: ["", "10KT", "18KT", "20KT", "22KT", "24KT", "CHAIN"]
        }
    ],

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.process === __("Grand Total")) {
            value = "<b>" + value + "</b>";
        }

        return value;
    },

    // Grand Total row ko data se nikaal kar datatable ke footer mein dikhao.
    // Footer scroll area ke bahar hota hai, isliye row freeze rehti hai.
    get_datatable_options: function(options) {
        const rows = options.data || [];
        const total_label = __("Grand Total");
        const total_row = rows.find(row => row && row.process === total_label);

        if (!total_row) return options;

        // Purana datatable saaf karo, taaki refresh par double na bane
        if (frappe.query_report.datatable) {
            frappe.query_report.datatable.destroy();
            frappe.query_report.datatable = null;
        }

        // this.data ko mat chhedo (export/print mein Grand Total row rehni chahiye)
        options.data = rows.filter(row => row !== total_row);
        options.showTotalRow = true;
        options.hooks = options.hooks || {};
        options.hooks.columnTotal = function(values, cell) {
            const key = (cell.column && (cell.column.fieldname || cell.column.id)) || "";
            const value = total_row[key];
            return value === undefined || value === null ? "" : value;
        };

        return options;
    },

    after_datatable_render: function(datatable) {
        // Footer ki Grand Total row bold dikhe
        if (datatable && datatable.footer) {
            datatable.footer.style.fontWeight = "bold";
        }
    },

    onload: function(report) {

        setup_prepared_report_loader(report);
        const is_admin = frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

        // Pre-select the Department from the user's Employee record
        frappe.call({
            method: "gke_customization.gke_catalog.report.worker_wise_performance_report.worker_wise_performance_report.get_default_department",
            callback: function(r) {
                if (!r.message) return;

                frappe.query_report.set_filter_value("department", r.message);

                // Non-admin ke liye Department lock, sirf tab jab Department mila ho
                if (!is_admin) {
                    const field = report.page.fields_dict.department;
                    field.df.read_only = 1;
                    field.df.description = __("Department is locked as per your Employee record");
                    field.refresh();
                }
            }
        });
    }
};
// Report Loader Function
const Report_Name = "Worker Wise Performance Report"; // change the Report Name as per the Report you want to update

function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._performance_loader_ready) return;
    report._performance_loader_ready = true;

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
        if (this.report_name === Report_Name && this._performance_loading) {
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
        if (report._performance_loading && data && data.name === report._performance_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}

function start_prepared_report_loader(report, prepared_report_name) {
    report._performance_loading = prepared_report_name;
    show_prepared_report_overlay(report);

    clearInterval(report._performance_poll);
    report._performance_poll = setInterval(() => {
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
    if (!report._performance_loading) return;
    clearInterval(report._performance_poll);
    report._performance_loading = null;
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
    $main.find(".performance-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="performance-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes performance-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:performance-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function hide_prepared_report_overlay(report) {
    report.page.main.find(".performance-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}
