// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt


frappe.query_reports["Branch Stock Summary"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1,
            "on_change": function() {
                clear_filters_quietly(['branch', 'manufacturer', 'department']);
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "as_on_date",
            "label": __("As On Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                return { filters: { company: frappe.query_report.get_filter_value('company') } };
            },
            "on_change": function() {
                clear_filters_quietly(['department']);
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer",
            "get_query": function() {
                return { filters: { company: frappe.query_report.get_filter_value('company') } };
            },
            "on_change": function() {
                clear_filters_quietly(['department']);
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "raw_material_type",
            "label": __("Raw Material Type"),
            "fieldtype": "Select",
            "options": ["", "Metal", "Diamond", "Gemstone", "Finding", "Alloy", "Other"].join('\n'),
            "default": "Metal",
            "reqd": 1
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                return {
                    query: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.department_query",
                    filters: {
                        company: frappe.query_report.get_filter_value('company'),
                        manufacturer: frappe.query_report.get_filter_value('manufacturer'),
                        branch: frappe.query_report.get_filter_value('branch')
                    }
                };
            }
        }
    ],


    "onload": function(report) {
        // Department access: management roles can change the Department filter
        // (and see the company-wide Summary); everyone else is locked to their
        // own department. The server enforces the same rule.
        frappe.call({
            method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_department_access",
            callback: function (r) {
                let access = r.message || {};
                frappe.query_report._bss_department_locked = !access.can_change;
                frappe.query_report._bss_user_department = access.department || "";

                if (access.can_change) {
                    // Summary button: explains this report's Grand Total vs the standard
                    // Stock Balance report's total for the same company/item group.
                    report.page.add_inner_button(__("Summary"), function () {
                        show_report_summary();
                    });
                }

                if (access.department) {
                    frappe.query_report._bss_skip_clear = true;
                    frappe.query_report.set_filter_value('department', access.department);
                    setTimeout(() => { frappe.query_report._bss_skip_clear = false; }, 1000);
                }

                if (!access.can_change) {
                    let field = report.get_filter('department');
                    if (field) {
                        field.df.read_only = 1;
                        field.df.description = __("Department is locked to your department");
                        field.refresh();
                    }
                }
            }
        });

        // Clear Filter button
        report.page.add_inner_button(__("Clear Filter"), function () {
            frappe.query_report._bss_skip_clear = true;
            report.filters.forEach(function (filter) {
                let field = report.get_filter(filter.fieldname);
                if (field && field.df) {
                    if (field.df.fieldtype === "MultiSelectList") {
                        field.set_value([]);
                    } else if (field.df.default) {
                        field.set_value(field.df.default);
                    } else {
                        field.set_value("");
                    }
                }
            });
            if (frappe.query_report._bss_department_locked) {
                frappe.query_report.set_filter_value('department', frappe.query_report._bss_user_department);
            }
            setTimeout(() => { frappe.query_report._bss_skip_clear = false; }, 1000);
            report.run();
        });


        // Pre-fill branch / manufacturer from the user's Employee record
        // (department comes from get_department_access above).
        frappe.db.get_value(
            "Employee",
            { user_id: frappe.session.user, status: "Active" },
            ["company", "branch", "manufacturer"]
        ).then(function (r) {
            let emp = r.message;
            if (!emp || !emp.company || emp.company !== frappe.query_report.get_filter_value('company')) {
                return;
            }
            let values = {};
            ['branch', 'manufacturer'].forEach(function (fieldname) {
                if (emp[fieldname]) values[fieldname] = emp[fieldname];
            });
            if (Object.keys(values).length) {
                // Don't let the branch/manufacturer on_change wipe the department being set here.
                frappe.query_report._bss_skip_clear = true;
                frappe.query_report.set_filter_value(values);
                setTimeout(() => { frappe.query_report._bss_skip_clear = false; }, 1000);
            }
        });


        // FIXED: Attach button event handlers
        attach_view_button_handlers();
    },


    // FIXED: Call attach handlers after refresh
    "refresh": function() {
        setTimeout(function() {
            attach_view_button_handlers();
        }, 1000);
    },


    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.is_department_header && column.fieldname !== "view_details") {
            return `<b>${value}</b>`;
        }

        return value;
    }
};


// FIXED: Separate function to attach button event handlers
function attach_view_button_handlers() {
    // Remove existing handlers to prevent duplicates
    $(document).off('click', '.view-stock-details');
    
    // Attach new handlers
    $(document).on('click', '.view-stock-details', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // attr() rather than data(): data() would coerce numeric-looking keys.
        let $button = $(this);
        let group = $button.attr('data-group');
        let key = $button.attr('data-key');
        let stock_key = $button.attr('data-stock-key');
        let label = $button.attr('data-label');

        if (group && key && stock_key) {
            show_stock_details(group, key, stock_key, label);
        } else {
            console.error('Missing button data:', {group, key, stock_key});
            frappe.msgprint({
                title: __('Error'),
                message: __('Button data is missing. Please refresh the report.'),
                indicator: 'red'
            });
        }
    });
}


// Clear dependent filters when a parent filter changes (skipped while filters
// are being filled programmatically, e.g. from the Employee record).
function clear_filters_quietly(fieldnames) {
    if (frappe.query_report._bss_skip_clear) return;
    fieldnames.forEach(function (fieldname) {
        if (fieldname === 'department' && frappe.query_report._bss_department_locked) return;
        let filter = frappe.query_report.get_filter(fieldname);
        if (filter && filter.get_value()) filter.set_input("");
    });
}


function show_report_summary() {
    let current_filters = frappe.query_report.get_filter_values();

    if (!current_filters.company) {
        frappe.msgprint({
            title: __('Missing Filter'),
            message: __('Company filter is required to view the summary'),
            indicator: 'red'
        });
        return;
    }
    if (!current_filters.raw_material_type) {
        frappe.msgprint({
            title: __('Missing Filter'),
            message: __('Raw Material Type filter is required to view the summary'),
            indicator: 'red'
        });
        return;
    }

    // freeze (not show_progress): the progress modal can stay stuck on screen
    // when a dialog is opened right after hiding it.
    frappe.call({
        method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_summary_comparison",
        freeze: true,
        freeze_message: __('Comparing with Stock Balance...'),
        args: {
            filters: JSON.stringify(current_filters)
        },
        callback: function (r) {
            if (r.message) {
                let dialog = new frappe.ui.Dialog({
                    title: __('Report Summary'),
                    size: "large",
                    fields: [
                        {
                            fieldtype: "HTML",
                            fieldname: "summary_html",
                            options: build_summary_html(r.message, current_filters)
                        }
                    ]
                });
                dialog.show();
            }
        },
        error: function () {
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to load summary. Check console for details.'),
                indicator: 'red'
            });
        }
    });
}


function build_summary_html(s, filters) {
    let fmt = (v) => Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
    let diff_color = Math.abs(s.difference) < 0.001 ? 'var(--green-600, #2e7d32)' : 'var(--red-500, #d1414a)';
    let cell = 'padding: 8px; border: 1px solid var(--border-color);';

    let unassigned_rows = (s.unassigned_breakdown || []).map(row => `
        <tr>
            <td style="${cell} padding-left: 24px;">${frappe.utils.escape_html(row.warehouse)}</td>
            <td style="${cell} text-align: right;">${fmt(row.qty)}</td>
        </tr>
    `).join('');

    // The summary is always for the whole company; warn when the report itself is filtered.
    let applied = [
        [__('Manufacturer'), filters && filters.manufacturer],
        [__('Department'), filters && filters.department],
        [__('Branch'), filters && filters.branch]
    ].filter(f => f[1]).map(f => `${f[0]}: ${frappe.utils.escape_html(f[1])}`);
    let filter_warning = applied.length ? `
        <div style="padding: 8px 10px; margin-bottom: 12px; border: 1px solid var(--yellow-300, #f0c36d); background-color: var(--yellow-50, #fffbea); color: var(--text-color); font-size: 12px;">
            ${__('The report is filtered by {0}, so its totals cover only part of the company. This summary is for the whole company, so the numbers will differ.', [applied.join(', ')])}
        </div>` : '';

    return `
        <div style="padding: 10px; color: var(--text-color); background-color: var(--card-bg);">
            ${filter_warning}
            <p style="color: var(--text-muted); margin-bottom: 15px;">
                <strong>${s.company}</strong> &bull; ${s.raw_material_type} &bull; as on ${s.as_on_date}
                &bull; ${__('whole company (Department / Manufacturer / Branch filters not applied)')}
            </p>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px;">
                <tr><td style="${cell}">${__('Departments ({0} items only)', [s.raw_material_type])}</td><td style="${cell} text-align: right;">${fmt(s.department_qty)}</td></tr>
                <tr><td style="${cell}">${__('Supplier / Job Work ({0} items only)', [s.raw_material_type])}</td><td style="${cell} text-align: right;">${fmt(s.supplier_qty)}</td></tr>
                <tr><td style="${cell}">${__('Unassigned Warehouses')}</td><td style="${cell} text-align: right;">${fmt(s.unassigned_qty)}</td></tr>
                ${unassigned_rows}
                <tr>
                    <td style="${cell} font-weight: bold;">${__('Stock Ledger Total')}</td>
                    <td style="${cell} text-align: right; font-weight: bold;">${fmt(s.ledger_total)}</td>
                </tr>
                <tr>
                    <td style="${cell}">${__('Stock Balance Total (same item group)')}</td>
                    <td style="${cell} text-align: right; font-weight: bold;">${fmt(s.stock_balance_qty)}</td>
                </tr>
                <tr>
                    <td style="${cell} font-weight: bold;">${__('Difference')}</td>
                    <td style="${cell} text-align: right; font-weight: bold; color: ${diff_color};">${fmt(s.difference)}</td>
                </tr>
            </table>

            ${s.uses_operations ? `
            <h5 style="margin-bottom: 5px;">${__('Work Order and Employee WIP')}</h5>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 13px;">
                <tr><td style="${cell}">${__('Stock Ledger Total')}</td><td style="${cell} text-align: right;">${fmt(s.ledger_total)}</td></tr>
                <tr><td style="${cell}">${__('&minus; Department Manufacturing Warehouses (Stock Ledger balance)')}</td><td style="${cell} text-align: right;">${fmt(-s.ledger_mfg_qty)}</td></tr>
                <tr><td style="${cell}">${__('+ Manufacturing Operations: Not Started, not In-Transit')}</td><td style="${cell} text-align: right;">${fmt(s.operations_mfg_qty)}</td></tr>
                <tr><td style="${cell}">${__('&minus; Employee WIP warehouses (Stock Ledger balance)')}</td><td style="${cell} text-align: right;">${fmt(-s.ledger_emp_wip_qty)}</td></tr>
                <tr><td style="${cell}">${__('+ Manufacturing Operations: WIP with employee, not In-Transit')}</td><td style="${cell} text-align: right;">${fmt(s.operations_emp_wip_qty)}</td></tr>
                <tr>
                    <td style="${cell} font-weight: bold;">${__('Branch Stock Summary Grand Total')}</td>
                    <td style="${cell} text-align: right; font-weight: bold;">${fmt(s.report_total)}</td>
                </tr>
            </table>
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 15px;">
                ${__('The report takes the Work Order and Employee WIP lines from the weight on Manufacturing Operations instead of the Stock Ledger, so its Grand Total differs from Stock Balance by the difference between those figures. Operations reflect today, regardless of As On Date.')}
            </p>` : `
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 15px;">
                ${__('Branch Stock Summary Grand Total')}: <strong>${fmt(s.report_total)}</strong>
            </p>`}

            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 5px;">
                ${__('Stock Ledger and Stock Balance are both read from the same ledger, so they should match. Unassigned Warehouses are warehouses with no department, no employee and no supplier set; set the department on them (or move their stock) to show it under a department.')}
            </p>
            <p style="font-size: 12px; color: var(--text-muted);">
                ${__('Finished pieces')}: <strong>${s.finished_goods_pieces || 0}</strong>, ${__('BOM weight')} <strong>${fmt(s.finished_goods_qty)}</strong> &mdash;
                ${__('shown in the FG columns on the line of the warehouse holding them (e.g. Tagging / Finished Goods). Finished pieces are separate items, so this weight is not in Stock Balance and not in Quantity. Pieces reflect today, regardless of As On Date.')}
            </p>
        </div>
    `;
}


function show_stock_details(group, key, stock_key, label) {
    let current_filters = frappe.query_report.get_filter_values();

    frappe.call({
        method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_stock_details",
        freeze: true,
        freeze_message: __('Loading Stock Details...'),
        args: {
            group: group,
            key: key,
            stock_key: stock_key,
            filters: JSON.stringify(current_filters)
        },
        callback: function(r) {

            if (r.message && Array.isArray(r.message) && r.message.length > 0) {
                let dialog = new frappe.ui.Dialog({
                    title: __('{0} Details', [label]),
                    size: "extra-large",
                    fields: [
                        {
                            fieldtype: "HTML",
                            fieldname: "details_html",
                            options: build_stock_details_table(r.message, label, current_filters.raw_material_type)
                        }
                    ],
                    primary_action_label: __('Export to Excel'),
                    primary_action: function() {
                        export_stock_details_to_excel(r.message, label);
                        dialog.hide();
                    }
                });
                dialog.show();
            } else {
                frappe.msgprint({
                    title: __('No Data Found'),
                    message: __('No stock found for {0}', [label]),
                    indicator: 'yellow'
                });
            }
        },
        error: function() {
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to load stock details. Check console for details.'),
                indicator: 'red'
            });
        }
    });
}


function build_stock_details_table(data, label, raw_material_type) {


    let headers = Object.keys(data[0]);
    let material_filter_text = raw_material_type ? ` (${raw_material_type})` : '';
    
    let html = `
        <div style="padding: 15px; color: var(--text-color); background-color: var(--card-bg);">
            <div style="margin-bottom: 15px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
                <h4 style="margin: 0 0 5px; color: var(--text-color); font-size: 16px;">${frappe.utils.escape_html(label)}</h4>
                <p style="margin: 0; color: var(--text-muted); font-size: 12px;">
                    ${material_filter_text} • ${data.length} records found
                </p>
            </div>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border-color); background-color: var(--card-bg);">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px; color: var(--text-color); background-color: var(--card-bg);">
                    <thead>
                        <tr style="background-color: var(--subtle-fg);">`;
    
    headers.forEach((header) => {
        let headerText = frappe.model.unscrub(header);
        html += `<th style="padding: 8px; border: 1px solid var(--border-color); font-weight: bold; font-size: 11px; text-align: left; color: var(--text-color); background-color: var(--subtle-fg);">${headerText}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    data.forEach((row, rowIndex) => {
        let bgColor = rowIndex % 2 === 0 ? 'var(--card-bg)' : 'var(--subtle-fg)';
        html += `<tr style="background-color: ${bgColor};">`;
        
        headers.forEach((header) => {
            let value = row[header] || '';
            
            // Simple number formatting
            if (typeof value === 'number' && value !== 0) {
                if (header.toLowerCase().includes('weight') || header.toLowerCase().includes('qty') || header.toLowerCase().includes('quantity')) {
                    value = Number(value).toFixed(3);
                } else {
                    value = value.toString();
                }
            }
            
            html += `<td style="padding: 6px; border: 1px solid var(--border-color); color: var(--text-color); background-color: ${bgColor};">${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += `</tbody></table></div></div>`;
    
    return html;
}


function export_stock_details_to_excel(data, label) {
    if (!data || data.length === 0) {
        frappe.msgprint({
            title: __('No Data'),
            message: __('No data available to export'),
            indicator: 'yellow'
        });
        return;
    }


    let headers = Object.keys(data[0]);
    let csv_content = headers.map(h => frappe.model.unscrub(h)).join(',') + '\n';
    
    data.forEach(row => {
        let row_data = headers.map(header => {
            let value = row[header] || '';
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                value = '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        });
        csv_content += row_data.join(',') + '\n';
    });


    let filename = `${label.replace(/[^\w-]+/g, '_')}_${frappe.datetime.now_date()}.csv`;
    
    let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
    let link = document.createElement('a');
    if (link.download !== undefined) {
        let url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        frappe.show_alert({
            message: __(`Successfully exported ${data.length} records to ${filename}`),
            indicator: 'green'
        });
    }
}


// FIXED: Initialize handlers when document is ready
$(document).ready(function() {
    // Delay to ensure report is loaded
    setTimeout(function() {
        attach_view_button_handlers();
    }, 3000);
});