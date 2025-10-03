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
			"reqd": 1,
			"depends_on": "company"
		},
		{
			"fieldname": "manufacturer",
			"label": __("Manufacturer"),
			"fieldtype": "Link", 
			"options": "Manufacturer",
			"reqd": 0,
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					filters: [
						["Manufacturer", "docstatus", "!=", 2]
					].concat(company ? [["Manufacturer", "company", "=", company]] : [])
				};
			},
			"on_change": function() {
				frappe.query_report.set_filter_value('department', '');
				update_department_options();
			}
		},
		{
			"fieldname": "raw_material_type",
			"label": __("Raw Material Type"),
			"fieldtype": "MultiSelectList",
			"options": [
				{"value": "Metal", "description": "Metal"},
				{"value": "Diamond", "description": "Diamond"},
				{"value": "Gemstone", "description": "Gemstone"},
				{"value": "Finding", "description": "Finding"},
				{"value": "Other", "description": "Other"}
			],
			"reqd": 0,
			"on_change": function() {
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Select",
			"reqd": 0,
			"depends_on": "manufacturer"
		}
	],

	"onload": function(report) {
		setTimeout(update_branch_options, 1000);
		setTimeout(update_department_options, 1500);

		setTimeout(function() {
			frappe.query_report.page.wrapper.find('.report-wrapper').css({
				'overflow-x': 'auto', 
				'white-space': 'nowrap',
				'max-width': '100%'
			});
		}, 2000);

		// Handle view details button clicks - UPDATED FOR REAL DATA
		$(document).off('click', '.view-details');
		$(document).on('click', '.view-details', function(e) {
			e.preventDefault();
			e.stopPropagation();
			
			let stock_type = $(this).attr('data-stock-type');
			let stock_key = $(this).attr('data-stock-key');
			
			if (stock_type && stock_key) {
				show_stock_details(stock_type, stock_key);
			}
		});

		// Refresh button
		frappe.query_report.page.add_inner_button(__("Refresh Data"), function() {
			frappe.query_report.refresh();
			frappe.show_alert({
				message: __('Branch Stock Summary refreshed successfully'),
				indicator: 'green'
			}, 3);
		});

		// Debug button for troubleshooting
		frappe.query_report.page.add_inner_button(__("Debug Data"), function() {
			let company = frappe.query_report.get_filter_value('company');
			let branch = frappe.query_report.get_filter_value('branch');
			let manufacturer = frappe.query_report.get_filter_value('manufacturer');
			
			if (!company || !branch) {
				frappe.msgprint('Please select Company and Branch first');
				return;
			}
			
			frappe.call({
				method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.debug_data_structure",
				args: {company: company, branch: branch, manufacturer: manufacturer},
				callback: function(r) {
					console.log("DEBUG RESULTS:", r.message);
					frappe.msgprint({
						title: "Debug Results (Check Console for Full Details)",
						message: `<pre>${JSON.stringify(r.message, null, 2)}</pre>`,
						indicator: 'blue'
					});
				}
			});
		});
	},

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (!data) return value;
		
		if (column.fieldname === 'stock_type') {
			return `<div style="font-weight: 500; color: #1a73e8;">${value}</div>`;
		}
		
		if (column.fieldname === 'view_details') {
			return value;
		}
		
		// Format float values with proper styling
		if (column.fieldtype === 'Float') {
			let numValue = parseFloat(value) || 0;
			let color = numValue > 0 ? '#1976d2' : '#757575';
			let bgColor = numValue > 0 ? '#f8f9fa' : '#ffffff';
			return `<div style="text-align: center; color: ${color}; background-color: ${bgColor}; padding: 4px; border-radius: 3px; font-weight: ${numValue > 0 ? '500' : 'normal'};">${frappe.format(numValue, {fieldtype: "Float", precision: 2})}</div>`;
		}
		
		return value;
	}
};

function update_branch_options() {
	let company = frappe.query_report.get_filter_value('company');
	if (!company) return;

	let company_branches = get_company_specific_branches(company);
	let options = company_branches.join('\n');
	frappe.query_report.page.fields_dict.branch.df.options = options;
	frappe.query_report.page.fields_dict.branch.refresh();
	
	// Auto-select default branch based on company
	if (company === "Gurukrupa Export Private Limited" && company_branches.includes("GEPL-ST-0002")) {
		frappe.query_report.set_filter_value('branch', 'GEPL-ST-0002');
	} else if (company === "KG GK Jewellers Private Limited" && company_branches.includes("KGJPL-ST-0001")) {
		frappe.query_report.set_filter_value('branch', 'KGJPL-ST-0001');
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
				
				console.log("Available departments for " + manufacturer + ":", r.message);
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
		"KG GK Jewellers Private Limited": [
			"KGJPL-ST-0001", "KGJPL-ST-0002", "KGJPL-HO-0001", "KGJPL-MU-0001"
		],
		"Default": ["ST-0001", "ST-0002", "ST-0003"]
	};
	return company_branch_map[company] || company_branch_map["Default"] || [];
}

function show_stock_details(stock_type, stock_key) {
	let current_filters = frappe.query_report.get_filter_values();
	
	frappe.show_progress(__('Loading Stock Details'), 10, 100, 'Please wait...');
	
	frappe.call({
		method: "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary.get_stock_details",
		args: {
			stock_type: stock_type,
			stock_key: stock_key,
			filters: JSON.stringify(current_filters)
		},
		callback: function(r) {
			frappe.hide_progress();
			
			if (r.message && r.message.length > 0) {
				let dialog = new frappe.ui.Dialog({
					title: `${stock_type} Details`,
					size: "extra-large",
					fields: [
						{ 
							fieldtype: "HTML", 
							fieldname: "details_html",
							options: build_stock_details_table(r.message, stock_type)
						}
					],
					primary_action_label: __('Export to Excel'),
					primary_action: function() {
						export_details_to_excel(r.message, stock_type);
					},
					secondary_action_label: __('Close'),
					secondary_action: function() { 
						dialog.hide(); 
					}
				});

				dialog.show();
			} else {
				frappe.msgprint({
					title: __('No Data'),
					message: __(`No data found for ${stock_type}`),
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

function build_stock_details_table(data, stock_type) {
    if (!data || data.length === 0) {
        return `<div style="padding: 20px; text-align: center; color: #888;">
                    <i class="fa fa-info-circle" style="font-size: 48px; margin-bottom: 16px;"></i>
                    <h4>No data found for ${stock_type}</h4>
                    <p>Try selecting different filters or check if data exists for the selected criteria.</p>
                </div>`;
    }

    let headers = Object.keys(data[0]);
    let html = `
        <div style="padding: 0;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin: 0; display: flex; align-items: center;">
                    <i class="fa fa-list-alt" style="margin-right: 10px;"></i> 
                    ${stock_type} Details
                </h3>
                <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">
                    <i class="fa fa-info-circle" style="margin-right: 5px;"></i>
                    Showing ${data.length} records
                </p>
            </div>
            <div style="overflow-x: auto; border: 1px solid #dee2e6; border-radius: 8px;">
                <table class="table table-striped table-hover" style="margin-bottom: 0; font-size: 13px;">
                    <thead style="background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%); color: white;">
                        <tr>
    `;
    
    headers.forEach(header => {
        html += `<th style="padding: 12px 8px; border: none; font-weight: 600; text-align: center; white-space: nowrap;">${frappe.model.unscrub(header)}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    data.forEach((row, index) => {
        let row_class = '';
        let row_style = '';
        
        // Highlight summary rows or important data
        if (row[headers[0]] && row[headers[0]].toString().includes('SUMMARY')) {
            row_class = 'table-success';
            row_style = 'font-weight: bold; background-color: #d4edda;';
        }
        
        html += `<tr class="${row_class}" style="${row_style}">`;
        headers.forEach((header, headerIndex) => {
            let value = row[header] || '';
            let cellStyle = 'padding: 10px 8px; vertical-align: middle;';
            
            // Format numbers
            if (typeof value === 'number' && !header.includes('Date') && !header.includes('Days')) {
                value = frappe.format(value, {fieldtype: "Float", precision: 2});
                cellStyle += ' text-align: right; font-weight: 500;';
            } else if (headerIndex === 0) {
                // First column styling
                cellStyle += ' font-weight: 500; color: #495057;';
            } else {
                cellStyle += ' text-align: center;';
            }
            
            html += `<td style="${cellStyle}">${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += `</tbody></table>
            </div>
            <div style="margin-top: 15px; padding: 12px; background-color: #f8f9fa; border-radius: 6px; font-size: 12px; color: #6c757d;">
                <i class="fa fa-lightbulb-o" style="margin-right: 5px;"></i>
                <strong>Tip:</strong> Click "Export to Excel" to download this data for further analysis.
            </div>
        </div>`;
    return html;
}

function export_details_to_excel(data, stock_type) {
	if (!data || data.length === 0) {
		frappe.msgprint({
			title: __('No Data'),
			message: __('No data available to export'),
			indicator: 'yellow'
		});
		return;
	}
	
	try {
		let headers = Object.keys(data[0]);
		let csv_content = headers.map(h => frappe.model.unscrub(h)).join(',') + '\n';
		
		data.forEach(row => {
			let row_data = headers.map(header => {
				let value = row[header] || '';
				// Handle CSV escaping
				if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
					value = '"' + value.replace(/"/g, '""') + '"';
				}
				return value;
			});
			csv_content += row_data.join(',') + '\n';
		});
		
		// Create and download file
		let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
		let link = document.createElement('a');
		let url = URL.createObjectURL(blob);
		link.setAttribute('href', url);
		
		// Create filename with timestamp
		let timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
		let filename = `${stock_type.replace(/\s+/g, '_')}_Details_${timestamp}.csv`;
		link.setAttribute('download', filename);
		
		link.style.visibility = 'hidden';
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		
		frappe.show_alert({
			message: __(`Excel file "${filename}" downloaded successfully`),
			indicator: 'green'
		}, 5);
		
	} catch (error) {
		console.error('Export error:', error);
		frappe.msgprint({
			title: __('Export Error'),
			message: __('Failed to export data. Please try again.'),
			indicator: 'red'
		});
	}
}

// Additional utility functions for enhanced functionality
function refresh_report_data() {
	frappe.query_report.refresh();
	frappe.show_alert({
		message: __('Report data refreshed'),
		indicator: 'blue'
	}, 2);
}

// Auto-refresh functionality (optional)
function setup_auto_refresh() {
	let auto_refresh_interval = 300000; // 5 minutes
	
	setInterval(function() {
		if (frappe.query_report && frappe.query_report.page.wrapper.is(':visible')) {
			console.log('Auto-refreshing Branch Stock Summary...');
			refresh_report_data();
		}
	}, auto_refresh_interval);
}

