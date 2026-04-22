import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {"fieldname": "ord_number", "label": _("Order Number"), "fieldtype": "Link", "options": "Order", "width": 130},
        {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 100},
        {"fieldname": "subcategory", "label": _("Sub Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "setting", "label": _("Setting"), "fieldtype": "Data", "width": 100},
        {"fieldname": "ref_no", "label": _("Design Type"), "fieldtype": "Data", "width": 130},
        {"fieldname": "party_code_and_name", "label": _("Party Code & Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "employee_id", "label": _("Employee ID"), "fieldtype": "Data", "width": 120},
        {"fieldname": "designer_name", "label": _("Designer Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
        {"fieldname": "draft_date_time", "label": _("Draft Date & Time"), "fieldtype": "Data", "width": 160},
        {"fieldname": "assign_date_time", "label": _("Assign Date & Time"), "fieldtype": "Data", "width": 160},
        {"fieldname": "start_design_date_time", "label": _("Start Design Date & Time"), "fieldtype": "Data", "width": 180},
        {"fieldname": "design_on_hold_date_time", "label": _("Design On Hold Date & Time"), "fieldtype": "Data", "width": 180},
        {"fieldname": "start_design_from_hold_date", "label": _("Start Design From Hold Date"), "fieldtype": "Data", "width": 200},
        {"fieldname": "send_to_qc_date_time", "label": _("Send to QC Date & Time"), "fieldtype": "Data", "width": 170},
        {"fieldname": "customer_approval_date_time", "label": _("Customer Approval Date & Time"), "fieldtype": "Data", "width": 190},
        {"fieldname": "design_rework_date_time", "label": _("Design Rework Date & Time"), "fieldtype": "Data", "width": 180},
        {"fieldname": "cad_update_date_time", "label": _("CAD Update Date & Time"), "fieldtype": "Data", "width": 170},
        {"fieldname": "update_item_date_time", "label": _("Update Item Date & Time"), "fieldtype": "Data", "width": 170},
        {"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Data", "width": 160},
        {"fieldname": "approved_date_time", "label": _("Approved Date & Time"), "fieldtype": "Data", "width": 160},
        {"fieldname": "gold_kt", "label": _("Gold KT"), "fieldtype": "Data", "width": 80},
        {"fieldname": "cam_type", "label": _("CAM Type"), "fieldtype": "Data", "width": 90},
        {"fieldname": "cad_weight", "label": _("CAD Weight"), "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "cam_weight", "label": _("CAM Weight"), "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "wax_weight", "label": _("WAX Weight"), "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "casting_weight", "label": _("Casting Weight"), "fieldtype": "Float", "width": 120, "precision": 3},
        {"fieldname": "finish_product_wt_without_finding", "label": _("Finish Product Wt (without Finding)"), "fieldtype": "Float", "width": 210, "precision": 3},
        {"fieldname": "casting_to_finish_loss_percentage", "label": _("Casting to Finish %% Loss"), "fieldtype": "Float", "width": 180, "precision": 2},
        {"fieldname": "loss", "label": _("Loss"), "fieldtype": "Float", "width": 80, "precision": 3},
        {"fieldname": "finding_wt", "label": _("Finding Wt"), "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "finish_product_wt", "label": _("Finish Product Wt"), "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "other_wt", "label": _("Other Wt"), "fieldtype": "Float", "width": 90, "precision": 3},
        {"fieldname": "diamond_wt", "label": _("Diamond Wt"), "fieldtype": "Float", "width": 100, "precision": 3},
        {"fieldname": "diamond_pcs", "label": _("Diamond Pcs"), "fieldtype": "Int", "width": 100},
        {"fieldname": "gold_wt", "label": _("Gold Wt"), "fieldtype": "Float", "width": 90, "precision": 3},
        {"fieldname": "gold_ratio", "label": _("Gold Ratio"), "fieldtype": "Float", "width": 100, "precision": 2},
        {"fieldname": "diamond_ratio", "label": _("Diamond Ratio"), "fieldtype": "Float", "width": 120, "precision": 4}
    ]


def get_data(filters):
    """Main function to fetch and compile data"""
    
    # Add limit based on date range to prevent slow queries
    limit = get_smart_limit(filters)
    
    # Step 1: Get base order data with LIMIT
    orders = get_base_orders(filters, limit)
    
    if not orders:
        return []
    
    order_names = [d['ord_number'] for d in orders]
    
    # Step 2: Fetch related data in batch
    enrich_designer_data(orders, order_names)
    enrich_assignment_dates(orders, order_names)
    enrich_timesheet_data(orders, order_names)
    enrich_bom_metal_data(orders, order_names)
    
    return orders


def get_smart_limit(filters):
    """Determine appropriate LIMIT based on filters"""
    
    # If specific order number, no limit
    if filters.get("order_number"):
        return None
    
    # If date range is small (< 7 days), allow 500 records
    if filters.get("from_date") and filters.get("to_date"):
        from frappe.utils import date_diff
        days = date_diff(filters.get("to_date"), filters.get("from_date"))
        if days <= 7:
            return 500
        elif days <= 30:
            return 300
        else:
            return 200
    
    # Default limit
    return 200


def get_base_orders(filters, limit=None):
    """Get base order data with basic filters"""
    
    conditions = ["docstatus < 2"]
    
    # BOM or CAD filter
    if filters.get("bom_or_cad"):
        conditions.append("bom_or_cad = %(bom_or_cad)s")
    else:
        conditions.append("bom_or_cad = 'CAD'")
    
    if filters.get("from_date"):
        conditions.append("order_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("order_date <= %(to_date)s")
    
    if filters.get("branch"):
        conditions.append("branch = %(branch)s")
    
    if filters.get("category"):
        conditions.append("category = %(category)s")
    
    if filters.get("workflow_state"):
        conditions.append("workflow_state = %(workflow_state)s")
    
    if filters.get("order_number"):
        conditions.append("name = %(order_number)s")
    
    where_clause = " AND ".join(conditions)
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    query = f"""
        SELECT 
            name as ord_number,
            category,
            subcategory,
            setting_type as setting,
            design_type as ref_no,
            customer_code,
            customer,
            CASE 
                WHEN customer_code IS NOT NULL AND customer IS NOT NULL 
                THEN CONCAT(customer_code, ' - ', customer)
                WHEN customer IS NOT NULL 
                THEN customer
                WHEN customer_code IS NOT NULL 
                THEN customer_code
                ELSE ''
            END as party_code_and_name,
            branch,
            DATE_FORMAT(order_date, '%%d-%%m-%%Y %%H:%%i:%%s') as draft_date_time,
            DATE_FORMAT(delivery_date, '%%d-%%m-%%Y %%H:%%i:%%s') as delivery_date,
            DATE_FORMAT(delivery_date, '%%d-%%m-%%Y %%H:%%i:%%s') as approved_date_time,
            finding_weight as finding_wt,
            metal_and_finding_weight as finish_product_wt,
            total_other_weight as other_wt,
            total_diamond_weight as diamond_wt,
            total_diamond_pcs as diamond_pcs,
            metal_weight as gold_wt,
            metal_to_diamond_ratio_excl_of_finding as gold_ratio,
            diamond_ratio
        FROM 
            `tabOrder`
        WHERE 
            {where_clause}
        ORDER BY 
            creation DESC
        {limit_clause}
    """
    
    return frappe.db.sql(query, filters, as_dict=1)


def enrich_designer_data(orders, order_names):
    """Enrich orders with designer data"""
    
    if not order_names:
        return
    
    query = """
        SELECT 
            parent as order_name,
            designer,
            designer_name
        FROM 
            `tabDesigner Assignment - CAD`
        WHERE 
            parent IN %(order_names)s
            AND parentfield = "designer_assignment"
            AND docstatus < 2
    """
    
    data = frappe.db.sql(query, {"order_names": order_names}, as_dict=1)
    designer_map = {d['order_name']: d for d in data}
    
    for order in orders:
        order_name = order['ord_number']
        if order_name in designer_map:
            order['designer_name'] = designer_map[order_name].get('designer_name')
            order['employee_id'] = designer_map[order_name].get('designer')
        else:
            order['designer_name'] = None
            order['employee_id'] = None


def enrich_assignment_dates(orders, order_names):
    """Enrich orders with assignment dates"""
    
    if not order_names:
        return
    
    query = """
        SELECT 
            docname as order_name,
            DATE_FORMAT(MIN(creation), '%%d-%%m-%%Y %%H:%%i:%%s') as assign_date
        FROM 
            `tabVersion`
        WHERE 
            ref_doctype = 'Order'
            AND docname IN %(order_names)s
            AND data LIKE '%%Assigned%%'
        GROUP BY 
            docname
    """
    
    data = frappe.db.sql(query, {"order_names": order_names}, as_dict=1)
    version_map = {d['order_name']: d['assign_date'] for d in data}
    
    for order in orders:
        order['assign_date_time'] = version_map.get(order['ord_number'])


def enrich_timesheet_data(orders, order_names):
    """Enrich orders with timesheet data - OPTIMIZED"""
    
    if not order_names:
        return
    
    # Single query for all timesheet activities
    query = """
        SELECT 
            t.order as order_name,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'CAD Designing' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as start_design,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'CAD Designing - On-Hold' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as on_hold,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'QC Activity' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as qc_activity,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'Customer Approval' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as customer_approval,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'Design Rework in Progress' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as design_rework,
            DATE_FORMAT(MIN(CASE WHEN td.activity_type = 'Cad Update' THEN td.from_time END), '%%d-%%m-%%Y %%H:%%i:%%s') as cad_update,
            DATE_FORMAT(MAX(CASE WHEN t.workflow_state = 'Approved' THEN t.modified END), '%%d-%%m-%%Y %%H:%%i:%%s') as approved_modified
        FROM 
            `tabTimesheet` t
        LEFT JOIN 
            `tabTimesheet Detail` td ON td.parent = t.name
        WHERE 
            t.order IN %(order_names)s
            AND t.docstatus < 2
        GROUP BY 
            t.order
    """
    
    data = frappe.db.sql(query, {"order_names": order_names}, as_dict=1)
    timesheet_map = {d['order_name']: d for d in data}
    
    # Separately get resume dates only for orders that have on_hold
    orders_on_hold = [k for k, v in timesheet_map.items() if v.get('on_hold')]
    
    if orders_on_hold:
        resume_query = """
            SELECT 
                t.order as order_name,
                DATE_FORMAT(MIN(td.from_time), '%%d-%%m-%%Y %%H:%%i:%%s') as resume_design
            FROM 
                `tabTimesheet` t
            INNER JOIN 
                `tabTimesheet Detail` td ON td.parent = t.name
            WHERE 
                t.order IN %(orders_on_hold)s
                AND td.activity_type = 'CAD Designing'
                AND t.docstatus < 2
                AND EXISTS (
                    SELECT 1 
                    FROM `tabTimesheet` t2
                    INNER JOIN `tabTimesheet Detail` td2 ON td2.parent = t2.name
                    WHERE td2.activity_type = 'CAD Designing - On-Hold'
                        AND t2.order = t.order
                        AND td2.from_time < td.from_time
                        AND t2.docstatus < 2
                )
            GROUP BY 
                t.order
        """
        
        resume_data = frappe.db.sql(resume_query, {"orders_on_hold": orders_on_hold}, as_dict=1)
        
        for d in resume_data:
            if d['order_name'] in timesheet_map:
                timesheet_map[d['order_name']]['resume_design'] = d['resume_design']
    
    # Enrich orders with timesheet data
    for order in orders:
        order_name = order['ord_number']
        if order_name in timesheet_map:
            ts = timesheet_map[order_name]
            order['start_design_date_time'] = ts.get('start_design')
            order['design_on_hold_date_time'] = ts.get('on_hold')
            order['start_design_from_hold_date'] = ts.get('resume_design')
            order['send_to_qc_date_time'] = ts.get('qc_activity')
            order['customer_approval_date_time'] = ts.get('customer_approval')
            order['design_rework_date_time'] = ts.get('design_rework')
            order['cad_update_date_time'] = ts.get('cad_update')
            order['update_item_date_time'] = ts.get('approved_modified')
        else:
            order['start_design_date_time'] = None
            order['design_on_hold_date_time'] = None
            order['start_design_from_hold_date'] = None
            order['send_to_qc_date_time'] = None
            order['customer_approval_date_time'] = None
            order['design_rework_date_time'] = None
            order['cad_update_date_time'] = None
            order['update_item_date_time'] = None


def enrich_bom_metal_data(orders, order_names):
    """Enrich orders with BOM metal data"""
    
    if not order_names:
        return
    
    query = """
        SELECT 
            parent as order_name,
            MAX(metal_touch) as metal_touch,
            SUM(cad_weight) as cad_weight,
            SUM(cam_weight) as cam_weight,
            SUM(wax_weight) as wax_weight,
            SUM(casting_weight) as casting_weight,
            SUM(finish_product_weight) as finish_product_weight,
            AVG(finish_loss_percentage) as finish_loss_percentage,
            SUM(finish_loss_grams) as finish_loss_grams
        FROM 
            `tabOrder BOM Metal Detail`
        WHERE 
            parent IN %(order_names)s
            AND docstatus < 2
        GROUP BY 
            parent
    """
    
    data = frappe.db.sql(query, {"order_names": order_names}, as_dict=1)
    bom_map = {d['order_name']: d for d in data}
    
    for order in orders:
        order_name = order['ord_number']
        order['cam_type'] = ''
        
        if order_name in bom_map:
            bom = bom_map[order_name]
            order['gold_kt'] = bom.get('metal_touch')
            order['cad_weight'] = bom.get('cad_weight')
            order['cam_weight'] = bom.get('cam_weight')
            order['wax_weight'] = bom.get('wax_weight')
            order['casting_weight'] = bom.get('casting_weight')
            order['finish_product_wt_without_finding'] = bom.get('finish_product_weight')
            order['casting_to_finish_loss_percentage'] = bom.get('finish_loss_percentage')
            order['loss'] = bom.get('finish_loss_grams')
        else:
            order['gold_kt'] = None
            order['cad_weight'] = None
            order['cam_weight'] = None
            order['wax_weight'] = None
            order['casting_weight'] = None
            order['finish_product_wt_without_finding'] = None
            order['casting_to_finish_loss_percentage'] = None
            order['loss'] = None
