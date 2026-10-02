// Copyright (c) 2024, Gurukrupa Export Private Limited and contributors
// For license information, please see license.txt

function gke_apply_department_restriction(report) {
    // Only System Manager / Administrator can view/change other departments.
    // Everyone else is locked to their own default (Employee) department, with
    // which field gets locked depending on the selected Status:
    //   Issued   -> From Department locked to own department
    //   Received -> To Department locked to own department
    //   Transit  -> neither field is locked, but either From or To must be the
    //               user's own department (enforced server-side); default From
    //               Department to it here purely for convenience.
    // Resolved server-side (not via a direct Employee lookup) since most report
    // users don't have read permission on the Employee doctype.
    var status = report.get_filter_value('status');

    frappe.call({
        method: "gke_customization.gke_catalog.report.department_stock_issue_report.department_stock_issue_report.get_user_department_filter",
        args: { status: status },
        callback: function (r) {
            var res = r.message || {};
            var from_filter = report.get_filter("from_department");
            var to_filter = report.get_filter("to_department");
            if (!from_filter || !to_filter) return;

            if (res.can_change_department) {
                from_filter.df.read_only = 0;
                to_filter.df.read_only = 0;
                from_filter.refresh();
                to_filter.refresh();
                return;
            }

            from_filter.df.read_only = 0;
            to_filter.df.read_only = 0;

            if (res.lock_field === "from_department") {
                from_filter.set_value(res.department || "");
                from_filter.df.read_only = 1;
            } else if (res.lock_field === "to_department") {
                to_filter.set_value(res.department || "");
                to_filter.df.read_only = 1;
            } else if (status === "Transit") {
                if (!from_filter.get_value() && !to_filter.get_value()) {
                    from_filter.set_value(res.department || "");
                }
            }

            from_filter.refresh();
            to_filter.refresh();
        }
    });
}

frappe.query_reports["Department Stock Issue Report"] = {
    "filters": [
        // {
        //     "fieldname": "company",
        //     "label": __("Company"),
        //     "fieldtype": "Link",
        //     "options": "Company",
        //     "default": frappe.defaults.get_user_default("Company"),
        //     "reqd": 1,
        //     "on_change": function() {
        //         // Clear department filters when company changes
        //         frappe.query_report.set_filter_value('from_department', '');
        //         frappe.query_report.set_filter_value('to_department', '');
        //     }
        // },
        // {
        //     "fieldname": "branch",
        //     "label": __("Branch"),
        //     "fieldtype": "Link",
        //     "options": "Branch"
        // },
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
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": ["", "Transit", "Received", "Issued"],
            "default": "",
            "reqd": 1,
            "on_change": function () {
                gke_apply_department_restriction(frappe.query_report);
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "from_department",
            "label": __("From Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                var filters = {
                    'is_group': 0,
                    'disabled': 0
                };
                if (company) {
                    filters['company'] = company;
                }
                return { filters: filters };
            }
        },
        {
            "fieldname": "to_department",
            "label": __("To Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                var filters = {
                    'is_group': 0,
                    'disabled': 0
                };
                if (company) {
                    filters['company'] = company;
                }
                return { filters: filters };
            }
        },
        {
            "fieldname": "raw_material",
            "label": __("Raw Material"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ],

    "tree": true,
    "parent_field": "stock_entry_id",
    "initial_depth": 1,

    onload: function (report) {
        gke_apply_department_restriction(report);
    },

    after_datatable_render: function (datatable) {
        // Frappe's native "Add Total Row" footer is disabled outright for tree/grouped
        // reports, so this renders an equivalent totals bar outside the grid rows,
        // directly under the datatable, instead of as data inside it. Recomputed off
        // whichever row indices are currently visible, so it tracks the datatable's
        // own inline column filters (typed under the column headers) live.
        var report = frappe.query_report;

        function render_footer(visible_indices) {
            var $wrapper = $(datatable.wrapper);
            $wrapper.siblings(".gke-report-total-footer").remove();

            var all_data = report.data || [];
            var rows = visible_indices
                .map(function (i) { return all_data[i]; })
                .filter(function (d) { return d && d.indent === 1; });

            var total_qty = rows.reduce(function (sum, d) { return sum + (flt(d.qty) || 0); }, 0);
            var total_pcs = rows.reduce(function (sum, d) { return sum + (flt(d.pcs) || 0); }, 0);

            var $footer = $(
                "<div class='gke-report-total-footer' style='" +
                    "display: flex; justify-content: flex-end; gap: 32px; " +
                    "font-weight: bold; color: #2490ef; " +
                    "border-top: 2px solid #2490ef; " +
                    "background-color: var(--subtle-fg, rgba(100,100,100,0.08)); " +
                    "padding: 8px 16px; margin-top: -1px;" +
                "'>" +
                    "<span>" + __("Total Qty") + ": " + format_number(total_qty) + "</span>" +
                    "<span>" + __("Total Pcs") + ": " + format_number(total_pcs, null, 0) + "</span>" +
                "</div>"
            );

            $wrapper.after($footer);
        }

        var datamanager = datatable.datamanager;
        if (!datamanager.filterRows.__gke_total_patched) {
            var original_filter_rows = datamanager.filterRows.bind(datamanager);
            var patched = function (filters) {
                return original_filter_rows(filters).then(function (result) {
                    render_footer(result.rowsToShow);
                    return result;
                });
            };
            patched.__gke_total_patched = true;
            datamanager.filterRows = patched;
        }

        render_footer(datamanager.getFilteredRowIndices());
    },

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "status") {
            if (value == "Transit") {
                value = "<span style='color: orange; font-weight: bold;'>Transit</span>";
            } else if (value == "Received") {
                value = "<span style='color: green; font-weight: bold;'>Received</span>";
            } else if (value == "Issued") {
                value = "<span style='color: #2490ef; font-weight: bold;'>Issued</span>";
            }
        }
        
        if (data && data.indent === 0) {
            if (column.fieldname == "stock_entry_id") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "to_department") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "manufacturer") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "qty") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
            if (column.fieldname == "pcs") {
                value = `<span style='font-weight: bold; color: #2490ef;'>${value}</span>`;
            }
        }

        return value;
    }
};
