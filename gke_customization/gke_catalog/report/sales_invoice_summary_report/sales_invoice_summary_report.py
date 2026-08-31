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
        {
            "label": _("Setting"), 
            "fieldname": "setting", 
            "fieldtype": "Data", 
            "width": 120
        },
        {
            "label": _("Material"), 
            "fieldname": "material", 
            "fieldtype": "Data", 
            "width": 100
        },
        {
            "label": _("Shape"), 
            "fieldname": "shape", 
            "fieldtype": "Data", 
            "width": 150
        },
        {
            "label": _("Purity"), 
            "fieldname": "purity", 
            "fieldtype": "Data", 
            "width": 120
        },
        {
            "label": _("Weight"), 
            "fieldname": "weight", 
            "fieldtype": "Float", 
            "width": 120,
            "precision": 3
        }
    ]

def get_data(filters):
    conditions = ["si.docstatus = 1"]
    
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
    
    if filters.get("invoice_no"):
        conditions.append("si.name = %(invoice_no)s")
    
    if filters.get("serial_no"):
        conditions.append("COALESCE(soi.serial_no, sii.batch_no) = %(serial_no)s")
    
    if filters.get("branch"):
        conditions.append("si.branch = %(branch)s")
    
    if filters.get("customer"):
        conditions.append("si.customer = %(customer)s")
    
    if filters.get("company"):
        conditions.append("si.company = %(company)s")
    
    # NEW FILTERS: Raw Material and Setting Type
    if filters.get("raw_material"):
        conditions.append("bom.setting_type = %(raw_material)s")
    
    if filters.get("setting_type"):
        conditions.append("bom.setting_type = %(setting_type)s")
    
    conditions_str = " AND " + " AND ".join(conditions) if conditions else ""
    
    query = f"""
    WITH rm AS (
        -- Metal
        SELECT
            si.name as invoice_no,
            COALESCE(soi.serial_no, sii.batch_no) as tag_no,
            bom.setting_type,
            'Metal' as material,
            bmd.metal_colour as shape,
            bmd.metal_purity as purity,
            bmd.quantity as weight
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
        LEFT JOIN `tabBOM` bom ON soi.bom = bom.name
        LEFT JOIN `tabBOM Metal Detail` bmd ON bmd.parent = bom.name
        WHERE 1=1 {conditions_str}

        UNION ALL

        -- Finding
        SELECT
            si.name as invoice_no,
            COALESCE(soi.serial_no, sii.batch_no) as tag_no,
            bom.setting_type,
            'Finding' as material,
            bfd.finding_type as shape,
            bfd.metal_purity as purity,
            bfd.quantity as weight
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
        LEFT JOIN `tabBOM` bom ON soi.bom = bom.name
        LEFT JOIN `tabBOM Finding Detail` bfd ON bfd.parent = bom.name
        WHERE 1=1 {conditions_str}

        UNION ALL

        -- Diamond
        SELECT
            si.name as invoice_no,
            COALESCE(soi.serial_no, sii.batch_no) as tag_no,
            bom.setting_type,
            'Diamond' as material,
            bdd.stone_shape as shape,
            bdd.diamond_grade as purity,
            bdd.quantity as weight
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
        LEFT JOIN `tabBOM` bom ON soi.bom = bom.name
        LEFT JOIN `tabBOM Diamond Detail` bdd ON bdd.parent = bom.name
        WHERE 1=1 {conditions_str}

        UNION ALL

        -- Gemstone
        SELECT
            si.name as invoice_no,
            COALESCE(soi.serial_no, sii.batch_no) as tag_no,
            bom.setting_type,
            'Gemstone' as material,
            bgd.stone_shape as shape,
            bgd.gemstone_grade as purity,
            bgd.quantity as weight
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
        LEFT JOIN `tabBOM` bom ON soi.bom = bom.name
        LEFT JOIN `tabBOM Gemstone Detail` bgd ON bgd.parent = bom.name
        WHERE 1=1 {conditions_str}
    )
    SELECT
        setting_type as setting,
        material,
        shape,
        purity,
        ROUND(SUM(weight), 3) as weight
    FROM rm
    WHERE weight IS NOT NULL
    GROUP BY setting_type, material, shape, purity
    ORDER BY material, setting, shape, purity
    """
    
    data = frappe.db.sql(query, filters, as_dict=1)
    return data
