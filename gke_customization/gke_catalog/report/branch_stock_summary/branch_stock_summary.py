# Copyright (c) 2025, Your Company and contributors
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
    if not filters.get("company"): frappe.throw(_("Company is required"))
    if filters.get("company") != "KG GK Jewellers Private Limited" and not filters.get("branch"): 
        frappe.throw(_("Branch is required"))
    if not filters.get("raw_material_type"): frappe.throw(_("Raw Material Type is required"))
    return get_branch_stock_summary_simplified(filters)

def get_branch_stock_summary_simplified(filters=None):
    columns = [
        {"fieldname": "section_name", "label": "Department", "fieldtype": "Data", "width": 400},
        {"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "view_details", "label": "View Details", "fieldtype": "Data", "width": 120}
    ]
    
    departments = get_departments_list(filters)
    if not departments: return columns, []
    
    data, summary_data = [], {"total_quantity": 0.0}
    raw_material_types = [filters.get("raw_material_type")] if filters.get("raw_material_type") else ["Metal"]
    
    for dept_info in departments:
        dept_name, dept_with_suffix = dept_info['department'], dept_info['db_department']
        stock_values = get_department_stock_values(dept_with_suffix, filters.get("company", ""), filters.get("branch", ""), filters.get("manufacturer"), raw_material_types)
        section_data = build_department_section_simplified(dept_name, stock_values)
        data.extend(section_data)
        add_department_total_row_simplified(data, section_data, f"{dept_name} Total", summary_data)
    
    add_grand_total_row_simplified(data, summary_data)
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
    
    try: return frappe.db.sql(dept_query, as_dict=True)
    except Exception as e: frappe.log_error(f"Department query error: {str(e)}"); return []

def build_department_section_simplified(dept_name, stock_values):
    section_data = [{"section_name": f"'{dept_name}'", "parent_section": None, "indent": 0.0, "section": dept_name, "quantity": "", "view_details": "", "is_department_header": True}]
    
    stock_types = [{"key": "work_order_stock", "label": "Work Order Stock"}, {"key": "employee_wip_stock", "label": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "label": "Supplier WIP Stock"}, {"key": "employee_msl_stock", "label": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "label": "Supplier MSL Stock"}, {"key": "employee_msl_hold_stock", "label": "Employee MSL Hold Stock"},
        {"key": "supplier_msl_hold_stock", "label": "Supplier MSL Hold Stock"}, {"key": "raw_material_stock", "label": "Raw Material Stock"},
        {"key": "reserve_stock", "label": "Reserve Stock"}, {"key": "transit_stock", "label": "Transit Stock"},
        {"key": "scrap_stock", "label": "Scrap Stock"}, {"key": "finished_goods", "label": "Finished Goods"}]
    
    for stock_type in stock_types:
        stock_value = stock_values.get(stock_type["key"], 0.0)
        # FIXED: Show blank for zero values instead of 0.000
        display_value = "" if stock_value == 0 else stock_value
        
        section_data.append({"section_name": stock_type["label"], "section": stock_type["label"], "parent_section": dept_name, "indent": 1.0,
            "quantity": display_value, "view_details": f'<button class="btn btn-xs btn-primary view-stock-details" data-department="{dept_name}" data-stock-type="{stock_type["label"]}" data-stock-key="{stock_type["key"]}">View</button>',
            "is_stock_type": True})
    
    return section_data

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
        AND (w.name LIKE '{dept_name} WO - {company_suffix}' OR w.name LIKE '{dept_name} Work Order - {company_suffix}')
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

def get_department_stock_values(dept_with_suffix, company, branch, manufacturer, raw_material_types=None):
    if not raw_material_types: raw_material_types = ["Metal"]
    stock_values = {'work_order_stock': 0.0, 'employee_wip_stock': 0.0, 'supplier_wip_stock': 0.0, 'employee_msl_stock': 0.0, 'supplier_msl_stock': 0.0, 'employee_msl_hold_stock': 0.0, 'supplier_msl_hold_stock': 0.0, 'raw_material_stock': 0.0, 'reserve_stock': 0.0, 'transit_stock': 0.0, 'scrap_stock': 0.0, 'finished_goods': 0.0}
    
    # Get manufacturer department filtering
    manufacturer_dept_filter = ""
    if manufacturer:
        allowed_departments = get_manufacturer_departments(manufacturer, company)
        if allowed_departments:
            dept_filter = "', '".join(allowed_departments)
            manufacturer_dept_filter = f" AND department IN ('{dept_filter}')"
    
    # For Stock Ledger queries
    item_groups = []
    if "Metal" in raw_material_types: item_groups.append("'Metal - V'")
    if "Diamond" in raw_material_types: item_groups.append("'Diamond - V'")
    if "Gemstone" in raw_material_types: item_groups.append("'Gemstone - V'")
    if "Finding" in raw_material_types: item_groups.append("'Finding - V'")
    
    # For Manufacturing Operation queries - weight fields
    weight_fields = []
    if "Metal" in raw_material_types: weight_fields.append("COALESCE(mop.net_wt, 0)")
    if "Diamond" in raw_material_types: weight_fields.append("COALESCE(mop.diamond_wt, 0)")
    if "Gemstone" in raw_material_types: weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
    if "Finding" in raw_material_types: weight_fields.append("COALESCE(mop.finding_wt, 0)")
    weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
    
    # For Main Slip + Loss Details queries
    variant_codes = []
    if "Metal" in raw_material_types: variant_codes.append("'M'")
    if "Diamond" in raw_material_types: variant_codes.append("'D'")
    if "Gemstone" in raw_material_types: variant_codes.append("'G'")
    if "Finding" in raw_material_types: variant_codes.append("'F'")
    
    today = getdate()
    branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
    
    # Work Order Stock using warehouse name pattern matching
    if item_groups:
        stock_values["work_order_stock"] = get_work_order_stock_by_warehouse_name(
            company, dept_with_suffix, item_groups, today
        )
        
        # Raw Material Stock using Stock Balance logic
        stock_values["raw_material_stock"] = get_stock_balance_using_sle_logic(
            company, dept_with_suffix, item_groups, today, "Raw Material"
        )
        
        # Reserve Stock using Stock Balance logic  
        stock_values["reserve_stock"] = get_stock_balance_using_sle_logic(
            company, dept_with_suffix, item_groups, today, "Reserve"
        )
        
        # FIXED: Scrap Stock using Stock Balance logic instead of Stock Entry
        stock_values["scrap_stock"] = get_stock_balance_using_sle_logic(
            company, dept_with_suffix, item_groups, today, "Scrap"
        )
        
        # FIXED: Transit Stock with correct Stock Entry Type (capital D)
        item_group_str = ', '.join(item_groups)
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
                AND i.item_group IN ({item_group_str})
            """, as_dict=True)
            if transit_result and transit_result[0].get('total_qty'): 
                stock_values["transit_stock"] = flt(transit_result[0]['total_qty'], 3)
        except Exception as e: 
            frappe.log_error(f"Transit stock error: {str(e)}")
    
    # FIXED: Finished Goods - Remove item group filter completely
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
            stock_values["finished_goods"] = flt(finished_result[0]['total_count'], 3)
    except Exception as e: 
        frappe.log_error(f"Finished goods error: {str(e)}")
    
    # FIXED: WIP Stock using Main Slip → Main Slip Operation → Manufacturing Operation
    if weight_sum and weight_fields:
        wip_queries = [
            ("employee_wip_stock", f"""
                SELECT SUM({weight_sum}) as total_weight 
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
                SELECT SUM({weight_sum}) as total_weight 
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
                    stock_values[key] = flt(result[0]['total_weight'], 3)
            except Exception as e: 
                frappe.log_error(f"WIP query error for {key}: {str(e)}")
    
    # Main Slip + Loss Details Queries (unchanged - already uses current department)
    if variant_codes:
        variant_code_str = ', '.join(variant_codes)
        msl_queries = [
            ("employee_msl_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'In Use' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of IN ({variant_code_str})"),
            ("supplier_msl_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'In Use' AND ms.subcontractor IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of IN ({variant_code_str})"),
            ("employee_msl_hold_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'On Hold' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of IN ({variant_code_str})"),
            ("supplier_msl_hold_stock", f"SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent WHERE ms.workflow_state = 'On Hold' AND ms.subcontractor IS NOT NULL AND ms.department = '{dept_with_suffix}' AND ld.variant_of IN ({variant_code_str})")
        ]
        
        for key, query in msl_queries:
            try:
                result = frappe.db.sql(query, as_dict=True)
                if result and result[0].get('total_qty'): 
                    stock_values[key] = flt(result[0]['total_qty'], 3)
            except Exception as e: 
                frappe.log_error(f"MSL query error for {key}: {str(e)}")
    
    return stock_values

def add_department_total_row_simplified(data, section_data, label, summary_data):
    total_quantity = sum(flt(row.get("quantity", 0.0)) for row in section_data if row.get("parent_section") and row.get("quantity") != "")
    summary_data["total_quantity"] += total_quantity
    
    # FIXED: Show blank if total is 0
    display_total = "" if total_quantity == 0 else total_quantity
    
    data.extend([{"section_name": f"'{label}'", "section": label, "parent_section": None, "indent": 0.0, "quantity": display_total, "view_details": "", "is_department_total": True}, {}])

def add_grand_total_row_simplified(data, summary_data):
    grand_total = summary_data.get("total_quantity", 0.0)
    # FIXED: Show blank if grand total is 0
    display_grand_total = "" if grand_total == 0 else grand_total
    data.append({"section_name": "'Grand Total'", "section": "Grand Total", "parent_section": None, "indent": 0.0, "quantity": display_grand_total, "view_details": "", "is_grand_total": True})

@frappe.whitelist()
def get_stock_details(department, stock_type, stock_key, filters=None):
    try:
        if isinstance(filters, str): import json; filters = json.loads(filters)
        company, branch, raw_material_types = filters.get("company"), filters.get("branch", ""), [filters.get("raw_material_type")] if filters.get("raw_material_type") else ["Metal"]
        dept_with_suffix = f"{department} - GEPL" if company == "Gurukrupa Export Private Limited" else f"{department} - KGJPL"
        
        detail_functions = {"work_order_stock": get_work_order_details, "employee_wip_stock": get_employee_wip_details, "supplier_wip_stock": get_supplier_wip_details, "employee_msl_stock": get_employee_msl_details, "supplier_msl_stock": get_supplier_msl_details, "employee_msl_hold_stock": get_employee_msl_hold_details, "supplier_msl_hold_stock": get_supplier_msl_hold_details, "raw_material_stock": get_raw_material_details, "reserve_stock": get_reserve_stock_details, "transit_stock": get_transit_stock_details, "scrap_stock": get_scrap_stock_details, "finished_goods": get_finished_goods_details}
        
        result = detail_functions.get(stock_key, lambda *args: [])(dept_with_suffix, company, branch, department, raw_material_types)
        return [row for row in result if any(isinstance(v, (int, float)) and v > 0 for v in row.values())]
    except Exception as e: frappe.log_error(f"Stock details error: {str(e)}"); return []

def get_weight_sum(raw_material_types):
    weight_fields = []
    if "Metal" in raw_material_types: weight_fields.append("COALESCE(mop.net_wt, 0)")
    if "Diamond" in raw_material_types: weight_fields.append("COALESCE(mop.diamond_wt, 0)")
    if "Gemstone" in raw_material_types: weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
    if "Finding" in raw_material_types: weight_fields.append("COALESCE(mop.finding_wt, 0)")
    return " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"

def get_item_groups(raw_material_types):
    item_groups = []
    if "Metal" in raw_material_types: item_groups.append("'Metal - V'")
    if "Diamond" in raw_material_types: item_groups.append("'Diamond - V'")
    if "Gemstone" in raw_material_types: item_groups.append("'Gemstone - V'")
    if "Finding" in raw_material_types: item_groups.append("'Finding - V'")
    return item_groups

def get_variant_codes(raw_material_types):
    variant_codes = []
    if "Metal" in raw_material_types: variant_codes.append("'M'")
    if "Diamond" in raw_material_types: variant_codes.append("'D'")
    if "Gemstone" in raw_material_types: variant_codes.append("'G'")
    if "Finding" in raw_material_types: variant_codes.append("'F'")
    return variant_codes

def get_work_order_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            today = getdate()
            # Use warehouse name pattern matching for Work Order details
            dept_name = department.replace(' - GEPL', '').replace(' - KGJPL', '')
            company_suffix = "GEPL" if "GEPL" in department else "KGJPL"
            item_group_str = ', '.join(item_groups)
            
            return frappe.db.sql(f"""
                SELECT final_data.item_code as 'Item Code', final_data.bal_qty as 'Weight' 
                FROM (
                    SELECT sle.item_code, sle.warehouse, 
                           SUM(sle.actual_qty) as bal_qty
                    FROM `tabStock Ledger Entry` sle
                    LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = %s 
                    AND (w.name LIKE '{dept_name} WO - {company_suffix}' OR w.name LIKE '{dept_name} Work Order - {company_suffix}')
                    AND i.item_group IN ({item_group_str})
                    AND sle.posting_date <= %s
                    AND sle.docstatus < 2 
                    AND sle.is_cancelled = 0
                    GROUP BY sle.item_code, sle.warehouse
                    HAVING SUM(sle.actual_qty) > 0
                ) as final_data
                ORDER BY final_data.bal_qty DESC
            """, [company, today], as_dict=True)
        else:
            return []
    except: return []

def get_employee_wip_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        # FIXED: Use Main Slip → Main Slip Operation → Manufacturing Operation chain
        weight_sum = get_weight_sum(raw_material_types)
        branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight', 
                mop.name as 'Operation',
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
            ORDER BY ({weight_sum}) DESC
        """, [department, company, department], as_dict=True)
    except: return []

def get_supplier_wip_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        # FIXED: Use Main Slip → Main Slip Operation → Manufacturing Operation chain
        weight_sum = get_weight_sum(raw_material_types)
        branch_condition = f"AND mwo.branch = '{branch}'" if branch else ""
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight', 
                mop.name as 'Operation',
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
            ORDER BY ({weight_sum}) DESC
        """, [department, company, department], as_dict=True)
    except: return []

def get_employee_msl_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            return frappe.db.sql(f"SELECT ms.name as 'Main Slip', COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name', ld.msl_qty as 'Weight', ld.variant_of as 'Material Type' FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name WHERE ms.workflow_state = 'In Use' AND ms.employee IS NOT NULL AND ms.department = %s AND ld.variant_of IN ({', '.join(variant_codes)}) ORDER BY ld.msl_qty DESC", [department], as_dict=True)
        else:
            return []
    except: return []

def get_supplier_msl_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            return frappe.db.sql(f"SELECT ms.name as 'Main Slip', COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name', ld.msl_qty as 'Weight', ld.variant_of as 'Material Type' FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name WHERE ms.workflow_state = 'In Use' AND ms.subcontractor IS NOT NULL AND ms.department = %s AND ld.variant_of IN ({', '.join(variant_codes)}) ORDER BY ld.msl_qty DESC", [department], as_dict=True)
        else:
            return []
    except: return []

def get_employee_msl_hold_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            return frappe.db.sql(f"SELECT ms.name as 'Main Slip', COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name', ld.msl_qty as 'Weight', ld.variant_of as 'Material Type' FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name WHERE ms.workflow_state = 'On Hold' AND ms.employee IS NOT NULL AND ms.department = %s AND ld.variant_of IN ({', '.join(variant_codes)}) ORDER BY ld.msl_qty DESC", [department], as_dict=True)
        else:
            return []
    except: return []

def get_supplier_msl_hold_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            return frappe.db.sql(f"SELECT ms.name as 'Main Slip', COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name', ld.msl_qty as 'Weight', ld.variant_of as 'Material Type' FROM `tabMain Slip` ms LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name WHERE ms.workflow_state = 'On Hold' AND ms.subcontractor IS NOT NULL AND ms.department = %s AND ld.variant_of IN ({', '.join(variant_codes)}) ORDER BY ld.msl_qty DESC", [department], as_dict=True)
        else:
            return []
    except: return []

def get_raw_material_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            today = getdate()
            # Use Stock Balance logic for view details too
            item_group_str = ', '.join(item_groups)
            return frappe.db.sql(f"""
                SELECT final_data.item_code as 'Item Code', final_data.bal_qty as 'Weight' 
                FROM (
                    SELECT sle.item_code, sle.warehouse, 
                           SUM(sle.actual_qty) as bal_qty
                    FROM `tabStock Ledger Entry` sle
                    LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = %s 
                    AND w.department = %s
                    AND w.warehouse_type = 'Raw Material'
                    AND i.item_group IN ({item_group_str})
                    AND sle.posting_date <= %s
                    AND sle.docstatus < 2 
                    AND sle.is_cancelled = 0
                    GROUP BY sle.item_code, sle.warehouse
                    HAVING SUM(sle.actual_qty) > 0
                ) as final_data
                ORDER BY final_data.bal_qty DESC
            """, [company, department, today], as_dict=True)
        else:
            return []
    except: return []

def get_reserve_stock_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            today = getdate()
            # Use Stock Balance logic for view details too
            item_group_str = ', '.join(item_groups)
            return frappe.db.sql(f"""
                SELECT final_data.item_code as 'Item Code', final_data.bal_qty as 'Weight' 
                FROM (
                    SELECT sle.item_code, sle.warehouse, 
                           SUM(sle.actual_qty) as bal_qty
                    FROM `tabStock Ledger Entry` sle
                    LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = %s 
                    AND w.department = %s
                    AND w.warehouse_type = 'Reserve'
                    AND i.item_group IN ({item_group_str})
                    AND sle.posting_date <= %s
                    AND sle.docstatus < 2 
                    AND sle.is_cancelled = 0
                    GROUP BY sle.item_code, sle.warehouse
                    HAVING SUM(sle.actual_qty) > 0
                ) as final_data
                ORDER BY final_data.bal_qty DESC
            """, [company, department, today], as_dict=True)
        else:
            return []
    except: return []

def get_transit_stock_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            # FIXED: Use correct Stock Entry Type 'Material Transfer to Department'
            return frappe.db.sql(f"SELECT se.stock_entry_type as 'Stock Entry Type', sed.s_warehouse as 'Source Warehouse', sed.t_warehouse as 'Target Warehouse', sed.qty as 'Weight' FROM `tabStock Entry` se LEFT JOIN `tabStock Entry Detail` sed ON se.name = sed.parent LEFT JOIN `tabItem` i ON sed.item_code = i.item_code WHERE se.stock_entry_type = 'Material Transfer to Department' OR se.stock_entry_type = 'Material Transfer(DEPARTMENT)' AND sed.t_warehouse LIKE '%Transit%' AND se.company = %s AND se.docstatus = 1 AND se.department = %s AND i.item_group IN ({', '.join(item_groups)}) ORDER BY sed.qty DESC", [company, department], as_dict=True)
        else:
            return []
    except: return []

def get_scrap_stock_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            today = getdate()
            # FIXED: Use Stock Balance logic for Scrap details too
            item_group_str = ', '.join(item_groups)
            return frappe.db.sql(f"""
                SELECT final_data.item_code as 'Item Code', final_data.bal_qty as 'Weight' 
                FROM (
                    SELECT sle.item_code, sle.warehouse, 
                           SUM(sle.actual_qty) as bal_qty
                    FROM `tabStock Ledger Entry` sle
                    LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = %s 
                    AND w.department = %s
                    AND w.warehouse_type = 'Scrap'
                    AND i.item_group IN ({item_group_str})
                    AND sle.posting_date <= %s
                    AND sle.docstatus < 2 
                    AND sle.is_cancelled = 0
                    GROUP BY sle.item_code, sle.warehouse
                    HAVING SUM(sle.actual_qty) > 0
                ) as final_data
                ORDER BY final_data.bal_qty DESC
            """, [company, department, today], as_dict=True)
        else:
            return []
    except: return []

def get_finished_goods_details(department, company, branch, dept_display_name, raw_material_types):
    try:
        # FIXED: Remove item group filter - show ALL Serial Numbers in department
        return frappe.db.sql(f"""
            SELECT 
                sn.name as 'Serial No', 
                sn.item_code as 'Item Code', 
                1 as 'Quantity'
            FROM `tabSerial No` sn 
            LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name 
            WHERE sn.company = %s 
            AND sn.status = 'Active' 
            AND w.department = %s
            ORDER BY sn.creation DESC
        """, [company, department], as_dict=True)
    except: 
        return []

@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    """Database-driven department mapping - matches actual system data"""
    dept_mapping = {
        "Siddhi": ["Nandi"], 
        "Service Center": ["Product Repair Center"], 
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"], 
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan & Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"], 
        "Labh": ["Accounts", "Administration", "Canteen", "Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware & Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "Housekeeping", "Human Resources", "Information Technology", "Information Technology & Data Analysis", "Item Bom Management", "Learning & Development - KGJPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan & Management", "Marketing", "Merchandise", "Model Making", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research & Development", "Sales", "Sales & Marketing", "Security - KGJPL", "Selling", "Serial Number", "Sketch", "Sketch/Computer Aided Designing", "Stores", "Studio - GEPL", "Sub Contracting", "Tagging", "Waxing"], 
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware & Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology & Data Analysis", "Item Bom Management", "Learning & Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan & Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research & Development", "Rhodium", "Rudraksha", "Sales", "Sales & Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }
    return dept_mapping.get(manufacturer, [])
