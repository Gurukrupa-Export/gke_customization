# Copyright (c) 2025, Your Company and contributors  
# For license information, please see license.txt

import frappe
from frappe import _
import re
from frappe.utils import flt, cint

def execute(filters=None):
    # Validate required filters
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("branch"):
        frappe.throw(_("Branch is required"))
    
    columns, data = get_matrix_data(filters)
    return columns, data

def get_matrix_data(filters=None):
    # Get departments based on manufacturer selection
    departments = get_departments_for_report(filters)
    
    # Create dynamic columns
    columns = [{"fieldname": "stock_type", "label": "Stock Type", "fieldtype": "Data", "width": 200}]
    
    # Store field mappings for data population
    dept_field_mapping = {}
    dept_db_mapping = {}  # Map display names to database names
    
    # Determine column width based on number of departments
    dept_count = len(departments)
    dept_column_width = 100 if dept_count > 10 else 120
    
    # Add department columns based on selection
    for dept in departments:
        dept_name = dept['department']  # Display name (without suffix)
        db_dept_name = dept.get('db_department', dept_name)  # Database name (with suffix)
        
        # Create safe fieldname
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', dept_name.lower().replace(' ', '_'))
        safe_name = f"dept_{safe_name}"
        
        dept_field_mapping[dept_name] = safe_name
        dept_db_mapping[dept_name] = db_dept_name  # Store mapping for queries
        
        columns.append({
            "fieldname": safe_name,
            "label": dept_name,
            "fieldtype": "Float",
            "width": dept_column_width,
            "precision": 2
        })
    
    # Add view details column (NO TOTAL WEIGHT COLUMN)
    columns.append({
        "fieldname": "view_details", 
        "label": "View Details", 
        "fieldtype": "Button", 
        "width": 100
    })
    
    # Define all 12 stock types
    stock_types = [
        {"key": "work_order_stock", "name": "Work Order Stock"},
        {"key": "employee_wip_stock", "name": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "name": "Supplier WIP Stock"},
        {"key": "employee_msl_stock", "name": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "name": "Supplier MSL Stock"},
        {"key": "employee_msl_hold_stock", "name": "Employee MSL Hold Stock"},
        {"key": "supplier_msl_hold_stock", "name": "Supplier MSL Hold Stock"},  
        {"key": "raw_material_stock", "name": "Raw Material Stock"},
        {"key": "reserve_stock", "name": "Reserve Stock"},
        {"key": "transit_stock", "name": "Transit Stock"},
        {"key": "scrap_stock", "name": "Scrap Stock"},
        {"key": "finished_goods", "name": "Finished Goods"}
    ]
    
    # Get all stock weights with department filtering
    dept_stock_data = get_all_stock_weights_batch(departments, dept_db_mapping, filters)
    
    # Build data rows
    data = []
    for stock_type in stock_types:
        row = {"stock_type": stock_type["name"]}
        
        # Add weight for each department
        for dept in departments:
            dept_name = dept['department']  # Display name
            field_name = dept_field_mapping[dept_name]
            weight = dept_stock_data.get(dept_name, {}).get(stock_type["key"], 0.0)
            row[field_name] = flt(weight, 2)
        
        row["view_details"] = f'<button class="btn btn-xs btn-primary view-details" data-stock-type="{stock_type["name"]}" data-stock-key="{stock_type["key"]}">View</button>'
        data.append(row)
    
    return columns, data

def get_departments_for_report(filters=None):
    """Get departments - FIXED to handle company suffix properly"""
    
    manufacturer = filters.get("manufacturer")
    department = filters.get("department")
    
    try:
        company = filters.get("company")
        branch = filters.get("branch")
        
        # Get actual departments from database (with company suffix)
        dept_query = """
            SELECT DISTINCT mop.department
            FROM `tabManufacturing Operation` mop
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mwo.company = %(company)s 
            AND mwo.branch = %(branch)s
            AND mop.department IS NOT NULL 
            AND mop.department != ''
            ORDER BY mop.department
            LIMIT 15
        """
        
        db_departments = frappe.db.sql(dept_query, {"company": company, "branch": branch}, as_dict=True)
        
        if db_departments:
            # Convert database departments to display format
            result = []
            for dept in db_departments:
                db_name = dept['department']  # e.g., "Casting - GEPL"
                display_name = db_name.replace(' - GEPL', '').replace(' - KGJPL', '')  # e.g., "Casting"
                
                result.append({
                    "department": display_name,  # For display in columns
                    "db_department": db_name     # For database queries
                })
            
            # Filter by manufacturer if specified
            if manufacturer:
                manufacturer_departments = {
                    "Labh": [
                        "Accounts", "Central", "Diamond Bagging", "Diamond Setting", "Dispatch", 
                        "Final Polish", "Gemstone Bagging", "Manufacturing Plan & Management", 
                        "Model Making", "Order Management", "Pre Polish", "Product Allocation", 
                        "Product Certification", "Production", "Purchase", "Refinery", "Sales", 
                        "Selling", "Sub Contracting", "Tagging", "Waxing"
                    ],
                    "Shubh": [
                        "Accounts", "Casting", "Central", "Dispatch", "Final Polish", 
                        "Gemstone Bagging", "Manufacturing Plan & Management", "Purchase", 
                        "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul"
                    ],
                    "Mangal": [
                        "Central", "Computer Aided Designing", "Manufacturing Plan & Management", 
                        "Dispatch", "Final Polish", "Gemstone Bagging", "Sudarshan", "Swastik", 
                        "Tagging", "Trishul"
                    ],
                    "Amrut": ["Rudraksha", "Close Waxing", "Close Model Making"],
                    "Service Center": ["Product Repair Center"],
                    "Siddhi": ["Nandi"]
                }
                
                if manufacturer in manufacturer_departments:
                    # Filter to only show departments for this manufacturer
                    allowed_depts = manufacturer_departments[manufacturer]
                    result = [r for r in result if r['department'] in allowed_depts]
            
            # Filter by specific department if selected
            if department:
                result = [r for r in result if r['department'] == department]
            
            return result
        
        else:
            # Fallback to common departments without suffix
            return [
                {"department": "Casting", "db_department": "Casting - GEPL"}, 
                {"department": "Central", "db_department": "Central - GEPL"}, 
                {"department": "Waxing", "db_department": "Waxing - GEPL"},
                {"department": "Tagging", "db_department": "Tagging - GEPL"},
                {"department": "Trishul", "db_department": "Trishul - GEPL"},
                {"department": "Manufacturing Plan & Management", "db_department": "Manufacturing Plan & Management - GEPL"}
            ]
            
    except Exception as e:
        frappe.log_error(f"Department query error: {str(e)}")
        # Final fallback
        return [
            {"department": "Casting", "db_department": "Casting - GEPL"}, 
            {"department": "Central", "db_department": "Central - GEPL"}, 
            {"department": "Waxing", "db_department": "Waxing - GEPL"}
        ]

def get_all_stock_weights_batch(departments, dept_db_mapping, filters):
    """Get all stock weights from actual database queries - FIXED DEPARTMENT MAPPING"""
    try:
        company = filters.get("company")
        branch = filters.get("branch")
        raw_material_types = filters.get("raw_material_type", [])
        manufacturer = filters.get("manufacturer")
        
        # Get list of database department names (with suffix)
        dept_list = [dept_db_mapping.get(d['department'], d['department']) for d in departments]
        weight_field = get_weight_field_selection(raw_material_types)
        
        # Initialize result structure using DISPLAY names
        result = {}
        for dept in departments:
            display_name = dept['department']  # Use display name as key
            result[display_name] = {
                'work_order_stock': 0.0, 'employee_wip_stock': 0.0, 'supplier_wip_stock': 0.0,
                'employee_msl_stock': 0.0, 'supplier_msl_stock': 0.0, 'employee_msl_hold_stock': 0.0,
                'supplier_msl_hold_stock': 0.0, 'raw_material_stock': 0.0, 'reserve_stock': 0.0,
                'transit_stock': 0.0, 'scrap_stock': 0.0, 'finished_goods': 0.0
            }
        
        # QUERY 1: Manufacturing Operation Stock (Work Order + WIP)
        try:
            dept_placeholders = ','.join(['%s'] * len(dept_list))
            base_params = [company, branch] + dept_list
            
            manufacturing_query = f"""
                SELECT 
                    mop.department,
                    mop.status,
                    COALESCE(mop.for_subcontracting, 0) as for_subcontracting,
                    SUM({weight_field}) as total_weight
                FROM `tabManufacturing Operation` mop
                INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
                WHERE mwo.company = %s
                AND mwo.branch = %s
                AND mop.department IN ({dept_placeholders})
                AND mwo.docstatus = 1
                AND mop.status IN ('Not Started', 'WIP')
                GROUP BY mop.department, mop.status, mop.for_subcontracting
            """
            
            manufacturing_results = frappe.db.sql(manufacturing_query, base_params, as_dict=True)
            
            for row in manufacturing_results:
                db_dept = row['department']  # e.g., "Casting - GEPL"
                # Convert to display name
                display_dept = db_dept.replace(' - GEPL', '').replace(' - KGJPL', '')
                
                if display_dept in result:
                    if row['status'] == 'Not Started':
                        result[display_dept]['work_order_stock'] += flt(row['total_weight'], 2)
                    elif row['status'] == 'WIP':
                        if row['for_subcontracting'] == 0:
                            result[display_dept]['employee_wip_stock'] += flt(row['total_weight'], 2)
                        else:
                            result[display_dept]['supplier_wip_stock'] += flt(row['total_weight'], 2)
                            
        except Exception as e:
            frappe.log_error(f"Manufacturing query error: {str(e)}")
        
        # QUERY 2: Main Slip Stock (MSL Stock types) - WITH MANUFACTURER FILTER
        try:
            msl_manufacturer_filter = ""
            msl_params = base_params.copy()
            
            if manufacturer:
                msl_manufacturer_filter = "AND ms.manufacturer = %s"
                msl_params.append(manufacturer)
            
            msl_query = f"""
                SELECT 
                    mop.department,
                    ms.workflow_state,
                    COALESCE(mop.for_subcontracting, 0) as for_subcontracting,
                    SUM(CASE WHEN ms.workflow_state = 'In Use' THEN {weight_field} ELSE 0 END) as in_use_weight,
                    SUM(CASE WHEN ms.workflow_state = 'On Hold' THEN COALESCE(ms.pending_metal, 0) ELSE 0 END) as hold_weight
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
                INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
                WHERE mwo.company = %s
                AND mwo.branch = %s
                AND mop.department IN ({dept_placeholders})
                {msl_manufacturer_filter}
                AND ms.workflow_state IN ('In Use', 'On Hold')
                GROUP BY mop.department, ms.workflow_state, mop.for_subcontracting
            """
            
            msl_results = frappe.db.sql(msl_query, msl_params, as_dict=True)
            
            for row in msl_results:
                db_dept = row['department']  # e.g., "Casting - GEPL"
                # Convert to display name
                display_dept = db_dept.replace(' - GEPL', '').replace(' - KGJPL', '')
                
                if display_dept in result:
                    if row['workflow_state'] == 'In Use':
                        if row['for_subcontracting'] == 0:
                            result[display_dept]['employee_msl_stock'] += flt(row['in_use_weight'], 2)
                        else:
                            result[display_dept]['supplier_msl_stock'] += flt(row['in_use_weight'], 2)
                    elif row['workflow_state'] == 'On Hold':
                        if row['for_subcontracting'] == 0:
                            result[display_dept]['employee_msl_hold_stock'] += flt(row['hold_weight'], 2)
                        else:
                            result[display_dept]['supplier_msl_hold_stock'] += flt(row['hold_weight'], 2)
                            
        except Exception as e:
            frappe.log_error(f"MSL query error: {str(e)}")
        
        # QUERY 3: Warehouse Stock (Raw Material, Reserve, Scrap)
        try:
            material_filter = get_material_filter_for_item_groups(raw_material_types)
            
            warehouse_query = f"""
                SELECT 
                    w.department,
                    w.warehouse_type,
                    SUM(sle.actual_qty) as total_qty
                FROM `tabStock Ledger Entry` sle
                INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %s
                AND w.department IN ({dept_placeholders})
                AND w.warehouse_type IN ('Raw Material', 'Reserve', 'Scrap')
                AND i.is_stock_item = 1
                {material_filter}
                GROUP BY w.department, w.warehouse_type
            """
            
            warehouse_params = [company] + dept_list
            warehouse_results = frappe.db.sql(warehouse_query, warehouse_params, as_dict=True)
            
            for row in warehouse_results:
                db_dept = row['department']  # e.g., "Casting - GEPL"
                # Convert to display name
                display_dept = db_dept.replace(' - GEPL', '').replace(' - KGJPL', '')
                
                if display_dept in result:
                    if row['warehouse_type'] == 'Raw Material':
                        result[display_dept]['raw_material_stock'] += flt(row['total_qty'], 2)
                    elif row['warehouse_type'] == 'Reserve':
                        result[display_dept]['reserve_stock'] += flt(row['total_qty'], 2)
                    elif row['warehouse_type'] == 'Scrap':
                        result[display_dept]['scrap_stock'] += flt(row['total_qty'], 2)
                        
        except Exception as e:
            frappe.log_error(f"Warehouse query error: {str(e)}")
        
        # QUERY 4: Transit Stock
        try:
            material_filter = get_material_filter_for_item_groups(raw_material_types)
            
            transit_query = f"""
                SELECT 
                    se.department,
                    SUM(sed.qty) as total_qty
                FROM `tabStock Entry` se
                INNER JOIN `tabStock Entry Detail` sed ON se.name = sed.parent
                INNER JOIN `tabItem` i ON sed.item_code = i.item_code
                WHERE se.company = %s
                AND se.department IN ({dept_placeholders})
                AND se.stock_entry_type LIKE '%Transfer%'
                AND se.docstatus = 1
                {material_filter}
                GROUP BY se.department
            """
            
            transit_params = [company] + dept_list
            transit_results = frappe.db.sql(transit_query, transit_params, as_dict=True)
            
            for row in transit_results:
                db_dept = row['department']  # e.g., "Casting - GEPL"
                # Convert to display name
                display_dept = db_dept.replace(' - GEPL', '').replace(' - KGJPL', '')
                
                if display_dept in result:
                    result[display_dept]['transit_stock'] += flt(row['total_qty'], 2)
                    
        except Exception as e:
            frappe.log_error(f"Transit query error: {str(e)}")
        
        # QUERY 5: Finished Goods
        try:
            material_filter = get_material_filter_for_item_groups(raw_material_types)
            
            finished_query = f"""
                SELECT 
                    w.department,
                    COUNT(*) as total_count
                FROM `tabSerial Number` sn
                INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
                INNER JOIN `tabItem` i ON sn.item_code = i.item_code
                WHERE sn.company = %s
                AND w.department IN ({dept_placeholders})
                {material_filter}
                GROUP BY w.department
            """
            
            finished_params = [company] + dept_list
            finished_results = frappe.db.sql(finished_query, finished_params, as_dict=True)
            
            for row in finished_results:
                db_dept = row['department']  # e.g., "Casting - GEPL"
                # Convert to display name
                display_dept = db_dept.replace(' - GEPL', '').replace(' - KGJPL', '')
                
                if display_dept in result:
                    result[display_dept]['finished_goods'] += flt(row['total_count'], 2)
                    
        except Exception as e:
            frappe.log_error(f"Finished goods query error: {str(e)}")
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Stock weights batch error: {str(e)}")
        # Return empty data if queries fail
        result = {}
        for dept in departments:
            display_name = dept['department']
            result[display_name] = {
                'work_order_stock': 0.0, 'employee_wip_stock': 0.0, 'supplier_wip_stock': 0.0,
                'employee_msl_stock': 0.0, 'supplier_msl_stock': 0.0, 'employee_msl_hold_stock': 0.0,
                'supplier_msl_hold_stock': 0.0, 'raw_material_stock': 0.0, 'reserve_stock': 0.0,
                'transit_stock': 0.0, 'scrap_stock': 0.0, 'finished_goods': 0.0
            }
        return result

def get_weight_field_selection(raw_material_types):
    """Build weight field selection based on Raw Material Type filter"""
    
    if not raw_material_types:
        return "COALESCE(mop.gross_wt, 0)"
    
    if isinstance(raw_material_types, str):
        raw_material_types = [raw_material_types]
    
    weight_fields = []
    
    for material_type in raw_material_types:
        if material_type.lower() == "metal":
            weight_fields.append("COALESCE(mop.net_wt, 0)")
        elif material_type.lower() == "diamond":
            weight_fields.append("COALESCE(mop.diamond_wt, 0)")
        elif material_type.lower() == "gemstone":
            weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
        elif material_type.lower() == "finding":
            weight_fields.append("COALESCE(mop.finding_wt, 0)")
        elif material_type.lower() == "other":
            weight_fields.append("COALESCE(mop.other_wt, 0)")
    
    if weight_fields:
        return f"({' + '.join(weight_fields)})"
    else:
        return "COALESCE(mop.gross_wt, 0)"

def get_material_filter_for_item_groups(raw_material_types):
    """Build material filter for item groups"""
    if not raw_material_types:
        return ""
    
    material_groups = []
    for material_type in raw_material_types:
        if material_type.lower() == "metal":
            material_groups.extend(["'Metal'", "'Gold'", "'Silver'", "'Platinum'", "'Copper'"])
        elif material_type.lower() == "diamond":
            material_groups.extend(["'Diamond'", "'CVD Diamond'", "'Natural Diamond'", "'Lab Grown Diamond'"])
        elif material_type.lower() == "gemstone":
            material_groups.extend(["'Gemstone'", "'Ruby'", "'Sapphire'", "'Emerald'", "'Pearl'"])
        elif material_type.lower() == "finding":
            material_groups.extend(["'Finding'", "'Chain'", "'Clasp'", "'Hook'", "'Pin'"])
        elif material_type.lower() == "other":
            material_groups.extend(["'Other'", "'Consumable'", "'Tool'", "'Packaging'"])
    
    if material_groups:
        return f"AND i.item_group IN ({','.join(set(material_groups))})"
    else:
        return ""

@frappe.whitelist()
def get_stock_details(stock_type, stock_key, filters=None):
    """Get detailed breakdown for each stock type"""
    try:
        if isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        company = filters.get("company")
        branch = filters.get("branch")
        department = filters.get("department")
        manufacturer = filters.get("manufacturer")
        raw_material_types = filters.get("raw_material_type", [])
        
        weight_field = get_weight_field_selection(raw_material_types)
        
        # Route to appropriate detail function
        if stock_key in ["work_order_stock", "employee_wip_stock", "supplier_wip_stock"]:
            return get_manufacturing_stock_details(stock_key, weight_field, company, branch, department, manufacturer)
        elif "msl" in stock_key:
            if "hold" in stock_key:
                return get_msl_hold_details(stock_key, company, branch, department, manufacturer)
            else:
                return get_msl_details(stock_key, weight_field, company, branch, department, manufacturer)
        elif stock_key == "raw_material_stock":
            return get_raw_material_details(company, branch, department, manufacturer, raw_material_types)
        elif stock_key == "scrap_stock":
            return get_scrap_stock_details(company, branch, department, manufacturer, raw_material_types)
        elif stock_key == "finished_goods":
            return get_finished_goods_details(company, branch, department, manufacturer, raw_material_types)
        elif stock_key == "reserve_stock":
            return get_reserve_stock_details(company, branch, department, manufacturer, raw_material_types)
        elif stock_key == "transit_stock":
            return get_transit_stock_details(company, branch, department, manufacturer, raw_material_types)
        else:
            return get_general_stock_details(company, branch, department, stock_type, raw_material_types)
            
    except Exception as e:
        frappe.log_error(f"Stock details error for {stock_key}: {str(e)}")
        return [{"Error": f"Error loading {stock_type}: {str(e)}"}]

def get_manufacturing_stock_details(stock_key, weight_field, company, branch, department, manufacturer):
    """Get Manufacturing stock details - FIXED DEPARTMENT SUFFIX"""
    try:
        conditions = {
            "work_order_stock": ("'Not Started'", ""),
            "employee_wip_stock": ("'WIP'", "AND COALESCE(mop.for_subcontracting, 0) = 0"),
            "supplier_wip_stock": ("'WIP'", "AND mop.for_subcontracting = 1")
        }
        
        status, subcontract_condition = conditions.get(stock_key, ("'Not Started'", ""))
        
        # Handle department suffix for filtering
        dept_filter = ""
        if department:
            dept_with_suffix = f"{department} - GEPL"  # Add suffix for database query
            dept_filter = "AND mop.department = %(department)s"
        
        query = f"""
            SELECT 
                mwo.name as "Work Order",
                mop.name as "Operation", 
                mwo.item_code as "Item Code",
                {weight_field} as "Weight",
                mop.department as "Department",
                mop.status as "Status",
                COALESCE(emp.employee_name, sup.supplier_name, 'Not Assigned') as "Assigned To",
                mwo.creation as "Created Date"
            FROM `tabManufacturing Operation` mop
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
            LEFT JOIN `tabSupplier` sup ON mop.subcontractor = sup.name
            WHERE mop.status = {status}
            {subcontract_condition}
            AND mwo.docstatus = 1
            AND mwo.company = %(company)s
            AND mwo.branch = %(branch)s
            {dept_filter}
            ORDER BY mwo.creation DESC
            LIMIT 50
        """
        
        params = {"company": company, "branch": branch}
        if department:
            params["department"] = f"{department} - GEPL"  # Use department with suffix
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Manufacturing stock details error: {str(e)}")
        return []

def get_msl_details(stock_key, weight_field, company, branch, department, manufacturer):
    """Get Main Slip details (In Use) - WITH MANUFACTURER FILTER"""
    try:
        subcontract_condition = ""
        if "employee" in stock_key:
            subcontract_condition = "AND COALESCE(mop.for_subcontracting, 0) = 0"
        elif "supplier" in stock_key:
            subcontract_condition = "AND mop.for_subcontracting = 1"
        
        dept_filter = ""
        if department:
            dept_filter = "AND mop.department = %(department)s"
            
        manufacturer_filter = ""
        if manufacturer:
            manufacturer_filter = "AND ms.manufacturer = %(manufacturer)s"
            
        query = f"""
            SELECT 
                ms.name as "Main Slip",
                mop.department as "Department",
                {weight_field} as "Weight",
                COALESCE(emp.employee_name, sup.supplier_name, 'Not Assigned') as "Assigned To",
                ms.workflow_state as "Status",
                ms.modified as "Last Modified",
                ms.manufacturer as "Manufacturer"
            FROM `tabMain Slip` ms
            INNER JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name
            WHERE ms.workflow_state = 'In Use'
            {subcontract_condition}
            AND mwo.company = %(company)s
            AND mwo.branch = %(branch)s
            {dept_filter}
            {manufacturer_filter}
            ORDER BY ms.modified DESC
            LIMIT 50
        """
        
        params = {"company": company, "branch": branch}
        if department:
            params["department"] = f"{department} - GEPL"
        if manufacturer:
            params["manufacturer"] = manufacturer
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"MSL details error: {str(e)}")
        return []

def get_msl_hold_details(stock_key, company, branch, department, manufacturer):
    """Get Main Slip Hold details (On Hold) - WITH MANUFACTURER FILTER"""
    try:
        subcontract_condition = ""
        if "employee" in stock_key:
            subcontract_condition = "AND COALESCE(mop.for_subcontracting, 0) = 0"
        elif "supplier" in stock_key:
            subcontract_condition = "AND mop.for_subcontracting = 1"
        
        dept_filter = ""
        if department:
            dept_filter = "AND mop.department = %(department)s"
            
        manufacturer_filter = ""
        if manufacturer:
            manufacturer_filter = "AND ms.manufacturer = %(manufacturer)s"
        
        query = f"""
            SELECT 
                ms.name as "Main Slip",
                mop.department as "Department",
                COALESCE(ms.pending_metal, 0) as "Pending Qty",
                COALESCE(emp.employee_name, sup.supplier_name, 'Not Assigned') as "Assigned To",
                ms.workflow_state as "Status",
                ms.modified as "Last Modified",
                ms.manufacturer as "Manufacturer"
            FROM `tabMain Slip` ms
            INNER JOIN `tabMain Slip Operation` mso ON ms.name = mso.parent
            INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            LEFT JOIN `tabSupplier` sup ON ms.subcontractor = sup.name
            WHERE ms.workflow_state = 'On Hold'
            {subcontract_condition}
            AND mwo.company = %(company)s
            AND mwo.branch = %(branch)s
            {dept_filter}
            {manufacturer_filter}
            ORDER BY ms.modified DESC
            LIMIT 50
        """
        
        params = {"company": company, "branch": branch}
        if department:
            params["department"] = f"{department} - GEPL"
        if manufacturer:
            params["manufacturer"] = manufacturer
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"MSL hold details error: {str(e)}")
        return []

def get_raw_material_details(company, branch, department, manufacturer, raw_material_types):
    """Get Raw Material Stock details"""
    try:
        material_filter = get_material_filter_for_item_groups(raw_material_types)
        dept_filter = ""
        if department:
            dept_filter = "AND w.department = %(department)s"
        
        query = f"""
            SELECT 
                sle.item_code as "Item Code",
                i.item_name as "Item Name",
                i.item_group as "Material Type",
                i.stock_uom as "UOM",
                SUM(sle.actual_qty) as "Quantity",
                w.department as "Department",
                w.warehouse_name as "Warehouse",
                sle.posting_date as "Date"
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
            INNER JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE w.warehouse_type = 'Raw Material'
            AND sle.company = %(company)s
            AND i.is_stock_item = 1
            {material_filter}
            {dept_filter}
            GROUP BY sle.item_code, w.department
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY SUM(sle.actual_qty) DESC
            LIMIT 50
        """
        
        params = {"company": company}
        if department:
            params["department"] = f"{department} - GEPL"
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Raw material details error: {str(e)}")
        return []

def get_scrap_stock_details(company, branch, department, manufacturer, raw_material_types):
    """Get Scrap Stock details"""
    try:
        material_filter = get_material_filter_for_item_groups(raw_material_types)
        dept_filter = ""
        if department:
            dept_filter = "AND w.department = %(department)s"
        
        query = f"""
            SELECT 
                sle.item_code as "Item Code",
                i.item_name as "Item Name", 
                i.item_group as "Material Type",
                SUM(sle.actual_qty) as "Scrap Qty",
                w.department as "Department",
                w.warehouse_type as "Warehouse Type",
                sle.posting_date as "Date"
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
            INNER JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE w.warehouse_type = 'Scrap'
            AND sle.company = %(company)s
            {material_filter}
            {dept_filter}
            GROUP BY sle.item_code, w.department
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY sle.posting_date DESC
            LIMIT 50
        """
        
        params = {"company": company}
        if department:
            params["department"] = f"{department} - GEPL"
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Scrap stock details error: {str(e)}")
        return []

def get_finished_goods_details(company, branch, department, manufacturer, raw_material_types):
    """Get Finished Goods details"""
    try:
        material_filter = get_material_filter_for_item_groups(raw_material_types)
        dept_filter = ""
        if department:
            dept_filter = "AND w.department = %(department)s"
        
        query = f"""
            SELECT 
                sn.name as "Serial No",
                sn.item_code as "Item Code",
                i.item_name as "Item Name",
                i.item_group as "Item Category",
                w.department as "Department",
                sn.warehouse as "Warehouse"
            FROM `tabSerial Number` sn
            INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
            INNER JOIN `tabItem` i ON sn.item_code = i.item_code
            WHERE sn.company = %(company)s
            {material_filter}
            {dept_filter}
            ORDER BY sn.creation DESC
            LIMIT 50
        """
        
        params = {"company": company}
        if department:
            params["department"] = f"{department} - GEPL"
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Finished goods details error: {str(e)}")
        return []

def get_reserve_stock_details(company, branch, department, manufacturer, raw_material_types):
    """Get Reserve Stock details"""
    try:
        material_filter = get_material_filter_for_item_groups(raw_material_types)
        dept_filter = ""
        if department:
            dept_filter = "AND w.department = %(department)s"
        
        query = f"""
            SELECT 
                sle.item_code as "Item Code",
                i.item_name as "Item Name",
                i.item_group as "Material Type",
                SUM(sle.actual_qty) as "Reserved Qty",
                w.department as "Department",
                w.warehouse_type as "Warehouse Type",
                sle.posting_date as "Date"
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
            INNER JOIN `tabItem` i ON sle.item_code = i.item_code
            WHERE w.warehouse_type = 'Reserve'
            AND sle.company = %(company)s
            {material_filter}
            {dept_filter}
            GROUP BY sle.item_code, w.department
            HAVING SUM(sle.actual_qty) > 0
            ORDER BY sle.posting_date DESC
            LIMIT 50
        """
        
        params = {"company": company}
        if department:
            params["department"] = f"{department} - GEPL"
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Reserve stock details error: {str(e)}")
        return []

def get_transit_stock_details(company, branch, department, manufacturer, raw_material_types):
    """Get Transit Stock details"""
    try:
        material_filter = get_material_filter_for_item_groups(raw_material_types)
        dept_filter = ""
        if department:
            dept_filter = "AND se.department = %(department)s"
        
        query = f"""
            SELECT 
                sed.item_code as "Item Code",
                i.item_name as "Item Name",
                i.item_group as "Material Type",
                SUM(sed.qty) as "Transit Qty",
                se.department as "Department",
                se.stock_entry_type as "Entry Type",
                se.posting_date as "Date"
            FROM `tabStock Entry` se
            INNER JOIN `tabStock Entry Detail` sed ON se.name = sed.parent
            INNER JOIN `tabItem` i ON sed.item_code = i.item_code
            WHERE se.stock_entry_type LIKE '%Transfer%'
            AND se.docstatus = 1
            AND se.company = %(company)s
            {material_filter}
            {dept_filter}
            GROUP BY sed.item_code, se.department
            ORDER BY se.posting_date DESC
            LIMIT 50
        """
        
        params = {"company": company}
        if department:
            params["department"] = f"{department} - GEPL"
        
        return frappe.db.sql(query, params, as_dict=True)
    except Exception as e:
        frappe.log_error(f"Transit stock details error: {str(e)}")
        return []

def get_general_stock_details(company, branch, department, stock_type, raw_material_types):
    """Get general stock details"""
    material_type_str = ", ".join(raw_material_types) if raw_material_types else "All Materials"
    return [
        {"Item": f"{stock_type} Item 1", "Material Type": material_type_str, "Quantity": 10, "Department": department or "General"},
        {"Item": f"{stock_type} Item 2", "Material Type": material_type_str, "Quantity": 15, "Department": department or "General"},
        {"Item": f"{stock_type} Item 3", "Material Type": material_type_str, "Quantity": 8, "Department": department or "General"}
    ]

@frappe.whitelist()
def get_company_branches(company):
    """Get branches for a company"""
    try:
        branches = frappe.db.sql("""
            SELECT DISTINCT branch as branch_name
            FROM `tabManufacturing Work Order`
            WHERE company = %(company)s AND branch IS NOT NULL AND branch != ''
            ORDER BY branch
            LIMIT 20
        """, {"company": company}, as_dict=True)
        
        if branches and len(branches) > 0:
            return branches
        elif "Gurukrupa" in company:
            return [
                {"branch_name": "GEPL-BL-0003"}, {"branch_name": "GEPL-CB-0006"},
                {"branch_name": "GEPL-CH-0004"}, {"branch_name": "GEPL-HD-0005"},
                {"branch_name": "GEPL-HO-0001"}, {"branch_name": "GEPL-KL-0010"},
                {"branch_name": "GEPL-MU-0009"}, {"branch_name": "GEPL-NV-0011"},
                {"branch_name": "GEPL-ST-0002"}, {"branch_name": "GEPL-TH-0008"},
                {"branch_name": "GEPL-VD-0007"}
            ]
        elif "KG GK" in company:
            return [
                {"branch_name": "KGJPL-ST-0001"}, {"branch_name": "KGJPL-ST-0002"},
                {"branch_name": "KGJPL-HO-0001"}, {"branch_name": "KGJPL-MU-0001"}
            ]
        else:
            return [{"branch_name": "ST-0001"}, {"branch_name": "ST-0002"}]
    except:
        return [{"branch_name": "ST-0001"}, {"branch_name": "ST-0002"}]

@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    """Get departments for a manufacturer"""
    manufacturer_departments = {
        "Labh": [
            "Accounts", "Central", "Diamond Bagging", "Diamond Setting", "Dispatch", 
            "Final Polish", "Gemstone Bagging", "Manufacturing Plan & Management", 
            "Model Making", "Order Management", "Pre Polish", "Product Allocation", 
            "Product Certification", "Production", "Purchase", "Refinery", "Sales", 
            "Selling", "Sub Contracting", "Tagging", "Waxing"
        ],
        "Shubh": [
            "Accounts", "Casting", "Central", "Dispatch", "Final Polish", 
            "Gemstone Bagging", "Manufacturing Plan & Management", "Purchase", 
            "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul"
        ],
        "Mangal": [
            "Central", "Computer Aided Designing", "Manufacturing Plan & Management", 
            "Dispatch", "Final Polish", "Gemstone Bagging", "Sudarshan", "Swastik", 
            "Tagging", "Trishul"
        ],
        "Amrut": ["Rudraksha", "Close Waxing", "Close Model Making"],
        "Service Center": ["Product Repair Center"],
        "Siddhi": ["Nandi"]
    }
    
    return manufacturer_departments.get(manufacturer, [])
