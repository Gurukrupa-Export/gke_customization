# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

# ------------------- Utility functions -------------------

def clean_bom_value(val):
    """Normalize BOM value: treat No, None, '', 0 as blank"""
    if val is None:
        return ""
    val = str(val).strip()
    if val.lower() in ["no", "none", "", "0"]:
        return ""
    return val

def normalize_for_compare(item_val, bom_val):
    """Compare decimals properly (17 vs 17.0 should match)"""
    try:
        if "." in str(item_val):
            return float(item_val), float(bom_val)
        else:
            if "." in str(bom_val):
                bom_val = str(int(float(bom_val)))  # remove .0 etc.
            return str(item_val), str(bom_val)
    except:
        return str(item_val), str(bom_val)

def get_image_modal_html(code, image_url):
    """Generate small image preview with click-to-enlarge modal"""
    if not image_url:
        return "-"
    modal_id = f"modal-{code}"
    thumb = (
        f'<img src="{image_url}" style="height:50px; border-radius:6px; '
        f'cursor:pointer; object-fit:contain;" '
        f'onclick="document.getElementById(\'{modal_id}\').style.display=\'flex\'">'
    )
    modal = (
        f'<div id="{modal_id}" class="custom-image-modal" '
        f'style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; '
        f'background-color:rgba(0,0,0,0.8); align-items:center; justify-content:center; '
        f'z-index:1000;" onclick="this.style.display=\'none\'">'
        f'<img src="{image_url}" style="max-width:90%; max-height:90%; border-radius:8px;" '
        f'onclick="event.stopPropagation()">'
        f'</div>'
    )
    return thumb + modal

# ------------------- Main execute -------------------

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"fieldname": "row_type", "label": "Type", "fieldtype": "Data", "width": 70, "freeze": 1},
        {"fieldname": "item_code", "label": "Item ID", "fieldtype": "Link", "options": "Item", "width": 160, "freeze": 1},
        {"fieldname": "image", "label": "Image", "fieldtype": "HTML", "width": 100},
        {"fieldname": "bom_name", "label": "BOM ID", "fieldtype": "Link", "options": "BOM", "width": 160, "freeze": 1},
        # --- attributes start ---
        # {"fieldname": "two_in_one", "label": "2 in 1", "fieldtype": "Data", "width": 100},
        # {"fieldname": "back_belt", "label": "Back Belt", "fieldtype": "Data", "width": 100},
        # {"fieldname": "back_belt_length", "label": "Back Belt Length", "fieldtype": "Data", "width": 120},
        # {"fieldname": "back_side_size", "label": "Back Side Size", "fieldtype": "Data", "width": 120},
        {"fieldname": "black_bead_line", "label": "Black Bead Line", "fieldtype": "Data", "width": 120},
        {"fieldname": "chain_length", "label": "Chain Length", "fieldtype": "Data", "width": 100},
        {"fieldname": "chain_type", "label": "Chain Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "count_of_spiral_turns", "label": "Count of Spiral Turns", "fieldtype": "Data", "width": 140},
        {"fieldname": "detachable", "label": "Detachable", "fieldtype": "Data", "width": 100},
        {"fieldname": "diamond_target", "label": "Diamond Target", "fieldtype": "Data", "width": 120},
        {"fieldname": "distance_between_kadi_to_mugappu", "label": "Distance Kadi to Mugappu", "fieldtype": "Data", "width": 160},
        {"fieldname": "enamal", "label": "Enamal", "fieldtype": "Data", "width": 100},
        {"fieldname": "feature", "label": "Feature", "fieldtype": "Data", "width": 100},
        {"fieldname": "gemstone_type1", "label": "Gemstone Type", "fieldtype": "Data", "width": 140},
        {"fieldname": "lock_type", "label": "Lock Type", "fieldtype": "Data", "width": 100},
        {"fieldname": "metal_colour", "label": "Metal Colour", "fieldtype": "Data", "width": 120},
        {"fieldname": "number_of_ant", "label": "Number of Ant", "fieldtype": "Data", "width": 120},
        {"fieldname": "product_size", "label": "Product Size", "fieldtype": "Data", "width": 120},
        {"fieldname": "rhodium", "label": "Rhodium", "fieldtype": "Data", "width": 100},
        {"fieldname": "sizer_type", "label": "Sizer Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "space_between_mugappu", "label": "Space Between Mugappu", "fieldtype": "Data", "width": 140},
        {"fieldname": "stone_changeable", "label": "Stone Changeable", "fieldtype": "Data", "width": 140},
        {"fieldname": "parent", "label": "Parent", "fieldtype": "Data", "hidden": 1},
        {"fieldname": "indent", "label": "Indent", "fieldtype": "Int", "hidden": 1},
    ]

    # --- Items ---
    conditions = [
        "is_design_code = 1",
        "item_group NOT IN ('Design DNU')",
        "disabled = 0",
        "master_bom IS NOT NULL",
        "master_bom != ''"
    ]
    args = []
    if filters.get("item_code"):
        conditions.append("item_code = %s")
        args.append(filters["item_code"])

    items = frappe.db.sql(f"""
        SELECT name, item_code, master_bom, image
        FROM tabItem
        WHERE {' AND '.join(conditions)}
        ORDER BY creation DESC
        LIMIT 500
    """, tuple(args), as_dict=True)

    if not items:
        return columns, []

    item_names = [i["name"] for i in items]

    # --- Item Variant Attributes ---
    variant_query = f"""
        SELECT parent,
            MAX(CASE WHEN attribute = '2 in 1' THEN attribute_value END) AS two_in_one,
            MAX(CASE WHEN attribute = 'Back Belt' THEN attribute_value END) AS back_belt,
            MAX(CASE WHEN attribute = 'Back Belt Length' THEN attribute_value END) AS back_belt_length,
            MAX(CASE WHEN attribute = 'Back Side Size' THEN attribute_value END) AS back_side_size,
            MAX(CASE WHEN attribute = 'Black Bead Line' THEN attribute_value END) AS black_bead_line,
            MAX(CASE WHEN attribute = 'Chain Length' THEN attribute_value END) AS chain_length,
            MAX(CASE WHEN attribute = 'Chain Type' THEN attribute_value END) AS chain_type,
            MAX(CASE WHEN attribute = 'Count of Spiral Turns' THEN attribute_value END) AS count_of_spiral_turns,
            MAX(CASE WHEN attribute = 'Detachable' THEN attribute_value END) AS detachable,
            MAX(CASE WHEN attribute = 'Diamond Target' THEN attribute_value END) AS diamond_target,
            MAX(CASE WHEN attribute = 'Distance Between Kadi To Mugappu' THEN attribute_value END) AS distance_between_kadi_to_mugappu,
            MAX(CASE WHEN attribute = 'Enamal' THEN attribute_value END) AS enamal,
            MAX(CASE WHEN attribute = 'Feature' THEN attribute_value END) AS feature,
            MAX(CASE WHEN attribute = 'Gemstone Type' THEN attribute_value END) AS gemstone_type1,
            MAX(CASE WHEN attribute = 'Lock Type' THEN attribute_value END) AS lock_type,
            MAX(CASE WHEN attribute = 'Metal Colour' THEN attribute_value END) AS metal_colour,
            MAX(CASE WHEN attribute = 'Number of Ant' THEN attribute_value END) AS number_of_ant,
            MAX(CASE WHEN attribute = 'Product Size' THEN attribute_value END) AS product_size,
            MAX(CASE WHEN attribute = 'Rhodium' THEN attribute_value END) AS rhodium,
            MAX(CASE WHEN attribute = 'Sizer Type' THEN attribute_value END) AS sizer_type,
            MAX(CASE WHEN attribute = 'Space between Mugappu' THEN attribute_value END) AS space_between_mugappu,
            MAX(CASE WHEN attribute = 'Stone Changeable' THEN attribute_value END) AS stone_changeable
        FROM `tabItem Variant Attribute`
        WHERE parent IN ({','.join(['%s'] * len(item_names))})
        GROUP BY parent
    """
    variants = frappe.db.sql(variant_query, tuple(item_names), as_dict=True)
    item_attrs_map = {v["parent"]: v for v in variants}

    # --- BOMs ---
    master_boms = [i["master_bom"] for i in items if i["master_bom"]]
    bom_query = f"""
        SELECT name, image,
            two_in_one, back_belt, back_belt_length, back_side_size, black_bead_line,
            chain_length, chain_type, count_of_spiral_turns, detachable, diamond_target,
            distance_between_kadi_to_mugappu, enamal, feature, gemstone_type1, lock_type,
            metal_colour, number_of_ant, product_size, rhodium, sizer_type,
            space_between_mugappu, stone_changeable
        FROM tabBOM
        WHERE name IN ({','.join(['%s'] * len(master_boms))})
    """
    boms = frappe.db.sql(bom_query, tuple(master_boms), as_dict=True)
    bom_map = {b["name"]: b for b in boms}

    attributes = [
        "two_in_one", "back_belt", "back_belt_length", "back_side_size", "black_bead_line",
        "chain_length", "chain_type", "count_of_spiral_turns", "detachable", "diamond_target",
        "distance_between_kadi_to_mugappu", "enamal", "feature", "gemstone_type1",
        "lock_type", "metal_colour", "number_of_ant", "product_size", "rhodium",
        "sizer_type", "space_between_mugappu", "stone_changeable"
    ]

    # --- Result building ---
    result = []
    for it in items:
        item_a = item_attrs_map.get(it["name"], {})
        bom_a = bom_map.get(it["master_bom"]) or {}
        mismatch = False
        item_row, bom_row = {}, {}

        for attr in attributes:
            item_val = str(item_a.get(attr) or "").strip()
            bom_val = clean_bom_value(bom_a.get(attr))
            if not item_val:
                continue
            item_comp, bom_comp = normalize_for_compare(item_val, bom_val)
            if str(item_comp) != str(bom_comp):
                mismatch = True
                item_row[attr] = f"<span style='color:red;font-weight:bold'>{item_val}</span>"
                bom_row[attr] = f"<span style='color:red;font-weight:bold'>{bom_val}</span>"
            else:
                item_row[attr] = item_val
                bom_row[attr] = bom_val

        if mismatch:
            item_image_html = get_image_modal_html(it["item_code"], it.get("image"))
            bom_image_html = get_image_modal_html(it["master_bom"], bom_a.get("image"))
            result.append({
                "row_type": "Item",
                "item_code": it["item_code"],
                "image": item_image_html,
                "bom_name": "",
                **item_row,
                "parent": None,
                "indent": 0
            })
            result.append({
                "row_type": "BOM",
                "item_code": "",
                "image": bom_image_html,
                "bom_name": it["master_bom"],
                **bom_row,
                "parent": it["item_code"],
                "indent": 1
            })

    return columns, result
