# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item Group", "fieldname": "item_group","fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": "Item Name", "fieldname": "name", "fieldtype": "Link","options": "Item", "width": 200},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Image", "fieldname": "image", "fieldtype": "Image", "options": "image", "width": 100},
    #   {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 150},
        {"label": "Is Variant", "fieldname": "has_variants", "fieldtype": "Check", "width": 100},
        {"label": "Reason for Design Code", "fieldname": "custom_reason_for_design_code_", "fieldtype": "Data", "width": 200},
        {"label": "Item Attributes", "fieldname": "item_attributes", "fieldtype": "Data", "width": 650},
    ]

def get_data(filters):
    
    conditions = get_conditions(filters)
    items =  frappe.db.get_all(
        "Item",
        fields=["name", "item_group", "item_code", "has_variants", "description", "custom_reason_for_design_code_", "image","sketch_image"],
        filters=conditions,
        # limit=50
    )

    data = []

    for row in items:
        
        row["item_attributes"] = get_item_attributes(row["name"])

        # image_url = row.get("image")
        image_url = row.get("sketch_image") or row.get("image")
        modal_id = "modal-{}".format(row["name"])

        if image_url:
            thumbnail_html = (
                '<img src="{0}" style="height:50px; border-radius:6px; cursor:pointer; object-fit:contain;" '
                'onclick="document.getElementById(\'{1}\').style.display=\'flex\'">'.format(image_url, modal_id)
            )

            modal_html = (
                '<div id="{0}" class="custom-image-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; '
                'background-color:rgba(0,0,0,0.8); align-items:center; justify-content:center; z-index:1000;" '
                'onclick="this.style.display=\'none\'">'
                '<img src="{1}" style="max-width:90%; max-height:90%; border-radius:8px;" '
                'onclick="event.stopPropagation()">'
                '</div>'.format(modal_id, image_url)
            )

            row["image"] = thumbnail_html + modal_html
        else:
            row["image"] = "-"

        data.append(row)

    return data

def get_conditions(filters):
    conditions = {}
    if filters.get("item_group"):
        conditions["item_group"] = ["in", filters["item_group"]]
    if filters.get("item"):
        conditions["name"] = ["in", filters["item"]]
    if filters.get("sketch_order"):
        conditions["custom_sketch_order_id"] = ["in", filters["sketch_order"]]
    return conditions

def get_item_attributes(item_code):
    attributes = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"],
        order_by="creation asc"
    )
    return ",  ".join(f"•  {attr.attribute}: {attr.attribute_value}" for attr in attributes) if attributes else ""
