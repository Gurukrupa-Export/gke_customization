# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Variant", "fieldname": "variant", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Old Style Bio", "fieldname": "old_stylebio", "fieldtype": "Data", "width": 130},
        {"label": "Old Tag No", "fieldname": "old_tag_no", "fieldtype": "Data", "width": 120},
        {"label": "Diamond Target", "fieldname": "diamond_target", "fieldtype": "Data", "width": 120},
        {"label": "Metal Colour", "fieldname": "metal_colour", "fieldtype": "Data", "width": 120},
        {"label": "Product Size", "fieldname": "product_size", "fieldtype": "Data", "width": 120},
        {"label": "Enamal", "fieldname": "enamal", "fieldtype": "Data", "width": 100},
        {"label": "Rhodium", "fieldname": "rhodium", "fieldtype": "Data", "width": 100},
        {"label": "Lock Type", "fieldname": "lock_type", "fieldtype": "Data", "width": 120},
        {"label": "Cap/Ganthan", "fieldname": "cap_ganthan", "fieldtype": "Data", "width": 120},
        {"label": "Gemstone Type", "fieldname": "gemstone_type", "fieldtype": "Data", "width": 130},
        {"label": "Sizer Type", "fieldname": "sizer_type", "fieldtype": "Data", "width": 120},
        {"label": "Chain Type", "fieldname": "chain_type", "fieldtype": "Data", "width": 120},
        {"label": "Stone Changeable", "fieldname": "stone_changeable", "fieldtype": "Data", "width": 140},
        {"label": "Detachable", "fieldname": "detachable", "fieldtype": "Data", "width": 110},
        {"label": "Chain Length", "fieldname": "chain_length", "fieldtype": "Data", "width": 120},
        {"label": "Charm", "fieldname": "charm", "fieldtype": "Data", "width": 100},
        {"label": "Two in One", "fieldname": "two_in_one", "fieldtype": "Data", "width": 110},
        {"label": "Feature", "fieldname": "feature", "fieldtype": "Data", "width": 110},
        {"label": "Back Belt", "fieldname": "back_belt", "fieldtype": "Data", "width": 110},
        {"label": "Back Belt Length", "fieldname": "back_belt_length", "fieldtype": "Data", "width": 150},
        {"label": "Back Side Size", "fieldname": "back_side_size", "fieldtype": "Data", "width": 130},
        {"label": "Distance Between Kadi To Mugappu", "fieldname": "distance_kadi_mugappu", "fieldtype": "Data", "width": 220},
        {"label": "Space between Mugappu", "fieldname": "space_between_mugappu", "fieldtype": "Data", "width": 180},
        {"label": "Number of Ant", "fieldname": "number_of_ant", "fieldtype": "Data", "width": 130},
        {"label": "Count of Spiral Turns", "fieldname": "spiral_turns", "fieldtype": "Data", "width": 160},
        {"label": "Chain", "fieldname": "chain", "fieldtype": "Data", "width": 100},
        {"label": "Black Bead Line", "fieldname": "black_bead_line", "fieldtype": "Data", "width": 140},
        {"label": "Chain Thickness", "fieldname": "chain_thickness", "fieldtype": "Data", "width": 140},
        {"label": "Back Chain", "fieldname": "back_chain", "fieldtype": "Data", "width": 120},
        {"label": "Black Bead", "fieldname": "black_bead", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            i.name as variant,
            i.stylebio as old_stylebio,
            i.old_tag_no as old_tag_no,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Diamond Target' THEN iva.attribute_value END), 'No') as diamond_target,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Metal Colour' THEN iva.attribute_value END), 'No') as metal_colour,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Product Size' THEN iva.attribute_value END), 'No') as product_size,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Enamal' THEN iva.attribute_value END), 'No') as enamal,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Rhodium' THEN iva.attribute_value END), 'No') as rhodium,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Lock Type' THEN iva.attribute_value END), 'No') as lock_type,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Cap/Ganthan' THEN iva.attribute_value END), 'No') as cap_ganthan,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Gemstone Type' THEN iva.attribute_value END), 'No') as gemstone_type,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Sizer Type' THEN iva.attribute_value END), 'No') as sizer_type,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Chain Type' THEN iva.attribute_value END), 'No') as chain_type,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Stone Changeable' THEN iva.attribute_value END), 'No') as stone_changeable,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Detachable' THEN iva.attribute_value END), 'No') as detachable,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Chain Length' THEN iva.attribute_value END), 'No') as chain_length,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Charm' THEN iva.attribute_value END), 'No') as charm,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Two in One' THEN iva.attribute_value END), 'No') as two_in_one,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Feature' THEN iva.attribute_value END), 'No') as feature,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Back Belt' THEN iva.attribute_value END), 'No') as back_belt,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Back Belt Length' THEN iva.attribute_value END), 'No') as back_belt_length,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Back Side Size' THEN iva.attribute_value END), 'No') as back_side_size,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Distance Between Kadi To Mugappu' THEN iva.attribute_value END), 'No') as distance_kadi_mugappu,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Space between Mugappu' THEN iva.attribute_value END), 'No') as space_between_mugappu,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Number of Ant' THEN iva.attribute_value END), 'No') as number_of_ant,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Count of Spiral Turns' THEN iva.attribute_value END), 'No') as spiral_turns,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Chain' THEN iva.attribute_value END), 'No') as chain,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Black Bead Line' THEN iva.attribute_value END), 'No') as black_bead_line,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Chain Thickness' THEN iva.attribute_value END), 'No') as chain_thickness,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Back Chain' THEN iva.attribute_value END), 'No') as back_chain,
            COALESCE(MAX(CASE WHEN iva.attribute = 'Black Bead' THEN iva.attribute_value END), 'No') as black_bead
        FROM `tabItem` i
        LEFT JOIN `tabItem Variant Attribute` iva ON i.name = iva.parent
        WHERE i.variant_of IS NOT NULL 
        AND i.disabled = 0
        {conditions}
        GROUP BY i.name
        ORDER BY i.name
    """
    return frappe.db.sql(query, filters, as_dict=True)

def get_conditions(filters):
    conditions = []
    variant_items = []
    template_items = []

    if filters.get("item_name"):
        for item_name in filters["item_name"]:
            item_doc = frappe.get_doc("Item", item_name)
            if item_doc.has_variants:
                template_items.append(item_name)
            else:
                variant_items.append(item_name)

    if template_items:
        conditions.append("AND i.variant_of IN %(template_items)s")
        filters["template_items"] = template_items
    if variant_items:
        conditions.append("AND i.name IN %(variant_items)s")
        filters["variant_items"] = variant_items

    if filters.get("item_group"):
        conditions.append("AND i.item_group = %(item_group)s")

    if filters.get("item_code"):
        conditions.append("AND i.name = %(item_code)s")

    if filters.get("old_stylebio"):
        conditions.append("AND i.stylebio = %(old_stylebio)s")

    if filters.get("old_tag_no"):
        conditions.append("AND i.old_tag_no = %(old_tag_no)s")

    return " ".join(conditions) if conditions else ""
