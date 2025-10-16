// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Raw Material Stock Summary Branch & Manufacturer Wise"] = {
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
        setTimeout(function() {
            update_branch_options();
        }, 500);
        
        setTimeout(function() {
            update_department_options();
        }, 1000);

        $(document).off('click', '.view-stock-details');
        $(document).on('click', '.view-stock-details', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            let department = $(this).attr('data-department');
            let stock_type = $(this).attr('data-stock-type');
            let stock_key = $(this).attr('data-stock-key');
            
            if (department && stock_type && stock_key) {
                show_simple_stock_details(department, stock_type, stock_key);
            }
        });
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.is_department_header) {
            return `<div style="font-weight: bold; background-color: #f8f9fa; padding: 4px;">${value}</div>`;
        } else if (data && data.is_department_total) {
            return `<div style="font-weight: bold; background-color: #e9ecef; padding: 4px;">${value}</div>`;
        } else if (data && data.is_grand_total) {
            return `<div style="font-weight: bold; background-color: #dee2e6; padding: 4px; border-top: 2px solid #495057;">${value}</div>`;
        }
        
        return value;
    }
};

function update_branch_options() {
    let company = frappe.query_report.get_filter_value('company');
    if (!company) return;

    if (company === "KG GK Jewellers Private Limited") {
        frappe.query_report.page.fields_dict.branch.df.options = "";
        frappe.query_report.page.fields_dict.branch.refresh();
        frappe.query_report.set_filter_value('branch', '');
        return;
    }

    let company_branches = get_company_specific_branches(company);
    let options = company_branches.join('\n');
    frappe.query_report.page.fields_dict.branch.df.options = options;
    frappe.query_report.page.fields_dict.branch.refresh();
    
    if (company === "Gurukrupa Export Private Limited" && company_branches.includes("GEPL-ST-0002")) {
        frappe.query_report.set_filter_value('branch', 'GEPL-ST-0002');
    } else if (company_branches.length > 0) {
        frappe.query_report.set_filter_value('branch', company_branches[0]);
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
        method: "gke_customization.gke_catalog.report.raw_material_stock_summary_branch_&_manufacturer_wise.raw_material_stock_summary_branch_&_manufacturer_wise.get_departments_by_manufacturer",
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
            "GEPL-BL-0003", "GEPL-CB-0006", "GEPL-CH-0004", "GEPL-HD-0005",
            "GEPL-HO-0001", "GEPL-KL-0010", "GEPL-MU-0009", "GEPL-NV-0011",
            "GEPL-ST-0002", "GEPL-TH-0008", "GEPL-VD-0007"
        ],
        "Default": ["ST-0001", "ST-0002", "ST-0003"]
    };
    return company_branch_map[company] || company_branch_map["Default"] || [];
}

function show_simple_stock_details(department, stock_type, stock_key) {
    let current_filters = frappe.query_report.get_filter_values();
    
    frappe.show_progress(__('Loading Details'), 50, 100, 'Please wait...');
    
    frappe.call({
        method: "gke_customization.gke_catalog.report.raw_material_stock_summary_branch_&_manufacturer_wise.raw_material_stock_summary_branch_&_manufacturer_wise.get_stock_details",
        args: {
            department: department,
            stock_type: stock_type,
            stock_key: stock_key,
            filters: JSON.stringify(current_filters)
        },
        callback: function(r) {
            frappe.hide_progress();
            
            if (r.message && r.message.length > 0) {
                // Sort data by material type order: Metal, Finding, Diamond, Gemstone, Others
                let sorted_data = sort_by_material_type(r.message);
                
                let dialog = new frappe.ui.Dialog({
                    title: `${stock_type} - ${department}`,
                    size: "medium",  // Changed from "large" to "medium"
                    fields: [
                        { 
                            fieldtype: "HTML", 
                            fieldname: "details_html",
                            options: build_compact_scrollable_table(sorted_data, stock_type, department)
                        }
                    ]
                });

                dialog.show();
                
            } else {
                frappe.msgprint({
                    title: __('No Data Found'),
                    message: __(`No ${stock_type.toLowerCase()} data found for ${department} department.`),
                    indicator: 'yellow'
                });
            }
        },
        error: function(err) {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to load details. Please try again.'),
                indicator: 'red'
            });
        }
    });
}

function sort_by_material_type(data) {
    // Define the sorting order: Metal, Finding, Diamond, Gemstone, Others
    const material_order = {
        'Metal - V': 1,
        'Finding - V': 2, 
        'Diamond - V': 3,
        'Gemstone - V': 4,
        'Others - V': 5,
        'Miscellaneous - V': 6,
        'Tools - V': 7
    };
    
    return data.sort((a, b) => {
        let material_a = a['Material Type'] || a['material_type'] || '';
        let material_b = b['Material Type'] || b['material_type'] || '';
        
        let order_a = material_order[material_a] || 999;
        let order_b = material_order[material_b] || 999;
        
        if (order_a !== order_b) {
            return order_a - order_b;
        }
        
        // If same material type, sort by weight/quantity descending
        let weight_a = parseFloat(a['Weight'] || a['weight'] || a['Qty'] || a['qty'] || 0);
        let weight_b = parseFloat(b['Weight'] || b['weight'] || b['Qty'] || b['qty'] || 0);
        
        return weight_b - weight_a;
    });
}

function build_compact_scrollable_table(data, stock_type, department) {
    if (!data || data.length === 0) {
        return `<div style="padding: 20px; text-align: center;">
                    <p>No data found for ${stock_type} in ${department} department.</p>
                </div>`;
    }

    let headers = Object.keys(data[0]);
    
    let html = `
        <div style="padding: 10px;">
            <p style="margin-bottom: 10px; color: #666; font-size: 13px;">
                <strong>${stock_type}</strong> for <strong>${department}</strong> (${data.length} records)
            </p>
            
            <!-- Compact scrollable table container -->
            <div style="max-height: 350px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead style="position: sticky; top: 0; background-color: #f8f9fa; z-index: 10;">
                        <tr>`;
    
    headers.forEach(header => {
        let headerText = frappe.model.unscrub(header);
        let isNumeric = ['weight', 'qty', 'quantity', 'amount', 'value'].some(keyword => 
            header.toLowerCase().includes(keyword));
        
        html += `<th style="
            padding: 8px 6px; 
            text-align: ${isNumeric ? 'right' : 'left'}; 
            border-bottom: 2px solid #dee2e6;
            font-weight: 600;
            color: #495057;
            font-size: 11px;
            background-color: #f8f9fa;
        ">${headerText}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    data.forEach((row, index) => {
        let rowBg = index % 2 === 0 ? '#ffffff' : '#f8f9fa';
        html += `<tr style="background-color: ${rowBg};">`;
        
        headers.forEach(header => {
            let value = row[header] || '';
            let isNumeric = ['weight', 'qty', 'quantity', 'amount', 'value'].some(keyword => 
                header.toLowerCase().includes(keyword));
            
            // Format numbers
            if (typeof value === 'number' && value !== 0) {
                if (header.toLowerCase().includes('value')) {
                    value = frappe.format(value, {fieldtype: "Currency"});
                } else if (isNumeric) {
                    value = frappe.format(value, {fieldtype: "Float", precision: 3});
                }
            }
            
            // Color coding for material types
            let cellStyle = `
                padding: 6px; 
                border-bottom: 1px solid #eee;
                text-align: ${isNumeric ? 'right' : 'left'};
                font-size: 11px;
            `;
            
            if (header === 'Material Type' && value) {
                let colorMap = {
                    'Metal - V': '#e67e22', 
                    'Finding - V': '#9b59b6', 
                    'Diamond - V': '#3498db', 
                    'Gemstone - V': '#27ae60', 
                    'Others - V': '#95a5a6',
                    'Miscellaneous - V': '#7f8c8d',
                    'Tools - V': '#34495e'
                };
                let color = colorMap[value] || '#6c757d';
                cellStyle += `color: ${color}; font-weight: 600;`;
            }
            
            html += `<td style="${cellStyle}">${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += `</tbody></table></div>
        </div>`;
    
    return html;
}
