const DEPT_WISE_DIAMOND_STOCK_REPORT_NAME = "Department Wise Diamond Stock";

frappe.query_reports[DEPT_WISE_DIAMOND_STOCK_REPORT_NAME] = {
	onload(report) {
		dwds_setup_prepared_report_loader(report);
		dwds_init_user_dept_permissions(report);
	},

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
			hidden: 1
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			reqd: 1
		},
		{
			fieldname: "manufacturer",
			label: __("Manufacturer"),
			fieldtype: "Link",
			options: "Manufacturer",
			hidden: 1
		}
	]
};

function dwds_init_user_dept_permissions(report) {
	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "User",
			name: frappe.session.user
		},
		callback: function (user_res) {
			const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
			const is_admin = frappe.session.user === "Administrator" || roles.includes("System Manager");

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
					}

					if (r.message.branch && report.get_filter("branch")) {
						report.get_filter("branch").set_value(r.message.branch);
					}

					if (r.message.department && report.get_filter("department")) {
						report.get_filter("department").set_value(r.message.department);

						if (!is_admin) {
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

/* ---------------- Prepared report loader ---------------- */

function dwds_setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._dwds_loader_ready) return;
    report._dwds_loader_ready = true;

    const original_generate = report.generate_background_report;
    const original_refresh = report.refresh;

    report.generate_background_report = function () {
        const result = original_generate.apply(this, arguments);
        if (this.report_name !== DEPT_WISE_DIAMOND_STOCK_REPORT_NAME || !result || !result.then) {
            return result;
        }
        return result.then((r) => {
            if (this.prepared_report_doc_name) {
                dwds_start_prepared_report_loader(this, this.prepared_report_doc_name);
            }
            return r;
        });
    };

    report.refresh = function () {
        if (this.report_name === DEPT_WISE_DIAMOND_STOCK_REPORT_NAME && this._dwds_loading) {
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
        if (report._dwds_loading && data && data.name === report._dwds_loading) {
            dwds_stop_prepared_report_loader(report, "Completed");
        }
    });
}

function dwds_start_prepared_report_loader(report, prepared_report_name) {
    report._dwds_loading = prepared_report_name;
    dwds_show_prepared_report_overlay(report);

    clearInterval(report._dwds_poll);
    report._dwds_poll = setInterval(() => {
        // user navigated to another report: stop watching
        if (report.report_name !== DEPT_WISE_DIAMOND_STOCK_REPORT_NAME) {
            dwds_stop_prepared_report_loader(report);
            return;
        }
        frappe.db.get_value("Prepared Report", prepared_report_name, ["status", "error_message"])
            .then((r) => {
                const doc = r.message || {};
                if (doc.status === "Completed" || doc.status === "Error") {
                    dwds_stop_prepared_report_loader(report, doc.status, doc.error_message);
                }
            })
            .catch(() => dwds_stop_prepared_report_loader(report));
    }, 4000);
}

function dwds_stop_prepared_report_loader(report, status, error_message) {
    if (!report._dwds_loading) return;
    clearInterval(report._dwds_poll);
    report._dwds_loading = null;
    dwds_hide_prepared_report_overlay(report);

    if (report.report_name !== DEPT_WISE_DIAMOND_STOCK_REPORT_NAME) return;

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

function dwds_show_prepared_report_overlay(report) {
    const $main = report.page.main;
    $main.find(".dwds-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="dwds-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes dwds-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:dwds-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function dwds_hide_prepared_report_overlay(report) {
    report.page.main.find(".dwds-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}