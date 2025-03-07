# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
import frappe
import urllib.parse
import json
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    # message = get_message()

    return columns, data


# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import urllib.parse
import json
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)


    return columns, data

def get_columns():
    return [
        {"fieldname": "pre_orderform_id", "label": "Pre Order Form ID", "fieldtype": "Data", "width": 150},
        {"fieldname": "branch_name", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "order_date", "label": "Order Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "created_date_time", "label": "Created Date/Time", "fieldtype": "Datetime", "width": 180},
        {"fieldname": "due_days", "label": "Due Days", "fieldtype": "Int", "width": 100},
         {"fieldname": "party_code", "label": "Party Code", "fieldtype": "Data", "width": 150},
        {"fieldname": "order_type", "label": "Order Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "po_no", "label": "PO Number", "fieldtype": "Data", "width": 180},
        {"fieldname": "order_no", "label": "Order No", "fieldtype": "Data", "width": 150},
        {"fieldname": "bulk_order_no", "label": "Bulk Order No", "fieldtype": "Data", "width": 150},
         {"fieldname": "stylebio", "label": "Style Bio", "fieldtype": "Data", "width": 180},
         {"fieldname": "tagno", "label": "Tag Number", "fieldtype": "Data", "width": 150},
        {"fieldname": "category", "label": "Category", "fieldtype": "Data", "width": 150},
         {"fieldname": "sub_category", "label": "Sub Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "setting_type", "label": "Setting Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "diamond_pcs", "label": "Diamond Pieces", "fieldtype": "Int", "width": 120},
        {"fieldname": "new_category", "label": "New Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "new_sub_category", "label": "New Sub Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "width": 150},
        {"fieldname": "item_variant", "label": "Item Variant", "fieldtype": "Data", "width": 150},
        {"fieldname": "bom", "label": "BOM", "fieldtype": "Data", "width": 150},
        {"fieldname": "order_form", "label": "Order Form", "fieldtype": "Data", "width": 150},
        {"fieldname": "order_form_type", "label": "Order Form Type", "fieldtype": "Data", "width": 150},  
        {"fieldname": "order_details_and_remarks", "label": "Order Details & Remarks", "fieldtype": "Data", "width": 250},  
          {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 150},  
    ]


def get_data(filters):
    conditions = []


    if filters.get("from_date"):
        conditions.append(f"""pofd.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""pofd.order_date <= "{filters['to_date']}" """)

    if filters.get("pre_order_id"):
        order_ids = "', '".join(filters["pre_order_id"])
        conditions.append(f"pof.name IN ('{order_ids}')")
    
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"pofd.branch_name IN ({branches})")

    if filters.get("party_code"):
        conditions.append(f'pofd.party_code = "{filters.get("party_code")}"')


    if filters.get("status"):
         conditions.append(f'pofd.status = "{filters.get("status")}"')

    conditions = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        
        select 
         pof.name AS pre_orderform_id,
         pofd.branch_name as branch_name,
         pofd.bulk_order_no as bulk_order_no,
         pofd.category as category,
         pof.date as created_date_time,
         pofd.diamond_pcs AS diamond_pcs,
         pofd.due_days AS due_days,
         pofd.order_date AS order_date,
         pofd.order_details_and_remarks,
         pofd.order_no AS order_no,
         pofd.order_type AS order_type,
         pofd.party_code AS party_code,
         pofd.po_number AS po_no,
         pofd.setting_type AS setting_type,
         pofd.stylebio AS stylebio,
         pofd.sub_category AS sub_category,
         pofd.tagno AS tagno,
         pofd.new_category AS new_category,
         pofd.new_sub_category AS new_sub_category,
         pofd.item_code AS item_code,
         pofd.item_variant AS item_variant,
         pofd.bom AS bom,
         pofd.status AS status,
         pofd.order_form AS order_form,
         pofd.order_form_type AS order_form_type
         
         
        from `tabPre Order Form`pof
        left join
        `tabPre Order Form Details` pofd
         on pof.name = pofd.parent  
         WHERE 
        {conditions}
        ORDER BY pof.creation DESC, pofd.name ASC    
    """

    data = frappe.db.sql(query, as_dict=True)

  
    return data






