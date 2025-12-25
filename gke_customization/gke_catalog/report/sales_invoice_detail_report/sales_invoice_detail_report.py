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
        {"label": _("Detail"), "fieldname": "detail", "fieldtype": "Data", "width": 80},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer Approval No"), "fieldname": "approval_no", "fieldtype": "Link", "options": "Customer Approval", "width": 200},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 150},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": _("Sales Invoice"), "fieldname": "bill_no", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Serial No"), "fieldname": "tag_no", "fieldtype": "Link", "options": "Serial No", "width": 120},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": _("Metal Wt"), "fieldname": "metal_wt", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Metal Wt Diff"), "fieldname": "metal_wt_diff", "fieldtype": "Float", "width": 100, "precision": 4},
        {"label": _("Chain Wt"), "fieldname": "chain_wt", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Pure Wt"), "fieldname": "pure_wt", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Dia Wts"), "fieldname": "dia_wts", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Dia Wts Diff"), "fieldname": "dia_wts_diff", "fieldtype": "Float", "width": 100, "precision": 4},
        {"label": _("Dia Pcs"), "fieldname": "dia_pcs", "fieldtype": "Int", "width": 90},
        {"label": _("Stone Wt"), "fieldname": "stone_wt", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Stone Pcs"), "fieldname": "stone_pcs", "fieldtype": "Int", "width": 90},
        {"label": _("Other Wts"), "fieldname": "other_wts", "fieldtype": "Float", "width": 90, "precision": 2},
        {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
        {"label": _("Sub Category"), "fieldname": "sub_category", "fieldtype": "Data", "width": 150},
        {"label": _("Setting"), "fieldname": "setting", "fieldtype": "Data", "width": 100},
        {"label": _("Finding Touch"), "fieldname": "finding_touch", "fieldtype": "Data", "width": 120},
        {"label": _("Metal Touch"), "fieldname": "metal_touch", "fieldtype": "Data", "width": 100},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
    ]

def get_data(filters):
    conditions = []

    if filters.get("from_date"):
        conditions.append("AND si.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("AND si.posting_date <= %(to_date)s")
    if filters.get("invoice_no"):
        conditions.append("AND si.name = %(invoice_no)s")
    if filters.get("serial_no"):
        conditions.append("AND sii.serial_no = %(serial_no)s")
    if filters.get("branch"):
        conditions.append("AND si.branch = %(branch)s")
    if filters.get("customer"):
        conditions.append("AND si.customer = %(customer)s")
    if filters.get("company"):
        conditions.append("AND si.company = %(company)s")

    conditions_str = " ".join(conditions) if conditions else ""

    query = """
        SELECT 
            '' as detail,
            si.posting_date,
            soi.custom_customer_approval as approval_no,
            sii.sales_order as sales_order,
            si.branch as branch,
            si.customer,
            si.name as bill_no,
            COALESCE(soi.serial_no, sii.batch_no) as tag_no,
            sii.item_code,
            ROUND(IFNULL((
                SELECT SUM(bmd.quantity)
                FROM `tabBOM Metal Detail` bmd
                WHERE bmd.parent = bom.name
            ), 0), 2) as metal_wt,
            ROUND(IFNULL((
                SELECT SUM(bmd.quantity)
                FROM `tabBOM Metal Detail` bmd
                WHERE bmd.parent = bom.name
            ), 0) - ROUND(IFNULL((
                SELECT SUM(bmd.quantity)
                FROM `tabBOM Metal Detail` bmd
                WHERE bmd.parent = bom.name
            ), 0), 2), 4) as metal_wt_diff,
            ROUND(IFNULL(bom.chain_weight, 0), 2) as chain_wt,
            ROUND(IFNULL((
                SELECT SUM(bmd.quantity * bmd.purity_percentage / 100)
                FROM `tabBOM Metal Detail` bmd
                WHERE bmd.parent = bom.name
            ), 0), 2) as pure_wt,
            ROUND(IFNULL(bom.total_diamond_weight, 0), 2) as dia_wts,
            ROUND(IFNULL(bom.total_diamond_weight, 0) - ROUND(IFNULL(bom.total_diamond_weight, 0), 2), 4) as dia_wts_diff,
            IFNULL(bom.total_diamond_pcs, 0) as dia_pcs,
            ROUND(IFNULL(bom.total_gemstone_weight, 0), 2) as stone_wt,
            IFNULL(bom.total_gemstone_pcs, 0) as stone_pcs,
            ROUND(IFNULL(bom.total_other_weight, 0), 2) as other_wts,
            bom.item_category as category,
            bom.item_subcategory as sub_category,
            bom.setting_type as setting,
            COALESCE((
                SELECT bfd.metal_touch
                FROM `tabBOM Finding Detail` bfd
                WHERE bfd.parent = bom.name
                ORDER BY bfd.idx
                LIMIT 1
            ), '') as finding_touch,
            bom.metal_touch as metal_touch,
            si.customer_name
        FROM 
            `tabSales Invoice` si
        INNER JOIN 
            `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN 
            `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
        LEFT JOIN 
            `tabBOM` bom ON soi.bom = bom.name
        WHERE 
            si.docstatus = 1
            {conditions}
        ORDER BY 
            si.posting_date DESC, si.name, sii.idx
    """.format(conditions=conditions_str)

    data = frappe.db.sql(query, filters, as_dict=1)

    for row in data:
        row["detail"] = (
            '<button class="btn btn-xs btn-default view-details-btn" '
            'data-serial-no="{0}" data-item-code="{1}" data-bill-no="{2}">View</button>'
        ).format(row.get("tag_no", ""), row.get("item_code", ""), row.get("bill_no", ""))

    return data

@frappe.whitelist()
def get_raw_material_details(serial_no, item_code, bill_no):
    """Get raw material details from BOM for Sales Invoice item"""

    try:
        if not bill_no or not item_code:
            return {
                "raw_materials": [{"type": "Error", "display": "Missing bill_no or item_code"}],
                "bom_name": "Error",
                "item_image": "",
                "item_category": "",
                "item_subcategory": "",
                "customer": "",
                "setting_type": ""
            }

        bom_info = frappe.db.sql(
            """
            SELECT 
                soi.bom,
                sii.item_code,
                si.customer,
                si.customer_name,
                bom.item_category,
                bom.item_subcategory,
                bom.setting_type,
                bom.image
            FROM `tabSales Invoice Item` sii
            LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
            LEFT JOIN `tabSales Order Item` soi ON sii.sales_order = soi.parent AND sii.so_detail = soi.name
            LEFT JOIN `tabBOM` bom ON soi.bom = bom.name
            WHERE si.name = %s AND sii.item_code = %s
            LIMIT 1
        """,
            (bill_no, item_code),
            as_dict=True,
        )

        if not bom_info:
            return {
                "raw_materials": [{"type": "Info", "display": "No BOM info found for this invoice item"}],
                "bom_name": "No BOM Info",
                "item_image": "",
                "item_category": "",
                "item_subcategory": "",
                "customer": "",
                "setting_type": ""
            }

        bom_data = bom_info[0]

        if not bom_data.get("bom"):
            return {
                "raw_materials": [{"type": "Info", "display": "No BOM linked to this item"}],
                "bom_name": "No BOM",
                "item_image": bom_data.get("image", "") or "",
                "item_category": bom_data.get("item_category", "") or "",
                "item_subcategory": bom_data.get("item_subcategory", "") or "",
                "customer": bom_data.get("customer_name", "") or "",
                "setting_type": ""
            }

        bom_name = bom_data.bom
        raw_materials = []

        # 1. Metal
        metal_items = frappe.db.sql(
            """
            SELECT 
                bmd.item_variant as item_code,
                bmd.metal_type,
                bmd.metal_touch,
                bmd.metal_purity,
                bmd.metal_colour,
                bmd.quantity as qty,
                1 as pcs,
                bmd.stock_uom as uom
            FROM `tabBOM Metal Detail` bmd
            WHERE bmd.parent = %s
            ORDER BY bmd.idx
        """,
            (bom_name,),
            as_dict=True,
        )

        for item in metal_items:
            display = (
                "{0}<br>Metal = {1}<br>Metal Touch = {2}<br>Metal Purity = {3}"
                "<br>Metal Color = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}"
            ).format(
                item.item_code or "N/A",
                item.metal_type or "N/A",
                item.metal_touch or "N/A",
                item.metal_purity or "N/A",
                item.metal_colour or "N/A",
                item.qty or 0,
                int(item.pcs or 1),
                item.uom or "Gram",
            )
            raw_materials.append({"type": "Metal", "display": display})

        # 2. Finding
        finding_items = frappe.db.sql(
            """
            SELECT 
                bfd.item_variant as item_code,
                bfd.finding_category,
                bfd.finding_type as finding_sub_category,
                bfd.metal_type,
                bfd.metal_touch,
                bfd.metal_purity,
                bfd.metal_colour,
                bfd.finding_size,
                bfd.quantity as qty,
                COALESCE(bfd.qty, 0) as pcs,
                bfd.stock_uom as uom
            FROM `tabBOM Finding Detail` bfd
            WHERE bfd.parent = %s
            ORDER BY bfd.idx
        """,
            (bom_name,),
            as_dict=True,
        )

        for item in finding_items:
            display = (
                "{0}<br>Finding Category = {1}<br>Finding Sub-Category = {2}"
                "<br>Metal = {3}<br>Metal Touch = {4}<br>Metal Purity = {5}"
                "<br>Metal Color = {6}<br>Size = {7}<br>Qty = {8:.3f}"
                "<br>Pcs = {9}<br>UOM = {10}"
            ).format(
                item.item_code or "N/A",
                item.finding_category or "N/A",
                item.finding_sub_category or "N/A",
                item.metal_type or "N/A",
                item.metal_touch or "N/A",
                item.metal_purity or "N/A",
                item.metal_colour or "N/A",
                item.finding_size or "N/A",
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or "Gram",
            )
            raw_materials.append({"type": "Finding", "display": display})

        # 3. Diamond
        diamond_items = frappe.db.sql(
            """
            SELECT 
                bdd.item_variant as item_code,
                bdd.diamond_type,
                bdd.stone_shape,
                bdd.diamond_grade,
                bdd.diamond_sieve_size,
                bdd.quantity as qty,
                bdd.pcs,
                'Carat' as uom
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = %s
            ORDER BY bdd.idx
        """,
            (bom_name,),
            as_dict=True,
        )

        for item in diamond_items:
            display = (
                "{0}<br>Diamond Type = {1}<br>Stone Shape = {2}"
                "<br>Diamond Grade = {3}<br>Diamond Sieve Size = {4}"
                "<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}"
            ).format(
                item.item_code or "N/A",
                item.diamond_type or "Natural",
                item.stone_shape or "Round",
                item.diamond_grade or "N/A",
                item.diamond_sieve_size or "N/A",
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or "Carat",
            )
            raw_materials.append({"type": "Diamond", "display": display})

        # 4. Gemstone
        gemstone_items = frappe.db.sql(
            """
            SELECT 
                bgd.item_variant as item_code,
                bgd.gemstone_type,
                bgd.stone_shape,
                bgd.gemstone_grade,
                bgd.cut_or_cab as cut,
                bgd.gemstone_quality,
                bgd.quantity as qty,
                bgd.pcs,
                'Carat' as uom
            FROM `tabBOM Gemstone Detail` bgd
            WHERE bgd.parent = %s
            ORDER BY bgd.idx
        """,
            (bom_name,),
            as_dict=True,
        )

        for item in gemstone_items:
            display = (
                "{0}<br>Gemstone Type = {1}<br>Stone Shape = {2}"
                "<br>Gemstone Grade = {3}<br>Cut/Cab = {4}"
                "<br>Gemstone Quality = {5}<br>Qty = {6:.3f}"
                "<br>Pcs = {7}<br>UOM = {8}"
            ).format(
                item.item_code or "N/A",
                item.gemstone_type or "N/A",
                item.stone_shape or "N/A",
                item.gemstone_grade or "N/A",
                item.cut or "N/A",
                item.gemstone_quality or "N/A",
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or "Carat",
            )
            raw_materials.append({"type": "Gemstone", "display": display})

        if not raw_materials:
            raw_materials.append(
                {"type": "Info", "display": "No raw material details found in BOM"}
            )

        return {
            "raw_materials": raw_materials,
            "bom_name": bom_name,
            "item_image": bom_data.get("image", "") or "",
            "item_category": bom_data.get("item_category", "") or "",
            "item_subcategory": bom_data.get("item_subcategory", "") or "",
            "customer": bom_data.get("customer_name", "") or "",
            "setting_type": bom_data.get("setting_type", "") or "",
        }

    except Exception as e:
        frappe.log_error("Sales Invoice Raw Material Details Error", str(e))
        return {
            "raw_materials": [{"type": "Error", "display": f"Error: {str(e)}"}],
            "bom_name": "Error",
            "item_image": "",
            "item_category": "",
            "item_subcategory": "",
            "customer": "",
            "setting_type": "",
        }
