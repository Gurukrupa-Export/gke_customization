# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe


def execute(filters=None):
	columns, data = [], []
	return columns, data
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
        {"fieldname": "Other_Materials", "label": _("Other Materials"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "finding_subcategory", "label": _("Finding Sub-Category"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "custom_finding_size", "label": _("Finding Size"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "metal_type", "label": _("Metal Type"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "metal_colour", "label": _("Metal Colour"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "metal_purity", "label": _("Metal Purity"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "weight", "label": _("Weight"), "fieldtype": "Float", "width": 100},
        # {"fieldname": "finding_size_thickness_x_width", "label": _("Size Thickness x Width"), "fieldtype": "Data", "width": 150}
    ]

def get_data(filters):
    query = """
    SELECT 
        i.item_code,
        i.image,
        MAX(CASE WHEN iv.attribute = 'Other Materials' THEN iv.attribute_value ELSE NULL END) AS Other_Materials
    FROM 
        tabItem i
    left JOIN 
        `tabItem Variant Attribute` iv ON i.item_code = iv.parent
    WHERE 
        i.item_group IN ('Other Material - V')
        and i.disabled = 0
    GROUP BY 
        i.item_code;
    """
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

