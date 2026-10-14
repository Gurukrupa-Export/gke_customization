# Copyright (c) 2025, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "label": _("Creation Date & Time"),
            "fieldname": "creation_date_time",
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "label": _("Gemstone Conversion ID"),
            "fieldname": "gemstone_conversion_id",
            "fieldtype": "Link",
            "options": "Gemstone Conversion",
            "width": 160
        },
        {
            "label": _("User"),
            "fieldname": "user_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        },
        {
            "label": _("Manufacturer"),
            "fieldname": "manufacturer",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 120
        },
        {
            "label": _("Source Item"),
            "fieldname": "source_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Source Item Qty"),
            "fieldname": "source_item_qty",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        },
        {
            "label": _("Target Item"),
            "fieldname": "target_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Target Item Qty"),
            "fieldname": "target_item_qty",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        },
        {
            "label": _("Inventory Type"),
            "fieldname": "inventory_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Loss Item"),
            "fieldname": "loss_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": _("Stock Entry ID"),
            "fieldname": "stock_entry_id",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 140
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get Gemstone Conversion records with Stock Entry join and User full_name
    conversion_query = f"""
        SELECT DISTINCT
            gc.creation,
            gc.name as conversion_id,
            gc.owner,
            u.full_name as user_full_name,
            gc.company,
            gc.branch,
            gc.manufacturer,
            gc.department,
            gc.g_source_item,
            gc.g_source_qty,
            gc.inventory_type,
            gc.g_loss_item,
            se.name as stock_entry_from_join
        FROM `tabGemstone Conversion` gc
        LEFT JOIN `tabStock Entry` se ON gc.name = se.custom_gemstone_conversion
        LEFT JOIN `tabUser` u ON gc.owner = u.name
        WHERE gc.docstatus = 1 {conditions}
        ORDER BY gc.creation DESC
    """
    
    conversions = frappe.db.sql(conversion_query, filters, as_dict=1)
    
    result = []
    
    for conversion in conversions:
        conversion_id = conversion.conversion_id
        
        # Get target items from child table (keep individual)
        target_query = """
            SELECT item_code, qty, inventory_type, idx
            FROM `tabSC Target Table`
            WHERE parent = %s AND parentfield = 'sc_target_table'
            ORDER BY idx
        """
        target_items = frappe.db.sql(target_query, (conversion_id,), as_dict=1)
        
        # If no target items in child table, create one row with parent data
        if not target_items:
            target_items = [{"item_code": conversion.g_target_item, "qty": conversion.g_target_qty, "inventory_type": None}]
        
        # Create rows for each target item
        for i, target in enumerate(target_items):
            # Show conversion data only in first row
            if i == 0:
                creation_date_time = conversion.creation
                user_name = conversion.user_full_name
                company = conversion.company
                branch = conversion.branch
                manufacturer = conversion.manufacturer
                department = conversion.department
                source_item = conversion.g_source_item
                source_item_qty = flt(conversion.g_source_qty, 3) if conversion.g_source_qty else ""
                inventory_type_display = target.get("inventory_type") or conversion.inventory_type
                loss_item = conversion.g_loss_item
                stock_entry_id = conversion.stock_entry_from_join
            else:
                # Blank for subsequent rows
                creation_date_time = ""
                user_name = ""
                company = ""
                branch = ""
                manufacturer = ""
                department = ""
                source_item = ""
                source_item_qty = ""
                inventory_type_display = target.get("inventory_type") or ""
                loss_item = ""
                stock_entry_id = ""
            
            result.append({
                "creation_date_time": creation_date_time,
                "gemstone_conversion_id": conversion_id,  # Show in ALL rows
                "user_name": user_name,
                "company": company,
                "branch": branch,
                "manufacturer": manufacturer,
                "department": department,
                "source_item": source_item,
                "source_item_qty": source_item_qty,
                "target_item": target.get("item_code", ""),
                "target_item_qty": flt(target.get("qty", 0), 3) if target.get("qty") else "",
                "inventory_type": inventory_type_display,
                "loss_item": loss_item,
                "stock_entry_id": stock_entry_id
            })
    
    # Replace zero values with None (blank) for better display
    for row in result:
        for field_name, field_value in list(row.items()):
            if field_value in (0, 0.0, 0.00, 0.000, '0', '0.0', '0.00', '0.000', '0.0000', '', 'None', 'null'):
                row[field_name] = None
    
    return result

def get_conditions(filters):
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND gc.company = %(company)s"
    
    if filters.get("branch"):
        conditions += " AND gc.branch = %(branch)s"
    
    if filters.get("manufacturer"):
        conditions += " AND gc.manufacturer = %(manufacturer)s"
    
    if filters.get("department"):
        conditions += " AND gc.department = %(department)s"
    
    if filters.get("from_date"):
        conditions += " AND DATE(gc.creation) >= %(from_date)s"
    
    if filters.get("to_date"):
        conditions += " AND DATE(gc.creation) <= %(to_date)s"
    
    if filters.get("inventory_type"):
        conditions += " AND (gc.inventory_type = %(inventory_type)s OR EXISTS (SELECT 1 FROM `tabSC Target Table` sct WHERE sct.parent = gc.name AND sct.inventory_type = %(inventory_type)s))"
    
    return conditions
