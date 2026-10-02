# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    # Validate mandatory filters
    validate_filters(filters)

    # Get columns based on department type
    columns = get_columns(filters)

    # Get data based on department
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    """Validate mandatory filters"""
    mandatory = ['company', 'department', 'manufacturer']

    for field in mandatory:
        if not filters.get(field):
            frappe.throw(_("{0} is mandatory").format(field.replace('_', ' ').title()))

    # Branch is mandatory only for GEPL
    if 'GEPL' in filters.get('department', '') and not filters.get('branch'):
        frappe.throw(_("Branch is mandatory for GEPL"))


def get_columns(filters):
    """Return columns based on department type"""
    is_gemstone = 'Gemstone' in filters.get('department', '')

    columns = [
        {
            "fieldname": "conversion_id",
            "label": _("Conversion ID"),
            "fieldtype": "Link",
            "options": "Gemstone Conversion" if is_gemstone else "Diamond Conversion",
            "width": 150
        },
        {
            "fieldname": "stock_entry",
            "label": _("Stock Entry"),
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 150
        },
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "source_item",
            "label": _("Source Item"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 200
        },
        {
            "fieldname": "source_qty",
            "label": _("Source Qty"),
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "fieldname": "target_item",
            "label": _("Target Item"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 200
        },
        {
            "fieldname": "sieve_size",
            "label": _("Sieve Size"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "target_qty",
            "label": _("Target Qty"),
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "fieldname": "total_target_qty",
            "label": _("Total Target Qty"),
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        }
    ]

    # Add Loss Type column only for Gemstone (before User Name)
    if is_gemstone:
        columns.append({
            "fieldname": "loss_type",
            "label": _("Loss Type"),
            "fieldtype": "Data",
            "width": 100
        })

    # User Name at the end
    columns.append({
        "fieldname": "user_full_name",
        "label": _("User Name"),
        "fieldtype": "Data",
        "width": 150
    })

    return columns


def get_data(filters):
    """Get data based on department type"""
    department = filters.get('department', '')

    if 'Diamond' in department:
        return get_diamond_conversion_data(filters)
    elif 'Gemstone' in department:
        return get_gemstone_conversion_data(filters)
    else:
        return []


def get_sieve_size(item_code):
    """Get Diamond Sieve Size from Item Variant Attributes"""
    if not item_code:
        return ""

    sieve_data = frappe.db.sql("""
        SELECT iva.attribute_value
        FROM `tabItem Variant Attribute` iva
        WHERE iva.parent = %s
          AND iva.attribute = 'Diamond Sieve Size'
        LIMIT 1
    """, (item_code,), as_dict=1)

    return sieve_data[0].attribute_value if sieve_data else ""


def get_diamond_conversion_data(filters):
    """Get Diamond Conversion data with child table details"""

    conditions = get_diamond_conditions(filters)

    # Get main conversion records first
    conversion_query = """
        SELECT DISTINCT
            dc.name as conversion_id,
            se.name as stock_entry,
            dc.date,
            dc.owner,
            u.full_name as user_full_name,
            dc.source_warehouse
        FROM `tabDiamond Conversion` dc
        LEFT JOIN `tabStock Entry` se ON dc.name = se.custom_diamond_conversion
        LEFT JOIN `tabUser` u ON dc.owner = u.name
        WHERE dc.docstatus = 1
            {conditions}
        ORDER BY dc.date DESC, dc.name
    """.format(conditions=conditions)

    conversions = frappe.db.sql(conversion_query, filters, as_dict=1)

    result = []

    for conversion in conversions:
        conversion_id = conversion.conversion_id

        # Get source items
        source_query = """
            SELECT item_code, qty, idx
            FROM `tabSC Source Table`
            WHERE parent = %s
            ORDER BY idx
        """
        source_items = frappe.db.sql(source_query, (conversion_id,), as_dict=1)

        # Get target items
        target_query = """
            SELECT item_code, qty, idx
            FROM `tabSC Target Table`
            WHERE parent = %s
            ORDER BY idx
        """
        target_items = frappe.db.sql(target_query, (conversion_id,), as_dict=1)

        # Calculate total target qty
        total_target = sum(flt(t.get("qty", 0)) for t in target_items)

        # Create rows - one row per target item
        if not target_items:
            target_items = [{"item_code": None, "qty": 0}]

        for i, target in enumerate(target_items):
            source_qty_value = flt(source_items[0].get("qty", 0), 3) if source_items else 0
            sieve_size = get_sieve_size(target.get("item_code"))

            # Show conversion data only in first row
            if i == 0:
                stock_entry_display = conversion.stock_entry
                date_display = conversion.date
                source_item_display = source_items[0].get("item_code") if source_items else ""
                source_qty_display = source_qty_value
                total_target_display = flt(total_target, 3)
                user_name_display = conversion.user_full_name
            else:
                # Blank for subsequent rows
                stock_entry_display = ""
                date_display = ""
                source_item_display = ""
                source_qty_display = None
                total_target_display = None
                user_name_display = ""

            result.append({
                "conversion_id": conversion_id,
                "stock_entry": stock_entry_display,
                "date": date_display,
                "source_item": source_item_display,
                "source_qty": source_qty_display,
                "target_item": target.get("item_code", ""),
                "sieve_size": sieve_size,
                "target_qty": flt(target.get("qty", 0), 3) if target.get("qty") else None,
                "total_target_qty": total_target_display,
                "user_full_name": user_name_display
            })

    return result


def get_gemstone_conversion_data(filters):
    """Get Gemstone Conversion data with child table details"""

    conditions = get_gemstone_conditions(filters)

    # Get main conversion records first
    conversion_query = """
        SELECT DISTINCT
            gc.name as conversion_id,
            se.name as stock_entry,
            gc.date,
            gc.owner,
            u.full_name as user_full_name,
            gc.g_source_item,
            gc.g_source_qty,
            gc.loss_type
        FROM `tabGemstone Conversion` gc
        LEFT JOIN `tabStock Entry` se ON gc.name = se.custom_gemstone_conversion
        LEFT JOIN `tabUser` u ON gc.owner = u.name
        WHERE gc.docstatus = 1
            {conditions}
        ORDER BY gc.date DESC, gc.name
    """.format(conditions=conditions)

    conversions = frappe.db.sql(conversion_query, filters, as_dict=1)

    result = []

    for conversion in conversions:
        conversion_id = conversion.conversion_id

        # Get target items from child table
        target_query = """
            SELECT item_code, qty, idx
            FROM `tabSC Target Table`
            WHERE parent = %s
            ORDER BY idx
        """
        target_items = frappe.db.sql(target_query, (conversion_id,), as_dict=1)

        # Calculate total target qty
        total_target = sum(flt(t.get("qty", 0)) for t in target_items)

        # If no target items, create one blank row
        if not target_items:
            target_items = [{"item_code": None, "qty": 0}]

        source_qty_value = flt(conversion.g_source_qty, 3) if conversion.g_source_qty else 0

        # Create rows - one row per target item
        for i, target in enumerate(target_items):
            sieve_size = get_sieve_size(target.get("item_code"))

            # Show conversion data only in first row
            if i == 0:
                stock_entry_display = conversion.stock_entry
                date_display = conversion.date
                source_item_display = conversion.g_source_item
                source_qty_display = source_qty_value
                total_target_display = flt(total_target, 3)
                loss_type_display = conversion.loss_type
                user_name_display = conversion.user_full_name
            else:
                # Blank for subsequent rows
                stock_entry_display = ""
                date_display = ""
                source_item_display = ""
                source_qty_display = None
                total_target_display = None
                loss_type_display = ""
                user_name_display = ""

            result.append({
                "conversion_id": conversion_id,
                "stock_entry": stock_entry_display,
                "date": date_display,
                "source_item": source_item_display,
                "source_qty": source_qty_display,
                "target_item": target.get("item_code", ""),
                "sieve_size": sieve_size,
                "target_qty": flt(target.get("qty", 0), 3) if target.get("qty") else None,
                "total_target_qty": total_target_display,
                "loss_type": loss_type_display,
                "user_full_name": user_name_display
            })

    return result


def get_diamond_conditions(filters):
    """Build WHERE conditions for Diamond Conversion - with table aliases"""
    conditions = []

    if filters.get('company'):
        conditions.append("AND dc.company = %(company)s")

    if filters.get('branch'):
        conditions.append("AND (dc.branch = %(branch)s OR dc.branch IS NULL)")

    if filters.get('department'):
        conditions.append("AND dc.department = %(department)s")

    if filters.get('manufacturer'):
        conditions.append("AND dc.manufacturer = %(manufacturer)s")

    if filters.get('from_date'):
        conditions.append("AND dc.date >= %(from_date)s")

    if filters.get('to_date'):
        conditions.append("AND dc.date <= %(to_date)s")

    return ' '.join(conditions)


def get_gemstone_conditions(filters):
    """Build WHERE conditions for Gemstone Conversion"""
    conditions = []

    if filters.get('company'):
        conditions.append("AND gc.company = %(company)s")

    if filters.get('branch'):
        conditions.append("AND (gc.branch = %(branch)s OR gc.branch IS NULL)")

    if filters.get('department'):
        conditions.append("AND gc.department = %(department)s")

    if filters.get('manufacturer'):
        conditions.append("AND gc.manufacturer = %(manufacturer)s")

    if filters.get('from_date'):
        conditions.append("AND gc.date >= %(from_date)s")

    if filters.get('to_date'):
        conditions.append("AND gc.date <= %(to_date)s")

    return ' '.join(conditions)