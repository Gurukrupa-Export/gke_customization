# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "sr_no", "label": _("Sr.No"), "fieldtype": "Int", "width": 60},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"fieldname": "min_qty", "label": _("Min Qty"), "fieldtype": "Float", "width": 90, "precision": 2},
        {"fieldname": "max_qty", "label": _("Max Qty"), "fieldtype": "Float", "width": 90, "precision": 2},
        {"fieldname": "total_bal", "label": _("Total Bal."), "fieldtype": "Float", "width": 120, "precision": 3},
        {"fieldname": "uom", "label": _("Unit"), "fieldtype": "Link", "options": "UOM", "width": 80},
        {"fieldname": "rate", "label": _("Rate"), "fieldtype": "Currency", "width": 100},
        {"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "stock_status", "label": _("Status"), "fieldtype": "Data", "width": 120}
    ]

def get_data(filters):
    conditions = []
    
    if filters.get('company'):
        conditions.append("AND w.company = %(company)s")
    
    if filters.get('warehouse'):
        conditions.append("AND b.warehouse = %(warehouse)s")
    
    if filters.get('item_group'):
        conditions.append("AND i.item_group = %(item_group)s")
    
    if filters.get('item_code'):
        conditions.append("AND (i.item_code LIKE CONCAT('%%', %(item_code)s, '%%') OR i.item_name LIKE CONCAT('%%', %(item_code)s, '%%'))")
    
    where_clause = " ".join(conditions)
    
    query = f"""
        SELECT 
            i.item_code,
            i.item_name,
            i.item_group,
            COALESCE(i.custom_min_qty, 0) as min_qty,
            COALESCE(i.custom_max_qty, 0) as max_qty,
            b.warehouse,
            COALESCE(b.actual_qty, 0) as actual_qty,
            i.stock_uom as uom,
            COALESCE(b.valuation_rate, i.valuation_rate, 0) as rate,
            COALESCE(b.stock_value, 0) as stock_value
        FROM `tabItem` i
        INNER JOIN `tabBin` b ON (b.item_code = i.item_code OR b.item_code = i.item_name)
        INNER JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE i.item_group IN (
            SELECT name FROM `tabItem Group`
            WHERE parent_item_group LIKE '%%Consumable%%'
        )
        AND i.disabled = 0
        AND b.actual_qty != 0
        {where_clause}
        ORDER BY i.item_group, i.item_name, b.warehouse
    """
    
    raw_data = frappe.db.sql(query, filters, as_dict=1)
    
    item_data = {}
    for row in raw_data:
        item_code = row['item_code']
        
        if item_code not in item_data:
            item_data[item_code] = {
                'item_code': row['item_code'],
                'item_name': row['item_name'],
                'item_group': row['item_group'],
                'min_qty': row['min_qty'],
                'max_qty': row['max_qty'],
                'uom': row['uom'],
                'total_bal': 0,
                'amount': 0,
                'rate': row['rate']
            }
        
        item_data[item_code]['total_bal'] = item_data[item_code]['total_bal'] + row['actual_qty']
        item_data[item_code]['amount'] = item_data[item_code]['amount'] + row['stock_value']
    
    result = []
    sr_no = 1
    
    for item_code in sorted(item_data.keys()):
        row = item_data[item_code]
        row['sr_no'] = sr_no
        
        total_bal = row['total_bal']
        min_qty = row['min_qty']
        max_qty = row['max_qty']
        
        if total_bal == 0:
            row['stock_status'] = 'Out of Stock'
        elif min_qty > 0 and total_bal < min_qty:
            row['stock_status'] = 'Below Min'
        elif max_qty > 0 and total_bal > max_qty:
            row['stock_status'] = 'Above Max'
        else:
            row['stock_status'] = 'In Stock'
        
        result.append(row)
        sr_no = sr_no + 1
    
    return result
