// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Order Detail Report"] = {
    filters: [
        // {
        //     fieldname: "company",
        //     label: __("Company"),
        //     fieldtype: "MultiSelectList",
        //     reqd: 0,
        //     get_data: function(txt) {
        //         return frappe.db.get_link_options("Company", txt);
        //     }
        // },
        // {
        //     fieldname: "branch",
        //     label: __("Branch"),
        //     fieldtype: "MultiSelectList",
        //     options: "Branch",
        //     reqd: 0,
        //     get_data: function (txt) {
        //         return frappe.db.get_link_options("Branch", txt);
        //     },
        // },
        {
            label: __("Manufacturing Work Order"),
            fieldname: "mp",
            fieldtype: "MultiSelectList",
            options: "Manufacturing Work Order",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Manufacturing Work Order", txt);
            },
        },
        {
            label: __("Quotation"),
            fieldname: "qt",
            fieldtype: "MultiSelectList",
            options: "Quotation",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Quotation", txt);
            },
        },
        {
            label: __("Sales Order"),
            fieldname: "so",
            fieldtype: "MultiSelectList",
            options: "Sales Order",
            reqd: 0,
            get_data: function(txt) {
                return frappe.db.get_link_options("Sales Order", txt);
            },
        },
        {
            fieldname: "customer_po",
            label: __("Customer PO No."),
            fieldtype: "MultiSelectList",
            options: [],
        },
        {
            fieldname: "customer",
            label: __("Customer Code"),
            fieldtype: "MultiSelectList",
            options: [],
        },
        {
            fieldname: "category",
            label: __("Item Category"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "delivery_date",
            label: __("Delivery Date"),
            fieldtype: "Date",
            reqd: 0,
        },
        {
            fieldname: "posting_date",
            label: __("Posting Date"),
            fieldtype: "DateRange",
            default: [
                frappe.datetime.add_days(frappe.datetime.now_date(), -90),
                frappe.datetime.now_date(),
            ],
            reqd: 0,
        },
        {
            fieldname: "hide_finished",
            label: __("Hide Finished Operations"),
            fieldtype: "Check",
            default: 1,
            reqd: 0,
        },
    ],

    onload: function (report) {
    //Report Loader Function
        setup_prepared_report_loader(report);
    // ✅ Clear Filter button
    report.page.add_inner_button(__("Clear Filter"), function () {
        report.filters.forEach(function (filter) {
            let field = report.get_filter(filter.fieldname);
            if (field.df.fieldtype === "MultiSelectList") {
                field.set_value([]);
            } else if (field.df.default) {
                field.set_value(field.df.default);
            } else {
                field.set_value("");
            }
        });
        report.run();
    });

    // ✅ Fetch logged-in user's employee Company + Department
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: ["company", "department"]
        },
        callback: function (r) {
            if (r.message) {
                // Set default Company
                if (r.message.company) {
                    let company_filter = report.get_filter("company");
                    if (company_filter) {
                        company_filter.set_value(r.message.company);
                        // Make read-only if needed
                        company_filter.df.read_only = 1;
                        company_filter.refresh();
                    }
                }

                // Set default Department
                if (r.message.department) {
                    let department_filter = report.get_filter("department");
                    if (department_filter && !department_filter.get_value()) {
                        department_filter.set_value(r.message.department);
                    }
                }

                // ✅ Auto load report after setting defaults
                report.refresh();
            }
        }
    });

    // ✅ Fetch dynamic options (fixed: use group_by instead of inline "distinct" in fields,
    // for compatibility across v15/v16 and future versions)
    function fetchOptions(doctype, field, filterField) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: doctype,

                // IMPORTANT FIX
                // Do not use:
                // fields: [`distinct ${field}`]
                fields: [field],
                group_by: field,   // ✅ achieves same unique-values result, compatible with v15 & v16

                order_by: `${field} asc`,
                limit_page_length: 20000,
            },
            callback: function (r) {
                if (r.message) {
                    const options = r.message
                        .map(row => row[field])
                        .filter(value => value !== null && value !== "");

                    if (["category", "status", "diamond_quality", "customer_po", "customer", "department"].includes(filterField)) {
                        options.unshift("");
                    }

                    const filter = report.get_filter(filterField);
                    if (filter) {
                        filter.df.options = options;
                        filter.refresh();
                    }
                }
            },
        });
    }

    // Fetch dropdown options
    fetchOptions("Parent Manufacturing Order", "po_no", "customer_po");
    fetchOptions("Parent Manufacturing Order", "customer", "customer");
    fetchOptions("Manufacturing Operation", "department", "department");
    fetchOptions("Parent Manufacturing Order", "item_category", "category");
},

    // ✅ Columns that should show a unique count (instead of a sum) in the
    // fixed total row at the bottom of the report.
    get_datatable_options(options) {
        const unique_count_fields = [
            "mwo_id",
            "mwo_mp_id",
            "mwo_customer",
            "mwo_design_id",
            "parent_mfg_order",
            "pmo_name",
            "pmo_sales_order_id",
            "pmo_order_form_id",
            "pmo_quotation_id",
        ];

        options.hooks = options.hooks || {};
        options.hooks.columnTotal = function (values, column, type) {
            if (unique_count_fields.includes(column.column.fieldname)) {
                const unique_values = new Set(
                    values.filter((v) => v !== null && v !== undefined && v !== "")
                );
                return unique_values.size ? String(unique_values.size) : "";
            }
            return frappe.utils.report_column_total(values, column, type);
        };

        return options;
    },
};
// Report Loader Function
const Report_Name = "Order Detail Report"; // change the Report Name as per the Report you want to update
 
function setup_prepared_report_loader(report) {
    // the query report view object is shared across reports, so wrap only once
    if (report._orderDetail_loader_ready) return;
    report._orderDetail_loader_ready = true;
 
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
        if (this.report_name === Report_Name && this._orderDetail_loading) {
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
        if (report._orderDetail_loading && data && data.name === report._orderDetail_loading) {
            stop_prepared_report_loader(report, "Completed");
        }
    });
}
 
function start_prepared_report_loader(report, prepared_report_name) {
    report._orderDetail_loading = prepared_report_name;
    show_prepared_report_overlay(report);
 
    clearInterval(report._orderDetail_poll);
    report._orderDetail_poll = setInterval(() => {
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
    if (!report._orderDetail_loading) return;
    clearInterval(report._orderDetail_poll);
    report._orderDetail_loading = null;
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
    $main.find(".orderDetail-report-loader").remove();
    $main.css("position", "relative");
    $main.append(`
        <div class="orderDetail-report-loader"
             style="position:absolute; inset:0; z-index:10; min-height:300px;
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    background:var(--bg-color); opacity:0.95;">
            <style>
                @keyframes orderDetail-report-spin { to { transform: rotate(360deg); } }
            </style>
            <div style="width:48px; height:48px; border-radius:50%;
                        border:4px solid var(--gray-300); border-top-color:var(--primary);
                        animation:orderDetail-report-spin 0.8s linear infinite;"></div>
            <div style="margin-top:15px; font-size:14px; color:var(--text-muted);">
                ${__("Generating report, please wait...")}
            </div>
        </div>
    `);
    report.page.btn_primary && report.page.btn_primary.prop("disabled", true);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", true);
}
 
function hide_prepared_report_overlay(report) {
    report.page.main.find(".orderDetail-report-loader").remove();
    report.page.btn_primary && report.page.btn_primary.prop("disabled", false);
    report.page.btn_secondary && report.page.btn_secondary.prop("disabled", false);
}