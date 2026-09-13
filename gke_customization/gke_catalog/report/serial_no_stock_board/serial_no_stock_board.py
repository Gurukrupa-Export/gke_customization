# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

STATUS_CASE_SQL = """
    CASE
        WHEN sn.warehouse LIKE '%%Product Allocation FG%%' AND sn.status = 'Active' THEN 'Stock'
        WHEN sn.status = 'Delivered' AND EXISTS (
            SELECT 1
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            WHERE si.docstatus = 1
              AND (
                    sii.serial_no = sn.name
                    OR FIND_IN_SET(
                        sn.name,
                        REPLACE(REPLACE(sii.serial_no, '\\n', ','), ' ', '')
                    ) > 0
                  )
        ) THEN 'Sale'
        WHEN sn.status = 'Delivered' THEN 'Transfer'
        WHEN sn.warehouse LIKE '%%Product Vault FG%%' AND sn.status = 'Active' THEN 'Locker'
        WHEN sn.warehouse LIKE '%%Product Certification %%' AND sn.status = 'Active' THEN 'Issue to Lab'
        WHEN sn.status = 'Reserved' THEN 'Approve'
        WHEN sn.warehouse LIKE '%%Marketing Person%%' AND sn.status = 'Active' THEN 'Salesman'
        WHEN sn.status = 'Active' AND (
            EXISTS (SELECT 1 FROM `tabRepair Order Form` WHERE scan_serial_no = sn.name)
            OR EXISTS (SELECT 1 FROM `tabRepair Order` WHERE scan_serial_no = sn.name)
        ) THEN 'Repair'
        ELSE 'Stock'
    END
"""

STATUS_INDICATOR = {
    "Stock": "Green",
    "Approve": "Blue",
    "Transfer": "Purple",
    "Salesman": "Orange",
    "Locker": "Yellow",
    "Repair": "Red",
    "Issue to Lab": "Cyan",
    "Sale": "Pink",
}


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    report_summary = get_report_summary(data)

    return columns, data, None, None, report_summary


def get_columns():
    return [
        {"fieldname": "tag_no", "label": _("Serial No"), "fieldtype": "Link", "options": "Serial No", "width": 130},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Data", "width": 200},
        {"fieldname": "detail", "label": _("Detail"), "fieldtype": "Data", "width": 220},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
        {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 110},
        {"fieldname": "sub_category", "label": _("Sub Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "style_bio", "label": _("Item_Code"), "fieldtype": "Data", "width": 130},
        {"fieldname": "touch", "label": _("Touch"), "fieldtype": "Data", "width": 90},
        {"fieldname": "diamond_quality", "label": _("Diamond Quality"), "fieldtype": "Data", "width": 100},
        {"fieldname": "diamond_grade", "label": _("Diamond Grade"), "fieldtype": "Data", "width": 100},

        {"fieldname": "setting_name", "label": _("Setting Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "order_no", "label": _("Order No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "po_no", "label": _("P.O. No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "gross_wt", "label": _("Gross Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "gold_wt", "label": _("Gold Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        
        {"fieldname": "dia_wt", "label": _("Dia Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "stone_wt", "label": _("Gemstone Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "chain_wt", "label": _("Chain Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "finding_wt", "label": _("Finding Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "other_wt", "label": _("Other Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        
    ]


def get_conditions(filters):
    conditions = []
    query_filters = {}

    if filters.get("company"):
        conditions.append("sn.company = %(company)s")
        query_filters["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("pmo.branch = %(branch)s")
        query_filters["branch"] = filters.get("branch")

    if filters.get("from_date"):
        conditions.append("DATE(sn.creation) >= %(from_date)s")
        query_filters["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(sn.creation) <= %(to_date)s")
        query_filters["to_date"] = filters.get("to_date")

    if filters.get("category"):
        conditions.append("COALESCE(bom.item_category, i.item_category) = %(category)s")
        query_filters["category"] = filters.get("category")

    if filters.get("sub_category"):
        conditions.append("COALESCE(bom.item_subcategory, i.item_subcategory) = %(sub_category)s")
        query_filters["sub_category"] = filters.get("sub_category")

    if filters.get("customer"):
        conditions.append("COALESCE(sn.customer, bom.customer) = %(customer)s")
        query_filters["customer"] = filters.get("customer")

    if filters.get("setting_type"):
        conditions.append("bom.setting_type = %(setting_type)s")
        query_filters["setting_type"] = filters.get("setting_type")

    if filters.get("tag_no"):
        conditions.append("sn.name = %(tag_no)s")
        query_filters["tag_no"] = filters.get("tag_no")

    if filters.get("status"):
        conditions.append(f"({STATUS_CASE_SQL}) = %(status)s")
        query_filters["status"] = filters.get("status")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, query_filters


def get_data(filters):
    where_clause, query_filters = get_conditions(filters)

    query = f"""
        SELECT
            sn.name AS tag_no,
            COALESCE(sn.customer, bom.customer, so.customer_name, '') AS customer,
            CONCAT_WS(' - ', COALESCE(snc.po_no, so.po_no), COALESCE(itcd.sku_code, sn.item_code)) AS detail,
            ({STATUS_CASE_SQL}) AS status,
            COALESCE(bom.item_category, i.item_category, '') AS category,
            COALESCE(bom.item_subcategory, i.item_subcategory, '') AS sub_category,
            i.stylebio AS style_bio,
            bom_metal.metal_touch AS touch,
            (
                SELECT bdd.quality
                FROM `tabBOM Diamond Detail` bdd
                WHERE bdd.parent = bom.name
                ORDER BY bdd.idx
                LIMIT 1
            ) AS diamond_quality,
            (
                SELECT bdd.diamond_grade
                FROM `tabBOM Diamond Detail` bdd
                WHERE bdd.parent = bom.name
                ORDER BY bdd.idx
                LIMIT 1
            ) AS diamond_grade,
            bom.setting_type AS setting_name,
            COALESCE(snc.order_form_id, pmo.name, '') AS order_no,
            COALESCE(snc.po_no, so.po_no, '') AS po_no,
            ROUND(COALESCE(bom.gross_weight, 0), 3) AS gross_wt,
            ROUND(COALESCE(bom.metal_weight, 0), 3) AS gold_wt,
            ROUND(COALESCE(bom.chain_weight, 0), 3) AS chain_wt,
            ROUND(COALESCE(bom.diamond_weight, 0), 3) AS dia_wt,
            ROUND(COALESCE(bom.gemstone_weight, 0), 3) AS stone_wt,
            ROUND(COALESCE(bom.finding_weight_, 0), 3) AS finding_wt,
            ROUND(COALESCE(bom.other_weight, 0), 3) AS other_wt

        FROM `tabSerial No` sn
        LEFT JOIN `tabItem` i
            ON i.name = sn.item_code
        LEFT JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no
        LEFT JOIN `tabSerial Number Creator` snc
            ON snc.name = bom.custom_serial_number_creator
        LEFT JOIN `tabParent Manufacturing Order` pmo
            ON pmo.name = snc.parent_manufacturing_order
        LEFT JOIN `tabBOM Metal Detail` bom_metal
            ON bom_metal.parent = bom.name
        LEFT JOIN `tabItem Theme Code Detail` itcd
            ON itcd.parent = i.name
        LEFT JOIN `tabSales Order Item` soi
            ON (
                soi.serial_no = sn.name
                OR FIND_IN_SET(
                    sn.name,
                    REPLACE(REPLACE(soi.serial_no, '\\n', ','), ' ', '')
                ) > 0
            )
        LEFT JOIN `tabSales Order` so
            ON so.name = soi.parent
        {where_clause}
        GROUP BY sn.name
        ORDER BY sn.creation DESC
    """

    return frappe.db.sql(query, query_filters, as_dict=True)


def get_report_summary(data):
    total_tags = len(data)
    total_gross_wt = sum(flt(row.get("gross_wt")) for row in data)
    total_gold_wt = sum(flt(row.get("gold_wt")) for row in data)
    total_chain_wt = sum(flt(row.get("chain_wt")) for row in data)

    status_counts = {}
    for row in data:
        status = row.get("status") or "Stock"
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = [
        {"value": total_tags, "indicator": "Blue", "label": _("Total Tags"), "datatype": "Int"},
        {"value": total_gross_wt, "indicator": "Blue", "label": _("Gross Wt."), "datatype": "Float", "precision": 3},
        {"value": total_gold_wt, "indicator": "Blue", "label": _("Gold Wt"), "datatype": "Float", "precision": 3},
        {"value": total_chain_wt, "indicator": "Blue", "label": _("Chain Wt."), "datatype": "Float", "precision": 3},
    ]

    for status, indicator in STATUS_INDICATOR.items():
        summary.append({
            "value": status_counts.get(status, 0),
            "indicator": indicator,
            "label": _(status),
            "datatype": "Int",
        })

    return summary
