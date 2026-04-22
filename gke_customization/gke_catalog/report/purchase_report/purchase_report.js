// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase report"] = {
    "filters": [
        {
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": "Gurukrupa Export Private Limited"
		},
        {
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_end()
		},
        {
            "fieldname": "item_code",
            "label": "Item Code",
            "fieldtype": "Link",
            "options": "Item"
        },
        {
			"fieldname": "item_group",
			"label": "Item Group",
			"fieldtype": "Link",
			"options": "Item Group",
			"get_query": function() {
				return {
					filters: {
						"is_group": 1
					}
				};
			}
		},
		{
            "fieldname": "supplier",
            "label": "Supplier",
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Link",
            "options": "Department"
        }
    ]
};