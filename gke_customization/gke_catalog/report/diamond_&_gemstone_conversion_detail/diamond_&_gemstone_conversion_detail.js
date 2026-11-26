// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Diamond & Gemstone Conversion Detail"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Select",
            "options": [
                "",
                // "Diamond Bagging - GEPL",
                "Diamond Bagging - KGJPL",
                // "Gemstone Bagging - GEPL",
                "Gemstone Bagging - KGJPL"
            ],
            "reqd": 1
        }
        
    ],

     onload: function(report) {
        setup_prepared_report_loader(report);
    },
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Bold Source Qty and Total Target Qty
        if ((column.fieldname === "source_qty" || column.fieldname === "total_target_qty") && data[column.fieldname] != null && data[column.fieldname] !== "") {
            value = `<span style="font-weight: bold;">${value}</span>`;
        }
        
        return value;
    }
};

// Report Loader Function
const Report_Name = "Diamond & Gemstone Conversion Detail"; // change the Report Name as per the Report you want to update

function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._coversion_loader_ready) return;
    report._coversion_loader_ready = true;

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
        if (this.report_name === Report_Name && this._coversion_loading) {
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
        if (report._coversion_loading && data && data.name === report._coversion_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}

function start_prepared_report_loader(report, prepared_report_name) {
    report._coversion_loading = prepared_report_name;
    show_prepared_report_overlay(report);

    clearInterval(report._coversion_poll);
    report._coversion_poll = setInterval(() => {
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
    if (!report._coversion_loading) return;
    clearInterval(report._coversion_poll);
    report._coversion_loading = null;
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
    $main.find(".coversion-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="coversion-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes coversion-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:coversion-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}

function hide_prepared_report_overlay(report) {
    report.page.main.find(".coversion-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}
