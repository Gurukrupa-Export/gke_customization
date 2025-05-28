# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import urllib.parse
import json
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)


    return columns, data

def get_columns(filters):
    pre_order_only = filters.get("pre_order_only", 0)

    columns = []

    if pre_order_only:
        columns.append({
            "fieldname": "pre_orderform_id",
            "label": "Pre Order Form",
            "fieldtype": "Link",
            "options": "Pre Order Form",
            "width": 180
        })

    columns += [
        { "fieldname": "company", "label": "Company", "fieldtype": "Data", "width": 150 },
        { "fieldname": "branch_name", "label": "Branch", "fieldtype": "Data", "width": 150 },
        { "fieldname": "customer_code", "label": "Customer", "fieldtype": "Data", "width": 150 },
        { "fieldname": "order_type", "label": "Order Type", "fieldtype": "Data", "width": 150 },
        { "fieldname": "party_code", "label": "Party Code", "fieldtype": "Data", "width": 150 },
        { "fieldname": "po_no", "label": "PO Number", "fieldtype": "Data", "width": 180 },
        { "fieldname": "diamond_quality", "label": "Diamond Quality", "fieldtype": "Data", "width": 150 },
        { "fieldname": "order_date", "label": "Order Date", "fieldtype": "Date", "width": 150 },
        { "fieldname": "created_date_time", "label": "Created Date/Time", "fieldtype": "Datetime", "width": 180 },
        { "fieldname": "order_no", "label": "Order No", "fieldtype": "Data", "width": 150 },
        { "fieldname": "bulk_order_no", "label": "Bulk Order No", "fieldtype": "Data", "width": 150 },
        { "fieldname": "stylebio", "label": "Style Bio", "fieldtype": "Data", "width": 180 },
        { "fieldname": "tagno", "label": "Tag Number", "fieldtype": "Data", "width": 150 },
        { "fieldname": "diamond_pcs", "label": "Diamond Pcs", "fieldtype": "Data", "width": 190 },
        { "fieldname": "setting_type", "label": "Setting Type", "fieldtype": "Data", "width": 150 },
        { "fieldname": "category", "label": "Category", "fieldtype": "Data", "width": 150 },
        { "fieldname": "sub_category", "label": "Sub Category", "fieldtype": "Data", "width": 150 },
        { "fieldname": "new_category", "label": "New Category", "fieldtype": "Data", "width": 150 },
        { "fieldname": "new_sub_category", "label": "New Sub Category", "fieldtype": "Data", "width": 150 },
        { "fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "width": 150 },
        { "fieldname": "item_variant", "label": "Item Variant", "fieldtype": "Data", "width": 150 },
        { "fieldname": "bom", "label": "BOM", "fieldtype": "Data", "width": 150 },
        { "fieldname": "order_details_and_remarks", "label": "Order Details & Remarks", "fieldtype": "Data", "width": 250 },
        { "fieldname": "item_and_bom_complete_date", "label": "Item & BOM Complete Date", "fieldtype": "Date", "width": 150 },
        { "fieldname": "status", "label": "Order Status", "fieldtype": "Data", "width": 150 },
        { "fieldname": "docstatus", "label": "Document Status", "fieldtype": "Data", "width": 150 },
        { "fieldname": "workflow_state", "label": "Workflow Status", "fieldtype": "Data", "width": 150 },
        { "fieldname": "delivery_date", "label": "Delivery Date", "fieldtype": "Date", "width": 150 }

        
    ]

    return columns


def get_data(filters):
    conditions = []


    if filters.get("from_date"):
        conditions.append(f"""pof.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""pof.order_date <= "{filters['to_date']}" """)

    if filters.get("pre_order_id"):
        order_ids = "', '".join(filters["pre_order_id"])
        conditions.append(f"pof.name IN ('{order_ids}')")
    
    if filters.get("company"):
        # branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""pof.company <= "{filters['company']}" """)
    
    if filters.get("branch"):
        # branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""pof.branch <= "{filters['branch']}" """)

    if filters.get("party_code"):
        conditions.append(f'pof.party_code = "{filters.get("party_code")}"')

    if filters.get("status"):
         conditions.append(f'pofd.status = "{filters.get("status")}"')

    if filters.get("docstatus"):
         conditions.append(f'pof.docstatus = "{filters.get("docstatus")}"')

    if filters.get("workflow_state"):
         conditions.append(f'pof.workflow_state = "{filters.get("workflow_state")}"')

    conditions = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        
        select 
         pof.name AS pre_orderform_id,
         pof.company AS company,
         pof.branch as branch_name,
         pof.customer_code AS customer_code,
         pof.order_type AS order_type,
         pof.party_code AS party_code,
         pof.po_no AS po_no,
         pof.diamond_quality AS diamond_quality,
         pof.order_date AS order_date,
         pof.creation as created_date_time,
         pofd.order_no AS order_no,
         pofd.bulk_order_no as bulk_order_no,
         pofd.stylebio AS stylebio,
        pofd.tagno AS tagno,
         pofd.diamond_pcs AS diamond_pcs,
         pofd.setting_type AS setting_type,
         pofd.category AS category,
         pofd.sub_category AS sub_category,
        pofd.new_category AS new_category,
         pofd.new_sub_category AS new_sub_category,
         pofd.item_code AS item_code,
         pofd.item_variant AS item_variant,
         pofd.bom AS bom,
        pofd.order_details_and_remarks,
        pofd.item_and_bom_complete_date AS item_and_bom_complete_date,
         pofd.status AS status,
         pofd.order_form_type AS order_form_type,
          CASE WHEN pof.docstatus = 0 THEN "Draft"
                 WHEN pof.docstatus = 1 THEN "Submitted"
                 WHEN pof.docstatus = 2 THEN "Cancelled" END AS docstatus, 
         pof.workflow_state,
         pof.delivery_date AS delivery_date 
        from `tabPre Order Form`pof
        left join
        `tabPre Order Form Details` pofd
         on pof.name = pofd.parent  
         WHERE 
        {conditions}
        ORDER BY pof.creation DESC, pofd.name ASC    
    """

    data = frappe.db.sql(query, as_dict=True)

    if data:
        unique_fields = ['pre_orderform_id', 'customer_code', 'order_no', 'stylebio', 'tagno', 'item_code']
        total_row = {}

        for field in unique_fields:
            unique_count = len(set(row.get(field) for row in data if row.get(field)))
    
            if field == 'pre_orderform_id':
                total_row[field] = "🟢Pre Order Forms: {}\u200B".format(unique_count)
                continue  # Skip the rest of the loop for this field
    
            label = {
        'customer_code': 'Customers ',
        'order_no': 'Orders ',
        'stylebio': 'Stylebio ',
        'tagno': 'Tag Nos ',
        'item_code': 'Item Codes '
    }.get(field, field.replace('_', ' ').title())

            total_row[field] = f"<b><span style='color: green;'>{label}:{unique_count}</span></b>"

        total_diamond_pcs = sum(
        float(row["diamond_pcs"]) for row in data 
        if row.get("diamond_pcs") not in (None, "", " ") and str(row.get("diamond_pcs")).replace(".", "", 1).isdigit()
    )   
        
        total_row["diamond_pcs"] = f"<b><span style='color: green;'>Diamond Pcs: {total_diamond_pcs}</span></b>"
        
        
        for col in get_columns(filters):
            if col["fieldname"] not in total_row:
                total_row[col["fieldname"]] = ""

        data.append(total_row)

    return data
