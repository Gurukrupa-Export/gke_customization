# Copyright (c) 2024, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, formatdate


def execute(filters=None):
    """
    Main execution function for Diamond Assortment Report
    """
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """
    Define report columns with Company, Branch, Manufacturer as FIRST columns
    """
    return [
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
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
            "options": "Manufacturer",
            "width": 120
        },
        {
            "label": _("Creation Date & Time"),
            "fieldname": "creation_date_time",
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "label": _("Diamond Conversion ID"),
            "fieldname": "diamond_conversion_id",
            "fieldtype": "Link",
            "options": "Diamond Conversion",
            "width": 160
        },
        {
            "label": _("User"),
            "fieldname": "user_name",
            "fieldtype": "Data",
            "width": 120
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
            "label": _("Sum of Source Qty"),
            "fieldname": "sum_of_source_qty",
            "fieldtype": "Data",  # Data type to allow HTML formatting
            "width": 140
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
            "label": _("Sum of Target Qty"),
            "fieldname": "sum_of_target_qty",
            "fieldtype": "Data",  # Data type to allow HTML formatting
            "width": 140
        },
        {
            "label": _("Stock Entry ID"),
            "fieldname": "stock_entry_id",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 120
        }
    ]


def get_data(filters):
    """
    Group source items by item_code, keep target items individual
    Show Diamond Conversion ID in ALL rows, get user full_name, make sum quantities bold
    Include Company, Branch, and Manufacturer as FIRST columns
    """
    conditions = get_conditions(filters)
    
    # Get Diamond Conversion records with Stock Entry join, User full_name, and additional fields
    conversion_query = f"""
        SELECT DISTINCT
            dc.creation,
            dc.name as conversion_id,
            dc.owner,
            u.full_name as user_full_name,
            dc.company,
            dc.branch,
            dc.manufacturer,
            dc.department,
            dc.sum_source_table,
            dc.sum_target_table,
            dc.stock_entry,
            se.name as stock_entry_from_join
        FROM `tabDiamond Conversion` dc
        LEFT JOIN `tabStock Entry` se ON dc.name = se.custom_diamond_conversion
        LEFT JOIN `tabUser` u ON dc.owner = u.name
        WHERE dc.docstatus = 1 {conditions}
        ORDER BY dc.creation DESC
    """
    
    conversions = frappe.db.sql(conversion_query, filters, as_dict=1)
    
    result = []
    
    for conversion in conversions:
        conversion_id = conversion.conversion_id
        
        # Get source items GROUPED by item_code (sum quantities for same items)
        source_query = """
            SELECT item_code, SUM(qty) as total_qty
            FROM `tabSC Source Table`
            WHERE parent = %s
            GROUP BY item_code
            ORDER BY item_code
        """
        source_items = frappe.db.sql(source_query, (conversion_id,), as_dict=1)
        
        # Get target items INDIVIDUAL (keep separate)
        target_query = """
            SELECT item_code, qty, idx
            FROM `tabSC Target Table`
            WHERE parent = %s
            ORDER BY idx
        """
        target_items = frappe.db.sql(target_query, (conversion_id,), as_dict=1)
        
        # Determine the maximum rows needed for this conversion
        max_rows = max(len(source_items), len(target_items), 1)
        
        # Create rows for each conversion
        for i in range(max_rows):
            # Source item data (grouped - blank if no more source items)
            if i < len(source_items):
                source_item = source_items[i].get("item_code", "")
                source_qty = flt(source_items[i].get("total_qty", 0), 3)
            else:
                source_item = ""
                source_qty = ""
            
            # Target item data (individual - blank if no more target items)
            if i < len(target_items):
                target_item = target_items[i].get("item_code", "")
                target_qty = flt(target_items[i].get("qty", 0), 3)
            else:
                target_item = ""
                target_qty = ""
            
            # Use Stock Entry from join or fallback to conversion field
            stock_entry_id = conversion.get("stock_entry_from_join") or conversion.get("stock_entry", "")
            
            # Format sum quantities with bold HTML if first row and not zero
            sum_source_formatted = ""
            sum_target_formatted = ""
            
            if i == 0:
                sum_source_raw = flt(conversion.sum_source_table, 3)
                sum_target_raw = flt(conversion.sum_target_table, 3)
                
                # Make sum quantities bold only if not zero
                if sum_source_raw != 0:
                    sum_source_formatted = f"<b>{sum_source_raw}</b>"
                
                if sum_target_raw != 0:
                    sum_target_formatted = f"<b>{sum_target_raw}</b>"
            
            result.append({
                "company": conversion.company if i == 0 else "",  # FIRST column
                "branch": conversion.branch if i == 0 else "",  # SECOND column
                "manufacturer": conversion.manufacturer if i == 0 else "",  # THIRD column
                "creation_date_time": conversion.creation if i == 0 else "",
                "diamond_conversion_id": conversion_id,  # Show Diamond Conversion ID in ALL rows
                "user_name": conversion.user_full_name if i == 0 else "",  # Use full_name from User doctype
                "department": conversion.department if i == 0 else "",
                "source_item": source_item,
                "source_item_qty": source_qty,
                "sum_of_source_qty": sum_source_formatted,  # Bold HTML formatted
                "target_item": target_item,
                "target_item_qty": target_qty,
                "sum_of_target_qty": sum_target_formatted,  # Bold HTML formatted
                "stock_entry_id": stock_entry_id if i == 0 else ""
            })
    
    # Step 3: Replace zero values with None (blank/null) for better display
    # But skip the sum columns since they're already formatted
    for row in result:
        # Process fields except the sum columns (which are already formatted)
        for field_name, field_value in list(row.items()):
            if field_name not in ["sum_of_source_qty", "sum_of_target_qty"]:
                # Check if the value represents zero in any form
                if field_value in (0, 0.0, 0.00, 0.000, '0', '0.0', '0.00', '0.000', '0.0000'):
                    row[field_name] = None
                
                # Also handle string representations that might be empty or None
                elif field_value in ('', 'None', 'null'):
                    row[field_name] = None
    
    return result


def get_conditions(filters):
    """
    Build WHERE conditions based on filters
    """
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND dc.company = %(company)s"
    
    if filters.get("branch"):
        conditions += " AND dc.branch = %(branch)s"
    
    if filters.get("manufacturer"):
        conditions += " AND dc.manufacturer = %(manufacturer)s"
    
    if filters.get("department"):
        conditions += " AND dc.department = %(department)s"
    
    if filters.get("from_date"):
        conditions += " AND DATE(dc.creation) >= %(from_date)s"
    
    if filters.get("to_date"):
        conditions += " AND DATE(dc.creation) <= %(to_date)s"
    
    return conditions
