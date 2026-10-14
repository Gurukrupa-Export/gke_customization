// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Diamond & Gemstone Conversion Detail"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Select",
            "options": [
                "",
                // "Diamond Bagging - GEPL",
                "Diamond Bagging - KGJPL",
                // "Gemstone Bagging - GEPL",
                "Gemstone Bagging - KGJPL"
            ],
            "reqd": 1
        }
        
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Bold Source Qty and Total Target Qty
        if ((column.fieldname === "source_qty" || column.fieldname === "total_target_qty") && data[column.fieldname] != null && data[column.fieldname] !== "") {
            value = `<span style="font-weight: bold;">${value}</span>`;
        }
        
        return value;
    }
};
