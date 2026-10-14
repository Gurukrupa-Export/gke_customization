# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": _("Serial No"), "fieldname": "tag_no", "fieldtype": "Link", "options": "Serial No", "width": 130},
        {"label": _("Customer"), "fieldname": "party_name", "fieldtype": "Data", "width": 110},
        {"label": _("Order Type"), "fieldname": "order_type", "fieldtype": "Data", "width": 110},
        {"label": _("Item Code"), "fieldname": "style_bio", "fieldtype": "Data", "width": 130},
        {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
        {"label": _("Sub Category"), "fieldname": "sub_category", "fieldtype": "Data", "width": 140},
        {"label": _("Finish Date"), "fieldname": "finish_date", "fieldtype": "Date", "width": 110},
        {"label": _("Gross Wt"), "fieldname": "gross_wt", "fieldtype": "Float", "width": 100},
        {"label": _("Gold Wt"), "fieldname": "gold_wt", "fieldtype": "Float", "width": 100},
        
        {"label": _("Setting"), "fieldname": "setting", "fieldtype": "Data", "width": 80},
        {"label": _("Metal Touch"), "fieldname": "metal_touch", "fieldtype": "Data", "width": 110},
        {"label": _("Diamond Quality"), "fieldname": "diamond_purity", "fieldtype": "Data", "width": 120},
        {"label": _("Stone Wt"), "fieldname": "stone_wt", "fieldtype": "Float", "width": 100},
        {"label": _("Other Wt"), "fieldname": "other_wt", "fieldtype": "Float", "width": 100},
        {"label": _("Dia Wt"), "fieldname": "dia_wt", "fieldtype": "Float", "width": 100},
        {"label": _("Dia Pcs"), "fieldname": "dia_pcs", "fieldtype": "Int", "width": 90},
        {"label": _("Customer PO No"), "fieldname": "po_no", "fieldtype": "Data", "width": 150},
    ]


def get_data(filters):
    conditions = []
    query_filters = {}

    
    # if filters.get("company"):
    #     conditions.append("w.company = %(company)s")
    #     query_filters["company"] = filters.get("company")

    # if filters.get("branch"):
    #     conditions.append("w.custom_branch = %(branch)s")
    #     query_filters["branch"] = filters.get("branch")

    if filters.get("department"):
        conditions.append("w.department = %(department)s")
        query_filters["department"] = filters.get("department")

    if filters.get("from_date"):
        conditions.append("DATE(sn.creation) >= %(from_date)s")
        query_filters["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(sn.creation) <= %(to_date)s")
        query_filters["to_date"] = filters.get("to_date")

    
    if filters.get("category"):
        conditions.append("b.item_category = %(category)s")
        query_filters["category"] = filters.get("category")

    if filters.get("item_name"):
        conditions.append("b.item = %(item_name)s")
        query_filters["item_name"] = filters.get("item_name")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    data = frappe.db.sql("""
        SELECT
            sn.name AS tag_no,
            b.customer AS party_name,
            pmo.order_type AS order_type,
            b.item AS style_bio,
            DATE(sn.creation) AS finish_date,
            COALESCE(sn.custom_gross_wt, 0) AS gross_wt,
            COALESCE(b.metal_weight, 0) AS gold_wt,
            b.item_category AS category,
            b.item_subcategory AS sub_category,
            b.setting_type AS setting,
            b.metal_touch AS metal_touch,
            b.diamond_quality AS diamond_purity,
            COALESCE(bgd.stone_wt, 0) AS stone_wt,
            COALESCE(bod.other_wt, 0) AS other_wt,
            COALESCE(bdd.dia_wt, 0) AS dia_wt,
            COALESCE(b.total_diamond_pcs, 0) AS dia_pcs,
            pmo.po_no AS po_no
        FROM `tabSerial No` sn
        LEFT JOIN `tabBOM` b
            ON b.name = sn.custom_bom_no
        LEFT JOIN `tabSerial Number Creator` snc
            ON snc.name = b.custom_serial_number_creator
        LEFT JOIN `tabParent Manufacturing Order` pmo
            ON pmo.name = snc.parent_manufacturing_order
        LEFT JOIN `tabWarehouse` w
            ON w.name = sn.warehouse
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS stone_wt
            FROM `tabBOM Gemstone Detail`
            GROUP BY parent
        ) bgd ON bgd.parent = b.name
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS other_wt
            FROM `tabBOM Other Detail`
            GROUP BY parent
        ) bod ON bod.parent = b.name
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS dia_wt
            FROM `tabBOM Diamond Detail`
            GROUP BY parent
        ) bdd ON bdd.parent = b.name
        WHERE sn.custom_bom_no IS NOT NULL
        {condition_sql}
        ORDER BY sn.creation, sn.name
    """.format(condition_sql=condition_sql), query_filters, as_dict=True)

    return data