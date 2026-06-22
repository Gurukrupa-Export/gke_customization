# Copyright (c) 2024, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns, data = [], []
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 140,
            "align": "left"
        },
        {
            "label": _("Stock Entry ID"),
            "fieldname": "stock_entry_id",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 190,
            "align": "left"
        },
        {
            "label": _("From Department"),
            "fieldname": "from_department",
            "fieldtype": "Data",
            "width": 200,
            "align": "left"
        },
        {
            "label": _("To Department"),
            "fieldname": "to_department",
            "fieldtype": "Data",
            "width": 190,
            "align": "left"
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
            "align": "center"
        },
        {
            "label": _("Manufacturer"),
            "fieldname": "manufacturer",
            "fieldtype": "Link",
            "options": "Manufacturer",
            "width": 150,
            "align": "left"
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180,
            "align": "left"
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 80,
            "align": "right"
        },
        {
            "label": _("Pcs"),
            "fieldname": "pcs",
            "fieldtype": "Int",
            "width": 80,
            "align": "right"
        },
        {
            "label": _(""),
            "fieldname": "indent",
            "fieldtype": "Int",
            "width": 10,
            "hidden": 1
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    query = """
        SELECT 
            se.posting_date as date,
            COALESCE(
                (SELECT department FROM `tabWarehouse` WHERE name = sed.s_warehouse),
                se.department,
                'N/A'
            ) as from_department,
            COALESCE(
                se.to_department,
                (SELECT department FROM `tabWarehouse` WHERE name = sed.t_warehouse),
                'N/A'
            ) as to_department,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM `tabStock Entry` se2 
                    WHERE (se2.outgoing_stock_entry = se.name OR se2.repack_entry = se.name)
                    AND se2.docstatus = 1
                ) THEN 'Received'
                ELSE 'Transit'
            END as status,
            se.name as stock_entry_id,
            COALESCE(se.manufacturer, '') as manufacturer,
            sed.item_code as item_code,
            sed.qty as qty,
            COALESCE(sed.pcs, 1) as pcs
        FROM 
            `tabStock Entry` se
        INNER JOIN 
            `tabStock Entry Detail` sed ON se.name = sed.parent
        INNER JOIN 
            `tabWarehouse` tw ON sed.t_warehouse = tw.name
        WHERE 
            se.stock_entry_type IN ('Material Transfer(Department)', 'Material Transfer (Department)', 'Customer Goods Transfer')
            AND se.docstatus = 1
            AND tw.warehouse_type = 'Transit'
            AND sed.serial_no IS NULL
            AND sed.batch_no IS NOT NULL
            {conditions}
        ORDER BY 
            se.posting_date DESC, se.name, sed.item_code
    """.format(conditions=conditions)
    
    raw_data = frappe.db.sql(query, filters, as_dict=1)
    
    grouped_data = group_by_stock_entry(raw_data)
    
    return grouped_data

def group_by_stock_entry(raw_data):
    result = []
    stock_entries = {}
    
    for row in raw_data:
        se_id = row['stock_entry_id']
        
        if se_id not in stock_entries:
            stock_entries[se_id] = []
        stock_entries[se_id].append(row)
    
    # FIXED SORTING: Date descending first, then quantity
    sorted_entries = sorted(
        stock_entries.items(), 
        key=lambda x: (x[1][0]['date'], sum(float(item['qty'] or 0) for item in x[1])), 
        reverse=True
    )
    
    for se_id, items in sorted_entries:
        first_item = items[0]
        
        entry_total_qty = sum(float(item['qty'] or 0) for item in items)
        entry_total_pcs = sum(float(item['pcs'] or 0) for item in items)
        
        result.append({
            'date': '',
            'stock_entry_id': f"{se_id}",
            'from_department': '',
            'to_department': f"<b>({len(items)} items)</b>",
            'status': '',
            'manufacturer': first_item['manufacturer'] if first_item['manufacturer'] else '',
            'item_code': '',
            'qty': entry_total_qty,
            'pcs': entry_total_pcs,
            'indent': 0
        })

        for item in items:
            item['indent'] = 1
            item['stock_entry_id'] = ''
            item['manufacturer'] = ''
            result.append(item)
    
    return result

def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("AND se.company = %(company)s")
    
    if filters.get("branch"):
        conditions.append("AND se.branch = %(branch)s")
    
    if filters.get("from_date"):
        conditions.append("AND se.posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("AND se.posting_date <= %(to_date)s")
    
    if filters.get("status"):
        if filters.get("status") == "Transit":
            conditions.append("""AND NOT EXISTS (
                SELECT 1 FROM `tabStock Entry` se2 
                WHERE (se2.outgoing_stock_entry = se.name OR se2.repack_entry = se.name)
                AND se2.docstatus = 1
            )""")
        elif filters.get("status") == "Received":
            conditions.append("""AND EXISTS (
                SELECT 1 FROM `tabStock Entry` se2 
                WHERE (se2.outgoing_stock_entry = se.name OR se2.repack_entry = se.name)
                AND se2.docstatus = 1
            )""")
    
    if filters.get("manufacturer"):
        conditions.append("AND se.manufacturer = %(manufacturer)s")
    
    if filters.get("from_department"):
        conditions.append("AND EXISTS (SELECT 1 FROM `tabWarehouse` WHERE name = sed.s_warehouse AND department = %(from_department)s)")
    
    if filters.get("to_department"):
        conditions.append("AND EXISTS (SELECT 1 FROM `tabWarehouse` WHERE name = sed.t_warehouse AND department = %(to_department)s)")
       
    if filters.get("raw_material"):
        conditions.append("AND sed.item_code = %(raw_material)s")
    
    return " ".join(conditions) if conditions else ""
