# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import getdate, today, flt


def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    return [
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 120},
        {"fieldname": "creation_date", "label": _("Creation Date & Time"), "fieldtype": "Datetime", "width": 150},
        {"fieldname": "serial_no", "label": _("Serial No"), "fieldtype": "Link", "options": "Serial No", "width": 120},
        {"fieldname": "view_details", "label": _("View"), "fieldtype": "HTML", "width": 80},
        {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 100},
        {"fieldname": "item_subcategory", "label": _("Sub Category"), "fieldtype": "Data", "width": 100},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 120},
        {"fieldname": "order_type", "label": _("Order Type"), "fieldtype": "Data", "width": 100},
        {"fieldname": "customer_po_no", "label": _("Customer PO No."), "fieldtype": "Data", "width": 120},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 120},
        {"fieldname": "manufacturer", "label": _("Manufacturer"), "fieldtype": "Link", "options": "Manufacturer", "width": 120},
        {"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 100},
        {"fieldname": "finding_touch", "label": _("Finding Touch"), "fieldtype": "Data", "width": 100},
        # REORDERED WEIGHT COLUMNS TO MATCH SCREENSHOT
        {"fieldname": "gross_wt", "label": _("Gross Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "metal_wt", "label": _("Metal Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "finding_wt", "label": _("Finding Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "net_wt", "label": _("Net Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "pure_wt", "label": _("Pure Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "alloy_wt", "label": _("Alloy Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "diamond_wt", "label": _("Diamond Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "diamond_pcs", "label": _("Diamond Pcs"), "fieldtype": "Data", "width": 100},
        {"fieldname": "gemstone_wt", "label": _("Gemstone Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "gemstone_pcs", "label": _("Gemstone Pcs"), "fieldtype": "Data", "width": 100},
        {"fieldname": "other_wt", "label": _("Other Wt"), "fieldtype": "Data", "width": 100},
        {"fieldname": "parent_manufacturing_order", "label": _("Parent Manufacturing Order"), "fieldtype": "Link", "options": "Parent Manufacturing Order", "width": 150},
        {"fieldname": "serial_no_status", "label": _("Serial No. Status"), "fieldtype": "Data", "width": 120}
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    
    # STEP 1: Get all serial numbers first - WITH SAMPLE AND CONSUMABLE EXCLUSION
    base_query = """
    SELECT 
        sn.item_code,
        sn.creation as creation_date,
        sn.name as serial_no,
        COALESCE(item.item_group, '') as category,
        COALESCE(sn.customer, '') as customer,
        COALESCE(sn.warehouse, '') as warehouse,
        COALESCE(sn.status, 'Active') as serial_no_status,
        sn.custom_bom_no
    FROM `tabSerial No` sn
    LEFT JOIN `tabItem` item ON item.name = sn.item_code
    WHERE sn.item_code NOT LIKE %s
    AND (item.item_group IS NULL OR LOWER(item.item_group) NOT LIKE %s)
    AND (item.item_group IS NULL OR LOWER(item.item_group) NOT LIKE %s)
    """
    
    # Prepare base parameters - ADDED SAMPLE AND CONSUMABLE EXCLUSION
    base_params = ['SN%', '%sample%', '%consumable%']
    
    # Add user conditions if they exist
    if conditions:
        base_query = base_query + " AND " + conditions
        # Add filter parameters in the same order as conditions
        if filters.get("from_date"):
            base_params.append(filters["from_date"])
        if filters.get("to_date"):
            base_params.append(filters["to_date"])
    
    # Add ordering and limit
    final_query = base_query + " ORDER BY sn.creation DESC LIMIT 1000"
    
    try:
        # Get basic serial data first
        data = frappe.db.sql(final_query, base_params, as_dict=True)
        
        # STEP 2: Apply filters at data level and enhance each record
        final_data = []
        
        for row in data:
            serial_no_val = row.get('serial_no', '')
            custom_bom_no = row.get('custom_bom_no', '')
            
            # Get PMO data first
            pmo_data = None
            if custom_bom_no:
                pmo_data = get_correct_bom_snc_pmo_data(serial_no_val, custom_bom_no)
            
            # Get manufacturer and company from SNC
            manufacturer = ''
            company_from_snc = ''
            if pmo_data:
                manufacturer = get_manufacturer_from_snc(serial_no_val, pmo_data.get('parent_manufacturing_order', ''))
                company_from_snc = get_company_from_snc(serial_no_val, pmo_data.get('parent_manufacturing_order', ''))
            
            # Apply filters at data level
            # Manufacturer filter (multi-select support)
            if filters.get("manufacturer"):
                manufacturer_list = filters.get("manufacturer")
                if isinstance(manufacturer_list, str):
                    # Convert string to list if single value
                    manufacturer_list = [manufacturer_list]
                elif isinstance(manufacturer_list, list):
                    # It's already a list
                    pass
                else:
                    manufacturer_list = []
                
                if manufacturer_list and manufacturer not in manufacturer_list:
                    continue  # Skip this row
            
            # Company filter (from SNC)
            if filters.get("company"):
                if company_from_snc != filters.get("company"):
                    continue  # Skip this row
            
            # Order type filter
            order_type = ''
            if pmo_data:
                order_type = pmo_data.get('order_type', '')
            
            if filters.get("order_type"):
                if order_type != filters.get("order_type"):
                    continue  # Skip this row
            
            # Set manufacturer in row
            row['manufacturer'] = manufacturer
            
            # BOM CHECK: Only process production details if BOM exists
            if custom_bom_no:  # Has BOM - Get full production details
                # Get BOM data with multi-purity support
                bom_data = get_serial_specific_bom_data(serial_no_val, custom_bom_no)
                if bom_data:
                    # Get basic weights from BOM
                    gross_wt = flt(bom_data.get('gross_weight', 0))
                    diamond_wt = flt(bom_data.get('total_diamond_weight', 0))
                    diamond_pcs = int(bom_data.get('total_diamond_pcs', 0))
                    gemstone_wt = flt(bom_data.get('total_gemstone_weight', 0))
                    gemstone_pcs = int(bom_data.get('total_gemstone_pcs', 0))
                    other_wt = flt(bom_data.get('other_weight', 0))
                    
                    # MULTI-PURITY METAL CALCULATION
                    metal_details = bom_data.get('metal_details', [])
                    metal_touch_display, metal_wt, metal_pure_wt = calculate_multi_purity_weights(metal_details)
                    
                    # MULTI-PURITY FINDING CALCULATION
                    finding_details = bom_data.get('finding_details', [])
                    finding_touch_display, finding_wt, finding_pure_wt = calculate_multi_purity_weights(finding_details)
                    
                    # Calculate Net Wt = Metal Wt + Finding Wt
                    net_wt = metal_wt + finding_wt
                    
                    # Total Pure Wt = Metal Pure Wt + Finding Pure Wt
                    total_pure_wt = metal_pure_wt + finding_pure_wt
                    
                    # Total Alloy Wt = Net Wt - Total Pure Wt
                    total_alloy_wt = net_wt - total_pure_wt if net_wt > 0 else 0
                    
                    row.update({
                        'gross_wt': format_weight_display(gross_wt),
                        'diamond_wt': format_weight_display(diamond_wt),
                        'diamond_pcs': str(diamond_pcs) if diamond_pcs > 0 else '',
                        'gemstone_wt': format_weight_display(gemstone_wt),
                        'gemstone_pcs': str(gemstone_pcs) if gemstone_pcs > 0 else '',
                        'other_wt': format_weight_display(other_wt),
                        'metal_wt': format_weight_display(metal_wt),
                        'finding_wt': format_weight_display(finding_wt),
                        'net_wt': format_weight_display(net_wt),
                        'pure_wt': format_weight_display(total_pure_wt),
                        'alloy_wt': format_weight_display(total_alloy_wt),
                        'metal_touch': metal_touch_display,
                        'finding_touch': finding_touch_display,
                        'category': bom_data.get('item_category', row.get('category', '')),
                        'item_subcategory': bom_data.get('item_subcategory', '')
                    })
                else:
                    # BOM exists but no data found - set to blank
                    row.update({
                        'gross_wt': '', 'diamond_wt': '', 'diamond_pcs': '',
                        'gemstone_wt': '', 'gemstone_pcs': '', 'other_wt': '',
                        'metal_wt': '', 'finding_wt': '', 'net_wt': '',
                        'metal_touch': '', 'finding_touch': '', 'pure_wt': '', 'alloy_wt': '',
                        'item_subcategory': ''
                    })
                
                # Update PMO data for BOM-linked serials
                if pmo_data:
                    row.update({
                        'customer': row.get('customer') or pmo_data.get('customer', ''),
                        'order_type': pmo_data.get('order_type', ''),
                        'customer_po_no': pmo_data.get('customer_po_no', ''),
                        'parent_manufacturing_order': pmo_data.get('parent_manufacturing_order', '')
                    })
                else:
                    row.update({
                        'order_type': '', 'customer_po_no': '', 'parent_manufacturing_order': ''
                    })
            
            else:  # No BOM - Set all production fields to blank
                row.update({
                    'gross_wt': '', 'diamond_wt': '', 'diamond_pcs': '',
                    'gemstone_wt': '', 'gemstone_pcs': '', 'other_wt': '',
                    'metal_wt': '', 'finding_wt': '', 'net_wt': '',
                    'metal_touch': '', 'finding_touch': '', 'pure_wt': '', 'alloy_wt': '',
                    'order_type': '', 'customer_po_no': '', 'parent_manufacturing_order': '',
                    'item_subcategory': ''
                })
            
            # Add this row to final data
            final_data.append(row)
        
        # Add View Details button to all final rows
        for row in final_data:
            # Add View Details button - SIMPLE WHITE BUTTON
            view_button_html = (
                '<button class="btn btn-sm" style="background: white; '
                'border: 1px solid #d1d8dd; color: #333; padding: 4px 12px; font-size: 12px; '
                'border-radius: 4px; cursor: pointer; transition: all 0.2s ease;" '
                'onmouseover="this.style.backgroundColor=\'#f8f9fa\'; this.style.borderColor=\'#adb5bd\';" '
                'onmouseout="this.style.backgroundColor=\'white\'; this.style.borderColor=\'#d1d8dd\';" '
                'onclick="show_serial_details(\'{0}\')">View</button>'.format(row["serial_no"])
            )
            row['view_details'] = view_button_html
        
        return final_data
        
    except Exception as e:
        frappe.throw(_("Error fetching data: {0}").format(str(e)))
        return []


def get_multi_purity_metal_data(bom_name):
    """Get metal details grouped by purity from BOM Metal Detail"""
    try:
        metal_query = """
        SELECT 
            bmd.metal_touch,
            SUM(bmd.quantity) as total_weight
        FROM `tabBOM Metal Detail` bmd
        WHERE bmd.parent = %s
        GROUP BY bmd.metal_touch
        ORDER BY bmd.metal_touch
        """
        
        result = frappe.db.sql(metal_query, (bom_name,), as_dict=True)
        return result if result else []
        
    except Exception as e:
        return []


def get_multi_purity_finding_data(bom_name):
    """Get finding details grouped by purity from BOM Finding Detail"""
    try:
        finding_query = """
        SELECT 
            bfd.metal_touch,
            SUM(bfd.quantity) as total_weight
        FROM `tabBOM Finding Detail` bfd
        WHERE bfd.parent = %s
        GROUP BY bfd.metal_touch
        ORDER BY bfd.metal_touch
        """
        
        result = frappe.db.sql(finding_query, (bom_name,), as_dict=True)
        return result if result else []
        
    except Exception as e:
        return []


def calculate_multi_purity_weights(purity_details):
    """Calculate total weight and touch display for multi-purity materials"""
    if not purity_details:
        return '', 0, 0
    
    # If only one purity, use simple display
    if len(purity_details) == 1:
        detail = purity_details[0]
        touch = detail.get('metal_touch', '')
        weight = flt(detail.get('total_weight', 0))
        touch_percent = convert_metal_touch_to_percent(touch)
        pure_weight = (weight * touch_percent) / 100 if touch_percent > 0 else 0
        return touch, weight, pure_weight
    
    # Multiple purities - create comma-separated display
    touch_list = []
    total_weight = 0
    total_pure_weight = 0
    
    for detail in purity_details:
        touch = detail.get('metal_touch', '')
        weight = flt(detail.get('total_weight', 0))
        
        if touch and touch not in touch_list:
            touch_list.append(touch)
        
        total_weight += weight
        
        # Calculate pure weight for this purity
        touch_percent = convert_metal_touch_to_percent(touch)
        if touch_percent > 0:
            pure_weight = (weight * touch_percent) / 100
            total_pure_weight += pure_weight
    
    # Create comma-separated touch display
    touch_display = ','.join(sorted(set(touch_list))) if touch_list else ''
    
    return touch_display, total_weight, total_pure_weight


def get_manufacturer_from_snc(serial_no, parent_manufacturing_order):
    """Get manufacturer from Serial Number Creator table"""
    try:
        # Method 1: Direct serial number match in Serial Number Creator
        snc_query = """
        SELECT COALESCE(snc.manufacturer, '') as manufacturer
        FROM `tabSerial Number Creator` snc
        WHERE snc.serial_no = %s
        LIMIT 1
        """
        
        result = frappe.db.sql(snc_query, (serial_no,), as_dict=True)
        if result and result[0].get('manufacturer'):
            return result[0]['manufacturer']
        
        # Method 2: Try via parent manufacturing order if available
        if parent_manufacturing_order:
            pmo_snc_query = """
            SELECT COALESCE(snc.manufacturer, '') as manufacturer
            FROM `tabSerial Number Creator` snc
            WHERE snc.parent_manufacturing_order = %s
            LIMIT 1
            """
            
            result = frappe.db.sql(pmo_snc_query, (parent_manufacturing_order,), as_dict=True)
            if result and result[0].get('manufacturer'):
                return result[0]['manufacturer']
        
        return ''
        
    except Exception as e:
        return ''


def get_company_from_snc(serial_no, parent_manufacturing_order):
    """Get company from Serial Number Creator table"""
    try:
        # Method 1: Direct serial number match in Serial Number Creator
        snc_query = """
        SELECT COALESCE(snc.company, '') as company
        FROM `tabSerial Number Creator` snc
        WHERE snc.serial_no = %s
        LIMIT 1
        """
        
        result = frappe.db.sql(snc_query, (serial_no,), as_dict=True)
        if result and result[0].get('company'):
            return result[0]['company']
        
        # Method 2: Try via parent manufacturing order if available
        if parent_manufacturing_order:
            pmo_snc_query = """
            SELECT COALESCE(snc.company, '') as company
            FROM `tabSerial Number Creator` snc
            WHERE snc.parent_manufacturing_order = %s
            LIMIT 1
            """
            
            result = frappe.db.sql(pmo_snc_query, (parent_manufacturing_order,), as_dict=True)
            if result and result[0].get('company'):
                return result[0]['company']
        
        return ''
        
    except Exception as e:
        return ''


def format_weight_display(weight_val):
    """Format weight values - show blank if 0, otherwise show formatted value"""
    if weight_val is None or flt(weight_val) == 0:
        return ''
    else:
        return '{:.3f}'.format(round(flt(weight_val), 3))


def get_serial_specific_bom_data(serial_no, custom_bom_no):
    """Get BOM data specific to the serial number - ENHANCED WITH MULTI-PURITY SUPPORT"""
    try:
        # Method 1: Use custom_bom_no if available
        if custom_bom_no:
            bom_query = """
            SELECT 
                bom.gross_weight,
                bom.total_diamond_weight,
                bom.total_diamond_pcs,
                bom.total_gemstone_weight,
                bom.total_gemstone_pcs,
                bom.other_weight,
                bom.total_metal_weight,
                bom.metal_weight,
                bom.finding_weight,
                bom.finding_weight_,
                bom.total_finding_weight_per_gram,
                bom.metal_touch,
                bom.finding_metal_touch,
                bom.item_category,
                bom.item_subcategory,
                bom.setting_type
            FROM `tabBOM` bom
            WHERE bom.name = %s
            LIMIT 1
            """
            
            result = frappe.db.sql(bom_query, (custom_bom_no,), as_dict=True)
            
            if result and result[0]:
                bom_data = result[0]
                
                # Get multi-purity metal details
                metal_details = get_multi_purity_metal_data(custom_bom_no)
                bom_data['metal_details'] = metal_details
                
                # Get multi-purity finding details
                finding_details = get_multi_purity_finding_data(custom_bom_no)
                bom_data['finding_details'] = finding_details
                
                return bom_data
        else:
            # Method 2: Find active BOM for item
            item_query = """
            SELECT sn.item_code
            FROM `tabSerial No` sn
            WHERE sn.name = %s
            """
            
            item_result = frappe.db.sql(item_query, (serial_no,), as_dict=True)
            if not item_result:
                return None
            
            item_code = item_result[0]['item_code']
            
            # Find active BOM and then call recursively with BOM name
            bom_query = """
            SELECT name
            FROM `tabBOM` bom
            WHERE bom.item = %s AND bom.is_active = 1
            ORDER BY bom.creation DESC
            LIMIT 1
            """
            
            bom_result = frappe.db.sql(bom_query, (item_code,), as_dict=True)
            if bom_result:
                return get_serial_specific_bom_data(serial_no, bom_result[0]['name'])
        
        return None
        
    except Exception as e:
        return None


def get_correct_bom_snc_pmo_data(serial_no, custom_bom_no):
    """Get PMO data via correct BOM-SNC join - FIXED using your working query"""
    try:
        # Method 1: Direct serial number match in Serial Number Creator
        direct_snc_query = """
        SELECT 
            pmo.name as parent_manufacturing_order,
            pmo.customer,
            COALESCE(pmo.po_no, pmo.child_po, ord.po_no) as customer_po_no,
            COALESCE(pmo.order_type, ord.order_type, snc.order_type) as order_type
        FROM `tabSerial Number Creator` snc
        LEFT JOIN `tabParent Manufacturing Order` pmo ON snc.parent_manufacturing_order = pmo.name
        LEFT JOIN `tabOrder` ord ON pmo.order_form_id = ord.name
        WHERE snc.serial_no = %s
        LIMIT 1
        """
        
        result = frappe.db.sql(direct_snc_query, (serial_no,), as_dict=True)
        if result and result[0] and result[0].get('parent_manufacturing_order'):
            return result[0]
        
        # Method 2: BOM-SNC join using your correct logic - FIXED
        if custom_bom_no:
            correct_bom_snc_query = """
            SELECT 
                snc.parent_manufacturing_order,
                pmo.customer,
                COALESCE(pmo.po_no, pmo.child_po, ord.po_no, snc.po_no) as customer_po_no,
                COALESCE(pmo.order_type, ord.order_type, snc.order_type) as order_type
            FROM `tabBOM` bom
            LEFT JOIN `tabSerial Number Creator` snc ON bom.custom_serial_number_creator = snc.name
            LEFT JOIN `tabParent Manufacturing Order` pmo ON snc.parent_manufacturing_order = pmo.name
            LEFT JOIN `tabOrder` ord ON pmo.order_form_id = ord.name
            WHERE bom.name = %s
            LIMIT 1
            """
            
            result = frappe.db.sql(correct_bom_snc_query, (custom_bom_no,), as_dict=True)
            if result and result[0] and result[0].get('parent_manufacturing_order'):
                return result[0]
        
        # Method 3: Direct PMO with exact serial number match
        direct_pmo_query = """
        SELECT 
            pmo.name as parent_manufacturing_order,
            pmo.customer,
            COALESCE(pmo.po_no, pmo.child_po, ord.po_no) as customer_po_no,
            COALESCE(pmo.order_type, ord.order_type) as order_type
        FROM `tabParent Manufacturing Order` pmo
        LEFT JOIN `tabOrder` ord ON pmo.order_form_id = ord.name
        WHERE pmo.serial_no = %s
        LIMIT 1
        """
        
        result = frappe.db.sql(direct_pmo_query, (serial_no,), as_dict=True)
        if result and result[0]:
            return result[0]
        
        # Method 4: Try Sales Invoice for exact serial number (delivered items)
        sales_query = """
        SELECT 
            si.customer,
            si.po_no as customer_po_no,
            %s as order_type,
            %s as parent_manufacturing_order
        FROM `tabSales Invoice Item` sii
        LEFT JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE sii.serial_no = %s AND si.docstatus = 1
        ORDER BY si.creation DESC
        LIMIT 1
        """
        
        result = frappe.db.sql(sales_query, ('Sales', '', serial_no), as_dict=True)
        if result and result[0] and result[0].get('customer'):
            return result[0]
        
        return None
        
    except Exception as e:
        return None


@frappe.whitelist()
def get_serial_drill_down_details(serial_no):
    """Get detailed drill-down information for serial number"""
    try:
        # Enhanced detail query with BOM info
        detail_query = """
        SELECT 
            sn.name as serial_no,
            sn.item_code,
            sn.custom_bom_no,
            COALESCE(sn.customer, '') as customer,
            COALESCE(item.item_group, '') as category,
            COALESCE(item.image, '') as product_image
        FROM `tabSerial No` sn
        LEFT JOIN `tabItem` item ON item.name = sn.item_code
        WHERE sn.name = %s
        LIMIT 1
        """
        
        detail_result = frappe.db.sql(detail_query, (serial_no,), as_dict=True)
        
        if not detail_result:
            return {
                "serial_no": serial_no,
                "item_code": "Not Found",
                "customer": "",
                "category": "",
                "sub_category": "",
                "setting_type": "",
                "customer_po_no": "",
                "raw_materials": [{"type": "Debug", "display": "Serial number {} not found".format(serial_no)}],
                "product_image": "",
                "bom_name": "Serial Not Found"
            }
        
        details = detail_result[0]
        custom_bom_no = details.get('custom_bom_no', '')
        
        # Get subcategory and setting type from BOM
        if custom_bom_no:
            # Get BOM data for subcategory and setting type
            bom_data = get_serial_specific_bom_data(serial_no, custom_bom_no)
            if bom_data:
                # Use item_category from BOM instead of item_group
                details['category'] = bom_data.get('item_category', details.get('category', ''))
                details['sub_category'] = bom_data.get('item_subcategory', '')
                details['setting_type'] = bom_data.get('setting_type', '')
            else:
                details['sub_category'] = ''
                details['setting_type'] = ''
            
            # Get enhanced PMO data for BOM-linked serials
            pmo_data = get_correct_bom_snc_pmo_data(serial_no, custom_bom_no)
            if pmo_data:
                details['customer'] = details.get('customer') or pmo_data.get('customer', '')
                details['customer_po_no'] = pmo_data.get('customer_po_no', '')
            else:
                details['customer_po_no'] = ''
        else:
            # No BOM - set fields to blank
            details['sub_category'] = ''
            details['setting_type'] = ''
            details['customer_po_no'] = ''
        
        # Get raw material details
        raw_material_data = get_raw_material_details(serial_no, details['item_code'])
        details['raw_materials'] = raw_material_data.get('raw_materials', [])
        details['bom_name'] = raw_material_data.get('bom_name', 'No BOM Found')
        
        return details
        
    except Exception as e:
        return {
            "serial_no": serial_no,
            "item_code": "Error",
            "customer": "",
            "category": "",
            "sub_category": "",
            "setting_type": "",
            "customer_po_no": "",
            "raw_materials": [{"type": "Error", "display": "Error: {}".format(str(e))}],
            "product_image": "",
            "bom_name": "Error"
        }


@frappe.whitelist()
def get_raw_material_details(serial_no, item_code=None):
    """Get raw material details from BOM Detail tables"""
    
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
                "raw_materials": [{"type": "Debug", "display": "Serial number {} not found".format(serial_no)}],
                "casting_info": {},
                "bom_name": "Serial Not Found",
                "item_image": ""
            }
        
        serial_data = serial_info[0]
        item_code = serial_data.item_code
        bom_name = serial_data.custom_bom_no
        
        # Step 2: Get item image (placeholder for now)
        item_image = ""
        
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
        
        if not bom_name:
            return {
                "raw_materials": [{"type": "Debug", "display": "No BOM found for item {}".format(item_code)}],
                "casting_info": {},
                "bom_name": "No BOM Found",
                "item_image": item_image
            }
        
        # Step 4: Get ALL raw materials from DETAIL TABLES
        raw_materials = []
        
        # 4.1: Get Metal Details
        metal_details = frappe.db.sql("""
        SELECT 
            bmd.item,
            bmd.item_variant,
            bmd.metal_type,
            bmd.metal_touch,
            bmd.metal_purity,
            bmd.metal_colour,
            bmd.quantity,
            bmd.stock_uom,
            'Metal' as material_type,
            bmd.idx
        FROM `tabBOM Metal Detail` bmd
        WHERE bmd.parent = %s
        ORDER BY bmd.idx
        """, (bom_name,), as_dict=True)
        
        for metal in metal_details:
            display = "{0}<br>Metal = {1}<br>Metal Touch = {2}<br>Metal Purity = {3}<br>Metal Color = {4}<br>Qty = {5:.3f}<br>Pcs = 1<br>UOM = {6}".format(
                metal.get('item_variant') or metal.get('item', ''),
                metal.get('metal_type', 'N/A'),
                metal.get('metal_touch', 'N/A'),
                metal.get('metal_purity', 'N/A'),
                metal.get('metal_colour', 'N/A'),
                flt(metal.get('quantity', 0)),
                metal.get('stock_uom', 'Gram')
            )
            raw_materials.append({
                "type": "Metal",
                "display": display
            })
        
        # 4.2: Get Finding Details
        finding_details = frappe.db.sql("""
        SELECT 
            bfd.item,
            bfd.item_variant,
            bfd.finding_category,
            bfd.finding_type as finding_sub_category,
            bfd.metal_type,
            bfd.metal_touch,
            bfd.metal_purity,
            bfd.metal_colour,
            bfd.finding_size,
            bfd.quantity,
            bfd.stock_uom,
            'Finding' as material_type,
            bfd.idx
        FROM `tabBOM Finding Detail` bfd
        WHERE bfd.parent = %s
        ORDER BY bfd.idx
        """, (bom_name,), as_dict=True)
        
        for finding in finding_details:
            display = "{0}<br>Finding Category = {1}<br>Finding Sub-Category = {2}<br>Metal = {3}<br>Metal Touch = {4}<br>Metal Purity = {5}<br>Metal Color = {6}<br>Size = {7}<br>Qty = {8:.3f}<br>Pcs = 1<br>UOM = {9}".format(
                finding.get('item_variant') or finding.get('item', ''),
                finding.get('finding_category', 'N/A'),
                finding.get('finding_sub_category', 'N/A'),
                finding.get('metal_type', 'N/A'),
                finding.get('metal_touch', 'N/A'),
                finding.get('metal_purity', 'N/A'),
                finding.get('metal_colour', 'N/A'),
                finding.get('finding_size', 'N/A'),
                flt(finding.get('quantity', 0)),
                finding.get('stock_uom', 'Gram')
            )
            raw_materials.append({
                "type": "Finding",
                "display": display
            })
        
        # 4.3: Get Diamond Details
        diamond_details = frappe.db.sql("""
        SELECT 
            bdd.item,
            bdd.item_variant,
            bdd.diamond_type,
            bdd.stone_shape,
            bdd.diamond_grade,
            bdd.diamond_sieve_size,
            bdd.pcs,
            bdd.quantity,
            bdd.stock_uom,
            'Diamond' as material_type,
            bdd.idx
        FROM `tabBOM Diamond Detail` bdd
        WHERE bdd.parent = %s
        ORDER BY bdd.idx
        """, (bom_name,), as_dict=True)
        
        for diamond in diamond_details:
            display = "{0}<br>Diamond Type = {1}<br>Stone Shape = {2}<br>Diamond Grade = {3}<br>Diamond Sieve Size = {4}<br>Qty = {5:.3f}<br>Pcs = {6}<br>UOM = {7}".format(
                diamond.get('item_variant') or diamond.get('item', ''),
                diamond.get('diamond_type', 'Natural'),
                diamond.get('stone_shape', 'Round'),
                diamond.get('diamond_grade', 'N/A'),
                diamond.get('diamond_sieve_size', 'N/A'),
                flt(diamond.get('quantity', 0)),
                int(diamond.get('pcs', 1)),
                diamond.get('stock_uom', 'Carat')
            )
            raw_materials.append({
                "type": "Diamond",
                "display": display
            })
        
        # 4.4: Get Gemstone Details
        gemstone_details = frappe.db.sql("""
        SELECT 
            bgd.item,
            bgd.item_variant,
            bgd.gemstone_type,
            bgd.stone_shape,
            bgd.gemstone_grade,
            bgd.gemstone_quality,
            bgd.gemstone_size,
            bgd.cut_or_cab as cut,
            bgd.pcs,
            bgd.quantity,
            bgd.stock_uom,
            'Gemstone' as material_type,
            bgd.idx
        FROM `tabBOM Gemstone Detail` bgd
        WHERE bgd.parent = %s
        ORDER BY bgd.idx
        """, (bom_name,), as_dict=True)
        
        for gemstone in gemstone_details:
            display = "{0}<br>Gemstone Type = {1}<br>Stone Shape = {2}<br>Gemstone Grade = {3}<br>Gemstone Size = {4}<br>Cut = {5}<br>Gemstone Quality = {6}<br>Qty = {7:.3f}<br>Pcs = {8}<br>UOM = {9}".format(
                gemstone.get('item_variant') or gemstone.get('item', ''),
                gemstone.get('gemstone_type', 'N/A'),
                gemstone.get('stone_shape', 'N/A'),
                gemstone.get('gemstone_grade', 'N/A'),
                gemstone.get('gemstone_size', 'N/A'),
                gemstone.get('cut', 'N/A'),
                gemstone.get('gemstone_quality', 'N/A'),
                flt(gemstone.get('quantity', 0)),
                int(gemstone.get('pcs', 1)),
                gemstone.get('stock_uom', 'Carat')
            )
            raw_materials.append({
                "type": "Gemstone",
                "display": display
            })
        
        # 4.5: Get Other Details
        other_details = frappe.db.sql("""
        SELECT 
            bod.item_code,
            bod.qty,
            bod.uom,
            'Other' as material_type,
            bod.idx
        FROM `tabBOM Other Detail` bod
        WHERE bod.parent = %s
        ORDER BY bod.idx
        """, (bom_name,), as_dict=True)
        
        for other in other_details:
            display = "{0}<br>Other Item<br>Qty = {1:.3f}<br>Pcs = 1<br>UOM = {2}".format(
                other.get('item_code', ''),
                flt(other.get('qty', 0)),
                other.get('uom', 'Unit')
            )
            raw_materials.append({
                "type": "Other",
                "display": display
            })
        
        return {
            "raw_materials": raw_materials,
            "casting_info": {},
            "bom_name": bom_name,
            "item_image": item_image
        }
    
    except Exception as e:
        return {
            "raw_materials": [{"type": "Error", "display": "Error: {}".format(str(e))}],
            "casting_info": {},
            "bom_name": "Error",
            "item_image": ""
        }


def convert_metal_touch_to_percent(metal_touch):
    """Convert metal touch values like 10KT, 14KT, 18KT, 22KT to percentage"""
    if not metal_touch:
        return 0
    
    # Define KT to percentage conversion
    kt_to_percent = {
        '10KT': 41.7,
        '14KT': 58.6,
        '18KT': 75.4,
        '20KT': 83.3,
        '22KT': 91.9
    }
    
    metal_touch_str = str(metal_touch).upper().strip()
    
    # Check if it's a KT value
    if metal_touch_str in kt_to_percent:
        return kt_to_percent[metal_touch_str]
    
    # Check if it's already a numeric percentage
    try:
        numeric_val = flt(metal_touch_str)
        if 0 < numeric_val <= 100:
            return numeric_val
        elif numeric_val > 100:
            # Might be purity value, convert to percentage
            return numeric_val / 10 if numeric_val < 1000 else numeric_val / 1000 * 100
    except:
        pass
    
    return 0


def get_conditions(filters):
    conditions = []
    
    # Remove company filter from SQL level since we're getting it from SNC
    
    if filters.get("from_date"):
        conditions.append("DATE(sn.creation) >= %s")
    
    if filters.get("to_date"):
        conditions.append("DATE(sn.creation) <= %s")
    
    return " AND ".join(conditions) if conditions else ""
