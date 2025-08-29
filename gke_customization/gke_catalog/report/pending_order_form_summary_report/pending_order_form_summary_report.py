# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
        {"label": _("ERP Order No."), "fieldname": "erp_order_no", "fieldtype": "Link", "options": "Order Form", "width": 150},
        {"label": _("Customer PO No."), "fieldname": "customer_po_no", "fieldtype": "Data", "width": 140},
        {"label": _("No. of Orders"), "fieldname": "no_of_orders", "fieldtype": "Data", "width": 120},
        {"label": _("No. of Designs"), "fieldname": "no_of_designs", "fieldtype": "Int", "width": 120},
        {"label": _("BOM Pending"), "fieldname": "bom_pending", "fieldtype": "Data", "width": 120},
        {"label": _("CAD Pending"), "fieldname": "cad_pending", "fieldtype": "Data", "width": 120},
        {"label": _("Total Pending Orders"), "fieldname": "total_pending_orders", "fieldtype": "Data", "width": 140}
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    cad_state_idx = [1,2,3,4,5,6,7,8,9,10,11,12,13,17,18,22,24,31,32]
    cad_idx_list = ','.join(map(str, cad_state_idx))

    query = f"""
    SELECT 
        of.delivery_date AS delivery_date,
        of.name AS erp_order_no,
        of.po_no AS customer_po_no,
        of.total_rows AS no_of_orders,
        COUNT(DISTINCT ofd.design_id) AS no_of_designs,

        -- BOM/CAD counts: Count ORDERS not pieces (PENDING ONLY including drafts)
        COALESCE(child_data.bom_pending, 0) AS bom_pending,
        COALESCE(child_data.cad_pending, 0) AS cad_pending,

        -- Total pending orders (including drafts)
        COALESCE(pending_orders.pending_order_count, 0) AS total_pending_orders

    FROM `tabOrder Form` of
    LEFT JOIN `tabOrder Form Detail` ofd ON of.name = ofd.parent

    -- Count PENDING orders by status (including drafts)
    LEFT JOIN (
        SELECT
            ofd.parent,
            COUNT(DISTINCT CASE 
                WHEN wds.idx NOT IN ({cad_idx_list}) 
                     AND (COALESCE(o.workflow_state, '') != 'Approved' OR o.docstatus = 0)
                THEN o.name 
            END) AS bom_pending,
            
            COUNT(DISTINCT CASE 
                WHEN wds.idx IN ({cad_idx_list}) 
                     AND (COALESCE(o.workflow_state, '') != 'Approved' OR o.docstatus = 0)
                THEN o.name 
            END) AS cad_pending
            
        FROM `tabOrder Form Detail` ofd
        INNER JOIN `tabOrder` o ON ofd.design_id = o.design_id AND ofd.parent = o.cad_order_form
        LEFT JOIN `tabWorkflow Document State` wds 
            ON o.workflow_state = wds.state 
            AND wds.parent = 'Order with Customer Approval Final'
        WHERE (o.workflow_state != 'Approved' OR o.docstatus = 0)
        GROUP BY ofd.parent
    ) child_data ON child_data.parent = of.name

    -- Count total pending orders (including drafts)
    LEFT JOIN (
        SELECT 
            cad_order_form, 
            COUNT(DISTINCT name) AS pending_order_count
        FROM `tabOrder`
        WHERE (workflow_state != 'Approved' OR docstatus = 0)
        GROUP BY cad_order_form
    ) pending_orders ON pending_orders.cad_order_form = of.name

    WHERE of.docstatus >= 0
      AND COALESCE(pending_orders.pending_order_count, 0) > 0
      {conditions}

    GROUP BY of.name, of.total_rows, of.delivery_date, of.po_no
    ORDER BY of.delivery_date ASC
    """

    return frappe.db.sql(query, as_dict=1)

def get_conditions(filters):
    conditions = []
    if filters.get("company"):
        conditions.append(f"of.company = '{filters['company']}'")
    if filters.get("branch"):
        conditions.append(f"of.branch = '{filters['branch']}'")
    if filters.get("from_date"):
        conditions.append(f"of.order_date >= '{filters['from_date']}'")
    if filters.get("to_date"):
        conditions.append(f"of.order_date <= '{filters['to_date']}'")
    if filters.get("order_form_no"):
        if isinstance(filters["order_form_no"], list):
            order_forms = ', '.join([f"'{order}'" for order in filters["order_form_no"]])
            conditions.append(f"of.name IN ({order_forms})")
        else:
            conditions.append(f"of.name = '{filters['order_form_no']}'")
    return " AND " + " AND ".join(conditions) if conditions else ""
