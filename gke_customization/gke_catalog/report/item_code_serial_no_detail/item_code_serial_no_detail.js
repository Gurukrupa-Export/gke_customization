// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Item Code Serial No Detail"] = {
    "filters": [
        {
            fieldname: "item_code",
            label: __("Search Serial No / Item Code"),
            fieldtype: "Data",
            width: 150
        },
        {
            fieldname: "item_category",
            label: __("Item Category"),
            fieldtype: "Data",
            width: 120,
            read_only: 1
        },
        {
            fieldname: "item_subcategory",
            label: __("Item Sub Category"),
            fieldtype: "Data",
            width: 140,
            read_only: 1
        }
    ],


    onload: function (report) {
        // RESTORE CATEGORY VALUES AFTER REPORT REFRESH
        frappe.after_ajax(() => {
            let stored_category = sessionStorage.getItem('serial_report_category');
            let stored_subcategory = sessionStorage.getItem('serial_report_subcategory');
            
            if (stored_category) {
                let cat_filter = frappe.query_report.get_filter('item_category');
                if (cat_filter) {
                    cat_filter.set_value(stored_category);
                }
            }
            
            if (stored_subcategory) {
                let subcat_filter = frappe.query_report.get_filter('item_subcategory');
                if (subcat_filter) {
                    subcat_filter.set_value(stored_subcategory);
                }
            }
        });
        
        // Autocomplete with focus fix
        let awesomplete_instance = null;
        
        frappe.after_ajax(() => {
            let filter = frappe.query_report.get_filter('item_code');
            if (filter && filter.$input) {
                filter.$input.attr('autocomplete', 'off');
                
                // Autocomplete input handler
                filter.$input.on('input', frappe.utils.debounce(function(e) {
                    let txt = $(this).val();
                    let input_element = this;
                    
                    if (txt.length >= 1) {
                        frappe.call({
                            method: "gke_customization.gke_catalog.report.item_code_serial_no_detail.item_code_serial_no_detail.get_autocomplete_options",
                            args: { txt: txt },
                            callback: function(r) {
                                if (r.message && r.message.length > 0) {
                                    // ONLY show the value (no suffix)
                                    let suggestions = r.message.map(item => item.value);
                                    
                                    if (awesomplete_instance) {
                                        awesomplete_instance.destroy();
                                    }
                                    
                                    awesomplete_instance = new Awesomplete(input_element, {
                                        list: suggestions,
                                        minChars: 0,
                                        maxItems: 20,
                                        autoFirst: true
                                    });
                                    
                                    awesomplete_instance.evaluate();
                                    awesomplete_instance.open();
                                    
                                    setTimeout(() => {
                                        $(input_element).focus();
                                    }, 0);
                                }
                            }
                        });
                    } else {
                        if (awesomplete_instance) {
                            awesomplete_instance.close();
                        }
                    }
                }, 300));
                
                // Handle awesomplete selection
                filter.$input.on('awesomplete-selectcomplete', function(e) {
                    // No need to split - just use the selected value directly
                    let selected = e.text.value;
                    filter.set_value(selected);
                    
                    // Fetch and populate categories
                    fetchAndPopulateCategories(selected);
                    
                    setTimeout(() => {
                        $(this).focus();
                    }, 0);
                });
                
                // Handle awesomplete open
                filter.$input.on('awesomplete-open', function() {
                    $(this).focus();
                });
                
                // Handle Enter key press
                filter.$input.on('keypress', function(e) {
                    if (e.which === 13) { // Enter key
                        let selected = $(this).val().trim();
                        if (selected) {
                            fetchAndPopulateCategories(selected);
                        }
                    }
                });
                
                // Handle blur (when user leaves the field)
                filter.$input.on('blur', function() {
                    let selected = $(this).val().trim();
                    if (selected) {
                        fetchAndPopulateCategories(selected);
                    }
                });
            }
        });
        
        // View Details button
        frappe.after_ajax(() => {
            $(document).off("click", ".view-details-btn");
            $(document).on("click", ".view-details-btn", function () {
                let serial_no = $(this).data("serial-no");
                let item_code = $(this).data("item-code");


                frappe.call({
                    method: "gke_customization.gke_catalog.report.item_code_serial_no_detail.item_code_serial_no_detail.get_raw_material_details",
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


        if (column.fieldname === "action" && value === "View Details") {
            return `<button class="btn btn-xs btn-primary view-details-btn" 
                        data-serial-no="${data.serial_no}" 
                        data-item-code="${data.item_code}">
                        <i class="fa fa-eye"></i> View Details
                    </button>`;
        }


        if (column.fieldtype === "Float" && value !== null && value !== undefined && value !== "") {
            let num = parseFloat(value);
            if (!isNaN(num)) {
                return num.toFixed(3);
            }
        }


        return value;
    }
};


// CATEGORY FETCH FUNCTION WITH SESSION STORAGE
function fetchAndPopulateCategories(item_code) {
    frappe.call({
        method: "gke_customization.gke_catalog.report.item_code_serial_no_detail.item_code_serial_no_detail.get_item_category_details",
        args: { item_code: item_code },
        callback: function(r) {
            if (r.message) {
                let cat_filter = frappe.query_report.get_filter('item_category');
                let subcat_filter = frappe.query_report.get_filter('item_subcategory');
                
                if (cat_filter) {
                    cat_filter.set_value(r.message.item_category || '');
                }
                
                if (subcat_filter) {
                    subcat_filter.set_value(r.message.item_subcategory || '');
                }
                
                // STORE IN SESSION STORAGE TO PERSIST AFTER REFRESH
                sessionStorage.setItem('serial_report_category', r.message.item_category || '');
                sessionStorage.setItem('serial_report_subcategory', r.message.item_subcategory || '');
                
                // Refresh report
                setTimeout(function() {
                    frappe.query_report.refresh();
                }, 200);
            }
        },
        error: function(err) {
            console.error('API Error:', err);
        }
    });
}


// UPDATED WITH DARK THEME SUPPORT - KEEPING EXACT FORMAT
function show_serial_details_modal_with_raw_materials(data, serial_no, item_code) {
    let raw_materials = data.raw_materials || [];
    let bom_name = data.bom_name || "N/A";
    let item_image = data.item_image || "";
    let item_category = data.item_category || "";
    let item_subcategory = data.item_subcategory || "";
    
    // Detect dark theme
    const isDarkTheme = document.documentElement.getAttribute('data-theme-mode') === 'dark';
    const headerTextColor = isDarkTheme ? '#ffffff' : '#000000';
    const tableHeaderBg = isDarkTheme ? '#3a3a3a' : '#f8f9fa';
    const tableBorderColor = isDarkTheme ? '#4a4a4a' : '#dee2e6';
    
    // Sort raw materials
    const type_order = ["Metal", "Finding", "Diamond", "Gemstone", "Other", "Debug", "Error"];
    raw_materials.sort((a, b) => {
        return type_order.indexOf(a.type) - type_order.indexOf(b.type);
    });
    
    // Build raw material table rows WITH BOLD VALUES
    let raw_material_rows = "";
    raw_materials.forEach(function(material) {
        let display = material.display || "";
        let lines = display.split('<br>');
        let code = lines[0] || '';
        
        // Extract Qty and Pcs from attributes
        let qty = '';
        let pcs = '';
        let uom = '';
        let attributes_without_qty_pcs = [];
        
        lines.slice(1).forEach(function(line) {
            if (line.includes('Qty =')) {
                qty = line.replace('Qty =', '').trim();
            } else if (line.includes('Pcs =')) {
                pcs = line.replace('Pcs =', '').trim();
            } else if (line.includes('UOM =')) {
                uom = line.replace('UOM =', '').trim();
            } else {
                attributes_without_qty_pcs.push(line);
            }
        });
        
        // Join attributes with <br> for line breaks
        let attributes = attributes_without_qty_pcs.join('<br>') || '';
        
        // BOLD THE VALUES WITH DARK THEME SUPPORT
        raw_material_rows += `
            <tr>
                <td style="color: ${headerTextColor}; border-color: ${tableBorderColor};"><strong style="color: ${headerTextColor};">${code}</strong></td>
                <td style="font-size: 12px; color: ${headerTextColor}; border-color: ${tableBorderColor};">${attributes}</td>
                <td style="text-align: right; color: ${headerTextColor}; border-color: ${tableBorderColor};"><strong style="color: ${headerTextColor};">${qty}</strong></td>
                <td style="text-align: right; color: ${headerTextColor}; border-color: ${tableBorderColor};"><strong style="color: ${headerTextColor};">${pcs}</strong></td>
                <td style="text-align: center; color: ${headerTextColor}; border-color: ${tableBorderColor};">${uom}</td>
            </tr>
        `;
    });
    
    if (raw_material_rows === "") {
        raw_material_rows = `
            <tr>
                <td colspan="5" style="text-align: center; color: #6c757d; padding: 20px; border-color: ${tableBorderColor};">No raw materials found</td>
            </tr>
        `;
    }
    
    // Image HTML WITH LIGHT BORDER
    let image_html = "";
    if (item_image) {
        image_html = `
            <h6 style="color: ${headerTextColor}; font-weight: 600;">Product Image</h6>
            <div class="text-center">
                <img src="${item_image}" 
                     style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;" 
                     onclick="show_full_image('${item_image}')">
            </div>
        `;
    }
    
    // KEEPING EXACT BASIC INFORMATION FORMAT - NO TABLE STRUCTURE
    let dialog_html = `
        <div style="margin-bottom: 20px;">
            <div class="row">
                <div class="col-md-8">
                    <h6 style="color: ${headerTextColor}; font-weight: 600;">Basic Information</h6>
                    <div style="color: ${headerTextColor};">
                        <p><strong style="color: ${headerTextColor};">Serial No:</strong> ${serial_no}</p>
                        <p><strong style="color: ${headerTextColor};">Item Code:</strong> ${item_code}</p>
                        <p><strong style="color: ${headerTextColor};">BOM:</strong> ${bom_name}</p>
                        <p><strong style="color: ${headerTextColor};">Item Category:</strong> ${item_category}</p>
                        <p><strong style="color: ${headerTextColor};">Item Subcategory:</strong> ${item_subcategory}</p>
                    </div>
                </div>
                <div class="col-md-4">
                    ${image_html}
                </div>
            </div>
        </div>


        <h6 style="color: ${headerTextColor}; font-weight: 600;">Raw Material Details</h6>
        <table class="table table-bordered" style="border-color: ${tableBorderColor};">
            <thead>
                <tr style="background-color: ${tableHeaderBg};">
                    <th style="width: 25%; color: ${headerTextColor}; background-color: ${tableHeaderBg}; border-color: ${tableBorderColor};">Raw Material Code</th>
                    <th style="width: 45%; color: ${headerTextColor}; background-color: ${tableHeaderBg}; border-color: ${tableBorderColor};">Attributes</th>
                    <th style="width: 10%; color: ${headerTextColor}; background-color: ${tableHeaderBg}; border-color: ${tableBorderColor};">Qty</th>
                    <th style="width: 10%; color: ${headerTextColor}; background-color: ${tableHeaderBg}; border-color: ${tableBorderColor};">Pcs</th>
                    <th style="width: 10%; color: ${headerTextColor}; background-color: ${tableHeaderBg}; border-color: ${tableBorderColor};">UOM</th>
                </tr>
            </thead>
            <tbody>
                ${raw_material_rows}
            </tbody>
        </table>
    `;
    
    let d = new frappe.ui.Dialog({
        title: '',
        fields: [
            {
                fieldtype: 'HTML',
                options: dialog_html
            }
        ],
        size: 'extra-large',
        primary_action_label: __('Close'),
        primary_action: function() {
            d.hide();
        }
    });
    
    d.show();
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
