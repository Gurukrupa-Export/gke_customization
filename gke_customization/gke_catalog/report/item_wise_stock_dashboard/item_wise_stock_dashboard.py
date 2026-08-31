# Copyright (c) 2026, Sajith and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"label": _("Min Qty"), "fieldname": "min_qty", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Max Qty"), "fieldname": "max_qty", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Opening Stock"), "fieldname": "opening_stock", "fieldtype": "Float", "width": 120, "precision": 3},
        {"label": _("Dept Issue Qty"), "fieldname": "dept_issue_qty", "fieldtype": "Float", "width": 130, "precision": 3},
        {"label": _("Employee Issue Qty"), "fieldname": "emp_issue_qty", "fieldtype": "Float", "width": 150, "precision": 3},
        {"label": _("Total Issue Qty"), "fieldname": "total_issue_qty", "fieldtype": "Float", "width": 130, "precision": 3},
        {"label": _("Closing Stock"), "fieldname": "closing_stock", "fieldtype": "Float", "width": 120, "precision": 3},
        {"label": _("Unit"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120}
    ]


def get_allowed_warehouses():
    return [
        "BL - CSB Procurement 1 - GEPL",
        "CH - CSB Procurement 1 - GEPL",
        "CSB Procurement - GEPL",
        "HD - CSB Procurement 1 - GEPL",
        "MU - CSB Procurement 1 - GEPL",
        "CSB Product Certification - SHC",
        "CSB Procurement - SHC",
        "CSB Procurement 1 - GEPL",
        "CSB Procurement 2 - GEPL",
        "CSB Procurement 1 - KGJPL",
        "CSB Procurement 2 - KGJPL"
    ]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_name_query(doctype, txt, searchfield, start, page_len, filters):
    txt = cstr(txt or "").strip()

    return frappe.db.sql("""
        SELECT DISTINCT
            i.item_code,
            COALESCE(
                NULLIF(iv.attribute_value, ''),
                NULLIF(i.item_name, ''),
                i.item_code
            ) AS item_display
        FROM `tabItem` i
        LEFT JOIN `tabItem Variant Attribute` iv
            ON iv.parent = i.name
           AND iv.attribute = 'Consumable Type'
        WHERE i.disabled = 0
          AND i.is_stock_item = 1
          AND EXISTS (
                SELECT 1
                FROM `tabItem Group` ig
                WHERE ig.name = i.item_group
                  AND (ig.name = 'Consumable' OR ig.parent_item_group LIKE '%%Consumable%%')
          )
          AND (
                i.item_code LIKE %(txt)s
                OR i.item_name LIKE %(txt)s
                OR iv.attribute_value LIKE %(txt)s
          )
        ORDER BY
            COALESCE(
                NULLIF(iv.attribute_value, ''),
                NULLIF(i.item_name, ''),
                i.item_code
            )
        LIMIT %(start)s, %(page_len)s
    """, {
        "txt": "%%%s%%" % txt,
        "start": start,
        "page_len": page_len
    })


def get_data(filters):
    filters = filters or {}

    from_date = filters.get("from_date", "2026-01-01")
    to_date = filters.get("to_date", "2026-01-15")
    branch = filters.get("branch")
    warehouse = filters.get("warehouse")
    item_group = filters.get("item_group")
    item_code = filters.get("item_code")
    item_name = filters.get("item_name")

    allowed_warehouses = tuple(get_allowed_warehouses())

    branch_filter = ""
    if branch:
        branch_filter = "AND w.custom_branch = %(branch)s"

    warehouse_filter = "AND sle.warehouse IN %(allowed_warehouses)s"
    if warehouse:
        warehouse_filter = "AND sle.warehouse = %(warehouse)s AND sle.warehouse IN %(allowed_warehouses)s"

    item_group_filter = ""
    if item_group:
        item_group_filter = """
        AND EXISTS (
            SELECT 1
            FROM `tabItem Group` ig
            WHERE ig.name = i.item_group
              AND (ig.name = %(item_group)s OR ig.parent_item_group LIKE CONCAT('%%', %(item_group)s, '%%'))
        )
        """

    item_code_filter = ""
    if item_code:
        item_code_filter = """
        AND (
            i.item_code = %(item_code)s
            OR i.item_code LIKE CONCAT('%%', %(item_code)s, '%%')
            OR i.item_name LIKE CONCAT('%%', %(item_code)s, '%%')
        )
        """

    item_name_filter = ""
    if item_name:
        item_name_filter = """
        AND i.item_code = %(item_name)s
        """

    query = f"""
    SELECT
        i.item_code,
        COALESCE(
            NULLIF(iv.attribute_value, ''),
            NULLIF(i.item_name, ''),
            i.item_code
        ) AS item_name,
        sle.warehouse,
        i.item_group,
        COALESCE(i.custom_min_qty, 0) AS min_qty,
        COALESCE(i.custom_max_qty, 0) AS max_qty,
        i.stock_uom AS uom,

        COALESCE(SUM(CASE
            WHEN sle.posting_date < %(from_date)s
            AND sle.is_cancelled = 0
            THEN sle.actual_qty
            ELSE 0
        END), 0) AS opening_stock,

        COALESCE(SUM(CASE
            WHEN sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND sle.voucher_type = 'Stock Entry'
            AND sle.actual_qty < 0
            AND EXISTS (
                SELECT 1
                FROM `tabStock Entry` se
                WHERE se.name = sle.voucher_no
                  AND se.stock_entry_type = 'Consumables Issue to  Department'
            )
            THEN ABS(sle.actual_qty)
            ELSE 0
        END), 0) AS dept_issue_qty,

        COALESCE(SUM(CASE
            WHEN sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND sle.voucher_type = 'Stock Entry'
            AND sle.actual_qty < 0
            AND EXISTS (
                SELECT 1
                FROM `tabStock Entry` se
                WHERE se.name = sle.voucher_no
                  AND se.stock_entry_type = 'Consumables Issue to  Employee'
            )
            THEN ABS(sle.actual_qty)
            ELSE 0
        END), 0) AS emp_issue_qty,

        COALESCE(SUM(CASE
            WHEN sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND sle.voucher_type = 'Stock Entry'
            AND sle.actual_qty < 0
            AND EXISTS (
                SELECT 1
                FROM `tabStock Entry` se
                WHERE se.name = sle.voucher_no
                  AND se.stock_entry_type IN ('Consumables Issue to  Department', 'Consumables Issue to  Employee')
            )
            THEN ABS(sle.actual_qty)
            ELSE 0
        END), 0) AS total_issue_qty,

        COALESCE((
            SELECT b.actual_qty
            FROM `tabBin` b
            WHERE b.item_code = i.item_code
              AND b.warehouse = sle.warehouse
            LIMIT 1
        ), 0) AS closing_stock,

        COALESCE((
            SELECT b.valuation_rate
            FROM `tabBin` b
            WHERE b.item_code = i.item_code
              AND b.warehouse = sle.warehouse
            LIMIT 1
        ), i.valuation_rate, 0) AS rate

    FROM `tabStock Ledger Entry` sle
    INNER JOIN `tabItem` i
        ON sle.item_code = i.item_code
       AND i.is_stock_item = 1
       AND i.disabled = 0
    LEFT JOIN `tabWarehouse` w
        ON w.name = sle.warehouse
    LEFT JOIN `tabItem Variant Attribute` iv
        ON iv.parent = i.name
       AND iv.attribute = 'Consumable Type'
    WHERE sle.docstatus = 1
      AND sle.is_cancelled = 0
      AND EXISTS (
            SELECT 1
            FROM `tabItem Group` ig
            WHERE ig.name = i.item_group
              AND (ig.name = 'Consumable' OR ig.parent_item_group LIKE '%%Consumable%%')
      )
      {warehouse_filter}
      {branch_filter}
      {item_group_filter}
      {item_code_filter}
      {item_name_filter}
    GROUP BY
        i.item_code,
        iv.attribute_value,
        i.item_name,
        sle.warehouse,
        i.item_group,
        i.custom_min_qty,
        i.custom_max_qty,
        i.stock_uom,
        i.valuation_rate
    HAVING ABS(opening_stock) > 0.001
        OR ABS(total_issue_qty) > 0.001
        OR ABS(closing_stock) > 0.001
    ORDER BY total_issue_qty DESC, closing_stock DESC
    LIMIT 1000
    """

    raw_data = frappe.db.sql(query, {
        "branch": branch,
        "warehouse": warehouse,
        "allowed_warehouses": allowed_warehouses,
        "item_group": item_group,
        "item_code": item_code,
        "item_name": item_name,
        "from_date": from_date,
        "to_date": to_date
    }, as_dict=1)

    result = []
    for row in raw_data:
        row["amount"] = (row.get("closing_stock") or 0) * (row.get("rate") or 0)
        result.append(row)

    return result