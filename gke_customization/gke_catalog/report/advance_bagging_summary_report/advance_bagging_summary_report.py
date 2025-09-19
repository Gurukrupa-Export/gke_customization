# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Sum of Quantity", "fieldname": "sum_of_quantity", "fieldtype": "Float", "width": 150, "precision": 3},
        {"label": "Count of Pcs", "fieldname": "count_of_pcs", "fieldtype": "Int", "width": 120}
    ]

def get_data(filters=None):
    # Get base data using the same logic as main report
    base_data = get_base_report_data(filters)
    
    # Group by item_code for summary
    item_summary = {}
    total_qty = 0
    total_pcs = 0
    
    for row in base_data:
        item_code = row.get("item_code")
        if not item_code:
            continue
            
        qty = flt(row.get("qty", 0))
        pcs = flt(row.get("pcs", 0))
        
        if item_code not in item_summary:
            item_summary[item_code] = {
                "item_code": item_code,
                "sum_of_quantity": 0,
                "count_of_pcs": 0
            }
        
        item_summary[item_code]["sum_of_quantity"] += qty
        item_summary[item_code]["count_of_pcs"] += pcs
        
        total_qty += qty
        total_pcs += pcs
    
    # Convert to list and sort by item_code
    result = list(item_summary.values())
    result.sort(key=lambda x: x["item_code"])
    
    # Add Grand Total row
    result.append({
        "item_code": "Grand Total",
        "sum_of_quantity": total_qty,
        "count_of_pcs": total_pcs
    })
    
    return result

def get_base_report_data(filters):
    """Get base data from main report logic"""
    filters_dict = {
        "material_request_type": "Manufacture",
        "workflow_state": ["!=", "Material Transferred to MOP"]
    }

    # Apply date filters
    if filters.get("from_date") and filters.get("to_date"):
        filters_dict["creation"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        filters_dict["creation"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        filters_dict["creation"] = ["<=", filters["to_date"]]

    # Apply other filters
    if filters.get("manufacturing_order"):
        filters_dict["manufacturing_order"] = ["in", filters["manufacturing_order"]]
    if filters.get("workflow_state"):
        filters_dict["workflow_state"] = ["in", filters["workflow_state"]]

    data = []

    # Get Material Requests
    material_requests = frappe.get_all("Material Request", 
        fields=[
            "name", "material_request_type", "title", "manufacturing_order",
            "workflow_state"
        ],
        filters=filters_dict,
    )

    for mr in material_requests:
        material_type = get_material_type_from_title(mr.title)
        
        # Filter by material type if specified
        if filters.get("material_type") and filters["material_type"] != material_type:
            continue

        # Get MR items
        mr_items = frappe.get_all("Material Request Item",
            fields=["item_code", "qty", "pcs"],
            filters={"parent": mr.name}
        )

        # Get PMO details for filtering
        pmo = frappe.get_value("Parent Manufacturing Order", mr.manufacturing_order,
            ["item_category", "setting_type"], as_dict=True
        ) if mr.manufacturing_order else {}

        # Apply PMO filters
        if filters.get("item_category") and pmo and pmo.get("item_category") not in filters["item_category"]:
            continue
        if filters.get("setting_type") and pmo and pmo.get("setting_type") not in filters["setting_type"]:
            continue

        for item in mr_items:
            row = {
                "item_code": item.item_code,
                "qty": item.qty,
                "pcs": item.pcs
            }
            data.append(row)

    return data

def get_material_type_from_title(title):
    """Extract material type from MR title"""
    if not title or len(title) < 3:
        return "Unknown"
    
    code = title[2]  # 3rd character
    return {
        "D": "Diamond",
        "M": "Metal", 
        "G": "Gemstone",
        "F": "Finding",
        "O": "Others"
    }.get(code, "Unknown")
