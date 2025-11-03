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
    
    if grand_total > 0:
        data.append({
            "section_name": "Grand Total", 
            "section": "Grand Total", 
            "parent_section": None, 
            "indent": 0.0, 
            "quantity": grand_total,
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
        display_value = "" if stock_value == 0 or stock_value == 0.0 else stock_value
        
        # View Details button
        view_button = f'<button class="btn btn-xs btn-primary view-stock-details" data-department="{dept_name}" data-stock-type="{stock_type["label"]}" data-stock-key="{stock_type["key"]}">View</button>'
        
        section_data.append({
            "section_name": stock_type["label"], "section": stock_type["label"], "parent_section": dept_name, "indent": 1.0,
            "quantity": display_value, "view_details": view_button,
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

def get_department_stock_values(dept_with_suffix, company, branch, manufacturer, raw_material_types=None):
    if not raw_material_types:
        raw_material_types = ["Metal"]
    
    stock_values = {k: 0.0 for k in ["work_order_stock", "employee_wip_stock", "supplier_wip_stock", "employee_msl_stock", "supplier_msl_stock", "employee_msl_hold_stock", "supplier_msl_hold_stock", "raw_material_stock", "reserve_stock", "transit_stock", "scrap_stock", "finished_goods"]}
    
    # FIXED: Correct item groups and better handling for Other Material
    item_groups, variant_codes = [], []
    
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            item_groups.extend(["Metal - V", "Metal DNU"]); variant_codes.append("M")
        elif rm_type == "Diamond":
            item_groups.extend(["Diamond - V", "Diamond DNU"]); variant_codes.append("D")
        elif rm_type == "Gemstone":
            item_groups.extend(["Gemstone - V", "Gemstone DNU"]); variant_codes.append("G")
        elif rm_type == "Finding":
            item_groups.extend(["Finding - V", "Finding DNU", "Finding - T"]); variant_codes.append("F")
        elif rm_type == "Aloy":
            item_groups.extend(["Alloy"]); variant_codes.append("A")
        elif rm_type == "Other":  # FIXED: Better Other material handling
            item_groups.extend(["Other Material - V", "Other Material - T", "Other - V", "Other DNU", "Other Material"]); variant_codes.append("O")
    
    today = getdate()
    
    # FIXED: Finished goods calculation - independent of raw material type but ensure consistency
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
            stock_values['finished_goods'] = float(finished_result[0]['total_count'])
    except:
        pass
    
    if item_groups:
        # FIXED: Use combined approach for all stock calculations
        stock_values['work_order_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "work_order")
        stock_values['employee_wip_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "employee_wip")
        stock_values['supplier_wip_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "supplier_wip")
        stock_values['transit_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "transit")
        stock_values['raw_material_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "raw_material")
        stock_values['reserve_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "reserve")
        stock_values['scrap_stock'] = get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, today, "scrap")
    
    # FIXED: MSL calculations using proper table structure and for_subcontracting logic (REMOVED docstatus = 1)
    if variant_codes:
        variant_code_str = "', '".join(variant_codes)
        try:
            # FIXED: Employee MSL Stock - for_subcontracting = 0 (REMOVED docstatus = 1)
            msl_result = frappe.db.sql(f"""
                SELECT SUM(mse.qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.for_subcontracting = 0
                  AND ms.department = '{dept_with_suffix}'
                  AND mse.variant_of IN ('{variant_code_str}') 
                  AND mse.qty > 0
            """, as_dict=True)
            if msl_result and msl_result[0].get('total_qty'):
                stock_values['employee_msl_stock'] += float(msl_result[0]['total_qty'])
                
            # FIXED: Employee MSL Hold Stock - for_subcontracting = 0 (REMOVED docstatus = 1)
            msl_hold_result = frappe.db.sql(f"""
                SELECT SUM(mse.qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.for_subcontracting = 0
                  AND ms.department = '{dept_with_suffix}'
                  AND mse.variant_of IN ('{variant_code_str}') 
                  AND mse.qty > 0
            """, as_dict=True)
            if msl_hold_result and msl_hold_result[0].get('total_qty'):
                stock_values['employee_msl_hold_stock'] += float(msl_hold_result[0]['total_qty'])
                
            # FIXED: Supplier MSL Stock - for_subcontracting = 1 (REMOVED docstatus = 1)
            supplier_msl_result = frappe.db.sql(f"""
                SELECT SUM(mse.qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{dept_with_suffix}'
                  AND mse.variant_of IN ('{variant_code_str}') 
                  AND mse.qty > 0
            """, as_dict=True)
            if supplier_msl_result and supplier_msl_result[0].get('total_qty'):
                stock_values['supplier_msl_stock'] += float(supplier_msl_result[0]['total_qty'])
                
            # FIXED: Supplier MSL Hold Stock - for_subcontracting = 1 (REMOVED docstatus = 1)
            supplier_msl_hold_result = frappe.db.sql(f"""
                SELECT SUM(mse.qty) as total_qty FROM `tabMain Slip` ms
                LEFT JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{dept_with_suffix}'
                  AND mse.variant_of IN ('{variant_code_str}') 
                  AND mse.qty > 0
            """, as_dict=True)
            if supplier_msl_hold_result and supplier_msl_hold_result[0].get('total_qty'):
                stock_values['supplier_msl_hold_stock'] += float(supplier_msl_hold_result[0]['total_qty'])
                
        except Exception as e:
            frappe.log_error(f"MSL calculation error: {str(e)}")
            pass
    
    return stock_values

# FIXED: Updated approach matching Work Order logic for Employee/Supplier WIP
def get_combined_stock_calculation(company, dept_with_suffix, item_groups, raw_material_types, to_date, stock_type):
    if not item_groups:
        return 0.0
    
    warehouse_stock = 0.0
    
    item_group_str = "', '".join(item_groups)
    dept_clean = dept_with_suffix.split(' - ')[0]
    
    # Warehouse-based calculations
    try:
        if stock_type == "work_order":
            # FIXED: Simple approach - All "Not Started" operations
            weight_fields = []
            for rm_type in raw_material_types:
                if rm_type == "Metal": 
                    weight_fields.append("COALESCE(mop.net_wt, 0)")
                elif rm_type == "Diamond": 
                    weight_fields.append("COALESCE(mop.diamond_wt, 0)")
                elif rm_type == "Gemstone": 
                    weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
                elif rm_type == "Finding": 
                    weight_fields.append("COALESCE(mop.finding_wt, 0)")
                elif rm_type == "Aloy": 
                    weight_fields.append("COALESCE(mop.alloy_wt, 0)")
                elif rm_type == "Other":
                    weight_fields.append("COALESCE(mop.other_wt, 0)")
            
            weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
            
            warehouse_result = frappe.db.sql(f"""
                SELECT SUM({weight_sum}) as total_balance
                FROM `tabManufacturing Operation` mop
                LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
                WHERE mop.status = 'Not Started'
                  AND mop.department = '{dept_with_suffix}' 
                  AND mwo.company = '{company}'
                  AND mwo.docstatus = 1
            """, as_dict=True)
            
        elif stock_type == "employee_wip":
            # FIXED: Use same approach as Work Order - All "WIP" operations where for_subcontracting = 0
            weight_fields = []
            for rm_type in raw_material_types:
                if rm_type == "Metal": 
                    weight_fields.append("COALESCE(mop.net_wt, 0)")
                elif rm_type == "Diamond": 
                    weight_fields.append("COALESCE(mop.diamond_wt, 0)")
                elif rm_type == "Gemstone": 
                    weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
                elif rm_type == "Finding": 
                    weight_fields.append("COALESCE(mop.finding_wt, 0)")
                elif rm_type == "Aloy": 
                    weight_fields.append("COALESCE(mop.alloy_wt, 0)")
                elif rm_type == "Other":
                    weight_fields.append("COALESCE(mop.other_wt, 0)")
            
            weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
            
            warehouse_result = frappe.db.sql(f"""
                SELECT SUM({weight_sum}) as total_balance
                FROM `tabManufacturing Operation` mop
                LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
                WHERE mop.status = 'WIP'
                  AND mop.for_subcontracting = 0
                  AND mop.department = '{dept_with_suffix}' 
                  AND mwo.company = '{company}'
                  AND mwo.docstatus = 1
            """, as_dict=True)
            
        elif stock_type == "supplier_wip":
            # FIXED: Use same approach - All "WIP" operations where for_subcontracting = 1
            weight_fields = []
            for rm_type in raw_material_types:
                if rm_type == "Metal": 
                    weight_fields.append("COALESCE(mop.net_wt, 0)")
                elif rm_type == "Diamond": 
                    weight_fields.append("COALESCE(mop.diamond_wt, 0)")
                elif rm_type == "Gemstone": 
                    weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
                elif rm_type == "Finding": 
                    weight_fields.append("COALESCE(mop.finding_wt, 0)")
                elif rm_type == "Aloy": 
                    weight_fields.append("COALESCE(mop.alloy_wt, 0)")
                elif rm_type == "Other":
                    weight_fields.append("COALESCE(mop.other_wt, 0)")
            
            weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
            
            warehouse_result = frappe.db.sql(f"""
                SELECT SUM({weight_sum}) as total_balance
                FROM `tabManufacturing Operation` mop
                LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
                WHERE mop.status = 'WIP'
                  AND mop.for_subcontracting = 1
                  AND mop.department = '{dept_with_suffix}' 
                  AND mwo.company = '{company}'
                  AND mwo.docstatus = 1
            """, as_dict=True)
            
        elif stock_type == "transit":
            warehouse_result = frappe.db.sql(f"""
                SELECT SUM(sle.actual_qty) as total_balance
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND w.warehouse_name LIKE '%{dept_clean} Transit%'
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{to_date}'
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
            """, as_dict=True)
            
        elif stock_type in ["raw_material", "reserve", "scrap"]:
            warehouse_type_map = {"raw_material": "Raw Material", "reserve": "Reserve", "scrap": "Scrap"}
            warehouse_result = frappe.db.sql(f"""
                SELECT SUM(sle.actual_qty) as total_balance
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name  
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND w.department = '{dept_with_suffix}'
                  AND w.warehouse_type = '{warehouse_type_map[stock_type]}'
                  AND i.item_group IN ('{item_group_str}') 
                  AND sle.posting_date <= '{to_date}' 
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
            """, as_dict=True)
        
        if warehouse_result and warehouse_result[0].get('total_balance'):
            warehouse_stock = warehouse_result[0]['total_balance']
    except Exception as e:
        frappe.log_error(f"Warehouse stock calculation error for {stock_type}: {str(e)}")
        pass
    
    return warehouse_stock if warehouse_stock > 0 else 0.0

def get_stock_balance_using_sle_logic(company, dept_with_suffix, item_groups, to_date, warehouse_type):
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
              AND w.warehouse_type = '{warehouse_type}'
              AND i.item_group IN ('{item_group_str}') 
              AND sle.posting_date <= '{to_date}' 
              AND sle.docstatus < 2 
              AND sle.is_cancelled = 0
        """, as_dict=True)
        
        return result[0]['total_balance'] if result and result[0].get('total_balance') and result[0]['total_balance'] > 0 else 0.0
    except Exception as e:
        frappe.log_error(f"Stock balance error: {str(e)}")
        return 0.0

def add_department_total_row_simplified(data, section_data, label):
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

def get_item_groups(raw_material_types):
    item_groups = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": 
            item_groups.extend(["Metal - V", "Metal DNU"])
        elif rm_type == "Diamond": 
            item_groups.extend(["Diamond - V", "Diamond DNU"])
        elif rm_type == "Gemstone": 
            item_groups.extend(["Gemstone - V", "Gemstone DNU"])
        elif rm_type == "Finding": 
            item_groups.extend(["Finding - V", "Finding DNU", "Finding - T"])
        elif rm_type == "Aloy": 
            item_groups.extend(["Alloy"])
        elif rm_type == "Other": 
            item_groups.extend(["Other Material - V", "Other Material - T", "Other - V", "Other DNU", "Other Material"])
    return item_groups

def get_variant_codes(raw_material_types):
    variant_codes = []
    for rm_type in raw_material_types:
        if rm_type == "Metal": variant_codes.append("M")
        elif rm_type == "Diamond": variant_codes.append("D")
        elif rm_type == "Gemstone": variant_codes.append("G")
        elif rm_type == "Finding": variant_codes.append("F")
        elif rm_type == "Aloy": variant_codes.append("A")
        elif rm_type == "Other": variant_codes.append("O")
    return variant_codes

# VIEW DETAILS FUNCTIONS - ALL CORRECTED WITH LATEST FIXES

def get_raw_material_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Raw Material Stock: Item Code, Weight"""
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
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Raw material details error: {str(e)}")
        return []

def get_reserve_stock_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Reserve Stock: Item Code, Weight"""
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
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Reserve stock details error: {str(e)}")
        return []

def get_work_order_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Work Order Stock: Manufacturing Work Order, Weight (raw material type wise)"""
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy": 
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        
        # FIXED: Simple approach - All "Not Started" operations (NO LIMIT)
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'Not Started'
              AND mop.department = '{department}' 
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True, debug=0)
    except Exception as e:
        frappe.log_error(f"Work order details error: {str(e)}")
        return []

def get_employee_wip_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Employee WIP Stock: Manufacturing Work Order, Weight (raw material type wise), Operation, Employee Name"""
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy": 
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        
        # FIXED: Employee WIP uses for_subcontracting = 0
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 0
              AND mop.department = '{department}' 
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1 
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True, debug=0)
        
    except Exception as e:
        frappe.log_error(f"Employee WIP details error: {str(e)}")
        return []

def get_supplier_wip_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Supplier WIP Stock: Manufacturing Work Order, Weight (raw material type wise), Operation, Supplier Name"""
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal": 
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond": 
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone": 
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding": 
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy": 
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")
        
        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        
        # FIXED: Supplier WIP uses for_subcontracting = 1
        return frappe.db.sql(f"""
            SELECT 
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                'Supplier Operation' as 'Supplier Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 1
              AND mop.department = '{department}' 
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1 
              AND ({weight_sum}) > 0
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True)
        
    except Exception as e:
        frappe.log_error(f"Supplier WIP details error: {str(e)}")
        return []

def get_employee_msl_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Employee MSL Stock: Main Slip, Employee Name, Department, Operation, Weight (raw material type wise)"""
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            # FIXED: Employee MSL should have for_subcontracting = 0 (REMOVED docstatus = 1)
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
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  AND ms.for_subcontracting = 0
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Employee MSL details error: {str(e)}")
        return []

def get_supplier_msl_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Supplier MSL Stock: Main Slip, Supplier Name, Department, Operation, Weight (raw material type wise)"""
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            # FIXED: Supplier MSL should have for_subcontracting = 1 (REMOVED docstatus = 1)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(ms.subcontractor, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use' 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Supplier MSL details error: {str(e)}")
        return []

def get_employee_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Employee MSL Hold Stock: Main Slip, Employee Name, Department, Operation, Weight (raw material type wise)"""
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            # FIXED: Employee MSL Hold should have for_subcontracting = 0 (REMOVED docstatus = 1)
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
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  AND ms.for_subcontracting = 0
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Employee MSL Hold details error: {str(e)}")
        return []

def get_supplier_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Supplier MSL Hold Stock: Main Slip, Supplier Name, Department, Operation, Weight (raw material type wise)"""
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            # FIXED: Supplier MSL Hold should have for_subcontracting = 1 (REMOVED docstatus = 1)
            return frappe.db.sql(f"""
                SELECT 
                    ms.name as 'Main Slip',
                    COALESCE(ms.subcontractor, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso 
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1), 
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold' 
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception as e:
        frappe.log_error(f"Supplier MSL Hold details error: {str(e)}")
        return []

def get_transit_stock_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Transit Stock: Stock Entry Type, Source Warehouse, Target Warehouse, Weight (raw material type wise)"""
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            dept_clean = department.split(' - ')[0]
            
            balance_details = frappe.db.sql(f"""
                SELECT 
                    'Current Balance' as 'Stock Entry Type',
                    w.warehouse_name as 'Source Warehouse',
                    'In Transit' as 'Target Warehouse',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND w.warehouse_name LIKE '%{dept_clean} Transit%'
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{getdate()}'
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
                GROUP BY w.warehouse_name
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
                
            return balance_details if balance_details else []
            
        return []
    except Exception as e:
        frappe.log_error(f"Transit stock details error: {str(e)}")
        return []

def get_scrap_stock_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Scrap Stock: Item Code, Qty, Department"""
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            
            return frappe.db.sql(f"""
                SELECT 
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Qty',
                    w.department as 'Department'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}' 
                  AND sle.docstatus < 2 
                  AND sle.is_cancelled = 0
                  AND w.department = '{department}'
                  AND w.warehouse_type = 'Scrap'
                  AND i.item_group IN ('{item_group_str}')
                GROUP BY sle.item_code, w.department
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
            
        return []
    except Exception as e:
        frappe.log_error(f"Scrap stock details error: {str(e)}")
        return []

def get_finished_goods_details(department, company, branch, manufacturer, raw_material_types):
    """🔹 Finished Goods: Department, Item Code, Quantity, Serial No - INDEPENDENT of raw material type"""
    try:
        # FIXED: Use correct column name 'item_subcategory' and proper order like your test result
        dept_clean = department.replace(' - GEPL', '').replace(' - KGJPL', '')
        
        return frappe.db.sql(f"""
            SELECT 
                w.department as 'Department',
                sn.item_code as 'Item Code',
                1 as 'Quantity',
                sn.name as 'Serial No'
            FROM `tabSerial No` sn
            LEFT JOIN `tabWarehouse` w ON sn.warehouse = w.name
            LEFT JOIN `tabItem` i ON sn.item_code = i.item_code
            WHERE sn.company = '{company}' 
              AND sn.status = 'Active' 
              AND (w.department = '{department}' OR w.department LIKE '%{dept_clean}%')
            ORDER BY sn.creation DESC
        """, as_dict=True, debug=0)
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
    """Get detailed stock information for a specific department and stock type"""
    try:
        if isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        company = filters.get("company")
        branch = filters.get("branch", "")
        manufacturer = filters.get("manufacturer", "")
        raw_material_types = [filters.get("raw_material_type")] if filters.get("raw_material_type") else ["Metal"]
        
        if company == "Gurukrupa Export Private Limited":
            if not department.endswith(" - GEPL"):
                dept_with_suffix = f"{department} - GEPL"
            else:
                dept_with_suffix = department
        elif company == "KG GK Jewellers Private Limited":
            if not department.endswith(" - KGJPL"):
                dept_with_suffix = f"{department} - KGJPL"  
            else:
                dept_with_suffix = department
        else:
            dept_with_suffix = department
        
        detail_functions = {
            'work_order_stock': get_work_order_details,
            'employee_wip_stock': get_employee_wip_details,
            'supplier_wip_stock': get_supplier_wip_details,
            'employee_msl_stock': get_employee_msl_details,
            'supplier_msl_stock': get_supplier_msl_details,
            'employee_msl_hold_stock': get_employee_msl_hold_details,
            'supplier_msl_hold_stock': get_supplier_msl_hold_details,
            'raw_material_stock': get_raw_material_details,
            'reserve_stock': get_reserve_stock_details,
            'transit_stock': get_transit_stock_details,
            'scrap_stock': get_scrap_stock_details,
            'finished_goods': get_finished_goods_details
        }
        
        result = detail_functions.get(stock_key, lambda *args: [])(dept_with_suffix, company, branch, manufacturer, raw_material_types)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Stock details error: {str(e)}")
        return []
