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
        {"fieldname": "finding_category", "label": _("Finding Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "finding_subcategory", "label": _("Finding Sub-Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "custom_finding_size", "label": _("Finding Size"), "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_type", "label": _("Metal Type"), "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_colour", "label": _("Metal Colour"), "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_purity", "label": _("Metal Purity"), "fieldtype": "Data", "width": 120},
        {"fieldname": "weight", "label": _("Weight"), "fieldtype": "Float", "width": 100},
        {"fieldname": "finding_size_thickness_x_width", "label": _("Size Thickness x Width"), "fieldtype": "Data", "width": 150}
    ]


def get_data(filters):
    query = """
    WITH pivoted AS (
        SELECT 
            i.item_code,
            i.image,
            MAX(CASE WHEN iv.attribute = 'Finding Category' THEN iv.attribute_value END) AS finding_category,
            MAX(CASE WHEN iv.attribute = 'Finding Sub-Category' THEN iv.attribute_value END) AS finding_subcategory,
            MAX(CASE WHEN iv.attribute = 'Finding Size' THEN iv.attribute_value END) AS finding_size,
            MAX(CASE WHEN iv.attribute = 'Metal Type' THEN iv.attribute_value END) AS metal_type,
            MAX(CASE WHEN iv.attribute = 'Metal Touch' THEN iv.attribute_value END) AS metal_touch,
            MAX(CASE WHEN iv.attribute = 'Metal Colour' THEN iv.attribute_value END) AS metal_colour,
            MAX(CASE WHEN iv.attribute = 'Metal Purity' THEN iv.attribute_value END) AS metal_purity
        FROM
            tabItem i
        LEFT JOIN
            `tabItem Variant Attribute` iv ON i.item_code = iv.parent
        WHERE
            i.item_group IN ('Finding - V') 
            AND i.item_group NOT IN ('Finding DNU')
            AND i.disabled = 0
        GROUP BY
            i.item_code, i.image
    ),
    weight_data AS (
        SELECT 
            custom_metal_touch,
            custom_metal_type,
            custom_metal_colour,
            custom_finding_size,
            MAX(weight) as weight,
            MAX(finding_size_thickness_x_width) as finding_size_thickness_x_width
        FROM `tabAttribute Value Finding Type Weight`
        GROUP BY custom_metal_touch, custom_metal_type, custom_metal_colour, custom_finding_size
    )
    SELECT
        p.item_code,
        p.image,
        p.finding_category,
        p.finding_subcategory,
        p.finding_size as custom_finding_size,
        p.metal_type,
        p.metal_touch,
        p.metal_colour,
        p.metal_purity,
        wd.weight,
        wd.finding_size_thickness_x_width
    FROM pivoted p
    LEFT JOIN weight_data wd
       ON wd.custom_metal_touch = p.metal_touch
       AND wd.custom_metal_type = p.metal_type
       AND wd.custom_metal_colour = p.metal_colour
       AND wd.custom_finding_size = p.finding_size
    ORDER BY p.item_code
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
