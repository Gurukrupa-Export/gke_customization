// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["OT and Night Shift Report"] = {
    "filters": [
        {
            fieldname: "date",
            label: "Date",
            fieldtype: "Date",
            default: frappe.datetime.nowdate()
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacture"),
            fieldtype: "Select",
            options: [],
            reqd: 0,
        },
        {
            fieldname: "branch",
            label: "Branch",
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options('Branch', txt);
            }
        },
        {
            fieldname: "department",
            label: "Department",
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options('Department', txt);
            }
        }
    ],
    onload: function (report) {
        function fetchOptions(doctype, field, filterField, includeBlank = false) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: doctype,
                    fields: [field],
                    order_by: `${field} asc`,
                    limit_page_length: 30000,
                },
                callback: function (r) {
                    if (r.message) {
                        let options = [...new Set(
                            r.message
                                .map(row => row[field])
                                .filter(value => value && value.trim() !== "")
                        )];

                        if (includeBlank) {
                            options.unshift("");
                        }

                        const filter = report.get_filter(filterField);
                        filter.df.options = options;
                        filter.refresh();
                    }
                },
            });
        }

        fetchOptions("Employee", "manufacturer", "manufacturer", true);

        report.page.add_inner_button(__('Testing method'), function () {
            frappe.call({
                method: 'gke_customization.gke_hrms.doc_events.ot_and_night_shift_report.send_auto_email_alert',
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint(__('Email alert sent successfully'));
                        report.refresh();
                    }
                }
            });
        });


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
        });
    },
};
