const LOADER_REPORT_NAME = "Metal Conversion Report";
frappe.query_reports["Metal Conversion Report"] = {
    onload: function(report) {
		setup_prepared_report_loader(report);
	},
    "filters": [
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "is_customer_metal",
            "label": __("Is Customer Metal"),
            "fieldtype": "Select",
            "options": "\nYes\nNo"
        },
        {
            "fieldname": "conversion_type",
            "label": __("Conversion Type"),
            "fieldtype": "Select",
            "options": "\nTouch to Pure\nPure to Touch\nOther Conversions"
        }
    ],
    
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Format quantities with proper decimal places
        if (column.fieldname == "source_qty" || 
            column.fieldname == "source_alloy_qty" || 
            column.fieldname == "target_qty") {
            if (value && !isNaN(value)) {
                value = parseFloat(value).toFixed(3);
            }
        }
        
        return value;
    }
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