// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Tag Search Detail"] = {
    filters: [
        {
            fieldname: "search_text",
            label: __("Search Serial No / Item Code"),
            fieldtype: "Small Text",
            width: 300,
            reqd: 0,
            description: __("Paste multiple Serial Nos. or Item Codes separated by new line, comma, space, or semicolon")
        }
    ],


    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);


        if (column.fieldname === "detail" && data && data.tag_no) {
            return `<button class="btn btn-xs btn-primary view-details-btn"
                        data-serial-no="${frappe.utils.escape_html(data.tag_no)}"
                        data-item-code="${frappe.utils.escape_html(data.item_code || "")}">
                        <i class="fa fa-eye"></i> View Detail
                    </button>`;
        }


        if (column.fieldtype === "Float" && value !== null && value !== undefined && value !== "") {
            let num = parseFloat(value);
            if (!isNaN(num)) {
                return num.toFixed(3);
            }
        }


        return value;
    },


    onload: function(report) {
        // View Summary Report Button - Pass same filters
        report.page.add_inner_button(__("View Summary Report"), function () {
            let current_filters = report.get_filter_values();
            frappe.set_route("query-report", "Tag Search Summary", current_filters);
        });

        $(document).off("click", ".view-details-btn");
        $(document).on("click", ".view-details-btn", function() {
            let serial_no = $(this).data("serial-no");
            let item_code = $(this).data("item-code");


            frappe.call({
                method: "gke_customization.gke_catalog.report.tag_search_detail.tag_search_detail.get_raw_material_details",
                args: {
                    serial_no: serial_no,
                    item_code: item_code
                },
                callback: function(r) {
                    if (r.message) {
                        show_serial_details_modal_with_raw_materials(r.message, serial_no, item_code);
                    } else {
                        frappe.msgprint(__("No details found for Serial No: {0}", [serial_no]));
                    }
                }
            });
        });
    }
};



function show_serial_details_modal_with_raw_materials(data, serial_no, item_code) {
    let raw_materials = data.raw_materials || [];
    let bom_name = data.bom_name || "N/A";
    let item_image = data.item_image || "";
    let item_category = data.item_category || "";
    let item_subcategory = data.item_subcategory || "";


    const isDarkTheme = document.documentElement.getAttribute("data-theme-mode") === "dark";
    const headerTextColor = isDarkTheme ? "#ffffff" : "#000000";
    const tableHeaderBg = isDarkTheme ? "#3a3a3a" : "#f8f9fa";
    const tableBorderColor = isDarkTheme ? "#4a4a4a" : "#dee2e6";


    const type_order = ["Metal", "Finding", "Diamond", "Gemstone", "Other", "Debug", "Error"];
    raw_materials.sort((a, b) => type_order.indexOf(a.type) - type_order.indexOf(b.type));


    let raw_material_rows = "";


    raw_materials.forEach(function(material) {
        let display = material.display || "";
        let lines = display.split("<br>");
        let code = lines[0] || "";
        let qty = "";
        let pcs = "";
        let uom = "";
        let attributes_without_qty_pcs = [];


        lines.slice(1).forEach(function(line) {
            if (line.includes("Qty =")) {
                qty = line.replace("Qty =", "").trim();
            } else if (line.includes("Pcs =")) {
                pcs = line.replace("Pcs =", "").trim();
            } else if (line.includes("UOM =")) {
                uom = line.replace("UOM =", "").trim();
            } else {
                attributes_without_qty_pcs.push(line);
            }
        });


        let attributes = attributes_without_qty_pcs.join("<br>") || "";


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
        title: "",
        fields: [
            {
                fieldtype: "HTML",
                options: dialog_html
            }
        ],
        size: "extra-large",
        primary_action_label: __("Close"),
        primary_action: function() {
            d.hide();
        }
    });


    d.show();
}



function show_full_image(image_url) {
    const image_modal_id = "serial-image-modal";
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


    $("body").append(modal_html);
}