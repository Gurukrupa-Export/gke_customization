# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    return [
        {"fieldname": "entry_date", "label": _("Entry Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "serial_no", "label": _("Serial No"), "fieldtype": "Link", "options": "Serial No", "width": 130},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
        {"fieldname": "bom", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 150},
        {"fieldname": "pmo", "label": _("PMO"), "fieldtype": "Link", "options": "Parent Manufacturing Order", "width": 150},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "sub_category", "label": _("Sub Category"), "fieldtype": "Data", "width": 140},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "finding_touch", "label": _("Finding Touch"), "fieldtype": "Data", "width": 110},
        {"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 110},
        {"fieldname": "setting_type", "label": _("Setting Type"), "fieldtype": "Data", "width": 130},
        {"fieldname": "order_no", "label": _("Order No"), "fieldtype": "Data", "width": 150},
        {"fieldname": "po_no", "label": _("P.O. No"), "fieldtype": "Data", "width": 150},
        {"fieldname": "batch_no", "label": _("Batch No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "gold_wt", "label": _("Gold Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "gross_wt", "label": _("Gross Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "chain_wt", "label": _("Chain Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "dia_wt", "label": _("Dia Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "dia_pcs", "label": _("Dia Pcs"), "fieldtype": "Int", "width": 90},
        {"fieldname": "diamond_purity", "label": _("Diamond Purity"), "fieldtype": "Data", "width": 120},
        {"fieldname": "stone_wt", "label": _("Stone Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "other_wt", "label": _("Other Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "stone_amt", "label": _("Stone Amt."), "fieldtype": "Currency", "width": 120},
        {"fieldname": "other_amt", "label": _("Other Amt."), "fieldtype": "Currency", "width": 120},
        {"fieldname": "cert_no", "label": _("Cert. No"), "fieldtype": "Data", "width": 130},
        {"fieldname": "customer_design_no", "label": _("Customer DesignNo"), "fieldtype": "Data", "width": 150},
        {"fieldname": "hallmarking_no", "label": _("HallMarking No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "locker", "label": _("Locker"), "fieldtype": "Data", "width": 100},
        {"fieldname": "current_dept", "label": _("Current Dept"), "fieldtype": "Link", "options": "Department", "width": 150},
        {"fieldname": "current_mgr", "label": _("Current Mgr"), "fieldtype": "Data", "width": 180},
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT
            sn.creation AS entry_date,
            sn.name AS serial_no,
            CASE 
                WHEN sn.warehouse LIKE '%%Product Allocation FG%%' AND sn.status = 'Active' THEN 'Stock'
                WHEN sn.status = 'Delivered' THEN 'Transfer'
                WHEN sn.warehouse LIKE '%%Product Vault FG%%' AND sn.status = 'Active' THEN 'Locker'
                WHEN sn.warehouse LIKE '%%Product Certification WO%%' AND sn.status = 'Active' THEN 'Issue to Lab'
                WHEN sn.status = 'Reserved' THEN 'Approve'
                WHEN sn.warehouse LIKE '%%Marketing Person%%' AND sn.status = 'Active' THEN 'Salesman'
                WHEN sn.status = 'Active' AND (
                    EXISTS (SELECT 1 FROM `tabRepair Order Form` WHERE scan_serial_no = sn.name)
                    OR EXISTS (SELECT 1 FROM `tabRepair Order` WHERE scan_serial_no = sn.name)
                ) THEN 'Repair'
                ELSE 'Stock'
            END AS status,
            COALESCE(sn.customer, bom.customer, '') AS customer,
            bom.name AS bom,
            pmo.name AS pmo,
            sn.warehouse AS warehouse,
            COALESCE(bom.item_category, i.item_category, '') AS category,
            COALESCE(bom.item_subcategory, i.item_subcategory, '') AS sub_category,
            sn.item_code AS item_code,
            bom_find.metal_touch AS finding_touch,
            bom_metal.metal_touch AS metal_touch,
            bom.setting_type AS setting_type,
            snc.order_form_id AS order_no,
            snc.po_no AS po_no,
            pmo.custom_jewelex_batch_no AS batch_no,
            ROUND(COALESCE(bom.metal_weight, 0), 3) AS gold_wt,
            ROUND(COALESCE(bom.gross_weight, 0), 3) AS gross_wt,
            ROUND(COALESCE(bom.chain_weight, 0), 3) AS chain_wt,
            ROUND(COALESCE(bom.diamond_weight, 0), 3) AS dia_wt,
            COALESCE(bom.total_diamond_pcs, 0) AS dia_pcs,
            bom_dia.diamond_grade AS diamond_purity,
            ROUND(COALESCE(bom.gemstone_weight, 0), 3) AS stone_wt,
            ROUND(COALESCE(bom.other_weight, 0), 3) AS other_wt,
            ROUND(COALESCE(bom.total_gemstone_amount, 0), 2) AS stone_amt,
            ROUND(
                COALESCE(
                    (SELECT SUM(bod.amount) FROM `tabBOM Other Detail` bod WHERE bod.parent = bom.name),
                    0
                ),
                2
            ) AS other_amt,
            huid.certification_no AS cert_no,
            COALESCE(itcd.digit_18code, itcd.sku_code, itcd.digit_15code, itcd.digit_14code, '') AS customer_design_no,
            huid.huid AS hallmarking_no,
            '' AS locker,
            wh.department AS current_dept,
            (SELECT e.employee_name
             FROM `tabEmployee` e
             WHERE e.department = wh.department
               AND e.designation = 'Manager'
             LIMIT 1) AS current_mgr
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
        LEFT JOIN `tabBOM Finding Detail` bom_find
            ON bom_find.parent = bom.name
        LEFT JOIN `tabBOM Diamond Detail` bom_dia
            ON bom_dia.parent = bom.name
        LEFT JOIN `tabHUID Detail` huid
            ON huid.parent = sn.name
        LEFT JOIN `tabItem Theme Code Detail` itcd
            ON itcd.parent = i.name
        LEFT JOIN `tabWarehouse` wh
            ON wh.name = sn.warehouse
        {conditions}
        GROUP BY sn.name
        ORDER BY sn.creation DESC
    """
    
    data = frappe.db.sql(query, filters, as_dict=True)
    return data


def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("sn.company = %(company)s")
    
    if filters.get("branch"):
        conditions.append("pmo.branch = %(branch)s")
    
    if filters.get("from_date"):
        conditions.append("DATE(sn.creation) >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("DATE(sn.creation) <= %(to_date)s")
    
    if filters.get("category"):
        conditions.append("COALESCE(bom.item_category, i.item_category) = %(category)s")
    
    if filters.get("sub_category"):
        conditions.append("COALESCE(bom.item_subcategory, i.item_subcategory) = %(sub_category)s")
    
    if filters.get("customer"):
        conditions.append("sn.customer = %(customer)s")
    
    if filters.get("department"):
        conditions.append("wh.department = %(department)s")
    
    if filters.get("setting_type"):
        conditions.append("bom.setting_type = %(setting_type)s")
    
    if filters.get("status"):
        status_condition = """
            (CASE 
                WHEN sn.warehouse LIKE '%%Product Allocation FG%%' AND sn.status = 'Active' THEN 'Stock'
                WHEN sn.status = 'Delivered' THEN 'Transfer'
                WHEN sn.warehouse LIKE '%%Product Vault FG%%' AND sn.status = 'Active' THEN 'Locker'
                WHEN sn.warehouse LIKE '%%Product Certification WO%%' AND sn.status = 'Active' THEN 'Issue to Lab'
                WHEN sn.status = 'Reserved' THEN 'Approve'
                WHEN sn.warehouse LIKE '%%Marketing Person%%' AND sn.status = 'Active' THEN 'Salesman'
                WHEN sn.status = 'Active' AND (
                    EXISTS (SELECT 1 FROM `tabRepair Order Form` WHERE scan_serial_no = sn.name)
                    OR EXISTS (SELECT 1 FROM `tabRepair Order` WHERE scan_serial_no = sn.name)
                ) THEN 'Repair'
                ELSE 'Stock'
            END) = %(status)s
        """
        conditions.append(status_condition)
    
    return "WHERE " + " AND ".join(conditions) if conditions else ""
