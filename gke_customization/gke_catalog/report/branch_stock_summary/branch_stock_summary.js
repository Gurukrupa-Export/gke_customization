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
                frappe.query_report.set_filter_value('branch', '');
                frappe.query_report.set_filter_value('manufacturer', '');
                frappe.query_report.set_filter_value('department', '');
                update_branch_options();
            }
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Select",
            "reqd": 0,
            "depends_on": "eval:doc.company && doc.company === 'Gurukrupa Export Private Limited'",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Select",
            "options": ["", "Shubh", "Mangal", "Labh", "Amrut", "Service Center", "Siddhi"].join('\n'),
            "reqd": 0,
            "on_change": function() {
                frappe.query_report.set_filter_value('department', '');
                update_department_options();
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "raw_material_type",
            "label": __("Raw Material Type"),
            "fieldtype": "Select",
            "options": ["", "Metal", "Diamond", "Gemstone", "Finding", "Alloy", "Other"].join('\n'), // FIXED: Added Aloy
            "default": "Metal",
            "reqd": 1,
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Select",
            "options": "",
            "reqd": 0,
            "depends_on": "eval:doc.manufacturer",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        }
    ],

    "onload": function(report) {
        // Clear Filter button
        report.page.add_inner_button(__("Clear Filter"), function () {
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
            frappe.query_report.set_filter_value('manufacturer', '');
            frappe.query_report.set_filter_value('department', '');
            frappe.query_report.set_filter_value('branch', '');
            report.run();
        });

        // Auto-fill user's company and department
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { user_id: frappe.session.user },
                fieldname: ["company", "department"]
            },
            callback: function (r) {
                if (r.message) {
                    if (r.message.company) {
                        let company_filter = report.get_filter("company");
                        if (company_filter) {
                            company_filter.set_value(r.message.company);
                        }
                    }

                    if (r.message.department) {
                        setTimeout(function() {
                            update_branch_options();
                        }, 500);
                        
                        setTimeout(function() {
                            let clean_dept = r.message.department.replace(" - GEPL", "").replace(" - KGJPL", "").trim();
                            let manufacturer = detect_manufacturer_from_department(clean_dept);
                            
                            if (manufacturer) {
                                frappe.query_report.set_filter_value('manufacturer', manufacturer);
                                
                                setTimeout(function() {
                                    update_department_options();
                                    
                                    setTimeout(function() {
                                        frappe.query_report.set_filter_value('department', clean_dept);
                                    }, 500);
                                }, 300);
                            }
                        }, 1000);
                    }

                    setTimeout(function() {
                        report.refresh();
                    }, 2500);
                }
            }
        });

        setTimeout(function() {
            update_branch_options();
        }, 500);
        
        setTimeout(function() {
            update_department_options();
        }, 1000);

        // FIXED: View Details button handler - following Serial No Detail Report pattern
        frappe.after_ajax(() => {
            $(document).off("click", ".view-stock-details");
            $(document).on("click", ".view-stock-details", function () {
                let department = $(this).data("department");
                let stock_type = $(this).data("stock-type");
                let stock_key = $(this).data("stock-key");
                
                if (department && stock_type && stock_key) {
                    show_stock_details(department, stock_type, stock_key);
                }
            });
        });
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.is_grand_total) {
            return `<div style="font-weight: bold; text-align: center; font-size: 14px; padding: 5px; border: 1px solid #ccc;">${value}</div>`;
        }
        
        return value;
    }
};

function update_branch_options() {
    let company = frappe.query_report.get_filter_value('company');
    if (!company) return;

    if (company === "KG GK Jewellers Private Limited") {
        if (frappe.query_report.page.fields_dict.branch) {
            frappe.query_report.page.fields_dict.branch.df.options = "";
            frappe.query_report.page.fields_dict.branch.refresh();
            frappe.query_report.set_filter_value('branch', '');
        }
        return;
    }

    if (company === "Gurukrupa Export Private Limited") {
        let company_branches = get_company_specific_branches(company);
        if (company_branches.length > 0) {
            let options = [""].concat(company_branches).join('\n');
            if (frappe.query_report.page.fields_dict.branch) {
                frappe.query_report.page.fields_dict.branch.df.options = options;
                frappe.query_report.page.fields_dict.branch.refresh();
                
                if (company_branches.includes("GEPL-ST-0002")) {
                    frappe.query_report.set_filter_value('branch', 'GEPL-ST-0002');
                } else if (company_branches.length > 0) {
                    frappe.query_report.set_filter_value('branch', company_branches[0]);
                }
            }
        }
    }
}

function update_department_options() {
    let manufacturer = frappe.query_report.get_filter_value('manufacturer');
    
    if (!manufacturer) {
        if (frappe.query_report.page.fields_dict.department) {
            frappe.query_report.page.fields_dict.department.df.options = "";
            frappe.query_report.page.fields_dict.department.refresh();
        }
        return;
    }

    frappe.call({
        method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_departments_by_manufacturer",
        args: { manufacturer: manufacturer },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let options = [""].concat(r.message);
                if (frappe.query_report.page.fields_dict.department) {
                    frappe.query_report.page.fields_dict.department.df.options = options.join('\n');
                    frappe.query_report.page.fields_dict.department.refresh();
                }
            } else {
                if (frappe.query_report.page.fields_dict.department) {
                    frappe.query_report.page.fields_dict.department.df.options = "";
                    frappe.query_report.page.fields_dict.department.refresh();
                }
            }
        }
    });
}

function get_company_specific_branches(company) {
    const company_branch_map = {
        "Gurukrupa Export Private Limited": [
            "GEPL-BL-0003", "GEPL-CB-0006", "GEPL-CH-0004", "GEPL-HD-0005",
            "GEPL-HO-0001", "GEPL-KL-0010", "GEPL-MU-0009", "GEPL-NV-0011",
            "GEPL-ST-0002", "GEPL-TH-0008", "GEPL-VD-0007"
        ]
    };
    return company_branch_map[company] || [];
}

function detect_manufacturer_from_department(department) {
    department = department.trim();
    
    const dept_to_manufacturer = {
        "Nandi": "Siddhi", 
        "Product Repair Center": "Service Center",
        "Close Diamond Bagging": "Amrut", "Close Diamond Setting": "Amrut", "Close Final Polish": "Amrut",
        "Close Gemstone Bagging": "Amrut", "Close Model Making": "Amrut", "Close Pre Polish": "Amrut",
        "Close Waxing": "Amrut", "Rudraksha": "Amrut",
        "Central MU": "Mangal", "Computer Aided Designing MU": "Mangal", "Manufacturing Plan Management MU": "Mangal",
        "Om MU": "Mangal", "Serial Number MU": "Mangal", "Sub Contracting MU": "Mangal", "Tagging MU": "Mangal",
        "Manufacturing Plan & Management": "Labh", "Casting": "Labh", "Central": "Labh", 
        "Computer Aided Designing": "Labh", "Computer Aided Manufacturing": "Labh", "Diamond Setting": "Labh",
        "Final Polish": "Labh", "Model Making": "Labh", "Pre Polish": "Labh", "Product Certification": "Labh",
        "Sub Contracting": "Labh", "Tagging": "Labh", "Waxing": "Labh"
    };
    
    if (dept_to_manufacturer[department]) {
        return dept_to_manufacturer[department];
    }
    
    if (department.includes("MU") && !department.includes("Purchase")) {
        return "Mangal";
    }
    
    if (department.includes("Purchase")) {
        return "Shubh";
    }
    
    const labh_keywords = ["Administration", "Accounts", "Computer", "IT", "Information Technology"];
    if (labh_keywords.some(keyword => department.includes(keyword))) {
        return "Labh";
    }
    
    return "Shubh";
}

function show_stock_details(department, stock_type, stock_key) {
    let current_filters = frappe.query_report.get_filter_values();
    
    if (!current_filters.raw_material_type) {
        frappe.msgprint({
            title: __('Missing Filter'),
            message: __('Raw Material Type filter is required for viewing details'),
            indicator: 'red'
        });
        return;
    }
    
    frappe.show_progress(__('Loading Stock Details'), 10, 100, 'Please wait...');
    
    frappe.call({
        method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_stock_details",
        args: {
            department: department,
            stock_type: stock_type,
            stock_key: stock_key,
            filters: JSON.stringify(current_filters)
        },
        callback: function(r) {
            frappe.hide_progress();
            
            if (r.message && r.message.length > 0) {
                let dialog = new frappe.ui.Dialog({
                    title: `${stock_type} Details - ${department} Department`,
                    size: "large",
                    fields: [
                        { 
                            fieldtype: "HTML", 
                            fieldname: "details_html",
                            options: build_stock_details_table(r.message, stock_type, department, current_filters.raw_material_type)
                        }
                    ],
                    primary_action_label: __('Export to Excel'),
                    primary_action: function() {
                        export_stock_details_to_excel(r.message, stock_type, department);
                    }
                });
                dialog.show();
                
            } else {
                frappe.msgprint({
                    title: __('No Data Found'),
                    message: __(`No ${stock_type.toLowerCase()} data found for ${department} department with the selected raw material type`),
                    indicator: 'yellow'
                });
            }
        },
        error: function(err) {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to load stock details. Please try again.'),
                indicator: 'red'
            });
        }
    });
}

// SIMPLIFIED: Build stock details table with clean, simple formatting
function build_stock_details_table(data, stock_type, department, raw_material_type) {
    if (!data || data.length === 0) {
        return `<div style="padding: 30px; text-align: center;">
                    <h4 style="color: #666;">No Data Found</h4>
                    <p style="color: #999;">No ${stock_type.toLowerCase()} records found for ${department} department.</p>
                </div>`;
    }

    let headers = Object.keys(data[0]);
    let material_filter_text = raw_material_type ? ` (${raw_material_type})` : '';
    
    let html = `
        <div style="padding: 15px;">
            <div style="margin-bottom: 15px; border-bottom: 1px solid #ddd; padding-bottom: 10px;">
                <h4 style="margin: 0 0 5px; color: #333; font-size: 16px;">${stock_type} Details</h4>
                <p style="margin: 0; color: #666; font-size: 12px;">
                    <strong>${department}</strong> Department${material_filter_text} • ${data.length} records found
                </p>
            </div>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd;">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="background-color: #f5f5f5;">`;
    
    // SIMPLIFIED: Basic header formatting without complex styling
    headers.forEach((header) => {
        let headerText = frappe.model.unscrub(header);
        html += `<th style="padding: 8px; border: 1px solid #ddd; font-weight: bold; font-size: 11px; text-align: left;">${headerText}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    // SIMPLIFIED: Basic row formatting without complex color coding
    data.forEach((row, rowIndex) => {
        let bgColor = rowIndex % 2 === 0 ? '#ffffff' : '#f9f9f9';
        html += `<tr style="background-color: ${bgColor};">`;
        
        headers.forEach((header) => {
            let value = row[header] || '';
            
            // Simple number formatting
            if (typeof value === 'number' && value !== 0) {
                value = frappe.format(value, {fieldtype: "Float", precision: 3});
            }
            
            html += `<td style="padding: 6px; border: 1px solid #ddd;">${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += `</tbody></table></div>
        <div style="margin-top: 10px; padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd; font-size: 11px; color: #666;">
            ${data.length} record${data.length !== 1 ? 's' : ''} found • Material Type: ${raw_material_type || 'All'} • Department: ${department}
        </div></div>`;
    
    return html;
}

function export_stock_details_to_excel(data, stock_type, department) {
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

    let filename = `${stock_type.replace(/\s+/g, '_')}_${department.replace(/\s+/g, '_')}_${frappe.datetime.now_date()}.csv`;
    
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
