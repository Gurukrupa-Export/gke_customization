// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt
const LOADER_REPORT_NAME = "Advance Bagging Report From MR";
frappe.query_reports["Advance Bagging Report From MR"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.month_end(),
        },
        {
            label: "Material Type",
            fieldname: "material_type",
            fieldtype: "Select",
            options: ["", "Diamond", "Gemstone", "Finding", "Others"],
            reqd: 0
        },
        {
            fieldname: "workflow_state",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Material Request", {
                    fields: ["workflow_state as value"],
                    filters: {
                        "material_request_type": "Manufacture",
                        "workflow_state": ["is", "set"],
                        "workflow_state": ["!=", "Material Transferred to MOP"]
                    },
                    order_by: "workflow_state",
                    limit: 0
                }).then(r => {
                    let seen = new Set();
                    return r
                        .filter(d => d.value && d.value.trim() !== "" && !seen.has(d.value) && seen.add(d.value))
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Warehouse", {
                    fields: ["name as value", "warehouse_name"],
                    filters: {
                        "disabled": 0
                    },
                    order_by: "name",
                    limit: 0
                }).then(r => {
                    return r
                        .filter(d => d.value && d.value.trim() !== "")
                        .map(d => {
                            return {
                                value: d.value,
                                description: d.warehouse_name || ""
                            }
                        });
                });
            }
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                let departments = new Set();
                
                return Promise.all([
                    frappe.db.get_list("Material Request", {
                        fields: ["custom_department as value"],
                        filters: {
                            "material_request_type": "Manufacture",
                            "custom_department": ["is", "set"],
                            "workflow_state": ["!=", "Material Transferred to MOP"]
                        },
                        limit: 0
                    }),
                    frappe.db.get_list("Parent Manufacturing Order", {
                        fields: ["department as value"],
                        filters: {
                            "department": ["is", "set"]
                        },
                        limit: 0
                    }),
                    frappe.db.get_list("Department", {
                        fields: ["name as value"],
                        filters: {
                            "disabled": 0
                        },
                        limit: 0
                    })
                ]).then(results => {
                    results.forEach(result => {
                        result.forEach(item => {
                            if (item.value && item.value.trim() !== "") {
                                departments.add(item.value);
                            }
                        });
                    });
                    
                    return Array.from(departments).sort().map(dept => {
                        return {
                            value: dept,
                            description: ""
                        }
                    });
                });
            }
        },
        {
            label: "Parent Manufacturing Order",
            fieldname: "manufacturing_order",
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Parent Manufacturing Order", txt);
            }
        },
        {
            fieldname: "item_category",
            label: __("Category"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Parent Manufacturing Order", {
                    fields: ["item_category as value"],
                    order_by: "item_category",
                    limit: 0
                }).then(r => {
                    let seen = new Set();
                    return r
                        .filter(d => d.value && d.value.trim() !== "" && !seen.has(d.value) && seen.add(d.value))
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
        {
            fieldname: "setting_type",
            label: __("Setting Type"),
            fieldtype: "MultiSelectList",
            options: [],
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_list("Parent Manufacturing Order", {
                    fields: ["setting_type as value"],
                    order_by: "setting_type",
                    limit: 0
                }).then(r => {
                    let seen = new Set();
                    return r
                        .filter(d => d.value && d.value.trim() !== "" && !seen.has(d.value) && seen.add(d.value))
                        .map(d => {
                            return {
                                value: d.value,
                                description: ""
                            }
                        });
                });
            }
        },
        {
            label: "Material Req Id",
            fieldname: "material_request",
            fieldtype: "MultiSelectList",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Material Request", txt, {
                    material_request_type: "Manufacture"
                });
            }
        },
    ],
    
    onload: function(report) {
         setup_prepared_report_loader(report);
        // Scan QR / Barcode Button - Adds scanned Material Request to the filter
        report.page.add_inner_button(__("Scan Material Req Id"), function () {
            new frappe.ui.Scanner({
                dialog: true,
                multiple: true,
                on_scan(data) {
                    let scanned_value = data && data.result && data.result.text;
                    if (!scanned_value) return;
                    scanned_value = scanned_value.trim();

                    frappe.db.exists("Material Request", scanned_value).then((exists) => {
                        if (!exists) {
                            frappe.show_alert({
                                message: __("{0} is not a valid Material Request", [scanned_value]),
                                indicator: "red"
                            });
                            return;
                        }

                        let field = report.get_filter("material_request");
                        let current_values = field.get_value() || [];
                        if (current_values.includes(scanned_value)) {
                            frappe.show_alert({
                                message: __("{0} is already added", [scanned_value]),
                                indicator: "orange"
                            });
                            return;
                        }

                        field.set_value([...current_values, scanned_value]);
                        frappe.show_alert({
                            message: __("Added {0}", [scanned_value]),
                            indicator: "green"
                        });
                    });
                }
            });
        }, __("Scan"));

        // **View Summary Report Button - Passes ALL current filters**
        report.page.add_inner_button(__("View Summary Report"), function () {
            // Get ALL current filter values
            let current_filters = report.get_filter_values();
            
            // Log filters to console for debugging (optional)
            console.log("Passing filters to summary report:", current_filters);
            
            // Navigate to summary report with ALL filters
            frappe.set_route("query-report", "Advance Bagging Summary Report", current_filters);
        });
        
        // Clear Filter Button
        report.page.add_inner_button(__("Clear Filter"), function () {
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);
                if (field && field.df.fieldtype === "MultiSelectList") {
                    field.set_value([]);
                } else if (field && field.df.default) {
                    field.set_value(field.df.default);
                } else if (field) {
                    field.set_value("");
                }
            });
            report.refresh();
        });
    }
}
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