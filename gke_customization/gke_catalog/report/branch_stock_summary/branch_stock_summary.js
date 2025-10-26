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
            "reqd": function() {
                return frappe.query_report.get_filter_value('company') !== "KG GK Jewellers Private Limited";
            },
            "depends_on": "eval:doc.company && doc.company !== 'KG GK Jewellers Private Limited'",
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Select",
            "options": [
                "",
                "Shubh",
                "Mangal", 
                "Labh",
                "Amrut",
                "Service Center",
                "Siddhi"
            ].join('\n'),
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
            "options": [
                "",
                "Metal",
                "Diamond",
                "Gemstone",
                "Finding",
                "Other"
            ].join('\n'),
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
                        }
                    }

                    // Set default Department based on user's employee department
                    if (r.message.department) {
                        // First update branch and manufacturer options
                        setTimeout(function() {
                            update_branch_options();
                        }, 500);
                        
                        // Detect manufacturer from department and set it
                        setTimeout(function() {
                            let clean_dept = r.message.department
                                .replace(" - GEPL", "")
                                .replace(" - KGJPL", "");
                            
                            let manufacturer = detect_manufacturer_from_department(clean_dept);
                            if (manufacturer) {
                                frappe.query_report.set_filter_value('manufacturer', manufacturer);
                                
                                // Update department options after setting manufacturer
                                setTimeout(function() {
                                    update_department_options();
                                    
                                    // Set department after options are loaded
                                    setTimeout(function() {
                                        frappe.query_report.set_filter_value('department', clean_dept);
                                    }, 500);
                                }, 300);
                            }
                        }, 1000);
                    }

                    // ✅ Auto load report after setting defaults
                    setTimeout(function() {
                        report.refresh();
                    }, 2500);
                }
            }
        });

        // Initialize branch options
        setTimeout(function() {
            update_branch_options();
        }, 500);
        
        // Initialize department options  
        setTimeout(function() {
            update_department_options();
        }, 1000);

        // Stock details modal click handler
        $(document).off('click', '.view-stock-details');
        $(document).on('click', '.view-stock-details', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            let department = $(this).attr('data-department');
            let stock_type = $(this).attr('data-stock-type');
            let stock_key = $(this).attr('data-stock-key');
            
            if (department && stock_type && stock_key) {
                show_stock_details(department, stock_type, stock_key);
            }
        });
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.is_department_header) {
            return `<div style="font-weight: bold; background-color: #f8f9fa; padding: 8px;">${value}</div>`;
        } else if (data && data.is_department_total) {
            return `<div style="font-weight: bold; color: #2e7d32;">${value}</div>`;
        } else if (data && data.is_grand_total) {
            return `<div style="font-weight: bold; color: #d32f2f; background-color: #fff3e0; padding: 8px;">${value}</div>`;
        }
        
        return value;
    }
};

function update_branch_options() {
    let company = frappe.query_report.get_filter_value('company');
    if (!company) return;

    // For KG GK Jewellers - No branches required
    if (company === "KG GK Jewellers Private Limited") {
        frappe.query_report.page.fields_dict.branch.df.options = "";
        frappe.query_report.page.fields_dict.branch.refresh();
        frappe.query_report.set_filter_value('branch', '');
        return;
    }

    // For Gurukrupa Export - Show branch options
    if (company === "Gurukrupa Export Private Limited") {
        let company_branches = get_company_specific_branches(company);
        let options = [""].concat(company_branches).join('\n');
        frappe.query_report.page.fields_dict.branch.df.options = options;
        frappe.query_report.page.fields_dict.branch.refresh();
        
        // Auto-select default branch (Surat Factory for manufacturing)
        if (company_branches.includes("GEPL-ST-0002")) {
            frappe.query_report.set_filter_value('branch', 'GEPL-ST-0002');
        } else if (company_branches.length > 0) {
            frappe.query_report.set_filter_value('branch', company_branches[0]);
        }
    }
}

function update_department_options() {
    let manufacturer = frappe.query_report.get_filter_value('manufacturer');
    
    if (!manufacturer) {
        frappe.query_report.page.fields_dict.department.df.options = "";
        frappe.query_report.page.fields_dict.department.refresh();
        return;
    }

    frappe.call({
        method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_departments_by_manufacturer",
        args: { manufacturer: manufacturer },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let options = [""].concat(r.message);
                frappe.query_report.page.fields_dict.department.df.options = options.join('\n');
                frappe.query_report.page.fields_dict.department.refresh();
            } else {
                frappe.query_report.page.fields_dict.department.df.options = "";
                frappe.query_report.page.fields_dict.department.refresh();
            }
        }
    });
}

function get_company_specific_branches(company) {
    const company_branch_map = {
        "Gurukrupa Export Private Limited": [
            "GEPL-BL-0003", 
            "GEPL-CB-0006", 
            "GEPL-CH-0004", 
            "GEPL-HD-0005", 
            "GEPL-HO-0001", 
            "GEPL-KL-0010", 
            "GEPL-MU-0009", 
            "GEPL-NV-0011", 
            "GEPL-ST-0002", 
            "GEPL-TH-0008", 
            "GEPL-VD-0007"  
        ]
        // KG GK Jewellers Private Limited - No branches needed
    };
    return company_branch_map[company] || [];
}

function detect_manufacturer_from_department(department) {
    // Department patterns to manufacturer mapping
    const dept_to_manufacturer = {
        "Nandi": "Siddhi",
        "Product Repair Center": "Service Center",
        
        // Amrut departments
        "Close Diamond Bagging": "Amrut",
        "Close Diamond Setting": "Amrut", 
        "Close Final Polish": "Amrut",
        "Close Gemstone Bagging": "Amrut",
        "Close Model Making": "Amrut",
        "Close Pre Polish": "Amrut",
        "Close Waxing": "Amrut",
        "Rudraksha": "Amrut",
        
        // Mangal departments  
        "Central MU": "Mangal",
        "Computer Aided Designing MU": "Mangal",
        "Manufacturing Plan Management MU": "Mangal",
        "Om MU": "Mangal",
        "Serial Number MU": "Mangal",
        "Sub Contracting MU": "Mangal",
        "Tagging MU": "Mangal"
    };
    
    // Check exact match first
    if (dept_to_manufacturer[department]) {
        return dept_to_manufacturer[department];
    }
    
    // Check for partial matches (for Shubh/Labh departments)
    if (department.includes("MU") || department.includes("Purchase")) {
        return department.includes("Purchase") ? "Shubh" : "Mangal";
    }
    
    // Default to Shubh for most departments, Labh for specific ones
    const labh_keywords = ["Administration", "Accounts", "Computer", "IT", "Information Technology"];
    if (labh_keywords.some(keyword => department.includes(keyword))) {
        return "Labh";
    }
    
    return "Shubh"; // Default manufacturer
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
                    ]
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
            console.error("Stock details error:", err);
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to load stock details. Please try again.'),
                indicator: 'red'
            });
        }
    });
}

function build_stock_details_table(data, stock_type, department, raw_material_type) {
    if (!data || data.length === 0) {
        return `<div style="padding: 30px; text-align: center;">
                    <h4>No Data Found</h4>
                    <p>No ${stock_type.toLowerCase()} records found for ${department} department.</p>
                </div>`;
    }

    let headers = Object.keys(data[0]);
    let material_filter_text = raw_material_type ? ` (${raw_material_type})` : '';
    
    let html = `
        <div style="padding: 15px;">
            <div style="margin-bottom: 15px;">
                <h4 style="margin: 0 0 5px; color: #2e7d32;">${stock_type} Details</h4>
                <p style="margin: 0; color: #666; font-size: 13px;">${department} Department${material_filter_text} • ${data.length} records</p>
            </div>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="background: #f5f5f5; position: sticky; top: 0;">`;
    
    headers.forEach((header, index) => {
        let headerText = frappe.model.unscrub(header);
        let isNumeric = ['weight', 'quantity', 'qty', 'amount', 'count'].some(keyword => 
            header.toLowerCase().includes(keyword));
        
        html += `<th style="
            padding: 10px 8px; 
            text-align: ${isNumeric ? 'right' : 'left'}; 
            border: 1px solid #ddd;
            font-weight: bold;
            background: #f8f9fa;
        ">${headerText}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    data.forEach((row, rowIndex) => {
        let bgColor = rowIndex % 2 === 0 ? '#ffffff' : '#f8f9fa';
        html += `<tr style="background-color: ${bgColor};">`;
        
        headers.forEach((header, cellIndex) => {
            let value = row[header] || '';
            let isNumeric = ['weight', 'quantity', 'qty', 'amount', 'count'].some(keyword => 
                header.toLowerCase().includes(keyword));
            
            if (typeof value === 'number' && value !== 0) {
                value = frappe.format(value, {fieldtype: "Float", precision: 3});
            }
            
            html += `<td style="
                padding: 8px;
                border: 1px solid #ddd;
                text-align: ${isNumeric ? 'right' : 'left'};
            ">${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += `</tbody></table></div>
        <div style="padding: 15px 0; color: #666; font-size: 11px; text-align: center; border-top: 1px solid #eee; margin-top: 10px;">
            <strong>${data.length}</strong> record${data.length !== 1 ? 's' : ''} found • Filtered by: <strong>${raw_material_type || 'All'}</strong>
        </div></div>`;
    
    return html;
}
