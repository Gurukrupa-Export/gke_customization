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
        {"fieldname": "action", "label": _(""), "fieldtype": "Data", "width": 150},
        {"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "serial_no", "label": _("Serial No."), "fieldtype": "Link", "options": "Serial No", "width": 150},
        {"fieldname": "serial_no_status", "label": _("Serial No status"), "fieldtype": "Data", "width": 120},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"fieldname": "item_category", "label": _("Item Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "item_subcategory", "label": _("Item Sub Category"), "fieldtype": "Data", "width": 140},
        {"fieldname": "gross_wt", "label": _("Gross Wt."), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "casting_wt", "label": _("Casting Wt."), "fieldtype": "Float", "precision": 3, "width": 130},
        {"fieldname": "finish_metal_wt", "label": _("Finish Metal Wt"), "fieldtype": "Float", "precision": 3, "width": 120},
        {"fieldname": "net_wt", "label": _("Net Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "finding_wt", "label": _("Finding Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "diamond_wt_cts", "label": _("Diamond Wt(cts)"), "fieldtype": "Float", "precision": 3, "width": 150},
        {"fieldname": "gemstone_wt_cts", "label": _("Gemstone Wt(cts)"), "fieldtype": "Float", "precision": 3, "width": 150},
        {"fieldname": "diamond_pcs", "label": _("Diamond Pcs"), "fieldtype": "Int", "width": 120},
        {"fieldname": "gemstone_pcs", "label": _("Gemstone Pcs"), "fieldtype": "Int", "width": 120},
        {"fieldname": "other_wt", "label": _("Other Wt"), "fieldtype": "Float", "precision": 3, "width": 100},
        {"fieldname": "product_size", "label": _("Product Size"), "fieldtype": "Float", "width": 150},
        {"fieldname": "chain_sub_category", "label": _("Chain Sub Category"), "fieldtype": "Data", "width": 180},
        {"fieldname": "setting_type", "label": _("Setting Type"), "fieldtype": "Data", "width": 130},
        {"fieldname": "diamond_grade", "label": _("Diamond Grade"), "fieldtype": "Data", "width": 130},
        {"fieldname": "diamond_quality", "label": _("Diamond Quality"), "fieldtype": "Data", "width": 150}
    ]


def get_data(filters):
    conditions = []
    
    # SMART SEARCH WITH PARSING
    if filters.get("item_code"):
        raw_value = filters.get("item_code")
        
        if " - " in raw_value:
            parts = raw_value.split(" - ")
            serial_no_part = parts[0].strip()
            item_code_part = parts[1].strip() if len(parts) > 1 else ""
            
            serial_check = frappe.db.sql("""
            SELECT item_code FROM `tabSerial No` WHERE name = %s
            """, (serial_no_part,), as_dict=True)
            
            if serial_check:
                item_code = serial_check[0].item_code
                conditions.append("sn.item_code = %(actual_item_code)s")
                filters["actual_item_code"] = item_code
            elif item_code_part:
                item_check = frappe.db.sql("""
                SELECT item_code FROM `tabSerial No` WHERE item_code = %s LIMIT 1
                """, (item_code_part,), as_dict=True)
                
                if item_check:
                    conditions.append("sn.item_code = %(actual_item_code)s")
                    filters["actual_item_code"] = item_code_part
                else:
                    conditions.append("(sn.name LIKE %(search_pattern)s OR sn.item_code LIKE %(search_pattern)s)")
                    filters["search_pattern"] = f"%{serial_no_part}%"
            else:
                conditions.append("(sn.name LIKE %(search_pattern)s OR sn.item_code LIKE %(search_pattern)s)")
                filters["search_pattern"] = f"%{serial_no_part}%"
        else:
            search_value = raw_value.strip()
            
            serial_check = frappe.db.sql("""
            SELECT item_code FROM `tabSerial No` WHERE name = %s
            """, (search_value,), as_dict=True)
            
            if serial_check:
                item_code = serial_check[0].item_code
                conditions.append("sn.item_code = %(actual_item_code)s")
                filters["actual_item_code"] = item_code
            else:
                conditions.append("(sn.name LIKE %(search_pattern)s OR sn.item_code LIKE %(search_pattern)s)")
                filters["search_pattern"] = f"%{search_value}%"
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    # FIXED: Using serial no's specific BOM + CORRECT WEIGHT FIELDS + ACCURATE DIAMOND/GEMSTONE CARATS
    query = f"""
    SELECT DISTINCT
        'View Details' as action,
        
        COALESCE(
            (SELECT si.posting_date
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            (SELECT si.posting_date
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.item_code = sn.item_code
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            NULL
        ) as posting_date,
        
        COALESCE(
            (SELECT sii.parent
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            (SELECT sii.parent
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.item_code = sn.item_code
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            ''
        ) as sales_invoice,
        
        COALESCE(
            sn.customer,
            (SELECT si.customer
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            (SELECT si.customer
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.item_code = sn.item_code
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            ''
        ) as customer,
        
        sn.item_code,
        sn.name as serial_no,
        COALESCE(sn.status, 'Active') as serial_no_status,
        COALESCE(sn.warehouse, '') as warehouse,
        
        COALESCE(i.item_category, '') as item_category,
        COALESCE(i.item_subcategory, '') as item_subcategory,
        
        ROUND(COALESCE(bom.gross_weight, 0), 3) as gross_wt,
        
        ROUND(COALESCE((
            SELECT mo.net_wt 
            FROM `tabSerial No` sn_inner
            LEFT JOIN `tabBOM` bom_inner ON bom_inner.name = sn_inner.custom_bom_no
            LEFT JOIN `tabSerial Number Creator` snc ON snc.name = bom_inner.custom_serial_number_creator
            LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.manufacturing_order = snc.parent_manufacturing_order
                AND mwo.department NOT IN ('Serial Number - GEPL', 'Serial Number - KGJPL', 'Serial Number MU - GEPL')
                AND COALESCE(mwo.is_finding_mwo, 0) = 0
            LEFT JOIN `tabManufacturing Operation` mo ON mo.manufacturing_work_order = mwo.name
                AND mo.operation = 'Casting'
            WHERE sn_inner.name = sn.name
            ORDER BY mo.creation DESC 
            LIMIT 1
        ), 0), 3) as casting_wt,
        
        ROUND(COALESCE(bom.total_metal_weight, 0), 3) as finish_metal_wt,
        ROUND(COALESCE(bom.metal_and_finding_weight, 0), 3) as net_wt,
        ROUND(COALESCE(
            NULLIF(bom.finding_weight_, 0),
            (SELECT SUM(bfd.quantity)
            FROM `tabBOM Finding Detail` bfd
            WHERE bfd.parent = bom.name),
            0
        ), 3) as finding_wt,
        
        ROUND(COALESCE((
            SELECT SUM(bdd.quantity)
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = bom.name
        ), 0), 3) as diamond_wt_cts,
        
        ROUND(COALESCE((
            SELECT SUM(bgd.quantity)
            FROM `tabBOM Gemstone Detail` bgd
            WHERE bgd.parent = bom.name
        ), 0), 3) as gemstone_wt_cts,
        
        COALESCE(bom.total_diamond_pcs, 0) as diamond_pcs,
        COALESCE(bom.total_gemstone_pcs, 0) as gemstone_pcs,
        ROUND(COALESCE(bom.custom_other_wt_2, 0), 3) as other_wt,
        COALESCE(bom.product_size, '') as product_size,
        
        COALESCE((
            SELECT bfd.finding_type
            FROM `tabBOM Finding Detail` bfd
            WHERE bfd.parent = bom.name 
            AND bfd.finding_category = 'Chains'
            ORDER BY bfd.idx
            LIMIT 1
        ), '') as chain_sub_category,
        
        COALESCE(bom.setting_type, '') as setting_type,
        
        COALESCE((
            SELECT bdd.diamond_grade
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = bom.name
            ORDER BY bdd.idx
            LIMIT 1
        ), '') as diamond_grade,
        
        COALESCE((
            SELECT bdd.quality
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = bom.name
            ORDER BY bdd.idx
            LIMIT 1
        ), '') as diamond_quality
        
    FROM `tabSerial No` sn
    LEFT JOIN `tabItem` i ON sn.item_code = i.name
    LEFT JOIN `tabBOM` bom ON bom.name = sn.custom_bom_no
    {where_clause}
    ORDER BY sn.creation DESC
    LIMIT 1000
    """
    
    try:
        data = frappe.db.sql(query, filters, as_dict=True)
        
        seen_serials = set()
        unique_data = []
        for row in data:
            serial_key = row['serial_no']
            if serial_key not in seen_serials:
                seen_serials.add(serial_key)
                unique_data.append(row)
        
        return unique_data
    except Exception as e:
        frappe.log_error("Serial No Detail Report Error", str(e))
        frappe.throw(_("Error fetching data: {0}").format(str(e)))
        return []


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_serial_or_item(doctype, txt, searchfield, start, page_len, filters):
    """Custom search query for autocomplete"""
    
    if not txt:
        return []
    
    serial_results = frappe.db.sql("""
        SELECT DISTINCT 
            sn.name as value,
            CONCAT(sn.name, ' - ', sn.item_code) as description
        FROM `tabSerial No` sn
        WHERE sn.name LIKE %(txt)s
        ORDER BY sn.name
        LIMIT %(page_len)s
    """, {
        'txt': f'%{txt}%',
        'page_len': page_len
    })
    
    item_results = frappe.db.sql("""
        SELECT DISTINCT 
            sn.item_code as value,
            CONCAT(sn.item_code, ' (Item Code)') as description
        FROM `tabSerial No` sn
        WHERE sn.item_code LIKE %(txt)s
        ORDER BY sn.item_code
        LIMIT %(page_len)s
    """, {
        'txt': f'%{txt}%',
        'page_len': page_len
    })
    
    all_results = list(serial_results) + list(item_results)
    
    seen = set()
    unique_results = []
    for item in all_results:
        if item[0] not in seen:
            seen.add(item[0])
            unique_results.append(item)
    
    return unique_results[:page_len]


@frappe.whitelist()
def get_autocomplete_options(txt):
    """Simple autocomplete for Data field - Returns only item codes and serial numbers"""
    
    if not txt or len(txt) < 2:
        return []
    
    try:
        serial_results = frappe.db.sql("""
            SELECT DISTINCT 
                sn.name as value,
                sn.name as description
            FROM `tabSerial No` sn
            WHERE sn.name LIKE %s
            ORDER BY sn.name
            LIMIT 10
        """, (f'%{txt}%',), as_dict=True)
        
        item_results = frappe.db.sql("""
            SELECT DISTINCT 
                sn.item_code as value,
                sn.item_code as description
            FROM `tabSerial No` sn
            WHERE sn.item_code LIKE %s
            ORDER BY sn.item_code
            LIMIT 10
        """, (f'%{txt}%',), as_dict=True)
        
        return serial_results + item_results
        
    except Exception as e:
        frappe.log_error("Autocomplete Error", str(e))
        return []


@frappe.whitelist()
def get_item_category_details(item_code):
    """Get item category and subcategory - FROM ITEM TABLE"""
    try:
        if " - " in item_code:
            parts = item_code.split(" - ")
            serial_no_part = parts[0].strip()
            
            serial_check = frappe.db.sql("""
            SELECT item_code FROM `tabSerial No` WHERE name = %s
            """, (serial_no_part,), as_dict=True)
            
            if serial_check:
                actual_item_code = serial_check[0].item_code
            else:
                actual_item_code = parts[1].strip() if len(parts) > 1 else item_code
        else:
            serial_check = frappe.db.sql("""
            SELECT item_code FROM `tabSerial No` WHERE name = %s
            """, (item_code,), as_dict=True)
            
            if serial_check:
                actual_item_code = serial_check[0].item_code
            else:
                actual_item_code = item_code
        
        category_data = frappe.db.sql("""
        SELECT item_category, item_subcategory
        FROM `tabItem` 
        WHERE name = %s
        """, (actual_item_code,), as_dict=True)
        
        if category_data:
            return {
                "item_category": category_data[0].item_category or "",
                "item_subcategory": category_data[0].item_subcategory or ""
            }
        
        return {"item_category": "", "item_subcategory": ""}
        
    except Exception as e:
        frappe.log_error("Category Details Error", str(e))
        return {"item_category": "", "item_subcategory": ""}


@frappe.whitelist()
def get_raw_material_details(serial_no, item_code=None):
    """Get raw material details from BOM Detail tables (Metal, Finding, Diamond, Gemstone)"""
    
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
        
        item_category = serial_data.get('item_category', '') or ""
        item_subcategory = serial_data.get('item_subcategory', '') or ""
        customer = serial_data.get('customer', '') or ""
        
        item_image = ""
        
        try:
            if bom_name:
                bom_data = frappe.db.sql("""
                SELECT image
                FROM `tabBOM` 
                WHERE name = %s
                """, (bom_name,), as_dict=True)
                
                if bom_data and bom_data[0]:
                    if bom_data[0].image:
                        item_image = bom_data[0].image
            
            if not item_image and item_code:
                item_img = frappe.db.sql("""
                SELECT image 
                FROM `tabItem` 
                WHERE name = %s AND image IS NOT NULL AND image != ''
                """, (item_code,), as_dict=True)
                
                if item_img and item_img[0].image:
                    item_image = item_img[0].image
                    
        except Exception as img_error:
            frappe.log_error("Image Fetch Error", f"Error getting image for {item_code}: {str(img_error)}")
        
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
                
                try:
                    bom_data = frappe.db.sql("""
                    SELECT image
                    FROM `tabBOM` 
                    WHERE name = %s
                    """, (bom_name,), as_dict=True)
                    
                    if bom_data and bom_data[0]:
                        if not item_image and bom_data[0].image:
                            item_image = bom_data[0].image
                except:
                    pass
        
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
        
        # 1. FETCH METAL DETAILS
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
                item.item_code or 'N/A',
                item.metal_type or 'N/A',
                item.metal_touch or 'N/A',
                item.metal_purity or 'N/A',
                item.metal_colour or 'N/A',
                item.qty or 0,
                int(item.pcs or 1),
                item.uom or 'Gram'
            )
            raw_materials.append({"type": "Metal", "display": display})
        
        # 2. FETCH FINDING DETAILS
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
                item.item_code or 'N/A',
                item.finding_category or 'N/A',
                item.finding_sub_category or 'N/A',
                item.metal_type or 'N/A',
                item.metal_touch or 'N/A',
                item.metal_purity or 'N/A',
                item.metal_colour or 'N/A',
                item.finding_size or 'N/A',
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or 'Gram'
            )
            raw_materials.append({"type": "Finding", "display": display})
        
        # 3. FETCH DIAMOND DETAILS
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
                item.item_code or 'N/A',
                item.diamond_type or 'Natural',
                item.stone_shape or 'Round',
                item.diamond_grade or 'N/A',
                item.diamond_sieve_size or 'N/A',
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or 'Carat'
            )
            raw_materials.append({"type": "Diamond", "display": display})
        
        # 4. FETCH GEMSTONE DETAILS
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
                item.item_code or 'N/A',
                item.gemstone_type or 'N/A',
                item.stone_shape or 'N/A',
                item.gemstone_grade or 'N/A',
                item.cut or 'N/A',
                item.gemstone_quality or 'N/A',
                item.qty or 0,
                int(item.pcs or 0),
                item.uom or 'Carat'
            )
            raw_materials.append({"type": "Gemstone", "display": display})
        
        if not raw_materials:
            raw_materials.append({"type": "Debug", "display": f"BOM {bom_name} has no material details"})
        
        # FETCH SETTING TYPE FROM BOM
        setting_type = ""
        if bom_name:
            bom_setting = frappe.db.sql("""
            SELECT setting_type FROM `tabBOM` WHERE name = %s
            """, (bom_name,), as_dict=True)
            if bom_setting and bom_setting[0]:
                setting_type = bom_setting[0].get('setting_type', '') or ""
        
        # FETCH CUSTOMER PO FROM SALES ORDER
        customer_po_no = ""
        try:
            customer_po_data = frappe.db.sql("""
            SELECT so.po_no
            FROM `tabSales Order Item` soi
            LEFT JOIN `tabSales Order` so ON so.name = soi.parent
            WHERE soi.serial_no = %s AND so.docstatus = 1
            ORDER BY so.transaction_date DESC LIMIT 1
            """, (serial_no,), as_dict=True)
            if customer_po_data and customer_po_data[0]:
                customer_po_no = customer_po_data[0].get('po_no', '') or ""
        except:
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


def get_material_pieces(bom_name, material_type, item_code, qty):
    """Direct match by sieve size from BOM Detail tables"""
    
    try:
        if material_type == "Diamond":
            import re
            sieve_match = re.search(r'\+[\d\.]+-[\d\.]+', item_code)
            
            if sieve_match:
                sieve_size = sieve_match.group()
                
                diamond_pcs = frappe.db.sql("""
                SELECT pcs 
                FROM `tabBOM Diamond Detail` 
                WHERE parent = %s 
                AND item_variant LIKE %s
                LIMIT 1
                """, (bom_name, f'%{sieve_size}%'), as_dict=True)
                
                if diamond_pcs and diamond_pcs[0].pcs:
                    return int(diamond_pcs[0].pcs)
            
            diamond_fallback = frappe.db.sql("""
            SELECT pcs 
            FROM `tabBOM Diamond Detail` 
            WHERE parent = %s
            ORDER BY idx
            LIMIT 1
            """, (bom_name,), as_dict=True)
            
            if diamond_fallback and diamond_fallback[0].pcs:
                return int(diamond_fallback[0].pcs)
            
            return 1
                
        elif material_type == "Gemstone":
            gemstone_pcs = frappe.db.sql("""
            SELECT pcs 
            FROM `tabBOM Gemstone Detail` 
            WHERE parent = %s 
            AND (item_variant = %s OR item = %s)
            LIMIT 1
            """, (bom_name, item_code, item_code), as_dict=True)
            
            if gemstone_pcs and gemstone_pcs[0].pcs:
                return int(gemstone_pcs[0].pcs)
                
            gemstone_fallback = frappe.db.sql("""
            SELECT pcs FROM `tabBOM Gemstone Detail` 
            WHERE parent = %s ORDER BY idx LIMIT 1
            """, (bom_name,), as_dict=True)
            
            return int(gemstone_fallback[0].pcs) if gemstone_fallback and gemstone_fallback[0].pcs else 1
            
        elif material_type == "Metal":
            metal_pcs = frappe.db.sql("""
            SELECT pcs 
            FROM `tabBOM Metal Detail` 
            WHERE parent = %s 
            AND (item_variant = %s OR item = %s)
            LIMIT 1
            """, (bom_name, item_code, item_code), as_dict=True)
            
            if metal_pcs and metal_pcs[0].pcs:
                return int(metal_pcs[0].pcs)
            
            return 1
            
        elif material_type == "Finding":
            finding_pcs = frappe.db.sql("""
            SELECT pcs 
            FROM `tabBOM Finding Detail` 
            WHERE parent = %s 
            AND (item_variant = %s OR item = %s)
            LIMIT 1
            """, (bom_name, item_code, item_code), as_dict=True)
            
            if finding_pcs and finding_pcs[0].pcs:
                return int(finding_pcs[0].pcs)
            
            return 1
            
        else:
            return 1
            
    except Exception as e:
        frappe.log_error("Get Material Pieces Error", f"Error getting pieces for {item_code} in {bom_name}: {str(e)}")
        return 1


def parse_description_enhanced(description):
    """Parse HTML description to extract material details"""
    
    if not description:
        return {"material_type": "Other"}
    
    import re
    parsed = {}
    
    if '<b><u>M</u></b>' in description:
        parsed["material_type"] = "Metal"
    elif '<b><u>D</u></b>' in description:
        parsed["material_type"] = "Diamond"
    elif '<b><u>G</u></b>' in description:
        parsed["material_type"] = "Gemstone"
    elif '<b><u>F</u></b>' in description:
        parsed["material_type"] = "Finding"
    else:
        parsed["material_type"] = "Other"
    
    patterns = {
        "metal_type": r"Metal Type : ([^<\n]+)",
        "metal_touch": r"Metal Touch : ([^<\n]+)",
        "metal_purity": r"Metal Purity : ([^<\n]+)",
        "metal_colour": r"Metal Colour : ([^<\n]+)",
        "diamond_type": r"Diamond Type : ([^<\n]+)",
        "stone_shape": r"Stone Shape : ([^<\n]+)",
        "diamond_grade": r"Diamond Grade : ([^<\n]+)",
        "diamond_sieve_size": r"Diamond Sieve Size : ([^<\n]+)",
        "gemstone_type": r"Gemstone Type : ([^<\n]+)",
        "gemstone_quality": r"Gemstone Quality : ([^<\n]+)",
        "gemstone_grade": r"Gemstone Grade : ([^<\n]+)",
        "cut": r"Cut : ([^<\n]+)",
        "cab": r"Cab : ([^<\n]+)",
        "finding_category": r"Finding Category : ([^<\n]+)",
        "finding_sub_category": r"Finding Sub-Category : ([^<\n]+)",
        "finding_size": r"Finding Size : ([^<\n]+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, description)
        if match:
            parsed[key] = match.group(1).strip()
    
    return parsed
