// Copyright (c) 2026, Gurukrupa Export Private Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Item With Tax"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                return [
                    { "value": "Consumable", "description": "" },
                    { "value": "Chemicals", "description": "" },
                    { "value": "Tools & Accessories", "description": "" },
                    { "value": "Medical Supplies", "description": "" },
                    { "value": "Stationary", "description": "" },
                    { "value": "Electric Accessories", "description": "" },
                    { "value": "Spare Accessories", "description": "" },
                    { "value": "Wax", "description": "" },
                    { "value": "Office Supplies", "description": "" },
                    { "value": "Machinery", "description": "" },
                    { "value": "Services", "description": "" },
                    { "value": "Subcontracting", "description": "" },
                    { "value": "IT Software Services", "description": "" },
                    { "value": "Expenses", "description": "" },
                    { "value": "Administrative Expense", "description": "" },
                    { "value": "Business Promotion Expense", "description": "" },
                    { "value": "Employee Benefits Expense", "description": "" },
                    { "value": "Finance Expense", "description": "" },
                    { "value": "Interest and Penalty Expense", "description": "" },
                    { "value": "Repairs and Maintance Expense", "description": "" },
                    { "value": "Selling and Distribution Expense", "description": "" },
                    { "value": "Utility Expense", "description": "" },
                    { "value": "Product Certification Expense", "description": "" },
                    { "value": "Dine & Stay Expense", "description": "" },
                    { "value": "Assets", "description": "" },
                    { "value": "Communication Devices", "description": "" },
                    { "value": "Landline Phones", "description": "" },
                    { "value": "Mobile", "description": "" },
                    { "value": "Computing Devices", "description": "" },
                    { "value": "Access Control", "description": "" },
                    { "value": "Ajax", "description": "" },
                    { "value": "Board", "description": "" },
                    { "value": "Computers", "description": "" },
                    { "value": "CPU", "description": "" },
                    { "value": "Keyboards", "description": "" },
                    { "value": "Laptop", "description": "" },
                    { "value": "Mice", "description": "" },
                    { "value": "Monitors", "description": "" },
                    { "value": "Printers", "description": "" },
                    { "value": "TV", "description": "" },
                    { "value": "Furniture", "description": "" },
                    { "value": "Chairs", "description": "" },
                    { "value": "Sofa", "description": "" },
                    { "value": "Lighting", "description": "" },
                    { "value": "Lamps", "description": "" },
                    { "value": "Networking Devices", "description": "" },
                    { "value": "Fire Safety", "description": "" },
                    { "value": "Network Equipment", "description": "" },
                    { "value": "Server", "description": "" },
                    { "value": "WiFi Routers", "description": "" },
                    { "value": "Surveillance", "description": "" },
                    { "value": "CCTV Cameras", "description": "" },
                    { "value": "CCTV Recorder", "description": "" },
                    { "value": "Weighing Scale", "description": "" },
                    { "value": "Vehicle", "description": "" },
                    { "value": "Four-Wheeler", "description": "" },
                    { "value": "Automated Screening Machine", "description": "" },
                    { "value": "Electronics", "description": "" },
                    { "value": "Machineries", "description": "" }
                ];
            }
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                let item_groups = [
                    "Consumable", "Chemicals", "Tools & Accessories", "Medical Supplies", 
                    "Stationary", "Electric Accessories", "Spare Accessories", "Wax", 
                    "Office Supplies", "Machinery", "Services", "Subcontracting", 
                    "IT Software Services", "Expenses", "Administrative Expense", 
                    "Business Promotion Expense", "Employee Benefits Expense", "Finance Expense", 
                    "Interest and Penalty Expense", "Repairs and Maintance Expense", 
                    "Selling and Distribution Expense", "Utility Expense", 
                    "Product Certification Expense", "Dine & Stay Expense", "Assets", 
                    "Communication Devices", "Landline Phones", "Mobile", "Computing Devices", 
                    "Access Control", "Ajax", "Board", "Computers", "CPU", "Keyboards", 
                    "Laptop", "Mice", "Monitors", "Printers", "TV", "Furniture", "Chairs", 
                    "Sofa", "Lighting", "Lamps", "Networking Devices", "Fire Safety", 
                    "Network Equipment", "Server", "WiFi Routers", "Surveillance", 
                    "CCTV Cameras", "CCTV Recorder", "Weighing Scale", "Vehicle", 
                    "Four-Wheeler", "Automated Screening Machine", "Electronics", "Machineries"
                ];
                
                return {
                    filters: {
                        "item_group": ["in", item_groups],
                        "disabled": 0
                    }
                };
            }
        }
    ]
};
