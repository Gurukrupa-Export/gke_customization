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
        {"fieldname": "Gemstone_Size", "label": _("Gemstone Size"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Stone_Shape", "label": _("Stone Shape"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Gemstone_Quality", "label": _("Gemstone Quality"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Gemstone_PR", "label": _("Gemstone PR"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Gemstone_Grade", "label": _("Gemstone Grade"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Per_Pc_or_Per_Carat", "label": _("Per Pc or Per Carat"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Faceted_or_Cabochon", "label": _("Faceted or Cabochon"), "fieldtype": "Data", "width": 120},
        {"fieldname": "Gemstone_Type", "label": _("Gemstone Type"), "fieldtype": "Data", "width": 100}
    ]

def get_data(filters):
    query = """
    SELECT 
    i.item_code,
    i.image,
    MAX(CASE WHEN iv.attribute = 'Gemstone Size' THEN iv.attribute_value ELSE NULL END) AS Gemstone_Size,
    MAX(CASE WHEN iv.attribute = 'Stone Shape' THEN iv.attribute_value ELSE NULL END) AS Stone_Shape,
    MAX(CASE WHEN iv.attribute = 'Gemstone Quality' THEN iv.attribute_value ELSE NULL END) AS Gemstone_Quality,
    MAX(CASE WHEN iv.attribute = 'Gemstone PR' THEN iv.attribute_value ELSE NULL END) AS Gemstone_PR,
    MAX(CASE WHEN iv.attribute = 'Gemstone Grade' THEN iv.attribute_value ELSE NULL END) AS Gemstone_Grade,
    MAX(CASE WHEN iv.attribute = 'Per Pc or Per Carat' THEN iv.attribute_value ELSE NULL END) AS Per_Pc_or_Per_Carat,
    MAX(CASE WHEN iv.attribute = 'Cut or Cab' THEN iv.attribute_value ELSE NULL END) AS Faceted_or_Cabochon,
    MAX(CASE WHEN iv.attribute = 'Gemstone Type' THEN iv.attribute_value ELSE NULL END) AS Gemstone_Type
    FROM 
    tabItem i
RIGHT JOIN 
    `tabItem Variant Attribute` iv ON i.item_code = iv.parent
WHERE 
    i.item_group IN ('Gemstone - V') 
    and i.item_group NOT IN ('Gemstone DNU')
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

