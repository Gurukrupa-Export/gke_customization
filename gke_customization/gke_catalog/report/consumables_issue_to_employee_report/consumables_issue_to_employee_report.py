# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    """Columns for summary view"""
    return [
        {
            "fieldname": "worker",
            "label": _("Worker"),
            "fieldtype": "Data",
            "width": 350
        },
        {
            "fieldname": "total_amount",
            "label": _("Total Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "view_details",
            "label": _("Details"),
            "fieldtype": "Data",
            "width": 150
        }
    ]

def get_data(filters):
    """Get summary data grouped by employee"""
    
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT 
            CONCAT(emp.employee_name, ' (', se.custom_employee, ')') as worker,
            se.custom_employee as worker_code,
            SUM(sed.qty * COALESCE(pri.rate, 0)) as total_amount,
            COUNT(DISTINCT se.name) as total_transactions
        FROM 
            `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN `tabEmployee` emp ON emp.name = se.custom_employee
        LEFT JOIN `tabBatch` batch ON batch.name = sed.batch_no
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = batch.reference_name 
            AND pri.item_code = sed.item_code 
            AND batch.reference_doctype = 'Purchase Receipt'
        WHERE 
            se.stock_entry_type = 'Consumables Issue to  Employee'
            AND se.docstatus = 1
            AND se.custom_employee IS NOT NULL
            {conditions}
        GROUP BY se.custom_employee, emp.employee_name
        ORDER BY total_amount DESC
    """
    
    data = frappe.db.sql(query, filters, as_dict=1)
    
    # Add view details button HTML
    for row in data:
        row['view_details'] = f'Details'
    
    return data

def get_conditions(filters):
    """Build WHERE conditions from filters"""
    conditions = []
    
    if filters.get("from_date"):
        conditions.append(f"""se.posting_date >= "{filters['from_date']}" """)
    
    if filters.get("to_date"):
        conditions.append(f"""se.posting_date <= "{filters['to_date']}" """)
    
    if filters.get("department"):
        departments = ', '.join([f'"{dept}"' for dept in filters.get("department")])
        conditions.append(f"emp.department IN ({departments})")
    
    return " AND " + " AND ".join(conditions) if conditions else ""

@frappe.whitelist()
def get_employee_details(employee_code, from_date=None, to_date=None):
    """API method to fetch employee details for popup"""
    
    conditions = []
    if from_date:
        conditions.append(f"""se.posting_date >= "{from_date}" """)
    if to_date:
        conditions.append(f"""se.posting_date <= "{to_date}" """)
    
    conditions.append(f"""se.custom_employee = "{employee_code}" """)
    
    conditions_sql = " AND " + " AND ".join(conditions)
    
    query = f"""
        SELECT 
            se.name as stock_entry,
            se.posting_date as issue_date,
            emp.department as dept,
            mgr.employee_name as manager,
            emp.employee_name as worker,
            se.custom_employee as worker_code,
            sed.item_code,
            item.item_name,
            item.item_group,
            item.custom_old_item_category as category,
            item.custom_old_item_sub_category as sub_category,
            sed.qty,
            pri.rate,
            sed.stock_uom as unit,
            (sed.qty * COALESCE(pri.rate, 0)) as total,
            batch.name as batch_no,
            batch.reference_name as purchase_receipt,
            pr.posting_date as pr_date
        FROM 
            `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN `tabEmployee` emp ON emp.name = se.custom_employee
        LEFT JOIN `tabEmployee` mgr ON mgr.name = emp.reports_to
        LEFT JOIN `tabItem` item ON item.name = sed.item_code
        LEFT JOIN `tabBatch` batch ON batch.name = sed.batch_no
        LEFT JOIN `tabPurchase Receipt` pr ON pr.name = batch.reference_name 
            AND batch.reference_doctype = 'Purchase Receipt'
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = batch.reference_name 
            AND pri.item_code = sed.item_code
        WHERE 
            se.stock_entry_type = 'Consumables Issue to  Employee'
            AND se.docstatus = 1
            {conditions_sql}
        ORDER BY se.posting_date DESC, se.name
    """
    
    data = frappe.db.sql(query, as_dict=1)
    
    # Add serial numbers
    for idx, row in enumerate(data, 1):
        row['serial_no'] = idx
    
    return data
