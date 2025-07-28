# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

def execute(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Fetch all potential duplicates
    data = frappe.db.sql("""
        SELECT 
            name, design_type, po_no, order_type, flow_type, design_id, qty,
            category, subcategory, setting_type, metal_type,
            bom_or_cad, customer_code, design_by, sub_setting_type1,
            metal_touch, diamond_target, metal_colour, diamond_type,
            metal_target, sizer_type, product_size, rhodium_,
            chain_length, gemstone_type, detachable,
            item, new_bom, item_remark
        FROM `tabOrder`
        WHERE creation BETWEEN %(from_date)s AND %(to_date)s
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    # Group by keys to find duplicates
    from collections import defaultdict
    grouped = defaultdict(list)
    for row in data:
        key = (
            row.design_type, row.customer_code, row.order_type, row.design_by,
            row.design_id, row.category, row.subcategory, row.setting_type, row.sub_setting_type1,
            row.metal_type, row.metal_target, row.sizer_type,
            row.chain_length, row.item, row.flow_type
        )
        grouped[key].append(row)

    result = []
    for group_rows in grouped.values():
        if len(group_rows) > 1:
            # First row — parent with tree structure
            base = group_rows[0]
            base_row = {
                "order_id": base.name,
                "parent_order": None,  # parent row
                "indent": 0,
                "has_value": True,
                "duplicate_count": len(group_rows) - 1,
                "design_type": base.design_type,
                "po_no": base.po_no,
                "order_type": base.order_type,
                "flow_type": base.flow_type,
                "design_id": base.design_id,
                "qty": base.qty,
                "category": base.category,
                "subcategory": base.subcategory,
                "setting_type": base.setting_type,
                "metal_type": base.metal_type
            }
            result.append(base_row)

            # Child rows with indent
            for child in group_rows[1:]:
                child_row = {
                    "order_id": child.name,
                    "parent_order": base.name,  
                    "indent": 1,
                    "has_value": True,
                    "duplicate_count": "",
                    "design_type": child.design_type,
                    "po_no": child.po_no,
                    "order_type": child.order_type,
                    "flow_type": child.flow_type,
                    "design_id": child.design_id,
                    "qty": child.qty,
                    "category": child.category,
                    "subcategory": child.subcategory,
                    "setting_type": child.setting_type,
                    "metal_type": child.metal_type
                }
                result.append(child_row)

    columns = [
        {"fieldname": "order_id", "label": "Order ID", "fieldtype": "Link", "options": "Order", "width": 180},
        {"fieldname": "parent_order", "label": "Parent", "fieldtype": "Data", "hidden": 1},
        {"fieldname": "duplicate_count", "label": "Duplicate Count", "fieldtype": "Data", "width": 150},
        {"fieldname": "design_type", "label": "Design Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "po_no", "label": "PO No", "fieldtype": "Data", "width": 100},
        {"fieldname": "order_type", "label": "Order Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "flow_type", "label": "Flow Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "design_id", "label": "Design ID", "fieldtype": "Data", "width": 120},
        {"fieldname": "qty", "label": "Qty", "fieldtype": "Int", "width": 80},
        {"fieldname": "category", "label": "Category", "fieldtype": "Data", "width": 100},
        {"fieldname": "subcategory", "label": "Subcategory", "fieldtype": "Data", "width": 100},
        {"fieldname": "setting_type", "label": "Setting Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_type", "label": "Metal Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "indent", "label": "Indent", "fieldtype": "Int", "width": 50, "hidden": 1},
        {"fieldname": "has_value", "label": "Has Value", "fieldtype": "Check", "hidden": 1}
    ]

    return columns, result