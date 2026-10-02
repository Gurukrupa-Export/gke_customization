# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import re
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
        {"fieldname": "detail", "label": _(""), "fieldtype": "Data", "width": 120},
        {"fieldname": "tag_no", "label": _("Tag No"), "fieldtype": "Link", "options": "Serial No", "width": 150},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "sub_category", "label": _("Sub Category"), "fieldtype": "Data", "width": 140},
        {"fieldname": "po_no", "label": _("PO No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "setting", "label": _("Setting"), "fieldtype": "Data", "width": 110},
        {"fieldname": "style_bio", "label": _("Style Bio"), "fieldtype": "Data", "width": 140},
        {"fieldname": "no_of_times_sold", "label": _("No. Of Times Sold"), "fieldtype": "Int", "width": 140},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Data", "width": 140},
        {"fieldname": "prod_date", "label": _("Prod. Date"), "fieldtype": "Datetime", "width": 150},
        {"fieldname": "prod_branch", "label": _("Prod. Branch"), "fieldtype": "Data", "width": 130},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Data", "width": 130},
        {"fieldname": "order_date", "label": _("Order Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "order_no", "label": _("Order No"), "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"fieldname": "order_customer", "label": _("Order Customer"), "fieldtype": "Data", "width": 200},
        {"fieldname": "batch_no", "label": _("Batch No"), "fieldtype": "Data", "width": 180},
        {"fieldname": "touch", "label": _("Touch"), "fieldtype": "Data", "width": 90},
        {"fieldname": "gross_wt", "label": _("Gross Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "gold_wt", "label": _("Gold Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "gold_pure_wt", "label": _("Gold PureWt"), "fieldtype": "Float", "precision": 3, "width": 110},
        {"fieldname": "chain_wt", "label": _("Chain Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "chain_pure_wt", "label": _("Chain PureWt"), "fieldtype": "Float", "precision": 3, "width": 115},
        {"fieldname": "dia_wt", "label": _("Dia Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "dia_pcs", "label": _("Dia Pcs"), "fieldtype": "Float", "precision": 0, "width": 90},
        {"fieldname": "stone_wt", "label": _("Stone Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "stone_pcs", "label": _("Stone Pcs"), "fieldtype": "Float", "precision": 0, "width": 90},
        {"fieldname": "other_wt", "label": _("Other Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
        {"fieldname": "invoice_no", "label": _("Invoice No"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"fieldname": "invoice_date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "size_remark", "label": _("Size Remark"), "fieldtype": "Data", "width": 130},
        {"fieldname": "certificate_no", "label": _("Certificate No."), "fieldtype": "Data", "width": 140},
        {"fieldname": "hallmarking_no", "label": _("HallMarking No"), "fieldtype": "Data", "width": 140},
        {"fieldname": "metal_color", "label": _("Metal Color"), "fieldtype": "Data", "width": 110},
        {"fieldname": "product_size", "label": _("Product Size"), "fieldtype": "Float", "width": 110},
        {"fieldname": "current_dept", "label": _("Current Dept"), "fieldtype": "Data", "width": 160},
        {"fieldname": "current_manager", "label": _("Current Manager"), "fieldtype": "Data", "width": 150},
        {"fieldname": "dia_purity", "label": _("Dia Purity"), "fieldtype": "Data", "width": 120},
    ]


def parse_multi_search(raw_text):
    if not raw_text:
        return []

    parts = re.split(r'[\n,;|\t ]+', raw_text.strip())
    cleaned = []
    seen = set()

    for part in parts:
        value = (part or "").strip()
        if not value:
            continue

        upper_value = value.upper()
        if upper_value not in seen:
            seen.add(upper_value)
            cleaned.append(value)

    return cleaned


def resolve_serial_numbers(search_values):
    if not search_values:
        return []

    rows = frappe.db.sql("""
        SELECT DISTINCT sn.name
        FROM `tabSerial No` sn
        WHERE sn.name IN %(search_values)s
           OR sn.item_code IN %(search_values)s
        ORDER BY sn.name
    """, {
        "search_values": tuple(search_values)
    }, as_dict=True)

    return [d.name for d in rows]


def get_data(filters):
    conditions = []
    query_filters = {}

    search_values = parse_multi_search(filters.get("search_text"))

    if search_values:
        serial_numbers = resolve_serial_numbers(search_values)

        if not serial_numbers:
            return []

        conditions.append("sn.name IN %(serial_numbers)s")
        query_filters["serial_numbers"] = tuple(serial_numbers)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            'View Detail' AS detail,
            sn.name AS tag_no,
            sn.item_code AS item_code,
            i.item_category AS category,
            i.item_subcategory AS sub_category,
            pmo.po_no AS po_no,
            bom.setting_type AS setting,
            i.stylebio AS style_bio,
            COALESCE(sold.no_of_times_sold, 0) AS no_of_times_sold,
            COALESCE(
                sn.customer,
                (
                    SELECT si.customer
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
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                ),
                so.customer,
                ''
            ) AS customer,
            sn.creation AS prod_date,
            mwo.branch AS prod_branch,
            pmo.branch AS branch,
            so.transaction_date AS order_date,
            so.name AS order_no,
            so.customer_name AS order_customer,
            mwo.name AS batch_no,
            wt.touch,
            ROUND(COALESCE(bom.gross_weight, 0), 3) AS gross_wt,
            ROUND(COALESCE(wt.gold_wt, 0), 3) AS gold_wt,
            ROUND(COALESCE(wt.gold_pure_wt, 0), 3) AS gold_pure_wt,
            ROUND(COALESCE(wt.chain_wt, 0), 3) AS chain_wt,
            ROUND(COALESCE(wt.chain_pure_wt, 0), 3) AS chain_pure_wt,
            ROUND(COALESCE(wt.dia_wt, 0), 3) AS dia_wt,
            COALESCE(wt.dia_pcs, 0) AS dia_pcs,
            ROUND(COALESCE(wt.stone_wt, 0), 3) AS stone_wt,
            COALESCE(wt.stone_pcs, 0) AS stone_pcs,
            ROUND(COALESCE(wt.other_wt, 0), 3) AS other_wt,
            sn.status AS status,

            COALESCE(
                (
                    SELECT sii.parent
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
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                ),
                (
                    SELECT sii.parent
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    WHERE si.docstatus = 1
                      AND sii.sales_order = so.name
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                ),
                (
                    SELECT sii.parent
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    WHERE si.docstatus = 1
                      AND sii.item_code = sn.item_code
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                )
            ) AS invoice_no,

            COALESCE(
                (
                    SELECT si.posting_date
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
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                ),
                (
                    SELECT si.posting_date
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    WHERE si.docstatus = 1
                      AND sii.sales_order = so.name
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                ),
                (
                    SELECT si.posting_date
                    FROM `tabSales Invoice Item` sii
                    INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
                    WHERE si.docstatus = 1
                      AND sii.item_code = sn.item_code
                    ORDER BY si.posting_date DESC, si.creation DESC
                    LIMIT 1
                )
            ) AS invoice_date,

            NULL AS size_remark,
            hd.certification_no AS certificate_no,
            hd.huid AS hallmarking_no,
            bom.metal_colour AS metal_color,
            bom.product_size AS product_size,
            wh.department AS current_dept,
            emp.employee_name AS current_manager,
            bom.diamond_quality AS dia_purity

        FROM `tabSerial No` sn
        LEFT JOIN `tabItem` i
            ON sn.item_code = i.name
        LEFT JOIN `tabBOM` bom
            ON sn.custom_bom_no = bom.name
        LEFT JOIN `tabSerial Number Creator` snc
            ON bom.custom_serial_number_creator = snc.name
        LEFT JOIN `tabParent Manufacturing Order` pmo
            ON snc.parent_manufacturing_order = pmo.name
        LEFT JOIN `tabManufacturing Work Order` mwo
            ON snc.manufacturing_work_order = mwo.name
        LEFT JOIN `tabSales Order Item` soi
            ON (
                soi.serial_no = sn.name
                OR FIND_IN_SET(
                    sn.name,
                    REPLACE(REPLACE(soi.serial_no, '\\n', ','), ' ', '')
                ) > 0
            )
        LEFT JOIN `tabSales Order` so
            ON soi.parent = so.name
        LEFT JOIN `tabWarehouse` wh
            ON sn.warehouse = wh.name
        LEFT JOIN `tabEmployee` emp
            ON wh.department = emp.department
           AND emp.designation = 'Manager'
        LEFT JOIN (
            SELECT
                parent,
                MAX(certification_no) AS certification_no,
                MAX(huid) AS huid
            FROM `tabHUID Detail`
            GROUP BY parent
        ) hd
            ON hd.parent = sn.name
        LEFT JOIN (
            SELECT
                sn2.name AS tag_no,
                COUNT(DISTINCT soi.name) AS no_of_times_sold
            FROM `tabSerial No` sn2
            LEFT JOIN `tabSales Order Item` soi
                ON (
                    soi.serial_no = sn2.name
                    OR FIND_IN_SET(
                        sn2.name,
                        REPLACE(REPLACE(soi.serial_no, '\\n', ','), ' ', '')
                    ) > 0
                )
            GROUP BY sn2.name
        ) sold
            ON sold.tag_no = sn.name
        LEFT JOIN (
            SELECT
                b.name AS bom_name,
                metal.touch,
                metal.gold_wt,
                metal.gold_pure_wt,
                finding.chain_wt,
                finding.chain_pure_wt,
                dia.dia_wt,
                dia.dia_pcs,
                stn.stone_wt,
                stn.stone_pcs,
                oth.other_wt
            FROM `tabBOM` b
            LEFT JOIN (
                SELECT
                    parent,
                    MAX(metal_touch) AS touch,
                    SUM(quantity) AS gold_wt,
                    SUM(quantity * purity_percentage / 100) AS gold_pure_wt
                FROM `tabBOM Metal Detail`
                GROUP BY parent
            ) metal
                ON metal.parent = b.name
            LEFT JOIN (
                SELECT
                    parent,
                    SUM(quantity) AS chain_wt,
                    SUM(quantity * purity_percentage / 100) AS chain_pure_wt
                FROM `tabBOM Finding Detail`
                GROUP BY parent
            ) finding
                ON finding.parent = b.name
            LEFT JOIN (
                SELECT
                    parent,
                    SUM(quantity) AS dia_wt,
                    SUM(pcs) AS dia_pcs
                FROM `tabBOM Diamond Detail`
                GROUP BY parent
            ) dia
                ON dia.parent = b.name
            LEFT JOIN (
                SELECT
                    parent,
                    SUM(quantity) AS stone_wt,
                    SUM(pcs) AS stone_pcs
                FROM `tabBOM Gemstone Detail`
                GROUP BY parent
            ) stn
                ON stn.parent = b.name
            LEFT JOIN (
                SELECT
                    parent,
                    SUM(quantity) AS other_wt
                FROM `tabBOM Other Detail`
                GROUP BY parent
            ) oth
                ON oth.parent = b.name
        ) wt
            ON wt.bom_name = bom.name
        {where_clause}
        ORDER BY sn.name
    """

    data = frappe.db.sql(query, query_filters, as_dict=True)

    unique_rows = []
    seen = set()

    for row in data:
        key = row.get("tag_no")
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    return unique_rows


@frappe.whitelist()
def get_raw_material_details(serial_no, item_code=None):
    try:
        serial_info = frappe.db.sql("""
            SELECT
                sn.item_code,
                sn.custom_bom_no,
                sn.warehouse,
                sn.status,
                sn.customer,
                i.item_name,
                i.item_category,
                i.item_subcategory
            FROM `tabSerial No` sn
            LEFT JOIN `tabItem` i ON sn.item_code = i.name
            WHERE sn.name = %s
        """, (serial_no,), as_dict=True)

        if not serial_info:
            return {
                "raw_materials": [{"type": "Debug", "display": f"Serial number {serial_no} not found"}],
                "casting_info": {},
                "bom_name": "Serial Not Found",
                "item_image": "",
                "item_category": "",
                "item_subcategory": "",
                "customer": "",
                "setting_type": "",
                "customer_po_no": ""
            }

        serial_data = serial_info[0]
        item_code = serial_data.item_code
        bom_name = serial_data.custom_bom_no
        item_category = serial_data.get("item_category", "") or ""
        item_subcategory = serial_data.get("item_subcategory", "") or ""
        customer = serial_data.get("customer", "") or ""
        item_image = ""

        try:
            if bom_name:
                bom_data = frappe.db.sql("""
                    SELECT image
                    FROM `tabBOM`
                    WHERE name = %s
                """, (bom_name,), as_dict=True)

                if bom_data and bom_data[0] and bom_data[0].image:
                    item_image = bom_data[0].image

            if not item_image and item_code:
                item_img = frappe.db.sql("""
                    SELECT image
                    FROM `tabItem`
                    WHERE name = %s AND image IS NOT NULL AND image != ''
                """, (item_code,), as_dict=True)

                if item_img and item_img[0].image:
                    item_image = item_img[0].image
        except Exception:
            pass

        if not bom_name:
            bom_info = frappe.db.sql("""
                SELECT name
                FROM `tabBOM`
                WHERE item = %s AND is_active = 1 AND docstatus = 1
                ORDER BY creation DESC
                LIMIT 1
            """, (item_code,), as_dict=True)

            if bom_info:
                bom_name = bom_info[0].name

        if not bom_name:
            return {
                "raw_materials": [{"type": "Debug", "display": f"No BOM found for item {item_code}"}],
                "casting_info": {},
                "bom_name": "No BOM Found",
                "item_image": item_image,
                "item_category": item_category,
                "item_subcategory": item_subcategory,
                "customer": customer,
                "setting_type": "",
                "customer_po_no": ""
            }

        raw_materials = []

        metal_items = frappe.db.sql("""
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
        """, (bom_name,), as_dict=True)

        for item in metal_items:
            display = "{0}<br>Metal = {1}<br>Metal Touch = {2}<br>Metal Purity = {3}<br>Metal Color = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}".format(
                item.item_code or "N/A",
                item.metal_type or "N/A",
                item.metal_touch or "N/A",
                item.metal_purity or "N/A",
                item.metal_colour or "N/A",
                item.qty or 0,
                int(item.pcs or 1),
                item.uom or "Gram"
            )
            raw_materials.append({"type": "Metal", "display": display})

        finding_items = frappe.db.sql("""
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
        """, (bom_name,), as_dict=True)

        for item in finding_items:
            display = "{0}<br>Finding Category = {1}<br>Finding Sub-Category = {2}<br>Metal = {3}<br>Metal Touch = {4}<br>Metal Purity = {5}<br>Metal Color = {6}<br>Size = {7}<br>Qty = {8:.3f}<br>Pcs = {9}<br>UOM = {10}".format(
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
                item.uom or "Gram"
            )
            raw_materials.append({"type": "Finding", "display": display})

        diamond_items = frappe.db.sql("""
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
        """, (bom_name,), as_dict=True)

        for item in diamond_items:
            display = "{0}<br>Diamond Type = {1}<br>Stone Shape = {2}<br>Diamond Grade = {3}<br>Diamond Sieve Size = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}".format(
                item.item_code or "N/A",
                item.diamond_type or "Natural",
                item.stone_shape or "Round",
                item.diamond_grade or "N/A",
                item.diamond_sieve_size or "N/A",
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or "Carat"
            )
            raw_materials.append({"type": "Diamond", "display": display})

        gemstone_items = frappe.db.sql("""
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
        """, (bom_name,), as_dict=True)

        for item in gemstone_items:
            display = "{0}<br>Gemstone Type = {1}<br>Stone Shape = {2}<br>Gemstone Grade = {3}<br>Cut/Cab = {4}<br>Gemstone Quality = {5}<br>Qty = {6:.3f}<br>Pcs = {7}<br>UOM = {8}".format(
                item.item_code or "N/A",
                item.gemstone_type or "N/A",
                item.stone_shape or "N/A",
                item.gemstone_grade or "N/A",
                item.cut or "N/A",
                item.gemstone_quality or "N/A",
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or "Carat"
            )
            raw_materials.append({"type": "Gemstone", "display": display})

        if not raw_materials:
            raw_materials.append({"type": "Debug", "display": f"BOM {bom_name} has no material details"})

        setting_type = ""
        if bom_name:
            bom_setting = frappe.db.sql("""
                SELECT setting_type
                FROM `tabBOM`
                WHERE name = %s
            """, (bom_name,), as_dict=True)
            if bom_setting and bom_setting[0]:
                setting_type = bom_setting[0].get("setting_type", "") or ""

        customer_po_no = ""
        try:
            customer_po_data = frappe.db.sql("""
                SELECT so.po_no
                FROM `tabSales Order Item` soi
                LEFT JOIN `tabSales Order` so ON so.name = soi.parent
                WHERE (
                    soi.serial_no = %s
                    OR FIND_IN_SET(
                        %s,
                        REPLACE(REPLACE(soi.serial_no, '\n', ','), ' ', '')
                    ) > 0
                )
                AND so.docstatus = 1
                ORDER BY so.transaction_date DESC
                LIMIT 1
            """, (serial_no, serial_no), as_dict=True)
            if customer_po_data and customer_po_data[0]:
                customer_po_no = customer_po_data[0].get("po_no", "") or ""
        except Exception:
            pass

        return {
            "raw_materials": raw_materials,
            "casting_info": {},
            "bom_name": bom_name,
            "item_image": item_image,
            "item_category": item_category,
            "item_subcategory": item_subcategory,
            "customer": customer,
            "setting_type": setting_type,
            "customer_po_no": customer_po_no
        }

    except Exception as e:
        frappe.log_error("Raw Material Details Error", str(e))
        return {
            "raw_materials": [{"type": "Error", "display": f"Error: {str(e)}"}],
            "casting_info": {},
            "bom_name": "Error",
            "item_image": "",
            "item_category": "",
            "item_subcategory": "",
            "customer": "",
            "setting_type": "",
            "customer_po_no": ""
        }