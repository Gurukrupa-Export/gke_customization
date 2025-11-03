// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No Detail Report"] = {
    "filters": [
        {
            fieldname: "item_code",
            label: __("Item Code / Serial No"),
            fieldtype: "Data",
            width: 150,
            placeholder: "Enter Item Code or Serial Number",
            change: function() {
                let item_code = this.get_value();
                if (item_code) {
                    // Get categories for this item code or serial number
                    frappe.call({
                        method: "gke_customization.gke_catalog.report.serial_no_detail_report.serial_no_detail_report.get_item_category_details",
                        args: { item_code: item_code },
                        callback: function(r) {
                            if (r.message) {
                                frappe.query_report.set_filter_value('item_category', r.message.item_category);
                                frappe.query_report.set_filter_value('item_subcategory', r.message.item_subcategory);
                            }
                        }
                    });
                } else {
                    frappe.query_report.set_filter_value('item_category', '');
                    frappe.query_report.set_filter_value('item_subcategory', '');
                }
            }
        },
        {
            fieldname: "item_category",
            label: __("Item Category"),
            fieldtype: "Data", 
            width: 100,
            read_only: 1
        },
        {
            fieldname: "item_subcategory", 
            label: __("Item Sub Category"),
            fieldtype: "Data",
            width: 120,
            read_only: 1
        }
    ],

    onload: function (report) {
        // Event binding for View Details button
        frappe.after_ajax(() => {
            $(document).off("click", ".view-details-btn");
            $(document).on("click", ".view-details-btn", function () {
                let serial_no = $(this).data("serial-no");
                let item_code = $(this).data("item-code");

                frappe.call({
                    method: "gke_customization.gke_catalog.report.serial_no_detail_report.serial_no_detail_report.get_raw_material_details",
                    args: { 
                        serial_no: serial_no,
                        item_code: item_code
                    },
                    callback: function (r) {
                        if (r.message) {
                            show_serial_details_modal_with_raw_materials(r.message, serial_no, item_code);
                        } else {
                            frappe.msgprint(__('No details found for Serial No: {0}', [serial_no]));
                        }
                    }
                });
            });
        });
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Format the View Details button
        if (column.fieldname === "action" && value === "View Details") {
            return `<button class="btn btn-xs btn-primary view-details-btn" 
                        data-serial-no="${data.serial_no}" 
                        data-item-code="${data.item_code}">
                        <i class="fa fa-eye"></i> View Details
                    </button>`;
        }

        // Format numeric columns with proper alignment and precision
        if (column.fieldtype === "Float" && value !== null && value !== undefined && value !== "") {
            let precision = column.precision || 3;
            let num_value = parseFloat(value);
            if (!isNaN(num_value)) {
                return `<div style="text-align: right;">${num_value.toFixed(precision)}</div>`;
            }
        }

        return value;
    }
};

// Modal function with REMOVED HEADER and ADDED CATEGORIES
function show_serial_details_modal_with_raw_materials(data, serial_no, item_code) {
    let materials = data.raw_materials || [];
    let bom_name = data.bom_name || '';
    let item_image = data.item_image || '';
    
    // NO HEADER - Directly to Basic Information with Categories
    let html = `
    <!-- Basic Information Section with CATEGORIES -->
    <div style="margin-bottom: 20px;">
        <div class="row">
            <div class="col-md-8">
                <h6>Basic Information</h6>
                <table class="table table-bordered table-sm">
                    <tr><td><strong>Serial No:</strong></td><td>${serial_no}</td></tr>
                    <tr><td><strong>Item Code:</strong></td><td>${item_code}</td></tr>
                    <tr><td><strong>BOM:</strong></td><td>${bom_name || 'N/A'}</td></tr>
                    <tr><td><strong>Item Category:</strong></td><td>${data.item_category || 'N/A'}</td></tr>
                    <tr><td><strong>Item Subcategory:</strong></td><td>${data.item_subcategory || 'N/A'}</td></tr>
                </table>
            </div>
            <div class="col-md-4">
                ${item_image ? `
                    <h6>Product Image</h6>
                    <div class="text-center">
                        <img src="${item_image}" 
                             style="height:250px; max-width:100%; border-radius:6px; cursor:pointer; object-fit:contain; border: 1px solid #ddd;" 
                             onclick="show_full_image('${item_image}')">
                    </div>
                ` : ''}
            </div>
        </div>
    </div>

    <!-- Raw Materials Table -->
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
        title: 'Serial No Details - ' + serial_no,
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

// Helper function to parse material data into columns
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
    const image_modal_id = "serial-image-modal";
    
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