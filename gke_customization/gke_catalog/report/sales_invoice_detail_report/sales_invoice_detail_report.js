// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Invoice Detail Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "invoice_no",
            "label": __("Invoice No"),
            "fieldtype": "Link",
            "options": "Sales Invoice"
        },
        {
            "fieldname": "serial_no",
            "label": __("Serial No"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "detail" && data.item_code) {
            return value;
        }
        
        return value;
    },
    
    "onload": function(report) {
        setTimeout(() => {
            attachViewDetailsHandlers();
        }, 500);
        
        // Add Raw Material Summary button - navigates to Summary Report with same filters
        report.page.add_inner_button(__("Raw Material Summary"), function() {
            const f = report.get_values();
            frappe.set_route('query-report', 'Sales Invoice Summary Report', {
                company: f.company,
                branch: f.branch || '',
                from_date: f.from_date,
                to_date: f.to_date,
                invoice_no: f.invoice_no || '',
                serial_no: f.serial_no || '',
                customer: f.customer || ''
            });
        });
    }
};

frappe.after_ajax(() => {
    attachViewDetailsHandlers();
});

function attachViewDetailsHandlers() {
    $('.view-details-btn').off('click').on('click', function() {
        const serialNo = $(this).data('serial-no');
        const itemCode = $(this).data('item-code');
        const billNo = $(this).data('bill-no');
        
        if (!itemCode || !billNo) {
            frappe.msgprint(__('Item Code or Bill No not found'));
            return;
        }
        
        showItemDetails(serialNo, itemCode, billNo);
    });
}

function showItemDetails(serialNo, itemCode, billNo) {
    frappe.call({
        method: 'gke_customization.gke_catalog.report.sales_invoice_detail_report.sales_invoice_detail_report.get_raw_material_details',
        args: {
            serial_no: serialNo || '',
            item_code: itemCode,
            bill_no: billNo
        },
        callback: function(r) {
            if (r.message) {
                displayItemDetails(serialNo, itemCode, billNo, r.message);
            } else {
                frappe.msgprint(__('No details found'));
            }
        },
        error: function(r) {
            frappe.msgprint(__('Error loading details. Please check console for more info.'));
            console.error('API Error:', r);
        }
    });
}

function displayItemDetails(serialNo, itemCode, billNo, data) {
    let raw_materials = data.raw_materials || [];
    let bom_name = data.bom_name || "N/A";
    let item_image = data.item_image || "";
    let item_category = data.item_category || "";
    let item_subcategory = data.item_subcategory || "";
    let customer = data.customer || "";
    let setting_type = data.setting_type || "";
    
    // Build header section
    let headerHtml = `
        <div style="padding: 15px; margin-bottom: 20px; border-left: 4px solid var(--primary-color); background-color: var(--bg-light-gray);">
            <h6 style="margin: 0; color: var(--primary-color); font-weight: 600; font-size: 14px;">
                Serial No: <span style="color: var(--text-color);">${serialNo || '-'}</span> | 
                Item: <span style="color: var(--text-color);">${itemCode || '-'}</span> | 
                BOM: <span style="color: var(--text-color);">${bom_name}</span>
            </h6>
            <p style="margin: 8px 0 0 0; color: var(--text-muted); font-size: 13px;">
                Sales Invoice: <strong style="color: var(--text-color);">${billNo || '-'}</strong>
            </p>
        </div>
    `;
    
    // Build two-column layout: Basic Information + Product Image
    let basicInfoHtml = `
        <div style="display: flex; gap: 20px; margin-bottom: 25px;">
            <div style="flex: 1;">
                <h6 style="font-weight: 600; margin-bottom: 12px; color: var(--text-color); font-size: 13px;">Basic Information</h6>
                <table class="table table-bordered" style="margin-bottom: 0; background-color: var(--control-bg);">
                    <tbody>
                        <tr>
                            <td style="width: 40%; font-weight: 600; background-color: var(--table-header-bg); color: var(--text-color); border: 1px solid var(--border-color);">Customer:</td>
                            <td style="border: 1px solid var(--border-color); color: var(--text-color);">${customer || '-'}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600; background-color: var(--table-header-bg); color: var(--text-color); border: 1px solid var(--border-color);">Category:</td>
                            <td style="border: 1px solid var(--border-color); color: var(--text-color);">${item_category || '-'}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600; background-color: var(--table-header-bg); color: var(--text-color); border: 1px solid var(--border-color);">Sub Category:</td>
                            <td style="border: 1px solid var(--border-color); color: var(--text-color);">${item_subcategory || '-'}</td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600; background-color: var(--table-header-bg); color: var(--text-color); border: 1px solid var(--border-color);">Setting Type:</td>
                            <td style="border: 1px solid var(--border-color); color: var(--text-color);">${setting_type || '-'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div style="flex: 0 0 300px;">
                <h6 style="font-weight: 600; margin-bottom: 12px; color: var(--text-color); font-size: 13px;">Product Image</h6>
                <div style="border: 1px solid var(--border-color); padding: 10px; background-color: var(--control-bg); text-align: center; min-height: 200px; display: flex; align-items: center; justify-content: center;">
                    ${item_image ? 
                        `<img src="${item_image}" alt="Product Image" style="max-width: 100%; max-height: 280px; object-fit: contain;">` : 
                        `<span style="color: var(--text-muted);">No Image Available</span>`
                    }
                </div>
            </div>
        </div>
    `;
    
    // Build Raw Material Details table
    let rawMaterialHtml = `
        <h6 style="font-weight: 600; margin-bottom: 12px; color: var(--text-color); font-size: 13px;">Raw Material Details</h6>
        <table class="table table-bordered" style="font-size: 13px; background-color: var(--control-bg);">
            <thead>
                <tr style="background-color: var(--table-header-bg);">
                    <th style="width: 20%; border: 1px solid var(--border-color); color: var(--text-color);">Raw Material Code</th>
                    <th style="width: 50%; border: 1px solid var(--border-color); color: var(--text-color);">Attributes</th>
                    <th style="width: 10%; text-align: right; border: 1px solid var(--border-color); color: var(--text-color);">Qty</th>
                    <th style="width: 10%; text-align: center; border: 1px solid var(--border-color); color: var(--text-color);">Pcs</th>
                    <th style="width: 10%; text-align: center; border: 1px solid var(--border-color); color: var(--text-color);">UOM</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    if (raw_materials.length > 0) {
        raw_materials.forEach(function(material) {
            let parsedData = parseRawMaterialDisplay(material.display);
            
            rawMaterialHtml += `
                <tr>
                    <td style="font-weight: 600; border: 1px solid var(--border-color); color: var(--text-color);">${parsedData.item_code}</td>
                    <td style="line-height: 1.6; border: 1px solid var(--border-color); color: var(--text-color);">${parsedData.attributes}</td>
                    <td style="text-align: right; font-weight: 600; border: 1px solid var(--border-color); color: var(--text-color);">${parsedData.qty}</td>
                    <td style="text-align: center; border: 1px solid var(--border-color); color: var(--text-color);">${parsedData.pcs}</td>
                    <td style="text-align: center; border: 1px solid var(--border-color); color: var(--text-color);">${parsedData.uom}</td>
                </tr>
            `;
        });
    } else {
        rawMaterialHtml += `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px; border: 1px solid var(--border-color);">
                    No raw material details found
                </td>
            </tr>
        `;
    }
    
    rawMaterialHtml += `
            </tbody>
        </table>
    `;
    
    // Combine all HTML
    let fullHtml = `
        <div style="padding: 20px;">
            ${headerHtml}
            ${basicInfoHtml}
            ${rawMaterialHtml}
        </div>
    `;
    
    // Create and show dialog
    let dialog = new frappe.ui.Dialog({
        title: __('Item Details - {0}', [itemCode]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'item_details_html',
                options: fullHtml
            }
        ],
        size: 'extra-large'
    });
    
    dialog.show();
}

function parseRawMaterialDisplay(display) {
    if (!display) {
        return {
            item_code: 'N/A',
            attributes: '',
            qty: '0.000',
            pcs: '0',
            uom: 'N/A'
        };
    }
    
    let lines = display.split('<br>');
    let item_code = lines[0] || 'N/A';
    let qty = '0.000';
    let pcs = '0';
    let uom = 'N/A';
    let attributes = [];
    
    lines.forEach(function(line) {
        if (line.includes('Qty = ')) {
            qty = line.split('Qty = ')[1] || '0.000';
        } else if (line.includes('Pcs = ')) {
            pcs = line.split('Pcs = ')[1] || '0';
        } else if (line.includes('UOM = ')) {
            uom = line.split('UOM = ')[1] || 'N/A';
        } else if (line !== item_code && line.trim() !== '') {
            attributes.push(line);
        }
    });
    
    return {
        item_code: item_code,
        attributes: attributes.join('<br>'),
        qty: qty,
        pcs: pcs,
        uom: uom
    };
}
