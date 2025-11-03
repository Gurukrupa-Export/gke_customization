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
    
    # SMART SEARCH: Item Code or Serial No detection
    if filters.get("item_code"):
        search_value = filters.get("item_code")
        
        # Check if it's a serial number first
        serial_check = frappe.db.sql("""
        SELECT item_code FROM `tabSerial No` WHERE name = %s
        """, (search_value,), as_dict=True)
        
        if serial_check:
            # It's a serial number - use the item_code from it
            item_code = serial_check[0].item_code
            conditions.append("sn.item_code = %(actual_item_code)s")
            filters["actual_item_code"] = item_code
        else:
            # It's an item code - use directly
            conditions.append("sn.item_code = %(item_code)s")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    # FIXED SALES INVOICE QUERY - Using BOTH approaches
    query = f"""
    SELECT DISTINCT
        ROW_NUMBER() OVER (ORDER BY sn.creation DESC) as no,
        'View Details' as action,
        
        -- FIXED: Try both serial_no field and item_code field in Sales Invoice Item
        COALESCE(
            -- Approach 1: Try serial_no field first
            (SELECT si.posting_date
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            -- Approach 2: Try item_code field
            (SELECT si.posting_date
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.item_code = sn.item_code
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            NULL
        ) as posting_date,
        
        -- FIXED: Sales Invoice ID with both approaches
        COALESCE(
            -- Approach 1: Try serial_no field first
            (SELECT sii.parent
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            -- Approach 2: Try item_code field
            (SELECT sii.parent
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.item_code = sn.item_code
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            ''
        ) as sales_invoice,
        
        -- FIXED: Customer with both approaches
        COALESCE(
            sn.customer,
            -- Approach 1: Try serial_no field first
            (SELECT si.customer
             FROM `tabSales Invoice Item` sii
             LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
             WHERE sii.serial_no = sn.name
             AND si.docstatus = 1
             ORDER BY si.posting_date DESC, si.creation DESC
             LIMIT 1),
            -- Approach 2: Try item_code field
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
        
        -- Gross Wt from BOM.gross_weight
        ROUND(COALESCE(bom.gross_weight, 0), 3) as gross_wt,
        
        -- Casting Wt - WORKING COMPLEX LOGIC
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
        
        -- Finish Metal Wt from BOM.total_metal_weight
        ROUND(COALESCE(bom.total_metal_weight, 0), 3) as finish_metal_wt,
        
        -- Net Wt from BOM.metal_and_finding_weight
        ROUND(COALESCE(bom.metal_and_finding_weight, 0), 3) as net_wt,
        
        -- Finding Wt from BOM.finding_weight
        ROUND(COALESCE(bom.finding_weight, 0), 3) as finding_wt,
        
        -- Diamond Wt(cts) from BOM.total_diamond_weight
        ROUND(COALESCE(bom.total_diamond_weight, 0), 3) as diamond_wt_cts,
        
        -- Gemstone Wt(cts) from BOM.total_gemstone_weight
        ROUND(COALESCE(bom.total_gemstone_weight, 0), 3) as gemstone_wt_cts,
        
        -- Diamond Pcs from BOM.total_diamond_pcs
        COALESCE(bom.total_diamond_pcs, 0) as diamond_pcs,
        
        -- Gemstone Pcs from BOM.total_gemstone_pcs
        COALESCE(bom.total_gemstone_pcs, 0) as gemstone_pcs,
        
        -- Other Wt from BOM.other_weight
        ROUND(COALESCE(bom.other_weight, 0), 3) as other_wt,
        
        -- Product Size from BOM.product_size
        COALESCE(bom.product_size, '') as product_size,
        
        -- Chain Sub Category from BOM Finding Detail when finding_category = 'Chains'
        COALESCE((
            SELECT bfd.finding_type
            FROM `tabBOM Finding Detail` bfd
            WHERE bfd.parent = bom.name 
            AND bfd.finding_category = 'Chains'
            ORDER BY bfd.idx
            LIMIT 1
        ), '') as chain_sub_category,
        
        -- Setting Type from BOM.setting_type
        COALESCE(bom.setting_type, '') as setting_type,
        
        -- Diamond Grade from BOM Diamond Detail.diamond_grade
        COALESCE((
            SELECT bdd.diamond_grade
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = bom.name
            ORDER BY bdd.idx
            LIMIT 1
        ), '') as diamond_grade,
        
        -- Diamond Quality from BOM Diamond Detail.quality
        COALESCE((
            SELECT bdd.quality
            FROM `tabBOM Diamond Detail` bdd
            WHERE bdd.parent = bom.name
            ORDER BY bdd.idx
            LIMIT 1
        ), '') as diamond_quality
        
    FROM `tabSerial No` sn
    LEFT JOIN `tabItem` i ON sn.item_code = i.item_code
    LEFT JOIN `tabBOM` bom ON bom.item = sn.item_code AND bom.is_active = 1 AND bom.docstatus = 1
    {where_clause}
    ORDER BY sn.creation DESC
    LIMIT 1000
    """
    
    try:
        data = frappe.db.sql(query, filters, as_dict=True)
        
        # Additional duplicate removal as backup
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
def get_item_category_details(item_code):
    """Get item category and subcategory for item code - WITH SERIAL NO SUPPORT"""
    try:
        # Check if input is a serial number first
        serial_check = frappe.db.sql("""
        SELECT item_code FROM `tabSerial No` WHERE name = %s
        """, (item_code,), as_dict=True)
        
        if serial_check:
            # It's a serial number - use the item_code from it
            actual_item_code = serial_check[0].item_code
        else:
            # It's an item code - use directly
            actual_item_code = item_code
        
        # Get BOM for this item
        bom_check = frappe.db.sql("""
        SELECT name FROM `tabBOM` 
        WHERE item = %s AND is_active = 1 AND docstatus = 1
        ORDER BY creation DESC LIMIT 1
        """, (actual_item_code,), as_dict=True)
        
        if bom_check:
            bom_name = bom_check[0].name
            
            # Get category from BOM
            category_data = frappe.db.sql("""
            SELECT item_category, item_subcategory
            FROM `tabBOM` 
            WHERE name = %s
            """, (bom_name,), as_dict=True)
            
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
    """Get raw material details from BOM Item table - WITH ITEM IMAGE AND CATEGORIES"""
    
    try:
        # Step 1: Get serial number info
        serial_info = frappe.db.sql("""
        SELECT 
            sn.item_code, 
            sn.custom_bom_no, 
            sn.warehouse, 
            sn.status,
            i.item_name
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
                "item_subcategory": ""
            }
        
        serial_data = serial_info[0]
        item_code = serial_data.item_code
        bom_name = serial_data.custom_bom_no
        
        # Step 2: Get item image - PRIORITY: BOM first, then Item table
        item_image = ""
        item_category = ""
        item_subcategory = ""
        
        try:
            if bom_name:
                # Try to get image and categories from BOM first
                bom_data = frappe.db.sql("""
                SELECT image, item_category, item_subcategory
                FROM `tabBOM` 
                WHERE name = %s
                """, (bom_name,), as_dict=True)
                
                if bom_data and bom_data[0]:
                    bom_info = bom_data[0]
                    if bom_info.image:
                        item_image = bom_info.image
                    item_category = bom_info.item_category or ""
                    item_subcategory = bom_info.item_subcategory or ""
            
            # If no BOM image, try Item table
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
        
        # Step 3: If no BOM, find active BOM for item
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
                
                # Try to get image and categories from newly found BOM
                try:
                    bom_data = frappe.db.sql("""
                    SELECT image, item_category, item_subcategory
                    FROM `tabBOM` 
                    WHERE name = %s
                    """, (bom_name,), as_dict=True)
                    
                    if bom_data and bom_data[0]:
                        bom_info_data = bom_data[0]
                        if not item_image and bom_info_data.image:
                            item_image = bom_info_data.image
                        if not item_category:
                            item_category = bom_info_data.item_category or ""
                        if not item_subcategory:
                            item_subcategory = bom_info_data.item_subcategory or ""
                except:
                    pass
        
        if not bom_name:
            return {
                "raw_materials": [{"type": "Debug", "display": f"No BOM found for item {item_code}"}],
                "casting_info": {},
                "bom_name": "No BOM Found",
                "item_image": item_image,
                "item_category": item_category,
                "item_subcategory": item_subcategory
            }
        
        # Step 4: Get BOM items (SAME AS BEFORE)
        bom_items = frappe.db.sql("""
        SELECT 
            bi.item_code,
            bi.qty,
            bi.uom,
            bi.stock_uom,
            bi.description,
            i.item_name,
            i.item_group
        FROM `tabBOM Item` bi
        LEFT JOIN `tabItem` i ON bi.item_code = i.name
        WHERE bi.parent = %s
        ORDER BY bi.idx
        """, (bom_name,), as_dict=True)
        
        if not bom_items:
            return {
                "raw_materials": [{"type": "Debug", "display": f"BOM {bom_name} has no items"}],
                "casting_info": {},
                "bom_name": bom_name,
                "item_image": item_image,
                "item_category": item_category,
                "item_subcategory": item_subcategory
            }
        
        # Step 5: Process each item (SAME AS BEFORE)
        raw_materials = []
        for item in bom_items:
            # Parse description
            parsed = parse_description_enhanced(item.description or "")
            material_type = parsed.get("material_type", "Other")
            
            # Get proper pieces count from ALL BOM detail tables
            actual_pcs = get_material_pieces(bom_name, material_type, item.item_code, item.qty)
            
            # Create display based on type (SAME AS BEFORE)
            if material_type == "Metal":
                display = "{0}<br>Metal = {1}<br>Metal Touch = {2}<br>Metal Purity = {3}<br>Metal Color = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}".format(
                    item.item_code,
                    parsed.get("metal_type", "N/A"),
                    parsed.get("metal_touch", "N/A"),
                    parsed.get("metal_purity", "N/A"),
                    parsed.get("metal_colour", "N/A"),
                    item.qty or 0,
                    actual_pcs,
                    item.uom or item.stock_uom or 'Gram'
                )
            elif material_type == "Diamond":
                display = "{0}<br>Diamond Type = {1}<br>Stone Shape = {2}<br>Diamond Grade = {3}<br>Diamond Sieve Size = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}".format(
                    item.item_code,
                    parsed.get("diamond_type", "Natural"),
                    parsed.get("stone_shape", "Round"),
                    parsed.get("diamond_grade", "N/A"),
                    parsed.get("diamond_sieve_size", "N/A"),
                    item.qty or 0,
                    actual_pcs,
                    item.uom or item.stock_uom or 'Carat'
                )
            elif material_type == "Gemstone":
                display = "{0}<br>Gemstone Type = {1}<br>Stone Shape = {2}<br>Gemstone Grade = {3}<br>Cut = {4}<br>Cab = {5}<br>Gemstone Quality = {6}<br>Qty = {7:.3f}<br>Pcs = {8}<br>UOM = {9}".format(
                    item.item_code,
                    parsed.get("gemstone_type", "N/A"),
                    parsed.get("stone_shape", "N/A"),
                    parsed.get("gemstone_grade", "N/A"),
                    parsed.get("cut", "N/A"),
                    parsed.get("cab", "N/A"),
                    parsed.get("gemstone_quality", "N/A"),
                    item.qty or 0,
                    actual_pcs,
                    item.uom or item.stock_uom or 'Carat'
                )
            elif material_type == "Finding":
                display = "{0}<br>Finding Category = {1}<br>Finding Sub-Category = {2}<br>Metal = {3}<br>Metal Touch = {4}<br>Metal Purity = {5}<br>Metal Color = {6}<br>Size = {7}<br>Qty = {8:.3f}<br>Pcs = {9}<br>UOM = {10}".format(
                    item.item_code,
                    parsed.get("finding_category", "N/A"),
                    parsed.get("finding_sub_category", "N/A"),
                    parsed.get("metal_type", "N/A"),
                    parsed.get("metal_touch", "N/A"),
                    parsed.get("metal_purity", "N/A"),
                    parsed.get("metal_colour", "N/A"),
                    parsed.get("finding_size", "N/A"),
                    item.qty or 0,
                    actual_pcs,
                    item.uom or item.stock_uom or 'Gram'
                )
            else:
                display = "{0}<br>{1}<br>Qty = {2:.3f}<br>Pcs = {3}<br>UOM = {4}".format(
                    item.item_code,
                    item.item_name or 'Other Item',
                    item.qty or 0,
                    actual_pcs,
                    item.uom or item.stock_uom or 'Unit'
                )
            
            raw_materials.append({
                "type": material_type,
                "display": display
            })
        
        return {
            "raw_materials": raw_materials,
            "casting_info": {},
            "bom_name": bom_name,
            "item_image": item_image,
            "item_category": item_category,
            "item_subcategory": item_subcategory
        }
    
    except Exception as e:
        frappe.log_error("Raw Material Details Error", str(e))
        return {
            "raw_materials": [{"type": "Error", "display": f"Error: {str(e)}"}],
            "casting_info": {},
            "bom_name": "Error",
            "item_image": "",
            "item_category": "",
            "item_subcategory": ""
        }


def get_material_pieces(bom_name, material_type, item_code, qty):
    """Direct match by sieve size from BOM Detail tables"""
    
    try:
        if material_type == "Diamond":
            # Extract sieve size from item_code
            import re
            sieve_match = re.search(r'\+[\d\.]+-[\d\.]+', item_code)
            
            if sieve_match:
                sieve_size = sieve_match.group()
                
                # Find exact sieve size match in BOM Diamond Detail
                diamond_pcs = frappe.db.sql("""
                SELECT pcs 
                FROM `tabBOM Diamond Detail` 
                WHERE parent = %s 
                AND item_variant LIKE %s
                LIMIT 1
                """, (bom_name, f'%{sieve_size}%'), as_dict=True)
                
                if diamond_pcs and diamond_pcs[0].pcs:
                    return int(diamond_pcs[0].pcs)
            
            # If no sieve match found, return first available diamond pcs
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
            # Direct match for gemstone by item code
            gemstone_pcs = frappe.db.sql("""
            SELECT pcs 
            FROM `tabBOM Gemstone Detail` 
            WHERE parent = %s 
            AND (item_variant = %s OR item = %s)
            LIMIT 1
            """, (bom_name, item_code, item_code), as_dict=True)
            
            if gemstone_pcs and gemstone_pcs[0].pcs:
                return int(gemstone_pcs[0].pcs)
                
            # Fallback to first gemstone
            gemstone_fallback = frappe.db.sql("""
            SELECT pcs FROM `tabBOM Gemstone Detail` 
            WHERE parent = %s ORDER BY idx LIMIT 1
            """, (bom_name,), as_dict=True)
            
            return int(gemstone_fallback[0].pcs) if gemstone_fallback and gemstone_fallback[0].pcs else 1
            
        elif material_type == "Metal":
            # Direct match for metal by item code
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
            # Direct match for finding by item code
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
    
    # Determine material type
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
    
    # Enhanced extraction patterns
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
