// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Assortment Report"] = {
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
            "options": "Branch",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        'company': company
                    }
                };
            }
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Select",
            "options": [
                "",
                "Diamond Bagging - GEPL",
                "Diamond Bagging - KGJPL",
                "Gemstone Bagging - GEPL",
                "Gemstone Bagging - KGJPL"
            ],
            "reqd": 1,
            "on_change": function() {
                // Auto-set company based on department
                let dept = frappe.query_report.get_filter_value('department');
                if (dept) {
                    if (dept.includes('GEPL')) {
                        frappe.query_report.set_filter_value('company', 'Gurukrupa Export Private Limited');
                    } else if (dept.includes('KGJPL')) {
                        frappe.query_report.set_filter_value('company', 'KG GK Jewellers Private Limited');
                    }
                }
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer",
            "reqd": 1,
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        'company': company
                    }
                };
            }
        },
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
