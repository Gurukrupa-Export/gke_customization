# Copyright (c) 2026, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _



def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data



def get_columns():
    """Define report columns"""
    return [
        {"fieldname": "sketch_order_id", "label": _("Sketch Order ID"), "fieldtype": "Link", "options": "Sketch Order", "width": 150},
        {"fieldname": "sketch_order_form_id", "label": _("Sketch Order Form ID"), "fieldtype": "Link", "options": "Sketch Order Form", "width": 180},
        {"fieldname": "qty", "label": _("Qty"), "fieldtype": "Int", "width": 80},
        {"fieldname": "docstatus", "label": _("Doc Status"), "fieldtype": "Data", "width": 100},
        {"fieldname": "customer_code", "label": _("Customer Code"), "fieldtype": "Link", "options": "Customer", "width": 120},
        {"fieldname": "order_date", "label": _("Sketch Order Date"), "fieldtype": "Date", "width": 160},
        {"fieldname": "delivery_date", "label": _("Sketch Delivery Date"), "fieldtype": "Date", "width": 160},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_category", "label": _("Item Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "item_sub_category", "label": _("Item Sub Category"), "fieldtype": "Data", "width": 150},
        {"fieldname": "customer_po_number", "label": _("Customer PO Number"), "fieldtype": "Data", "width": 150},
        {"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "item_final_sketch_cmo", "label": _("Item (Final Sketch Approval CMO)"), "fieldtype": "Data", "width": 180},
        {"fieldname": "diamond_wt_approx", "label": _("Diamond Wt Approx (CMO)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "gold_wt_approx", "label": _("Gold Wt Approx (CMO)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "designer_final_sketch_cmo", "label": _("Designer (Final Sketch CMO)"), "fieldtype": "Data", "width": 180},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "flow_type", "label": _("Flow Type"), "fieldtype": "Data", "width": 100},
        {"fieldname": "owner", "label": _("Owner"), "fieldtype": "Link", "options": "User", "width": 180},
        {"fieldname": "loc", "label": _("LOC"), "fieldtype": "Data", "width": 120},
        {"fieldname": "order_no", "label": _("Order No"), "fieldtype": "Link", "options": "Order", "width": 150},
        {"fieldname": "order_form_id", "label": _("Order Form ID"), "fieldtype": "Link", "options": "Order", "width": 150},
        {"fieldname": "order_form_date", "label": _("Order Form Date"), "fieldtype": "Datetime", "width": 160},
        {"fieldname": "order_complete_date", "label": _("Order Complete Date"), "fieldtype": "Datetime", "width": 160},
        {"fieldname": "jewelx_style_no", "label": _("Jewelx Style No"), "fieldtype": "Data", "width": 150}
    ]



def get_data(filters):
    """Fetch report data - One row per template item"""
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT 
            so.name as sketch_order_id,
            so.sketch_order_form as sketch_order_form_id,
            so.qty,
            CASE 
                WHEN so.docstatus = 0 THEN 'Draft'
                WHEN so.docstatus = 1 THEN 'Approved'
                WHEN so.docstatus = 2 THEN 'Cancelled'
                ELSE 'Unknown'
            END as docstatus,
            so.customer_code,
            so.order_date as order_date,
            so.delivery_date as delivery_date,
            COALESCE(NULLIF(i.variant_of, ''), i.name, so.item_code) as item_code,
            so.category as item_category,
            COALESCE(i.item_subcategory, so.subcategory) as item_sub_category,
            so.po_no as customer_po_number,
            so.supplier_name,
            so.branch,
            so.flow_type,
            so.order_type as loc,
            so.owner,
            (SELECT item FROM `tabFinal Sketch Approval CMO` WHERE parent = so.name AND parenttype = 'Sketch Order' LIMIT 1) as item_final_sketch_cmo,
            (SELECT diamond_wt_approx FROM `tabFinal Sketch Approval CMO` WHERE parent = so.name AND parenttype = 'Sketch Order' LIMIT 1) as diamond_wt_approx,
            (SELECT gold_wt_approx FROM `tabFinal Sketch Approval CMO` WHERE parent = so.name AND parenttype = 'Sketch Order' LIMIT 1) as gold_wt_approx,
            (SELECT designer FROM `tabFinal Sketch Approval CMO` WHERE parent = so.name AND parenttype = 'Sketch Order' LIMIT 1) as designer_final_sketch_cmo,
            i.stylebio as jewelx_style_no,
            (
                SELECT name 
                FROM `tabOrder` 
                WHERE item IN (
                    SELECT name FROM `tabItem` 
                    WHERE custom_sketch_order_id = so.name 
                    AND (variant_of = COALESCE(NULLIF(i.variant_of, ''), i.name) OR name = i.name)
                )
                AND design_type = 'Sketch Design' 
                ORDER BY order_date ASC 
                LIMIT 1
            ) as order_no,
            (
                SELECT cad_order_form 
                FROM `tabOrder` 
                WHERE item IN (
                    SELECT name FROM `tabItem` 
                    WHERE custom_sketch_order_id = so.name 
                    AND (variant_of = COALESCE(NULLIF(i.variant_of, ''), i.name) OR name = i.name)
                )
                AND design_type = 'Sketch Design' 
                ORDER BY order_date ASC 
                LIMIT 1
            ) as order_form_id,
            (
                SELECT order_date 
                FROM `tabOrder` 
                WHERE item IN (
                    SELECT name FROM `tabItem` 
                    WHERE custom_sketch_order_id = so.name 
                    AND (variant_of = COALESCE(NULLIF(i.variant_of, ''), i.name) OR name = i.name)
                )
                AND design_type = 'Sketch Design' 
                ORDER BY order_date ASC 
                LIMIT 1
            ) as order_form_date,
            (
                SELECT delivery_date 
                FROM `tabOrder` 
                WHERE item IN (
                    SELECT name FROM `tabItem` 
                    WHERE custom_sketch_order_id = so.name 
                    AND (variant_of = COALESCE(NULLIF(i.variant_of, ''), i.name) OR name = i.name)
                )
                AND design_type = 'Sketch Design' 
                ORDER BY order_date ASC 
                LIMIT 1
            ) as order_complete_date
        FROM `tabSketch Order` so
        LEFT JOIN `tabSketch Order Form` sof ON so.sketch_order_form = sof.name
        LEFT JOIN `tabItem` i ON i.custom_sketch_order_id = so.name
        WHERE so.workflow_state = 'Approved' and so.docstatus = 1
        {conditions}
        GROUP BY so.name, COALESCE(NULLIF(i.variant_of, ''), i.name, so.item_code)
        ORDER BY so.creation DESC
    """
    
    data = frappe.db.sql(query, filters, as_dict=1)
    return data



def get_conditions(filters):
    """Build WHERE conditions from filters"""
    conditions = []
    
    # Date filters - using Sketch Order order_date
    if filters.get("from_date"):
        conditions.append("DATE(so.order_date) >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("DATE(so.order_date) <= %(to_date)s")
    
    # ID filters
    if filters.get("sketch_order_id"):
        conditions.append("so.name = %(sketch_order_id)s")
    if filters.get("order_form_id"):
        conditions.append("""
            EXISTS (
                SELECT 1 FROM `tabOrder` ord 
                WHERE ord.item IN (
                    SELECT name FROM `tabItem` WHERE custom_sketch_order_id = so.name
                ) 
                AND ord.cad_order_form = %(order_form_id)s
            )
        """)
    
    # LOC filter
    if filters.get("order_type"):
        conditions.append("so.order_type = %(order_type)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""
