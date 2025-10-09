# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Order Date"), "fieldname": "order_date", "fieldtype": "Date", "width": 120},
        {"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
        {"label": _("Order No."), "fieldname": "erp_order_no", "fieldtype": "Link", "options": "Order Form", "width": 150},
        {"label": _("Customer PO No."), "fieldname": "customer_po_no", "fieldtype": "Data", "width": 140},
        {"label": _("No. of Orders"), "fieldname": "no_of_orders", "fieldtype": "Int", "width": 120},
        {"label": _("No. of Designs"), "fieldname": "no_of_designs", "fieldtype": "Int", "width": 120},
        {"label": _("No. of Orders Approved"), "fieldname": "no_of_orders_approved", "fieldtype": "Int", "width": 140},
        {"label": _("No. of Orders Pending"), "fieldname": "no_of_orders_pending", "fieldtype": "Int", "width": 140},
        {"label": _("CAD Pending"), "fieldname": "cad_pending", "fieldtype": "Int", "width": 120},
        {"label": _("IBM Pending"), "fieldname": "bom_pending", "fieldtype": "Int", "width": 120}
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # CAD Pending States
    cad_states = "'Assigned','Assigned - On-Hold','Designing','Sent to QC','Update Requested','Designing - On-Hold','Sent to QC - On-Hold','Customer Approval','Customer Approved','Customer Design Rejected','Create CAD','Update Designer','Design Rework in Progress','Design Rework in Progress - On Hold'"
    
    # IBM Pending States  
    ibm_states = "'Update Item','Update BOM','Order BOM','Create BOM','BOM QC','Creating BOM','Updating BOM','BOM QC - On-Hold','Creating BOM - On-Hold','Updating BOM - On-Hold'"

    query = f"""
    SELECT 
        of.order_date AS order_date,
        of.delivery_date AS delivery_date,
        of.name AS erp_order_no,
        of.po_no AS customer_po_no,
        COUNT(DISTINCT o.name) AS no_of_orders,
        COUNT(DISTINCT ofd.design_id) AS no_of_designs,

        COALESCE(approved_count.approved_orders, 0) AS no_of_orders_approved,
        COALESCE(pending_count.pending_orders, 0) AS no_of_orders_pending,
        COALESCE(cad_pending_count.cad_pending, 0) AS cad_pending,
        COALESCE(bom_pending_count.bom_pending, 0) AS bom_pending

    FROM `tabOrder Form` of
    LEFT JOIN `tabOrder Form Detail` ofd ON of.name = ofd.parent
    LEFT JOIN `tabOrder` o ON o.cad_order_form = of.name

    LEFT JOIN (
        SELECT o1.cad_order_form, COUNT(DISTINCT o1.name) AS approved_orders
        FROM `tabOrder` o1
        WHERE o1.workflow_state = 'Approved'
        GROUP BY o1.cad_order_form
    ) approved_count ON approved_count.cad_order_form = of.name

    LEFT JOIN (
        SELECT o2.cad_order_form, 
               COUNT(DISTINCT CASE WHEN o2.workflow_state NOT IN ('Approved', 'Cancelled') THEN o2.name END) AS pending_orders
        FROM `tabOrder` o2
        GROUP BY o2.cad_order_form
    ) pending_count ON pending_count.cad_order_form = of.name

    LEFT JOIN (
        SELECT
            ofd3.parent,
            COUNT(DISTINCT o3.name) AS cad_pending
        FROM `tabOrder Form Detail` ofd3
        INNER JOIN `tabOrder` o3 ON ofd3.design_id = o3.design_id AND ofd3.parent = o3.cad_order_form
        WHERE o3.workflow_state IN ({cad_states}) AND o3.workflow_state != 'Cancelled'
        GROUP BY ofd3.parent
    ) cad_pending_count ON cad_pending_count.parent = of.name

    LEFT JOIN (
        SELECT
            ofd4.parent,
            COUNT(DISTINCT o4.name) AS bom_pending
        FROM `tabOrder Form Detail` ofd4
        INNER JOIN `tabOrder` o4 ON ofd4.design_id = o4.design_id AND ofd4.parent = o4.cad_order_form
        WHERE o4.workflow_state IN ({ibm_states}) AND o4.workflow_state != 'Cancelled'
        GROUP BY ofd4.parent
    ) bom_pending_count ON bom_pending_count.parent = of.name

    WHERE 
        of.docstatus IN (0, 1)
        AND of.workflow_state NOT IN ('Cancelled')
        AND (
            of.workflow_state IN ('Draft', 'Creating Item & BOM', 'On Hold', 'Send For Approval')
            OR (
                of.workflow_state = 'Approved' 
                AND EXISTS (
                    SELECT 1 FROM `tabOrder` o_check 
                    WHERE o_check.cad_order_form = of.name 
                    AND o_check.workflow_state NOT IN ('Approved', 'Cancelled')
                )
            )
        )
      {conditions}

    GROUP BY of.name, of.order_date, of.delivery_date, of.po_no
    ORDER BY of.order_date DESC
    """
    
    return frappe.db.sql(query, as_dict=1)

def get_conditions(filters):
    conditions = []
    if filters.get("company"):
        conditions.append(f"of.company = '{filters['company']}'")
    if filters.get("branch"):
        conditions.append(f"of.branch = '{filters['branch']}'")
    if filters.get("order_form_no"):
        if isinstance(filters["order_form_no"], list):
            order_forms = ', '.join([f"'{order}'" for order in filters["order_form_no"]])
            conditions.append(f"of.name IN ({order_forms})")
        else:
            conditions.append(f"of.name = '{filters['order_form_no']}'")
    return " AND " + " AND ".join(conditions) if conditions else ""