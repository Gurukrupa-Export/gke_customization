// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Production Report"] = {
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
            "default": frappe.datetime.get_today(),
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
            "fieldname": "order_type",
            "label": __("Order Type"),
            "fieldtype": "Select",
            "options": "\nSales\nStock Order\nRepair"
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Apply custom formatting for specific columns
        if (column.fieldname === "serial_no_status") {
            if (value === "Active") {
                value = `<span class="indicator green">Active</span>`;
            } else if (value === "Delivered") {
                value = `<span class="indicator blue">Delivered</span>`;
            } else if (value === "Reserved") {
                value = `<span class="indicator orange">Reserved</span>`;
            } else {
                value = `<span class="indicator gray">${value}</span>`;
            }
        }
        
        // Format weight columns to show blank for empty values
        const weightColumns = [
            "gross_wt", "diamond_wt", "gemstone_wt", "other_wt", 
            "metal_wt", "finding_wt", "net_wt", "pure_wt", "alloy_wt"
        ];
        
        if (weightColumns.includes(column.fieldname)) {
            if (value === "" || value === null || value === undefined || value === "0.000") {
                value = "";
            }
        }
        
        // Format piece columns to show blank for zero values
        const pieceColumns = ["diamond_pcs", "gemstone_pcs"];
        
        if (pieceColumns.includes(column.fieldname)) {
            if (value === "" || value === null || value === undefined || value === "0" || value === 0) {
                value = "";
            }
        }
        
        return value;
    }
};

// Global function for View Details button - Updated to match Serial No Detail Report
window.show_serial_details = function(serial_no) {
    frappe.call({
        method: 'gke_customization.gke_catalog.report.production_report.production_report.get_serial_drill_down_details',
        args: {
            serial_no: serial_no
        },
        callback: function(r) {
            if (r.message) {
                show_serial_details_modal_with_raw_materials(r.message);
            } else {
                frappe.msgprint(__('No details found for Serial No: {0}', [serial_no]));
            }
        }
    });
};

function show_serial_details_modal_with_raw_materials(details) {
    let materials = details.raw_materials || [];
    let bom_name = details.bom_name || '';
    let item_image = details.product_image || '';
    
    // Build header exactly like Serial No Detail Report
    let html = `
    <div style="margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #007bff;">
        <div style="font-size: 16px; font-weight: 500; text-align: center;">
            <strong>Serial No:</strong> ${details.serial_no} | <strong>Item:</strong> ${details.item_code} | <strong>BOM:</strong> ${bom_name || ""}
        </div>
    </div>
    
    <!-- Basic Information Section - REMOVED QUANTITY & PIECES -->
    <div style="margin-bottom: 20px;">
        <div class="row">
            <div class="col-md-6">
                <h6>Basic Information</h6>
                <table class="table table-bordered table-sm">
                    <tr><td><strong>Customer:</strong></td><td>${details.customer || ''}</td></tr>
                    <tr><td><strong>Category:</strong></td><td>${details.category || ''}</td></tr>
                    <tr><td><strong>Sub Category:</strong></td><td>${details.sub_category || ''}</td></tr>
                    <tr><td><strong>Setting Type:</strong></td><td>${details.setting_type || ''}</td></tr>
                    <tr><td><strong>Customer PO No:</strong></td><td>${details.customer_po_no || ''}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                
                ${details.product_image ? `
                    <h6>Product Image</h6>
                    <div class="text-center">
                        <img src="${details.product_image}" 
                             style="height:100px; border-radius:6px; cursor:pointer; object-fit:contain; border: 1px solid #ddd;" 
                             onclick="show_full_image('${details.product_image}')">
                    </div>
                ` : ''}
            </div>
        </div>
    </div>

    <!-- Raw Materials Table - REMOVED TYPE COLUMN -->
    <h6>Raw Material Details</h6>
    <table class="table table-bordered">
        <thead>
            <tr style="background-color: #f8f9fa;">
                <th style="width: 25%;">Raw Material Code</th>
                <th style="width: 45%;">Attributes</th>
                <th style="width: 10%;">Qty</th>
                <th style="width: 10%;">Pcs</th>
                <th style="width: 10%;">UOM</th>
            </tr>
        </thead>
        <tbody>
    `;

    if (materials && materials.length > 0) {
        materials.forEach(function (material) {
            let parsedData = parseMaterialData(material.display);
            
            html += `
            <tr>
                <td><strong>${parsedData.code}</strong></td>
                <td style="font-size: 12px;">${parsedData.attributes}</td>
                <td style="text-align: right;"><strong>${parsedData.qty}</strong></td>
                <td style="text-align: right;"><strong>${parsedData.pcs}</strong></td>
                <td style="text-align: center;">${parsedData.uom}</td>
            </tr>
            `;
        });
    } else {
        html += `
        <tr>
            <td colspan="5" style="text-align: center; color: #6c757d; padding: 20px;">
                No raw material data available
            </td>
        </tr>
        `;
    }

    html += `
        </tbody>
    </table>
    `;

    let dialog = new frappe.ui.Dialog({
        title: 'Serial No Details - ' + details.serial_no,
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'serial_details_html'
            }
        ]
    });

    dialog.fields_dict.serial_details_html.$wrapper.html(html);
    dialog.show();
}

// Helper function to parse material data into columns (EXACT COPY from Serial No Detail Report)
function parseMaterialData(display) {
    let lines = display.split('<br>');
    let code = lines[0] || '';
    let qty = '';
    let pcs = '';
    let uom = '';
    let attributes = [];
    
    // Extract qty, pcs, uom and build attributes
    lines.forEach((line, index) => {
        if (index === 0) return; // Skip first line (code)
        
        if (line.includes('Qty = ')) {
            qty = line.replace('Qty = ', '').trim();
        } else if (line.includes('Pcs = ')) {
            pcs = line.replace('Pcs = ', '').trim();
        } else if (line.includes('UOM = ')) {
            uom = line.replace('UOM = ', '').trim();
        } else if (line.trim() !== '') {
            // Add to attributes (excluding qty, pcs, uom)
            attributes.push(line.trim());
        }
    });
    
    return {
        code: code,
        attributes: attributes.join('<br>'),
        qty: qty,
        pcs: pcs,
        uom: uom
    };
}

// Function to show full image in overlay
function show_full_image(image_url) {
    const image_modal_id = "production-image-modal";
    
    // Remove existing modal if any
    $(`#${image_modal_id}`).remove();
    
    let modal_html = `
        <div id="${image_modal_id}" class="custom-image-modal" 
             style="display:flex; position:fixed; top:0; left:0; width:100%; height:100%; 
                    background-color:rgba(0,0,0,0.8); align-items:center; justify-content:center; z-index:2000;" 
             onclick="this.style.display='none'">
            <img src="${image_url}" 
                 style="max-width:90%; max-height:90%; border-radius:8px;" 
                 onclick="event.stopPropagation()">
        </div>
    `;
    
    $('body').append(modal_html);
}