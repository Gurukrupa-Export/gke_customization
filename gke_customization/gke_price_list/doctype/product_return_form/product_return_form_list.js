// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.listview_settings['Product Return Form'] = {
    // hide_name_column: true,
    get_indicator: function (doc) {
        if (doc.status === "Draft") {
            return [__("Draft"), "orange", "status,=,Draft"];
        } else if (doc.status === "Item & BOM Creation") {
            return [__("Item & BOM Creation"), "yellow", "status,=,Item & BOM Creation"];
        } else if (doc.status === "Send to Pricing") {
            return [__("Send to Pricing"), "purple", "status,=,Send to Pricing"];
        } else if (doc.status === "Verified") {
            return [__("Verified"), "blue", "status,=,Verified"];
        } else if (doc.status === "Approved") {
            return [__("Approved"), "green", "status,=,Approved"];
        } else if (doc.status === "Issued") {
            return [__("Issued"), "green", "status,=,Issued"];
        } else if (doc.status === "Cancelled") {
            return [__("Cancelled"), "red", "status,=,Cancelled"];
        }
    }
};