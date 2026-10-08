// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt



frappe.query_reports["Production Report"] = {
    "filters": [
        // {
        //     "fieldname": "department",
        //     "label": __("Department"),
        //     "fieldtype": "Link",
        //     "options": "Department",
        //     // "reqd": 1,
        //     // "default": frappe.defaults.get_user_default("department")
        // },
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
    ],

    "onload": function(report) {
        const is_admin = frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

        if (!is_admin) {
            const user_department = frappe.defaults.get_user_default("department");

            if (user_department) {
                report.set_filter_value("department", user_department);
            }

            report.page.fields_dict.department.df.read_only = 1;
            report.page.fields_dict.department.df.description = __("Department is locked as per user default");
            report.page.fields_dict.department.refresh();
        }
    },



    "get_datatable_options": function(options) {
        return Object.assign(options, {
            hooks: {
                columnTotal: function(columnValues, cell) {
                    if (cell.column.fieldname === "serial_no") {
                        return columnValues.filter((v) => v).length;
                    }
                }
            }
        });
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        // Status color logic
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



        // Weight columns blank for zero values
        const weightColumns = [
            "gross_wt", "diamond_wt", "gemstone_wt", "other_wt",
            "metal_wt", "finding_wt", "net_wt", "pure_wt", "alloy_wt"
        ];
        const isDepartmentGrossWtColumn = column.fieldname && column.fieldname.startsWith("gross_wt_");
        if (weightColumns.includes(column.fieldname) || isDepartmentGrossWtColumn) {
            if (value === "" || value === null || value === undefined || value === "0.000") {
                value = "";
            }
        }



        // Piece columns blank for zero values
        const pieceColumns = ["diamond_pcs", "gemstone_pcs"];
        if (pieceColumns.includes(column.fieldname)) {
            if (value === "" || value === null || value === undefined || value === "0" || value === 0) {
                value = "";
            }
        }



        return value;
    }
};




// Global function for View Details button
window.show_serial_details = function(serial_no) {
    frappe.call({
        method: 'gke_customization.gke_catalog.report.production_report.production_report.get_serial_drill_down_details',
        args: { serial_no },
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



    // Detect dark theme
    const isDarkTheme = document.documentElement.getAttribute('data-theme-mode') === 'dark';
    const headerBgColor = isDarkTheme ? '#2d2d2d' : '#f8f9fa';
    const headerTextColor = isDarkTheme ? '#ffffff' : '#000000';
    const tableHeaderBg = isDarkTheme ? '#3a3a3a' : '#f8f9fa';
    const tableBorderColor = isDarkTheme ? '#4a4a4a' : '#dee2e6';



    // Modal HTML
    let html = `
    <div style="margin-bottom: 15px; padding: 15px; background: ${headerBgColor}; border-radius: 5px; border-left: 4px solid #007bff;">
        <div style="font-size: 16px; font-weight: 500; text-align: center; color: ${headerTextColor};">
            <strong>Serial No:</strong> ${details.serial_no} | <strong>Item:</strong> ${details.item_code} | <strong>BOM:</strong> ${bom_name || ""}
        </div>
    </div>
    <div style="margin-bottom: 20px;">
        <div class="row">
            <div class="col-md-6">
                <h6 style="color: ${headerTextColor}; font-weight: 600;">Basic Information</h6>
                <table class="table table-bordered table-sm" style="border-color: ${tableBorderColor};">
                    <tr><td><strong>Customer:</strong></td><td>${details.customer || ''}</td></tr>
                    <tr><td><strong>Category:</strong></td><td>${details.category || ''}</td></tr>
                    <tr><td><strong>Sub Category:</strong></td><td>${details.sub_category || ''}</td></tr>
                    <tr><td><strong>Setting Type:</strong></td><td>${details.setting_type || ''}</td></tr>
                    <tr><td><strong>Customer PO No:</strong></td><td>${details.customer_po_no || ''}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                ${details.product_image ? `
                    <h6 style="color: ${headerTextColor}; font-weight: 600;">Product Image</h6>
                    <div class="text-center">
                        <img src="${details.product_image}" 
                             style="height:200px; max-width:250px; border-radius:6px; cursor:pointer; object-fit:contain; border:1px solid #ddd;" 
                             onclick="show_full_image('${details.product_image}')">
                    </div>
                ` : ''}
            </div>
        </div>
    </div>
    <h6 style="color: ${headerTextColor}; font-weight: 600;">Raw Material Details</h6>
    <table class="table table-bordered" style="border-color: ${tableBorderColor};">
        <thead>
            <tr style="background-color: ${tableHeaderBg};">
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
        materials.forEach(function(material) {
            let parsedData = parseMaterialData(material.display);
            html += `
            <tr>
                <td><strong>${parsedData.code}</strong></td>
                <td style="font-size:12px;">${parsedData.attributes}</td>
                <td style="text-align:right;"><strong>${parsedData.qty}</strong></td>
                <td style="text-align:right;"><strong>${parsedData.pcs}</strong></td>
                <td style="text-align:center;">${parsedData.uom}</td>
            </tr>
            `;
        });
    } else {
        html += `
        <tr>
            <td colspan="5" style="text-align:center; color:#6c757d; padding:20px;">
                No raw material data available
            </td>
        </tr>
        `;
    }



    html += ` </tbody></table> `;



    let dialog = new frappe.ui.Dialog({
        // title: 'Serial No Details - ' + details.serial_no,
        size: 'extra-large',
        fields: [{ fieldtype: 'HTML', fieldname: 'serial_details_html' }]
    });



    dialog.fields_dict.serial_details_html.$wrapper.html(html);
    dialog.show();
}



// Helper to parse material display string into columns
function parseMaterialData(display) {
    let lines = display.split('<br>');
    let code = lines[0] || '';
    let qty = '', pcs = '', uom = '';
    let attributes = [];



    lines.forEach((line, index) => {
        if (index === 0) return;
        if (line.includes('Qty = ')) qty = line.replace('Qty = ', '').trim();
        else if (line.includes('Pcs = ')) pcs = line.replace('Pcs = ', '').trim();
        else if (line.includes('UOM = ')) uom = line.replace('UOM = ', '').trim();
        else if (line.trim()) attributes.push(line.trim());
    });



    return {
        code: code,
        attributes: attributes.join('<br>'),
        qty: qty,
        pcs: pcs,
        uom: uom
    };
}



// Full image overlay
function show_full_image(image_url) {
    const image_modal_id = "production-image-modal";
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