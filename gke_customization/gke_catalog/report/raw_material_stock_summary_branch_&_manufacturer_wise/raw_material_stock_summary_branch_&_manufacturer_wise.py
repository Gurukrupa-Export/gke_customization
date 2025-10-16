# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
    # Handle empty filters gracefully
    if not filters:
        filters = {}
    
    # Set defaults
    if not filters.get("company"):
        filters["company"] = frappe.defaults.get_user_default("Company") or "Gurukrupa Export Private Limited"
    
    if filters.get("company") != "KG GK Jewellers Private Limited" and not filters.get("branch"):
        filters["branch"] = "GEPL-ST-0002"
    
    return get_raw_material_stock_summary_branch_manufacturer_wise(filters)

def get_raw_material_stock_summary_branch_manufacturer_wise(filters=None):
    columns = [
        {"fieldname": "section_name", "label": "Department", "fieldtype": "Data", "width": 400},
        {"fieldname": "metal", "label": "Metal", "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "diamond", "label": "Diamond", "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "gemstone", "label": "Gemstone", "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "finding", "label": "Finding", "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "others", "label": "Others", "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "view_details", "label": "View Details", "fieldtype": "Data", "width": 120}
    ]
    
    departments = get_departments_list(filters)
    if not departments: 
        return columns, []
    
    data, summary_data = [], {"total_metal": 0.0, "total_diamond": 0.0, "total_gemstone": 0.0, "total_finding": 0.0, "total_others": 0.0}
    
    for dept_info in departments:
        dept_name, dept_with_suffix = dept_info['department'], dept_info['db_department']
        stock_values = get_department_stock_values_by_material(dept_with_suffix, filters.get("company", ""), filters.get("branch", ""), filters.get("manufacturer"))
        section_data = build_department_section_with_materials(dept_name, stock_values)
        data.extend(section_data)
        add_department_total_row_with_materials(data, section_data, f"{dept_name} Total", summary_data)
    
    add_grand_total_row_with_materials(data, summary_data)
    return columns, data

def get_departments_list(filters):
    company, branch, manufacturer, department = filters.get("company"), filters.get("branch", ""), filters.get("manufacturer"), filters.get("department")
    
    # FIXED: Added Computer Aided Designing to excluded departments
    excluded_departments = ['Canteen', 'HR', 'Admin', 'Security', 'Housekeeping', 'IT', 'Transport', 'Maintenance', 'Computer Aided Designing']
    excluded_condition = " AND " + " AND ".join([f"mop.department NOT LIKE '%{dept}%'" for dept in excluded_departments])
    
    # Better manufacturer filtering - filter departments by manufacturer mapping
    manufacturer_dept_condition = ""
    if manufacturer:
        allowed_departments = get_manufacturer_departments(manufacturer, company)
        if allowed_departments:
            dept_filter = "', '".join(allowed_departments)
            manufacturer_dept_condition = f" AND mop.department IN ('{dept_filter}')"
    
    dept_query = f"""SELECT DISTINCT REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') as department, mop.department as db_department
        FROM `tabManufacturing Operation` mop LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
        WHERE mwo.company = '{company}' AND mwo.docstatus = 1 AND mop.department IS NOT NULL AND mop.department != '' {excluded_condition}{manufacturer_dept_condition}"""
    
    if branch: dept_query += f" AND mwo.branch = '{branch}'"
    if department: dept_query += f" AND mop.department LIKE '%{department}%'"
    dept_query += " ORDER BY mop.department LIMIT 20"
    
    try: 
        return frappe.db.sql(dept_query, as_dict=True)
    except Exception as e: 
        frappe.log_error(f"Department query error: {str(e)}")
        return []

def build_department_section_with_materials(dept_name, stock_values):
    section_data = [{
        "section_name": f"'{dept_name}'", 
        "parent_section": None, 
        "indent": 0.0, 
        "section": dept_name, 
        "metal": "", 
        "diamond": "", 
        "gemstone": "", 
        "finding": "", 
        "others": "", 
        "view_details": "", 
        "is_department_header": True
    }]
    
    stock_types = [
        {"key": "work_order_stock", "label": "Work Order Stock"}, 
        {"key": "employee_wip_stock", "label": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "label": "Supplier WIP Stock"}, 
        {"key": "employee_msl_stock", "label": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "label": "Supplier MSL Stock"}, 
        {"key": "employee_msl_hold_stock", "label": "Employee MSL Hold Stock"},
        {"key": "supplier_msl_hold_stock", "label": "Supplier MSL Hold Stock"}, 
        {"key": "raw_material_stock", "label": "Raw Material Stock"},
        {"key": "reserve_stock", "label": "Reserve Stock"}, 
        {"key": "transit_stock", "label": "Transit Stock"},
        {"key": "scrap_stock", "label": "Scrap Stock"}, 
        {"key": "finished_goods", "label": "Finished Goods"}
    ]
    
    for stock_type in stock_types:
        stock_material_values = stock_values.get(stock_type["key"], {})
        
        # Get values for each material type, show blank for zero values
        metal_val = stock_material_values.get("metal", 0.0)
        diamond_val = stock_material_values.get("diamond", 0.0)
        gemstone_val = stock_material_values.get("gemstone", 0.0)
        finding_val = stock_material_values.get("finding", 0.0)
        others_val = stock_material_values.get("others", 0.0)
        
        section_data.append({
            "section_name": stock_type["label"], 
            "section": stock_type["label"], 
            "parent_section": dept_name, 
            "indent": 1.0,
            "metal": "" if metal_val == 0 else metal_val,
            "diamond": "" if diamond_val == 0 else diamond_val,
            "gemstone": "" if gemstone_val == 0 else gemstone_val,
            "finding": "" if finding_val == 0 else finding_val,
            "others": "" if others_val == 0 else others_val,
            "view_details": f'<button class="btn btn-xs btn-primary view-stock-details" data-department="{dept_name}" data-stock-type="{stock_type["label"]}" data-stock-key="{stock_type["key"]}">View</button>',
            "is_stock_type": True
        })
    
    return section_data

def get_department_stock_values_by_material(dept_with_suffix, company, branch, manufacturer):
    """Get stock values broken down by material type for each stock category"""
    stock_values = {
        'work_order_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'employee_wip_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'supplier_wip_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'employee_msl_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'supplier_msl_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'employee_msl_hold_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'supplier_msl_hold_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'raw_material_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'reserve_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'transit_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'scrap_stock': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}, 
        'finished_goods': {"metal": 0.0, "diamond": 0.0, "gemstone": 0.0, "finding": 0.0, "others": 0.0}
    }
    
    # Material type mappings
    material_groups = {
        "metal": ["'Metal - V'"],
        "diamond": ["'Diamond - V'"],
        "gemstone": ["'Gemstone - V'"],
        "finding": ["'Finding - V'"],
        "others": ["'Others - V'", "'Miscellaneous - V'", "'Tools - V'"]
    }
    
    today = getdate()
    branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
    
    # Calculate each stock type by material
    for material_type, item_groups in material_groups.items():
        if item_groups:
            # Work Order Stock using warehouse name pattern matching
            stock_values["work_order_stock"][material_type] = get_work_order_stock_by_warehouse_name(
                company, dept_with_suffix, item_groups, today
            )
            
            # Raw Material Stock using Stock Balance logic
            stock_values["raw_material_stock"][material_type] = get_stock_balance_using_sle_logic(
                company, dept_with_suffix, item_groups, today, "Raw Material"
            )
            
            # Reserve Stock using Stock Balance logic  
            stock_values["reserve_stock"][material_type] = get_stock_balance_using_sle_logic(
                company, dept_with_suffix, item_groups, today, "Reserve"
            )
            
            # Scrap Stock using Stock Balance logic
            stock_values["scrap_stock"][material_type] = get_stock_balance_using_sle_logic(
                company, dept_with_suffix, item_groups, today, "Scrap"
            )
            
            # Transit Stock with correct Stock Entry Type
            try:
                transit_result = frappe.db.sql(f"""
                    SELECT SUM(sed.qty) as total_qty 
                    FROM `tabStock Entry` se 
                    LEFT JOIN `tabStock Entry Detail` sed ON se.name = sed.parent 
                    LEFT JOIN `tabItem` i ON sed.item_code = i.item_code 
                    WHERE se.stock_entry_type = 'Material Transfer to Department' 
                    AND sed.t_warehouse LIKE '%Transit%' 
                    AND se.company = '{company}' 
                    AND se.docstatus = 1 
                    AND se.department = '{dept_with_suffix}' 
                    AND i.item_group IN ({', '.join(item_groups)})
                """, as_dict=True)
                if transit_result and transit_result[0].get('total_qty'): 
                    stock_values["transit_stock"][material_type] = flt(transit_result[0]['total_qty'], 3)
            except Exception as e: 
                frappe.log_error(f"Transit stock error: {str(e)}")
    
    # Finished Goods - Remove item group filter completely
    try:
        finished_result = frappe.db.sql(f"""
            SELECT COUNT(*) as total_count 
            FROM `tabSerial No` sn 
            LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name 
            WHERE sn.company = '{company}' 
            AND sn.status = 'Active' 
            AND w.department = '{dept_with_suffix}'
        """, as_dict=True)
        if finished_result and finished_result[0].get('total_count'): 
            total_count = flt(finished_result[0]['total_count'], 3)
            stock_values["finished_goods"]["others"] = total_count
    except Exception as e: 
        frappe.log_error(f"Finished goods error: {str(e)}")
    
    # WIP Stock using Main Slip → Main Slip Operation → Manufacturing Operation
    material_weight_mapping = {
        "metal": "COALESCE(mop.net_wt, 0)",
        "diamond": "COALESCE(mop.diamond_wt, 0)",
        "gemstone": "COALESCE(mop.gemstone_wt, 0)",
        "finding": "COALESCE(mop.finding_wt, 0)",
        "others": "COALESCE(mop.other_wt, 0)"
    }
    
    for material_type, weight_field in material_weight_mapping.items():
        wip_queries = [
            ("employee_wip_stock", f"""
                SELECT SUM({weight_field}) as total_weight 
                FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
                LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
                LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
                WHERE mop.status = 'WIP'
                AND ms.employee IS NOT NULL 
                AND ms.for_subcontracting = 0
                AND ms.department = '{dept_with_suffix}'
                AND mwo.company = '{company}' {branch_condition}
                AND mwo.docstatus = 1 
                AND mop.department = '{dept_with_suffix}'
            """),
            ("supplier_wip_stock", f"""
                SELECT SUM({weight_field}) as total_weight 
                FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
                LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
                LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
                WHERE mop.status = 'WIP'
                AND ms.subcontractor IS NOT NULL 
                AND ms.for_subcontracting = 1
                AND ms.department = '{dept_with_suffix}'
                AND mwo.company = '{company}' {branch_condition}
                AND mwo.docstatus = 1 
                AND mop.department = '{dept_with_suffix}'
            """)
        ]
        
        for key, query in wip_queries:
            try:
                result = frappe.db.sql(query, as_dict=True)
                if result and result[0].get('total_weight'): 
                    stock_values[key][material_type] = flt(result[0]['total_weight'], 3)
            except Exception as e: 
                frappe.log_error(f"WIP query error for {key}: {str(e)}")
    
    # Main Slip + Loss Details Queries by variant code
    variant_code_mapping = {
        "metal": "'M'",
        "diamond": "'D'",
        "gemstone": "'G'",
        "finding": "'F'",
        "others": "'O'"
    }
    
    for material_type, variant_code in variant_code_mapping.items():
        msl_queries = [
            ("employee_msl_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'In Use' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of = {variant_code}"),
            ("supplier_msl_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'In Use' AND ms.subcontractor IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of = {variant_code}"),
            ("employee_msl_hold_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'On Hold' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of = {variant_code}"),
            ("supplier_msl_hold_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'On Hold' AND ms.subcontractor IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of = {variant_code}")
        ]
        
        for key, query in msl_queries:
            try:
                result = frappe.db.sql(query, as_dict=True)
                if result and result[0].get('total_qty'): 
                    stock_values[key][material_type] = flt(result[0]['total_qty'], 3)
            except Exception as e:
                frappe.log_error(f"MSL query error for {key}: {str(e)}")
    
    return stock_values

def add_department_total_row_with_materials(data, section_data, label, summary_data):
    total_metal = sum(flt(row.get("metal", 0.0)) for row in section_data if row.get("parent_section") and row.get("metal") != "")
    total_diamond = sum(flt(row.get("diamond", 0.0)) for row in section_data if row.get("parent_section") and row.get("diamond") != "")
    total_gemstone = sum(flt(row.get("gemstone", 0.0)) for row in section_data if row.get("parent_section") and row.get("gemstone") != "")
    total_finding = sum(flt(row.get("finding", 0.0)) for row in section_data if row.get("parent_section") and row.get("finding") != "")
    total_others = sum(flt(row.get("others", 0.0)) for row in section_data if row.get("parent_section") and row.get("others") != "")
    
    summary_data["total_metal"] += total_metal
    summary_data["total_diamond"] += total_diamond
    summary_data["total_gemstone"] += total_gemstone
    summary_data["total_finding"] += total_finding
    summary_data["total_others"] += total_others
    
    data.extend([{
        "section_name": f"'{label}'", 
        "section": label, 
        "parent_section": None, 
        "indent": 0.0, 
        "metal": "" if total_metal == 0 else total_metal,
        "diamond": "" if total_diamond == 0 else total_diamond,
        "gemstone": "" if total_gemstone == 0 else total_gemstone,
        "finding": "" if total_finding == 0 else total_finding,
        "others": "" if total_others == 0 else total_others,
        "view_details": "", 
        "is_department_total": True
    }, {}])

def add_grand_total_row_with_materials(data, summary_data):
    grand_total_metal = summary_data.get("total_metal", 0.0)
    grand_total_diamond = summary_data.get("total_diamond", 0.0)
    grand_total_gemstone = summary_data.get("total_gemstone", 0.0)
    grand_total_finding = summary_data.get("total_finding", 0.0)
    grand_total_others = summary_data.get("total_others", 0.0)
    
    data.append({
        "section_name": "'Grand Total'", 
        "section": "Grand Total", 
        "parent_section": None, 
        "indent": 0.0, 
        "metal": "" if grand_total_metal == 0 else grand_total_metal,
        "diamond": "" if grand_total_diamond == 0 else grand_total_diamond,
        "gemstone": "" if grand_total_gemstone == 0 else grand_total_gemstone,
        "finding": "" if grand_total_finding == 0 else grand_total_finding,
        "others": "" if grand_total_others == 0 else grand_total_others,
        "view_details": "", 
        "is_grand_total": True
    })

def get_manufacturer_departments(manufacturer, company):
    """FIXED: Updated with exact database department names including 'Close' prefix and special characters"""
    dept_mapping = {
        "Siddhi": ["Nandi"],
        "Service Center": ["Product Repair Center"],
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"],
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan & Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"],
        "Labh": ["Accounts", "Administration", "Canteen", "Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware & Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "Housekeeping", "Human Resources", "Information Technology", "Information Technology & Data Analysis", "Item Bom Management", "Learning & Development - KGJPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan & Management", "Marketing", "Merchandise", "Model Making", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research & Development", "Sales", "Sales & Marketing", "Security - KGJPL", "Selling", "Serial Number", "Sketch", "Sketch/Computer Aided Designing", "Stores", "Studio - GEPL", "Sub Contracting", "Tagging", "Waxing"],
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware & Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology & Data Analysis", "Item Bom Management", "Learning & Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan & Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research & Development", "Rhodium", "Rudraksha", "Sales", "Sales & Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }
    
    base_departments = dept_mapping.get(manufacturer, [])
    if not base_departments:
        return []
    
    # Add company suffix - SAME LOGIC AS BEFORE
    if company == "Gurukrupa Export Private Limited":
        return [f"{dept} - GEPL" for dept in base_departments]
    elif company == "KG GK Jewellers Private Limited":
        return [f"{dept} - KGJPL" for dept in base_departments]
    
    return base_departments

def get_work_order_stock_by_warehouse_name(company, dept_with_suffix, item_groups, to_date):
    """Get Work Order Stock by matching warehouse name pattern like 'Casting WO - GEPL'"""
    if not item_groups:
        return 0.0
        
    float_precision = cint(frappe.db.get_default("float_precision")) or 3
    item_group_str = ', '.join(item_groups)
    
    # Extract department name without company suffix for warehouse matching
    dept_name = dept_with_suffix.replace(' - GEPL', '').replace(' - KGJPL', '')
    company_suffix = "GEPL" if "GEPL" in dept_with_suffix else "KGJPL"
    
    # Look for warehouses with pattern: "Department WO - Company" (e.g., "Casting WO - GEPL")
    sle_query = f"""
        SELECT sle.item_code, sle.warehouse, sle.posting_date, sle.actual_qty, 
               sle.qty_after_transaction, sle.stock_value_difference, sle.voucher_type, 
               sle.voucher_no, sle.posting_datetime, sle.creation
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
        WHERE sle.company = '{company}'
        AND (w.name LIKE '{dept_name} WO - {company_suffix}' OR w.name LIKE '{dept_name} Work Order - {company_suffix}' OR sle.warehouse LIKE '%{dept_name}%WO%')
        AND i.item_group IN ({item_group_str})
        AND sle.posting_date <= '{to_date}'
        AND sle.docstatus < 2 
        AND sle.is_cancelled = 0
        ORDER BY sle.item_code, sle.warehouse, sle.posting_datetime, sle.creation
    """
    
    try:
        sle_entries = frappe.db.sql(sle_query, as_dict=True)
        
        # Process entries using Stock Balance report logic
        item_warehouse_map = {}
        
        for entry in sle_entries:
            # Group by (company, item_code, warehouse) - Same as Stock Balance report
            group_by_key = (entry.item_code, entry.warehouse)
            
            if group_by_key not in item_warehouse_map:
                # Initialize data same as Stock Balance report
                item_warehouse_map[group_by_key] = {
                    "item_code": entry.item_code,
                    "warehouse": entry.warehouse, 
                    "bal_qty": 0.0,
                    "bal_val": 0.0
                }
            
            qty_dict = item_warehouse_map[group_by_key]
            
            # Same calculation logic as Stock Balance report prepare_item_warehouse_map()
            qty_diff = flt(entry.actual_qty)
            value_diff = flt(entry.stock_value_difference or 0)
            
            # Update running balance - Same as Stock Balance report
            qty_dict["bal_qty"] += qty_diff
            qty_dict["bal_val"] += value_diff
        
        # Filter items with no transactions - Same as Stock Balance report filter_items_with_no_transactions()
        filtered_map = {}
        for group_by_key, qty_dict in item_warehouse_map.items():
            bal_qty = flt(qty_dict["bal_qty"], float_precision)
            bal_val = flt(qty_dict["bal_val"], float_precision)
            
            # Only include items with positive balance
            if bal_qty > 0:
                filtered_map[group_by_key] = qty_dict
        
        # Sum all positive balances
        total_qty = sum(flt(data["bal_qty"], float_precision) for data in filtered_map.values())
        return total_qty
        
    except Exception as e:
        frappe.log_error(f"Work Order stock calculation error: {str(e)}")
        return 0.0

def get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, to_date, warehouse_type):
    """Uses the exact same approach as Stock Balance report for accurate calculations"""
    if not item_groups:
        return 0.0
        
    float_precision = cint(frappe.db.get_default("float_precision")) or 3
    item_group_str = ', '.join(item_groups)
    
    # Get Stock Ledger Entries - Same query structure as Stock Balance report
    sle_query = f"""
        SELECT sle.item_code, sle.warehouse, sle.posting_date, sle.actual_qty, 
               sle.qty_after_transaction, sle.stock_value_difference, sle.voucher_type, 
               sle.voucher_no, sle.posting_datetime, sle.creation
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
        WHERE sle.company = '{company}'
        AND w.department = '{dept_with_suffix}'
        AND w.warehouse_type = '{warehouse_type}'
        AND i.item_group IN ({item_group_str})
        AND sle.posting_date <= '{to_date}'
        AND sle.docstatus < 2 
        AND sle.is_cancelled = 0
        ORDER BY sle.item_code, sle.warehouse, sle.posting_datetime, sle.creation
    """
    
    try:
        sle_entries = frappe.db.sql(sle_query, as_dict=True)
        
        # Process entries using Stock Balance report logic
        item_warehouse_map = {}
        
        for entry in sle_entries:
            # Group by (company, item_code, warehouse) - Same as Stock Balance report
            group_by_key = (entry.item_code, entry.warehouse)
            
            if group_by_key not in item_warehouse_map:
                # Initialize data same as Stock Balance report
                item_warehouse_map[group_by_key] = {
                    "item_code": entry.item_code,
                    "warehouse": entry.warehouse, 
                    "bal_qty": 0.0,
                    "bal_val": 0.0
                }
            
            qty_dict = item_warehouse_map[group_by_key]
            
            # Same calculation logic as Stock Balance report prepare_item_warehouse_map()
            qty_diff = flt(entry.actual_qty)
            value_diff = flt(entry.stock_value_difference or 0)
            
            # Update running balance - Same as Stock Balance report
            qty_dict["bal_qty"] += qty_diff
            qty_dict["bal_val"] += value_diff
        
        # Filter items with no transactions - Same as Stock Balance report filter_items_with_no_transactions()
        filtered_map = {}
        for group_by_key, qty_dict in item_warehouse_map.items():
            bal_qty = flt(qty_dict["bal_qty"], float_precision)
            bal_val = flt(qty_dict["bal_val"], float_precision)
            
            # Only include items with positive balance
            if bal_qty > 0:
                filtered_map[group_by_key] = qty_dict
        
        # Sum all positive balances
        total_qty = sum(flt(data["bal_qty"], float_precision) for data in filtered_map.values())
        return total_qty
        
    except Exception as e:
        frappe.log_error(f"Stock balance calculation error: {str(e)}")
        return 0.0

@frappe.whitelist()
def get_stock_details(department, stock_type, stock_key, filters=None):
    """Get specific stock type details - not combined"""
    try:
        if isinstance(filters, str): 
            import json; 
            filters = json.loads(filters)
        
        company, branch = filters.get("company"), filters.get("branch", "")
        dept_with_suffix = f"{department} - GEPL" if company == "Gurukrupa Export Private Limited" else f"{department} - KGJPL"
        
        # Route to specific detail function based on stock_key
        detail_functions = {
            "raw_material_stock": get_raw_material_stock_details,
            "reserve_stock": get_reserve_stock_details,
            "work_order_stock": get_work_order_stock_details,
            "employee_wip_stock": get_employee_wip_stock_details,
            "supplier_wip_stock": get_supplier_wip_stock_details,
            "employee_msl_stock": get_employee_msl_stock_details,
            "supplier_msl_stock": get_supplier_msl_stock_details,
            "employee_msl_hold_stock": get_employee_msl_hold_stock_details,
            "supplier_msl_hold_stock": get_supplier_msl_hold_stock_details,
            "transit_stock": get_transit_stock_details,
            "scrap_stock": get_scrap_stock_details,
            "finished_goods": get_finished_goods_details
        }
        
        detail_function = detail_functions.get(stock_key, lambda *args: [])
        result = detail_function(dept_with_suffix, company, branch, department)
        
        return result
        
    except Exception as e: 
        frappe.log_error(f"Stock details error: {str(e)}")
        return []

# SPECIFIC DETAIL FUNCTIONS FOR EACH STOCK TYPE - ALL LIMIT CLAUSES REMOVED

def get_raw_material_stock_details(department, company, branch, dept_display_name):
    """🔹 Raw Material Stock - Item Code, Weight"""
    try:
        today = getdate()
        return frappe.db.sql(f"""
            SELECT 
                sle.item_code as 'Item Code',
                SUM(sle.actual_qty) as 'Weight'
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = %s 
            AND w.department = %s
            AND w.warehouse_type = 'Raw Material'
            AND i.item_group IN ('Metal - V', 'Diamond - V', 'Gemstone - V', 'Finding - V', 'Others - V')
            AND sle.posting_date <= %s
            AND sle.docstatus < 2 
            AND sle.is_cancelled = 0
            GROUP BY sle.item_code
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY SUM(sle.actual_qty) DESC
        """, [company, department, today], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Raw material details error: {str(e)}")
        return []

def get_reserve_stock_details(department, company, branch, dept_display_name):
    """🔹 Reserve Stock - Item Code, Weight"""
    try:
        today = getdate()
        return frappe.db.sql(f"""
            SELECT 
                sle.item_code as 'Item Code',
                SUM(sle.actual_qty) as 'Weight'
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = %s 
            AND w.department = %s
            AND w.warehouse_type = 'Reserve'
            AND i.item_group IN ('Metal - V', 'Diamond - V', 'Gemstone - V', 'Finding - V', 'Others - V')
            AND sle.posting_date <= %s
            AND sle.docstatus < 2 
            AND sle.is_cancelled = 0
            GROUP BY sle.item_code
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY SUM(sle.actual_qty) DESC
        """, [company, department, today], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Reserve stock details error: {str(e)}")
        return []

def get_work_order_stock_details(department, company, branch, dept_display_name):
    """🔹 Work Order Stock - Manufacturing Work Order, Weight (raw material type wise), Operation"""
    try:
        dept_name = department.replace(' - GEPL', '').replace(' - KGJPL', '')
        company_suffix = "GEPL" if "GEPL" in department else "KGJPL"
        today = getdate()
        
        return frappe.db.sql(f"""
            SELECT 
                sle.warehouse as 'Warehouse',
                sle.item_code as 'Item Code',
                i.item_name as 'Item Name',
                i.item_group as 'Material Type',
                SUM(sle.actual_qty) as 'Weight'
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = %s 
            AND (w.name LIKE %s OR w.name LIKE %s OR sle.warehouse LIKE %s)
            AND sle.posting_date <= %s
            AND sle.docstatus < 2 
            AND sle.is_cancelled = 0
            GROUP BY sle.warehouse, sle.item_code
            HAVING SUM(sle.actual_qty) != 0
            ORDER BY ABS(SUM(sle.actual_qty)) DESC
        """, [company, f'{dept_name} WO - {company_suffix}', f'{dept_name} Work Order - {company_suffix}', f'%{dept_name}%WO%', today], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Work order details error: {str(e)}")
        return []

def get_employee_wip_stock_details(department, company, branch, dept_display_name):
    """🔹 Employee WIP Stock - Manufacturing Work Order, Weight (raw material type wise), Operation, Employee Name"""
    try:
        branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                COALESCE(mop.net_wt, 0) as 'Metal Weight',
                COALESCE(mop.diamond_wt, 0) as 'Diamond Weight',
                COALESCE(mop.gemstone_wt, 0) as 'Gemstone Weight', 
                COALESCE(mop.finding_wt, 0) as 'Finding Weight',
                COALESCE(mop.other_wt, 0) as 'Others Weight',
                mop.operation as 'Operation',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name'
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            WHERE mop.status = 'WIP'
            AND ms.employee IS NOT NULL 
            AND ms.for_subcontracting = 0
            AND ms.department = %s
            AND mwo.company = %s {branch_condition}
            AND mwo.docstatus = 1 
            AND mop.department = %s
            AND (COALESCE(mop.net_wt, 0) > 0 OR COALESCE(mop.diamond_wt, 0) > 0 OR COALESCE(mop.gemstone_wt, 0) > 0 OR COALESCE(mop.finding_wt, 0) > 0 OR COALESCE(mop.other_wt, 0) > 0)
            ORDER BY (COALESCE(mop.net_wt, 0) + COALESCE(mop.diamond_wt, 0) + COALESCE(mop.gemstone_wt, 0) + COALESCE(mop.finding_wt, 0) + COALESCE(mop.other_wt, 0)) DESC
        """, [department, company, department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Employee WIP details error: {str(e)}")
        return []

def get_supplier_wip_stock_details(department, company, branch, dept_display_name):
    """🔹 Supplier WIP Stock - Manufacturing Work Order, Weight (raw material type wise), Operation, Supplier Name"""
    try:
        branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                COALESCE(mop.net_wt, 0) as 'Metal Weight',
                COALESCE(mop.diamond_wt, 0) as 'Diamond Weight',
                COALESCE(mop.gemstone_wt, 0) as 'Gemstone Weight', 
                COALESCE(mop.finding_wt, 0) as 'Finding Weight',
                COALESCE(mop.other_wt, 0) as 'Others Weight',
                mop.operation as 'Operation',
                COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name'
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
            LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name
            WHERE mop.status = 'WIP'
            AND ms.subcontractor IS NOT NULL 
            AND ms.for_subcontracting = 1
            AND ms.department = %s
            AND mwo.company = %s {branch_condition}
            AND mwo.docstatus = 1 
            AND mop.department = %s
            AND (COALESCE(mop.net_wt, 0) > 0 OR COALESCE(mop.diamond_wt, 0) > 0 OR COALESCE(mop.gemstone_wt, 0) > 0 OR COALESCE(mop.finding_wt, 0) > 0 OR COALESCE(mop.other_wt, 0) > 0)
            ORDER BY (COALESCE(mop.net_wt, 0) + COALESCE(mop.diamond_wt, 0) + COALESCE(mop.gemstone_wt, 0) + COALESCE(mop.finding_wt, 0) + COALESCE(mop.other_wt, 0)) DESC
        """, [department, company, department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Supplier WIP details error: {str(e)}")
        return []

def get_employee_msl_stock_details(department, company, branch, dept_display_name):
    """🔹 Employee MSL Stock - Main Slip, Employee Name, Department, Operation, Weight (raw material type wise)"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                ms.name as 'Main Slip',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                ms.department as 'Department',
                mop.operation as 'Operation',
                SUM(CASE WHEN ld.variant_of = 'M' THEN ld.msl_qty ELSE 0 END) as 'Metal Weight',  
                SUM(CASE WHEN ld.variant_of = 'D' THEN ld.msl_qty ELSE 0 END) as 'Diamond Weight',
                SUM(CASE WHEN ld.variant_of = 'G' THEN ld.msl_qty ELSE 0 END) as 'Gemstone Weight',
                SUM(CASE WHEN ld.variant_of = 'F' THEN ld.msl_qty ELSE 0 END) as 'Finding Weight',
                SUM(CASE WHEN ld.variant_of = 'O' THEN ld.msl_qty ELSE 0 END) as 'Others Weight'
            FROM `tabMain Slip` ms 
            LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent 
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation 
            WHERE ms.workflow_state = 'In Use' 
            AND ms.employee IS NOT NULL 
            AND ms.department = %s 
            AND ld.variant_of IN ('M', 'D', 'G', 'F', 'O') 
            AND ld.msl_qty > 0
            GROUP BY ms.name, emp.employee_name, ms.department, mop.operation
            HAVING (SUM(ld.msl_qty) > 0)
            ORDER BY SUM(ld.msl_qty) DESC
        """, [department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Employee MSL details error: {str(e)}")
        return []

def get_supplier_msl_stock_details(department, company, branch, dept_display_name):
    """🔹 Supplier MSL Stock - Main Slip, Supplier Name, Department, Operation, Weight (raw material type wise)"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                ms.name as 'Main Slip',
                COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name',
                ms.department as 'Department',
                mop.operation as 'Operation',
                SUM(CASE WHEN ld.variant_of = 'M' THEN ld.msl_qty ELSE 0 END) as 'Metal Weight',  
                SUM(CASE WHEN ld.variant_of = 'D' THEN ld.msl_qty ELSE 0 END) as 'Diamond Weight',
                SUM(CASE WHEN ld.variant_of = 'G' THEN ld.msl_qty ELSE 0 END) as 'Gemstone Weight',
                SUM(CASE WHEN ld.variant_of = 'F' THEN ld.msl_qty ELSE 0 END) as 'Finding Weight',
                SUM(CASE WHEN ld.variant_of = 'O' THEN ld.msl_qty ELSE 0 END) as 'Others Weight'
            FROM `tabMain Slip` ms 
            LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent 
            LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation 
            WHERE ms.workflow_state = 'In Use' 
            AND ms.subcontractor IS NOT NULL 
            AND ms.department = %s 
            AND ld.variant_of IN ('M', 'D', 'G', 'F', 'O') 
            AND ld.msl_qty > 0
            GROUP BY ms.name, sup.supplier_name, ms.department, mop.operation
            HAVING (SUM(ld.msl_qty) > 0)
            ORDER BY SUM(ld.msl_qty) DESC
        """, [department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Supplier MSL details error: {str(e)}")
        return []

def get_employee_msl_hold_stock_details(department, company, branch, dept_display_name):
    """🔹 Employee MSL Hold Stock - Main Slip, Employee Name, Department, Operation, Weight (raw material type wise)"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                ms.name as 'Main Slip',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                ms.department as 'Department',
                mop.operation as 'Operation',
                SUM(CASE WHEN ld.variant_of = 'M' THEN ld.msl_qty ELSE 0 END) as 'Metal Weight',  
                SUM(CASE WHEN ld.variant_of = 'D' THEN ld.msl_qty ELSE 0 END) as 'Diamond Weight',
                SUM(CASE WHEN ld.variant_of = 'G' THEN ld.msl_qty ELSE 0 END) as 'Gemstone Weight',
                SUM(CASE WHEN ld.variant_of = 'F' THEN ld.msl_qty ELSE 0 END) as 'Finding Weight',
                SUM(CASE WHEN ld.variant_of = 'O' THEN ld.msl_qty ELSE 0 END) as 'Others Weight'
            FROM `tabMain Slip` ms 
            LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent 
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation 
            WHERE ms.workflow_state = 'On Hold' 
            AND ms.employee IS NOT NULL 
            AND ms.department = %s 
            AND ld.variant_of IN ('M', 'D', 'G', 'F', 'O') 
            AND ld.msl_qty > 0
            GROUP BY ms.name, emp.employee_name, ms.department, mop.operation
            HAVING (SUM(ld.msl_qty) > 0)
            ORDER BY SUM(ld.msl_qty) DESC
        """, [department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Employee MSL hold details error: {str(e)}")
        return []

def get_supplier_msl_hold_stock_details(department, company, branch, dept_display_name):
    """🔹 Supplier MSL Hold Stock - Main Slip, Supplier Name, Department, Operation, Weight (raw material type wise)"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                ms.name as 'Main Slip',
                COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name',
                ms.department as 'Department',
                mop.operation as 'Operation',
                SUM(CASE WHEN ld.variant_of = 'M' THEN ld.msl_qty ELSE 0 END) as 'Metal Weight',  
                SUM(CASE WHEN ld.variant_of = 'D' THEN ld.msl_qty ELSE 0 END) as 'Diamond Weight',
                SUM(CASE WHEN ld.variant_of = 'G' THEN ld.msl_qty ELSE 0 END) as 'Gemstone Weight',
                SUM(CASE WHEN ld.variant_of = 'F' THEN ld.msl_qty ELSE 0 END) as 'Finding Weight',
                SUM(CASE WHEN ld.variant_of = 'O' THEN ld.msl_qty ELSE 0 END) as 'Others Weight'
            FROM `tabMain Slip` ms 
            LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent 
            LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation 
            WHERE ms.workflow_state = 'On Hold' 
            AND ms.subcontractor IS NOT NULL 
            AND ms.department = %s 
            AND ld.variant_of IN ('M', 'D', 'G', 'F', 'O') 
            AND ld.msl_qty > 0
            GROUP BY ms.name, sup.supplier_name, ms.department, mop.operation
            HAVING (SUM(ld.msl_qty) > 0)
            ORDER BY SUM(ld.msl_qty) DESC
        """, [department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Supplier MSL hold details error: {str(e)}")
        return []

def get_transit_stock_details(department, company, branch, dept_display_name):
    """🔹 Transit Stock - Stock Entry Type, Source Warehouse, Target Warehouse, Weight (raw material type wise)"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                se.stock_entry_type as 'Stock Entry Type',
                sed.s_warehouse as 'Source Warehouse',
                sed.t_warehouse as 'Target Warehouse',
                SUM(CASE WHEN i.item_group = 'Metal - V' THEN sed.qty ELSE 0 END) as 'Metal Weight',
                SUM(CASE WHEN i.item_group = 'Diamond - V' THEN sed.qty ELSE 0 END) as 'Diamond Weight',
                SUM(CASE WHEN i.item_group = 'Gemstone - V' THEN sed.qty ELSE 0 END) as 'Gemstone Weight',
                SUM(CASE WHEN i.item_group = 'Finding - V' THEN sed.qty ELSE 0 END) as 'Finding Weight',
                SUM(CASE WHEN i.item_group IN ('Others - V', 'Miscellaneous - V') THEN sed.qty ELSE 0 END) as 'Others Weight'
            FROM `tabStock Entry` se 
            LEFT JOIN `tabStock Entry Detail` sed ON se.name = sed.parent 
            LEFT JOIN `tabItem` i ON sed.item_code = i.item_code 
            WHERE se.stock_entry_type = 'Material Transfer to Department' 
            AND sed.t_warehouse LIKE '%Transit%' 
            AND se.company = %s 
            AND se.docstatus = 1 
            AND se.department = %s 
            AND i.item_group IN ('Metal - V', 'Diamond - V', 'Gemstone - V', 'Finding - V', 'Others - V', 'Miscellaneous - V') 
            AND sed.qty > 0
            GROUP BY se.stock_entry_type, sed.s_warehouse, sed.t_warehouse
            HAVING SUM(sed.qty) > 0
            ORDER BY SUM(sed.qty) DESC
        """, [company, department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Transit stock details error: {str(e)}")
        return []

def get_scrap_stock_details(department, company, branch, dept_display_name):
    """🔹 Scrap Stock - Item Code, Qty, Department, Operation, Employee"""
    try:
        today = getdate()
        return frappe.db.sql(f"""
            SELECT 
                sle.item_code as 'Item Code',
                SUM(sle.actual_qty) as 'Qty',
                w.department as 'Department',
                'Scrap Operation' as 'Operation',
                COALESCE(sle.voucher_no, 'System') as 'Employee'
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = %s 
            AND w.department = %s
            AND w.warehouse_type = 'Scrap'
            AND i.item_group IN ('Metal - V', 'Diamond - V', 'Gemstone - V', 'Finding - V', 'Others - V')
            AND sle.posting_date <= %s
            AND sle.docstatus < 2 
            AND sle.is_cancelled = 0
            GROUP BY sle.item_code, w.department, sle.voucher_no
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY SUM(sle.actual_qty) DESC
        """, [company, department, today], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Scrap stock details error: {str(e)}")
        return []

def get_finished_goods_details(department, company, branch, dept_display_name):
    """🔹 Finished Goods - Serial No, Item Code, Quantity(default 1), Gross Wt"""
    try:
        return frappe.db.sql(f"""
            SELECT 
                sn.name as 'Serial No',
                sn.item_code as 'Item Code',
                1 as 'Quantity',
                COALESCE(snc.gross_wt, sc.gross_wt, 0) as 'Gross Wt'
            FROM `tabSerial No` sn 
            LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name
            LEFT JOIN `tabSerial Number Creator` snc ON sn.name = snc.name
            LEFT JOIN `tabSerial Creator` sc ON sn.name = sc.name 
            WHERE sn.company = %s 
            AND sn.status = 'Active' 
            AND w.department = %s
            ORDER BY sn.creation DESC
        """, [company, department], as_dict=True)
    except Exception as e:
        frappe.log_error(f"Finished goods details error: {str(e)}")
        return []

@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    """Database-driven department mapping - matches actual system data"""
    return get_manufacturer_departments(manufacturer, "")
