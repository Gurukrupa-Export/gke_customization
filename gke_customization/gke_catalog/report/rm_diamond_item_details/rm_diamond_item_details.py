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
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options":"Item", "width": 300},
        # {"fieldname": "name", "label": _("Item Name"), "fieldtype": "Link", "options":"Item", "width": 120},
        {"fieldname": "image", "label": _("Image"), "fieldtype": "HTML", "width": 100},
        {"fieldname": "Diamond_Sieve_Size", "label": _("Diamond Sieve Size"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Diameter", "label": _("Diameter"), "fieldtype": "Float", "width": 120},
        {"fieldname": "Diamond_Type", "label": _("Diamond Type"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Stone_Shape", "label": _("Stone Shape"), "fieldtype": "Data", "width": 120},
		{"fieldname": "Diamond_Grade", "label": _("Diamond Grade"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Diamond_Sieve_Size_Range", "label": _("Diamond_Sieve_Size_Range"), "fieldtype": "Data", "width": 120}
    ]

def get_data(filters):
    query = """
   SELECT 
    i.item_code AS item_code,
    i.image,
    MAX(CASE WHEN iv.attribute = 'Diamond Sieve Size' THEN iv.attribute_value ELSE NULL END) AS "Diamond_Sieve_Size",
     MAX(av.diameter) AS "Diameter",
    MAX(CASE WHEN iv.attribute = 'Diamond Type' THEN iv.attribute_value ELSE NULL END) AS "Diamond_Type",
    MAX(CASE WHEN iv.attribute = 'Stone Shape' THEN iv.attribute_value ELSE NULL END) AS "Stone_Shape",
    MAX(CASE WHEN iv.attribute = 'Diamond Grade' THEN iv.attribute_value ELSE NULL END) AS "Diamond_Grade",
    MAX(CASE WHEN iv.attribute = 'Diamond Sieve Size Range' THEN iv.attribute_value ELSE NULL END) AS "Diamond_Sieve_Size_Range"
FROM 
    tabItem i
RIGHT JOIN 
    `tabItem Variant Attribute` iv ON i.item_code = iv.parent
LEFT JOIN 
    `tabAttribute Value` av ON iv.attribute_value = av.attribute_value
WHERE 
    i.item_group IN ('Diamond - V') 
    AND i.item_group NOT IN ('Diamond DNU')
    and i.disabled = 0
GROUP BY 
    i.item_code;"""
    rows = frappe.db.sql(query, as_dict=1)
    data = []
    for row in rows:
        image_url = row.get("image")
        modal_id = "modal-{}".format(row["item_code"])
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

