frappe.query_reports["Metal Conversion Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                }
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value('company')
                    }
                }
            }
        },
        {
            "fieldname": "is_customer_metal",
            "label": __("Is Customer Metal"),
            "fieldtype": "Select",
            "options": "\nYes\nNo"
        }
    ],
    
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Format quantities with proper decimal places
        if (column.fieldname == "source_qty" || 
            column.fieldname == "source_alloy_qty" || 
            column.fieldname == "target_qty") {
            if (value && !isNaN(value)) {
                value = parseFloat(value).toFixed(3);
            }
        }
        
        return value;
    }
};
