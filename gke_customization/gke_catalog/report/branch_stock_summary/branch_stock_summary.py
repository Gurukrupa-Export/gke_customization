# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
    if not filters.get("company"): 
        frappe.throw(_("Company is required"))
    if filters.get("company") == "Gurukrupa Export Private Limited" and not filters.get("branch"): 
        frappe.throw(_("Branch is required for Gurukrupa Export Private Limited"))
    if not filters.get("raw_material_type"): 
        frappe.throw(_("Raw Material Type is required"))
    
    return get_branch_stock_summary_simplified(filters)

def get_branch_stock_summary_simplified(filters=None):
    columns = [
        {"fieldname": "section_name", "label": "Department", "fieldtype": "Data", "width": 400},
        {"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "view_details", "label": "View Details", "fieldtype": "Data", "width": 120}
    ]
    
    departments = get_departments_list(filters)
    if not departments:
        return columns, []
    
    data = []
    grand_total = 0.0
    raw_material_types = [filters.get("raw_material_type")] if filters.get("raw_material_type") else ["Metal"]
    
    for dept_info in departments:
        dept_name, dept_with_suffix = dept_info["department"], dept_info["db_department"]
        stock_values = get_department_stock_values(dept_with_suffix, filters.get("company"), filters.get("branch", ""), filters.get("manufacturer", ""), raw_material_types)
        section_data = build_department_section_simplified(dept_name, stock_values)
        data.extend(section_data)
        dept_total = add_department_total_row_simplified(data, section_data, f"{dept_name} Total")
        grand_total += dept_total
    
    # FIXED: ADD GRAND TOTAL ROW - No rounding
    if grand_total > 0:
        data.append({
            "section_name": "Grand Total", 
            "section": "Grand Total", 
            "parent_section": None, 
            "indent": 0.0, 
            "quantity": grand_total,  # FIXED: No flt() rounding
            "view_details": "", 
            "is_grand_total": True
        })
    
    return columns, data

def get_departments_list(filters):
    company, branch, manufacturer, department = (filters.get("company"), filters.get("branch", ""), filters.get("manufacturer", ""), filters.get("department"))
    
    excluded_departments = ["Canteen", "HR", "Admin", "Security", "Housekeeping", "IT", "Transport", "Maintenance"]
    excluded_condition = " AND " + " AND ".join([f"mop.department NOT LIKE '%{dept}%'" for dept in excluded_departments])
    
    manufacturer_dept_condition = ""
    if manufacturer:
        allowed_departments = get_manufacturer_departments(manufacturer, company)
        if allowed_departments:
            dept_filter = "', '".join(allowed_departments)
            manufacturer_dept_condition = f" AND mop.department IN ('{dept_filter}')"
    
    dept_query = f"""
        SELECT DISTINCT 
            REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') as department,
            mop.department as db_department
        FROM `tabManufacturing Operation` mop
        LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
        WHERE mwo.company = '{company}' AND mwo.docstatus = 1 AND mop.department IS NOT NULL AND mop.department != ''
          {excluded_condition}{manufacturer_dept_condition}
    """
    
    if company == "Gurukrupa Export Private Limited" and branch:
        dept_query += f" AND mwo.branch = '{branch}'"
    if department:
        dept_query += f" AND mop.department LIKE '%{department}%'"
    
    dept_query += " ORDER BY mop.department LIMIT 20"
    
    try:
        return frappe.db.sql(dept_query, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Department query error: {str(e)}")
        return []

# FIXED: Show blank for zero values
def build_department_section_simplified(dept_name, stock_values):
    section_data = [{"section_name": f"{dept_name}", "parent_section": None, "indent": 0.0, "section": dept_name, "quantity": "", "view_details": "", "is_department_header": True}]
    
    stock_types = [
        {"key": "work_order_stock", "label": "Work Order Stock"}, {"key": "employee_wip_stock", "label": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "label": "Supplier WIP Stock"}, {"key": "employee_msl_stock", "label": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "label": "Supplier MSL Stock"}, {"key": "employee_msl_hold_stock", "label": "Employee MSL Hold Stock"},
        {"key": "supplier_msl_hold_stock", "label": "Supplier MSL Hold Stock"}, {"key": "raw_material_stock", "label": "Raw Material Stock"},
        {"key": "reserve_stock", "label": "Reserve Stock"}, {"key": "transit_stock", "label": "Transit Stock"},
        {"key": "scrap_stock", "label": "Scrap Stock"}, {"key": "finished_goods", "label": "Finished Goods"}
    ]
    
    for stock_type in stock_types:
        stock_value = stock_values.get(stock_type["key"], 0.0)
        # FIXED: Show blank instead of 0
        display_value = "" if stock_value == 0 or stock_value == 0.0 else stock_value
        section_data.append({
            "section_name": stock_type["label"], "section": stock_type["label"], "parent_section": dept_name, "indent": 1.0,
            "quantity": display_value, "view_details": f'<button class="btn btn-xs btn-primary view-stock-details" data-department="{dept_name}" data-stock-type="{stock_type["label"]}" data-stock-key="{stock_type["key"]}">View</button>',
            "is_stock_type": True
        })
    
    return section_data

def get_manufacturer_departments(manufacturer, company):
    dept_mapping = {
        "Siddhi": ["Nandi"], "Service Center": ["Product Repair Center"],
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"],
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"],
        "Labh": ["Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Diamond Setting", "Final Polish", "Manufacturing Plan & Management", "Model Making", "Pre Polish", "Product Certification", "Sub Contracting", "Tagging", "Waxing"],
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology Data Analysis", "Item Bom Management", "Learning Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales", "Sales Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }
    
    base_departments = dept_mapping.get(manufacturer, [])
    if not base_departments:
        return []
    
    if company == "Gurukrupa Export Private Limited":
        return [f"{dept} - GEPL" for dept in base_departments]
    elif company == "KG GK Jewellers Private Limited":
        return [f"{dept} - KGJPL" for dept in base_departments]
    return base_departments

def get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, to_date, warehouse_type):
    if not item_groups:
        return 0.0
    
    float_precision = cint(frappe.db.get_default("float_precision")) or 3
    item_group_str = "', '".join(item_groups)
    
    try:
        sle_entries = frappe.db.sql(f"""
            SELECT sle.item_code, sle.warehouse, sle.actual_qty, sle.stock_value_difference
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name  
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = '{company}' AND w.department = '{dept_with_suffix}' AND w.warehouse_type = '{warehouse_type}'
              AND i.item_group IN ('{item_group_str}') AND sle.posting_date <= '{to_date}' AND sle.docstatus < 2 AND sle.is_cancelled = 0
            ORDER BY sle.item_code, sle.warehouse, sle.posting_datetime, sle.creation
        """, as_dict=True)
        
        item_warehouse_map = {}
        for entry in sle_entries:
            group_by_key = (entry.item_code, entry.warehouse)
            if group_by_key not in item_warehouse_map:
                item_warehouse_map[group_by_key] = {'bal_qty': 0.0, 'bal_val': 0.0}
            
            item_warehouse_map[group_by_key]['bal_qty'] += float(entry.actual_qty or 0)
            item_warehouse_map[group_by_key]['bal_val'] += float(entry.stock_value_difference or 0)
        
        # FIXED: No rounding - exact sum
        filtered_map = {k: v for k, v in item_warehouse_map.items() if v['bal_qty'] > 0}
        return sum(data['bal_qty'] for data in filtered_map.values())
    except:
        return 0.0

# FIXED: WO Stock using Manufacturing Operations - No rounding
def get_work_order_stock_by_manufacturing_operations(company, dept_with_suffix, raw_material_types, to_date):
    if not raw_material_types:
        return 0.0
    
    weight_fields = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": 
            weight_fields.append("COALESCE(mop.net_wt, 0)")
        elif rm_type == "Diamond": 
            weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
        elif rm_type == "Gemstone": 
            weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
        elif rm_type == "Finding": 
            weight_fields.append("COALESCE(mop.finding_wt, 0)")
    
    weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
    
    try:
        result = frappe.db.sql(f"""
            SELECT SUM({weight_sum}) as total_weight
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status IN ('Open', 'Not Started') 
              AND mop.department = '{dept_with_suffix}' 
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1 
              AND ({weight_sum}) > 0
        """, as_dict=True)
        return result[0]['total_weight'] if result and result[0].get('total_weight') else 0.0  # REMOVED flt()
    except:
        return 0.0

# FIXED: Transit Stock Balance - REVERTED to SLE Balance Logic (Net Balance)
def get_transit_stock_balance(company, dept_with_suffix, item_groups, to_date):
    if not item_groups:
        return 0.0
    
    item_group_str = "', '".join(item_groups)
    
    try:
        result = frappe.db.sql(f"""
            SELECT SUM(sle.actual_qty) as total_balance
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE sle.company = '{company}' 
              AND w.department = '{dept_with_suffix}'
              AND w.warehouse_type = 'Transit'
              AND i.item_group IN ('{item_group_str}')
              AND sle.posting_date <= '{to_date}'
              AND sle.docstatus < 2 
              AND sle.is_cancelled = 0
        """, as_dict=True)
        return result[0]['total_balance'] if result and result[0].get('total_balance') else 0.0
    except:
        return 0.0

# UPDATED: Get department stock values - No rounding
def get_department_stock_values(dept_with_suffix, company, branch, manufacturer, raw_material_types=None):
    if not raw_material_types:
        raw_material_types = ["Metal"]
    
    stock_values = {k: 0.0 for k in ["work_order_stock", "employee_wip_stock", "supplier_wip_stock", "employee_msl_stock", "supplier_msl_stock", "employee_msl_hold_stock", "supplier_msl_hold_stock", "raw_material_stock", "reserve_stock", "transit_stock", "scrap_stock", "finished_goods"]}
    
    item_groups, variant_codes = [], []
    
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            item_groups.append("Metal - V"); variant_codes.append("M")
        elif rm_type == "Diamond":
            item_groups.append("Diamond - V"); variant_codes.append("D")
        elif rm_type == "Gemstone":
            item_groups.append("Gemstone - V"); variant_codes.append("G")
        elif rm_type == "Finding":
            item_groups.append("Finding - V"); variant_codes.append("F")
    
    today = getdate()
    branch_condition = f"AND mwo.branch = '{branch}'" if company == "Gurukrupa Export Private Limited" and branch else ""
    
    # FIXED: All stock calculations with correct Transit Stock logic (SLE balance)
    stock_values['work_order_stock'] = get_work_order_stock_by_manufacturing_operations(company, dept_with_suffix, raw_material_types, today)
    stock_values['transit_stock'] = get_transit_stock_balance(company, dept_with_suffix, item_groups, today)  # FIXED: SLE balance
    
    if item_groups:
        item_group_str = "', '".join(item_groups)
        stock_values['raw_material_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Raw Material")
        stock_values['reserve_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Reserve")
        stock_values['scrap_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Scrap")
        stock_values['supplier_wip_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Sub Contracting WO")
        stock_values['supplier_msl_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Sub Contracting RM")
        stock_values['supplier_msl_hold_stock'] = get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, today, "Sub Contracting Transit")
        
        # Finished goods calculation - No rounding
        try:
            finished_result = frappe.db.sql(f"""
                SELECT COUNT(*) as total_count 
                FROM `tabSerial No` sn
                LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name
                WHERE sn.company = '{company}' 
                  AND sn.status = 'Active' 
                  AND w.department = '{dept_with_suffix}'
            """, as_dict=True)
            if finished_result and finished_result[0].get("total_count"):
                stock_values['finished_goods'] = float(finished_result[0]['total_count'])  # REMOVED flt()
        except:
            pass
    
    # Employee WIP calculation - No rounding
    weight_fields = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": 
            weight_fields.append("COALESCE(mop.net_wt, 0)")
        elif rm_type == "Diamond": 
            weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
        elif rm_type == "Gemstone": 
            weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
        elif rm_type == "Finding": 
            weight_fields.append("COALESCE(mop.finding_wt, 0)")
    
    if weight_fields:
        weight_sum = " + ".join(weight_fields)
        try:
            wip_result = frappe.db.sql(f"""
                SELECT SUM({weight_sum}) as total_weight FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
                LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
                LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
                WHERE mop.status = 'WIP' AND ms.employee IS NOT NULL AND ms.for_subcontracting = 0
                  AND ms.department = '{dept_with_suffix}' AND mwo.company = '{company}' {branch_condition}
                  AND mwo.docstatus = 1 AND mop.department = '{dept_with_suffix}'
            """, as_dict=True)
            if wip_result and wip_result[0].get('total_weight'):
                stock_values['employee_wip_stock'] = float(wip_result[0]['total_weight'])  # REMOVED flt()
        except:
            pass
    
    # MSL Stock calculation - No rounding
    if variant_codes:
        variant_code_str = "', '".join(variant_codes)
        try:
            msl_result = frappe.db.sql(f"""
                SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent
                WHERE ms.workflow_state = 'In Use' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}'
                  AND ld.variant_of IN ('{variant_code_str}') AND ld.msl_qty > 0
            """, as_dict=True)
            if msl_result and msl_result[0].get('total_qty'):
                stock_values['employee_msl_stock'] = float(msl_result[0]['total_qty'])  # REMOVED flt()
                
            msl_hold_result = frappe.db.sql(f"""
                SELECT SUM(ld.msl_qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabLoss Details` ld ON ms.name = ld.parent
                WHERE ms.workflow_state = 'On Hold' AND ms.employee IS NOT NULL AND ms.department = '{dept_with_suffix}'
                  AND ld.variant_of IN ('{variant_code_str}') AND ld.msl_qty > 0
            """, as_dict=True)
            if msl_hold_result and msl_hold_result[0].get('total_qty'):
                stock_values['employee_msl_hold_stock'] = float(msl_hold_result[0]['total_qty'])  # REMOVED flt()
        except:
            pass
    
    return stock_values

# FIXED: Department totals - No rounding, exact sum
def add_department_total_row_simplified(data, section_data, label):
    # FIXED: No rounding - exact sum only
    total_quantity = sum(float(row.get("quantity", 0.0)) for row in section_data if row.get("parent_section") and row.get("quantity") != "" and row.get("quantity") != 0)
    display_total = "" if total_quantity == 0 else total_quantity
    data.append({
        "section_name": f"{label}", 
        "section": label, 
        "parent_section": None, 
        "indent": 0.0, 
        "quantity": display_total, 
        "view_details": "", 
        "is_department_total": True
    })
    return total_quantity

def get_weight_sum(raw_material_types):
    weight_fields = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": weight_fields.append("COALESCE(mop.net_wt, 0)")
        elif rm_type == "Diamond": weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
        elif rm_type == "Gemstone": weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
        elif rm_type == "Finding": weight_fields.append("COALESCE(mop.finding_wt, 0)")
    return " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"

def get_item_groups(raw_material_types):
    item_groups = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": item_groups.append("Metal - V")
        elif rm_type == "Diamond": item_groups.append("Diamond - V")
        elif rm_type == "Gemstone": item_groups.append("Gemstone - V")
        elif rm_type == "Finding": item_groups.append("Finding - V")
    return item_groups

def get_variant_codes(raw_material_types):
    variant_codes = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": variant_codes.append("M")
        elif rm_type == "Diamond": variant_codes.append("D")
        elif rm_type == "Gemstone": variant_codes.append("G")
        elif rm_type == "Finding": variant_codes.append("F")
    return variant_codes

# DETAIL FUNCTIONS - ALL FIXED:

def get_raw_material_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            return frappe.db.sql(f"""
                SELECT 
                    sle.item_code as 'Item Code', 
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name 
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' AND w.department = '{department}' AND w.warehouse_type = 'Raw Material'
                  AND i.item_group IN ('{item_group_str}') AND sle.posting_date <= '{getdate()}' AND sle.docstatus < 2 AND sle.is_cancelled = 0
                GROUP BY sle.item_code HAVING SUM(sle.actual_qty) > 0 ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True)
        return []
    except: return []

def get_reserve_stock_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            return frappe.db.sql(f"""
                SELECT 
                    sle.item_code as 'Item Code', 
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name 
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' AND w.department = '{department}' AND w.warehouse_type = 'Reserve'
                  AND i.item_group IN ('{item_group_str}') AND sle.posting_date <= '{getdate()}' AND sle.docstatus < 2 AND sle.is_cancelled = 0
                GROUP BY sle.item_code HAVING SUM(sle.actual_qty) > 0 ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True)
        return []
    except: return []

def get_work_order_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        branch_condition = f"AND mwo.branch = '{branch}'" if company == "Gurukrupa Export Private Limited" and branch else ""
        
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status IN ('Open', 'Not Started') 
              AND mop.department = '{department}' 
              AND mwo.company = '{company}' {branch_condition}
              AND mwo.docstatus = 1 
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Work order details error: {str(e)}")
        return []

def get_employee_wip_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        branch_condition = f"AND mwo.branch = '{branch}'" if company == "Gurukrupa Export Private Limited" and branch else ""
        
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name'
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            WHERE mop.status = 'WIP' 
              AND ms.employee IS NOT NULL 
              AND ms.for_subcontracting = 0
              AND ms.department = '{department}'
              AND mwo.company = '{company}' {branch_condition}
              AND mwo.docstatus = 1
              AND mop.department = '{department}'
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True)
    except: return []

def get_supplier_wip_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")  # CARATS
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")  # CARATS
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        branch_condition = f"AND mwo.branch = '{branch}'" if company == "Gurukrupa Export Private Limited" and branch else ""
        
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name'
            FROM `tabMain Slip` ms
            LEFT JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            LEFT JOIN `tabManufacturing Work Order` mwo ON mwo.name = mso.manufacturing_work_order
            LEFT JOIN `tabManufacturing Operation` mop ON mop.name = mso.manufacturing_operation
            LEFT JOIN `tabSupplier` sup ON ms.supplier = sup.name
            WHERE mop.status = 'WIP' 
              AND ms.supplier IS NOT NULL 
              AND ms.for_subcontracting = 1
              AND ms.department = '{department}'
              AND mwo.company = '{company}' {branch_condition}
              AND mwo.docstatus = 1
              AND mop.department = '{department}'
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True)
    except: return []

def get_employee_msl_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    ld.msl_qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabLoss Details` ld ON ms.name = ld.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.employee IS NOT NULL 
                  AND ms.department = '{department}'
                  AND ld.variant_of IN ('{variant_code_str}')
                  AND ld.msl_qty > 0
                ORDER BY ld.msl_qty DESC
            """, as_dict=True)
        return []
    except Exception as e:
        frappe.log_error(f"Employee MSL details error: {str(e)}")
        return []

def get_supplier_msl_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    ld.msl_qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabLoss Details` ld ON ms.name = ld.parent
                LEFT JOIN `tabSupplier` sup ON ms.supplier = sup.name
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.supplier IS NOT NULL 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND ld.variant_of IN ('{variant_code_str}')
                  AND ld.msl_qty > 0
                ORDER BY ld.msl_qty DESC
            """, as_dict=True)
        return []
    except: return []

def get_employee_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    ld.msl_qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabLoss Details` ld ON ms.name = ld.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.employee IS NOT NULL 
                  AND ms.department = '{department}'
                  AND ld.variant_of IN ('{variant_code_str}')
                  AND ld.msl_qty > 0
                ORDER BY ld.msl_qty DESC
            """, as_dict=True)
        return []
    except: return []

def get_supplier_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(sup.supplier_name, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    ld.msl_qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabLoss Details` ld ON ms.name = ld.parent
                LEFT JOIN `tabSupplier` sup ON ms.supplier = sup.name
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.supplier IS NOT NULL 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND ld.variant_of IN ('{variant_code_str}')
                  AND ld.msl_qty > 0
                ORDER BY ld.msl_qty DESC
            """, as_dict=True)
        return []
    except: return []

# FIXED: Transit Stock Details - Show current stock items in Transit warehouse (matches SLE balance)
def get_transit_stock_details(department, company, branch, manufacturer, raw_material_types):
    """FIXED: Show current stock items in Transit warehouse (matches SLE balance)"""
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            return frappe.db.sql(f"""
                SELECT 
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Current Balance',
                    w.warehouse_name as 'Transit Warehouse'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND w.department = '{department}'
                  AND w.warehouse_type = 'Transit'
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code, sle.warehouse
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True)
        return []
    except Exception as e:
        frappe.log_error(f"Transit stock details error: {str(e)}")
        return []

# FIXED: Scrap Stock Details - Keep blank if no employee/operation found
def get_scrap_stock_details(department, company, branch, manufacturer, raw_material_types):
    """FIXED: Keep Operation and Employee blank if not found"""
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            
            # Get scrap stock with simplified employee lookup
            scrap_data = frappe.db.sql(f"""
                SELECT 
                    sle.item_code,
                    SUM(sle.actual_qty) as total_qty,
                    w.department
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
                  AND w.department = '{department}'
                  AND w.warehouse_type = 'Scrap'
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.actual_qty > 0
                GROUP BY sle.item_code, w.department
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True)
            
            # For each scrap item, find the most recent employee operation
            result = []
            for item in scrap_data:
                # Get most recent employee for this department
                employee_data = frappe.db.sql(f"""
                    SELECT 
                        emp.employee_name,
                        mop.operation
                    FROM `tabMain Slip` ms
                    INNER JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
                    INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                    LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                    WHERE ms.department = '{department}' 
                      AND ms.employee IS NOT NULL
                      AND mop.operation IS NOT NULL
                    ORDER BY ms.creation DESC
                    LIMIT 1
                """, as_dict=True)
                
                # FIXED: Keep blank if not found, no fallback text
                operation = employee_data[0]['operation'] if employee_data and employee_data[0].get('operation') else ""
                employee = employee_data[0]['employee_name'] if employee_data and employee_data[0].get('employee_name') else ""
                
                result.append({
                    'Item Code': item['item_code'],
                    'Qty': item['total_qty'],
                    'Department': item['department'],
                    'Operation': operation,
                    'Employee': employee
                })
            
            return result
        return []
    except Exception as e:
        frappe.log_error(f"Scrap stock details error: {str(e)}")
        return []

def get_finished_goods_details(department, company, branch, manufacturer, raw_material_types):
    try:
        return frappe.db.sql(f"""
            SELECT 
                sn.name as 'Serial No',
                sn.item_code as 'Item Code',
                COALESCE(i.item_category, i.item_group, 'N/A') as 'Item Category',
                1 as 'Quantity',
                w.department as 'Department'
            FROM `tabSerial No` sn
            LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name
            LEFT JOIN `tabItem` i ON sn.item_code = i.item_code
            WHERE sn.company = '{company}' 
              AND sn.status = 'Active' 
              AND w.department = '{department}'
            ORDER BY sn.creation DESC
            LIMIT 100
        """, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Finished goods details error: {str(e)}")
        return []

@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    dept_mapping = {
        "Siddhi": ["Nandi"], "Service Center": ["Product Repair Center"],
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"],
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"],
        "Labh": ["Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Diamond Setting", "Final Polish", "Manufacturing Plan & Management", "Model Making", "Pre Polish", "Product Certification", "Sub Contracting", "Tagging", "Waxing"],
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology Data Analysis", "Item Bom Management", "Learning Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales", "Sales Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }
    return dept_mapping.get(manufacturer, [])

@frappe.whitelist()
def get_stock_details(department, stock_type, stock_key, filters=None):
    try:
        if isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        company, branch, raw_material_types = (filters.get("company"), filters.get("branch", ""), [filters.get("raw_material_type")] if filters.get("raw_material_type") else ["Metal"])
        dept_with_suffix = f"{department} - GEPL" if company == "Gurukrupa Export Private Limited" else f"{department} - KGJPL"
        manufacturer = filters.get("manufacturer", "")
        
        detail_functions = {
            'work_order_stock': get_work_order_details, 'employee_wip_stock': get_employee_wip_details, 'supplier_wip_stock': get_supplier_wip_details,
            'employee_msl_stock': get_employee_msl_details, 'supplier_msl_stock': get_supplier_msl_details, 'employee_msl_hold_stock': get_employee_msl_hold_details,
            'supplier_msl_hold_stock': get_supplier_msl_hold_details, 'raw_material_stock': get_raw_material_details, 'reserve_stock': get_reserve_stock_details,
            'transit_stock': get_transit_stock_details, 'scrap_stock': get_scrap_stock_details, 'finished_goods': get_finished_goods_details
        }
        
        result = detail_functions.get(stock_key, lambda *args: [])(dept_with_suffix, company, branch, manufacturer, raw_material_types)
        return result
    except Exception as e:
        frappe.log_error(f"Stock details error: {str(e)}")
        return []
