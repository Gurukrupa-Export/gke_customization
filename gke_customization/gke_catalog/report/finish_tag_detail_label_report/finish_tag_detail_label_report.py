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
        {"label": _("Finish Date"), "fieldname": "finish_date", "fieldtype": "Datetime", "width": 140},
        {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
        {"label": _("Sub Category"), "fieldname": "sub_category", "fieldtype": "Data", "width": 140},
        {"label": _("Metal Color"), "fieldname": "metal_color", "fieldtype": "Data", "width": 110},
        {"label": _("StyleBio"), "fieldname": "style_bio", "fieldtype": "Data", "width": 130},
        {"label": _("TagNo"), "fieldname": "tag_no", "fieldtype": "Link", "options": "Serial No", "width": 130},
        {"label": _("DiaWt"), "fieldname": "dia_wt", "fieldtype": "Data", "width": 120},
        {"label": _("ChainWt"), "fieldname": "chain_wt", "fieldtype": "Data", "width": 120},
        {"label": _("GrossWt"), "fieldname": "gross_wt", "fieldtype": "Data", "width": 120},
        {"label": _("StoneWt"), "fieldname": "stone_wt", "fieldtype": "Data", "width": 120},
        {"label": _("Remark"), "fieldname": "remark", "fieldtype": "Data", "width": 100},
        {"label": _("OtherWt"), "fieldname": "other_wt", "fieldtype": "Data", "width": 120},
        {"label": _("Main PO No"), "fieldname": "main_po_no", "fieldtype": "Data", "width": 150},
        {"label": _("PO No"), "fieldname": "po_no", "fieldtype": "Data", "width": 150},
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 400},
    ]


def get_data(filters):
    conditions = []
    query_filters = {}

    if filters.get("company"):
        conditions.append("w.company = %(company)s")
        query_filters["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("w.custom_branch = %(branch)s")
        query_filters["branch"] = filters.get("branch")

    if filters.get("department"):
        conditions.append("w.department = %(department)s")
        query_filters["department"] = filters.get("department")

    if filters.get("from_date"):
        conditions.append("""
            DATE(
                CASE
                    WHEN al.reference_name IS NOT NULL THEN snc.modified
                    ELSE sn.creation
                END
            ) >= %(from_date)s
        """)
        query_filters["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("""
            DATE(
                CASE
                    WHEN al.reference_name IS NOT NULL THEN snc.modified
                    ELSE sn.creation
                END
            ) <= %(to_date)s
        """)
        query_filters["to_date"] = filters.get("to_date")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    data = frappe.db.sql("""
        SELECT
            CASE
                WHEN al.reference_name IS NOT NULL THEN snc.modified
                ELSE sn.creation
            END AS finish_date,
            b.item_category AS category,
            b.item_subcategory AS sub_category,
            b.metal_colour AS metal_color,
            b.item AS style_bio,
            sn.name AS tag_no,
            COALESCE(bdd.dia_wt, 0) AS dia_wt_raw,
            COALESCE(bfd.chain_wt, 0) AS chain_wt_raw,
            COALESCE(b.gross_weight, 0) AS gross_wt_raw,
            COALESCE(bgd.stone_wt, 0) AS stone_wt_raw,
            '' AS remark,
            COALESCE(bod.other_wt, 0) AS other_wt_raw,
            pmo.po_no AS main_po_no,
            pmo.child_po AS po_no,
            sn.item_code AS item_code
        FROM `tabSerial No` sn
        LEFT JOIN `tabBOM` b
            ON b.name = sn.custom_bom_no
        LEFT JOIN `tabSerial Number Creator` snc
            ON snc.name = b.custom_serial_number_creator
        LEFT JOIN (
            SELECT
                reference_name,
                MAX(creation) AS log_time
            FROM `tabActivity Log`
            WHERE reference_doctype = 'Serial Number Creator'
              AND operation = 'Submit'
            GROUP BY reference_name
        ) al
            ON al.reference_name = snc.name
        LEFT JOIN `tabParent Manufacturing Order` pmo
            ON pmo.name = snc.parent_manufacturing_order
        LEFT JOIN `tabWarehouse` w
            ON w.name = sn.warehouse
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS dia_wt
            FROM `tabBOM Diamond Detail`
            GROUP BY parent
        ) bdd
            ON bdd.parent = b.name
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS chain_wt
            FROM `tabBOM Finding Detail`
            GROUP BY parent
        ) bfd
            ON bfd.parent = b.name
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS stone_wt
            FROM `tabBOM Gemstone Detail`
            GROUP BY parent
        ) bgd
            ON bgd.parent = b.name
        LEFT JOIN (
            SELECT parent, SUM(quantity) AS other_wt
            FROM `tabBOM Other Detail`
            GROUP BY parent
        ) bod
            ON bod.parent = b.name
        WHERE sn.custom_bom_no IS NOT NULL
        {condition_sql}
        ORDER BY finish_date, sn.name
    """.format(condition_sql=condition_sql), query_filters, as_dict=True)

    item_codes = list({d.item_code for d in data if d.get("item_code")})
    descriptions_map = get_item_variant_descriptions(item_codes)

    for row in data:
        row["dia_wt"] = format_qty("Dia Wt", row.pop("dia_wt_raw", 0))
        row["chain_wt"] = format_qty("Chain Wt", row.pop("chain_wt_raw", 0))
        row["gross_wt"] = format_qty("Gross Wt", row.pop("gross_wt_raw", 0))
        row["stone_wt"] = format_qty("Stone Wt", row.pop("stone_wt_raw", 0))
        row["other_wt"] = format_qty("Other Wt", row.pop("other_wt_raw", 0))
        row["description"] = descriptions_map.get(row.get("item_code"), "")
        row.pop("item_code", None)

    return data


def get_item_variant_descriptions(item_codes):
    if not item_codes:
        return {}

    rows = frappe.db.sql("""
        SELECT
            parent,
            attribute,
            attribute_value
        FROM `tabItem Variant Attribute`
        WHERE parent IN %(item_codes)s
        ORDER BY idx
    """, {"item_codes": tuple(item_codes)}, as_dict=True)

    descriptions = {}

    for row in rows:
        parent = row.parent
        attribute = (row.attribute or "").strip()
        value = str(row.attribute_value or "").strip()

        if not value:
            continue

        if value.lower() in ("no", "none", "null", ""):
            continue

        text = f"{attribute}: {value}" if attribute else value

        if parent not in descriptions:
            descriptions[parent] = []

        descriptions[parent].append(text)

    return {k: " || ".join(v) for k, v in descriptions.items()}


def format_qty(label, value):
    value = flt(value)
    return f"{label}: {value:.3f}"


def flt(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0