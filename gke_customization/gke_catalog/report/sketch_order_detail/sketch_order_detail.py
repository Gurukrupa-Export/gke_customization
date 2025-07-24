# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def get_columns():
    return [
        {"label": "Sketch Order Id", "fieldname": "name", "fieldtype": "Link", "options": "Sketch Order", "width": 150},
        {"label": "Sketch Order Form", "fieldname": "sketch_order_form", "fieldtype": "Link", "options": "Sketch Order Form", "width": 180},       
        # {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 120},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 130},
        {"label": "Customer", "fieldname": "customer_code", "fieldtype": "Link","options":"Customer", "width": 150},
        {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 130},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Date", "width": 150},
        {"label": "Sketch Delivery", "fieldname": "est_delivery_date", "fieldtype": "Date", "width": 160},
        {"label": "Salesman", "fieldname": "salesman_name", "fieldtype": "Data", "width": 150},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
        {"label": "Design By", "fieldname": "design_by", "fieldtype": "Data", "width": 120},
        {"label": "Design Type", "fieldname": "design_type", "fieldtype": "Data", "width": 120},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 100},
        {"label": "Subcategory", "fieldname": "subcategory", "fieldtype": "Data", "width": 150},
        {"label": "Setting Type", "fieldname": "setting_type", "fieldtype": "Data", "width": 120},
        {"label": "Metal Target", "fieldname": "metal_target", "fieldtype": "Float", "width": 120},
        {"label": "Diamond Target", "fieldname": "diamond_target", "fieldtype": "Float", "width": 150},
        {"label": "Approx Gold Wt", "fieldname": "gold_wt_approx", "fieldtype": "Float", "width": 150},
        {"label": "Approx Diamond Wt", "fieldname": "diamond_wt_approx", "fieldtype": "Float", "width": 180},
        {"label": "Design Assigned", "fieldname": "count_1", "fieldtype": "Int", "width": 140},
        {"label": "Rough Approved Sketch", "fieldname": "rough_approved", "fieldtype": "Int", "width": 150},
        {"label": "Rough Rejected Sketch", "fieldname": "rough_rejected", "fieldtype": "Int", "width": 150},
        {"label": "Final Approved Sketch", "fieldname": "final_approved", "fieldtype": "Int", "width": 150},
        {"label": "Final Rejected Sketch", "fieldname": "final_rejected", "fieldtype": "Int", "width": 150},
        {"label": "Final (CMO/CPO)", "fieldname": "cmo_count", "fieldtype": "Int", "width": 150},
        {"label": "Items", "fieldname": "item_counts", "fieldtype": "HTML", "width": 100},
    ]

def get_data(filters=None):
    
    condition_sql = get_conditions(filters or {})
    where_clause = f"WHERE {condition_sql}" if condition_sql else ""

    result =  frappe.db.sql(f"""
        SELECT
            so.name,
            so.company,
            so.branch,
            so.workflow_state,           
            so.customer_code,
            so.order_date,
            so.delivery_date,
            so.est_delivery_date,
            so.salesman_name,
            so.order_type,
            so.design_by,
            so.design_type,
            so.sketch_order_form,
            so.category,
            so.subcategory,
            so.setting_type,
            so.metal_target,
            so.diamond_target,
            dsa.count_1,
            rsa.approved AS rough_approved,
            rsa.reject AS rough_rejected,
            fsa.approved AS final_approved,
            fsa.reject AS final_rejected,
            cmo_sub.cmo_count,
            item_counts.item_counts
        FROM `tabSketch Order` so
        LEFT JOIN `tabDesigner Assignment` dsa ON so.name = dsa.parent
        LEFT JOIN `tabRough Sketch Approval` rsa ON so.name = rsa.parent
        LEFT JOIN `tabFinal Sketch Approval HOD` fsa ON so.name = fsa.parent
        LEFT JOIN (
    SELECT parent, COUNT(name) AS cmo_count
    FROM `tabFinal Sketch Approval CMO`
    GROUP BY parent
) AS cmo_sub ON cmo_sub.parent = so.name
        LEFT JOIN `tabCustomer` cst on so.customer_code = cst.name
        LEFT JOIN (
    SELECT custom_sketch_order_id, COUNT(name) AS item_counts
    FROM `tabItem`
    GROUP BY custom_sketch_order_id
) AS item_counts ON item_counts.custom_sketch_order_id = so.name
        {where_clause}
        GROUP BY so.name 
        ORDER BY so.order_date DESC     
    """, filters, as_dict=True)

    gold_wt_map = defaultdict(float)
    diamond_wt_map = defaultdict(float)

    cmo_data = frappe.db.get_all(
        "Final Sketch Approval CMO",
        fields=["parent", "gold_wt_approx", "diamond_wt_approx"],
        filters={"parent": ["in", [r["name"] for r in result]]}
    )

    for row_cmo in cmo_data:
        parent = row_cmo["parent"]
        gold_wt_map[parent] += safe_float(row_cmo.get("gold_wt_approx"))
        diamond_wt_map[parent] += safe_float(row_cmo.get("diamond_wt_approx"))

    for row in result:
       if row.get("item_counts"):
        row["item_counts"] = f"""<a href="/app/query-report/Sketch Order Item Detail?sketch_order={row['name']}" target="_blank" style="color: inherit; text-decoration: underline;">{row['item_counts']}</a>"""
        row["gold_wt_approx"] = round(gold_wt_map.get(row["name"], 0.0), 3)
        row["diamond_wt_approx"] = round(diamond_wt_map.get(row["name"], 0.0), 3)
    return result  

def get_conditions(filters):
    conditions = []

    if filters.get("from_date"):
        conditions.append(f"""so.modified >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""so.modified <= "{filters['to_date']}" """)
    if filters.get("branch"):
        conditions.append(f"""so.branch = "{filters['branch']}" """)
    if filters.get("customer"):
        if isinstance(filters["customer"], list):
            raw_customer_list = filters["customer"]
            customer_list = []
            for item in raw_customer_list:
                customer_list.extend([c.strip() for c in item.split(",") if c.strip()])
        else:
            customer_list = [c.strip() for c in filters["customer"].split(",") if c.strip()]
        if customer_list:
            conditions.append("so.customer_code IN %(customer_list)s")
            filters["customer_list"] = customer_list
    if filters.get("customer_group"):
        conditions.append(f"""cst.customer_group = "{filters['customer_group']}" """)
    if filters.get("docstatus") not in (None, "", "undefined"):
        conditions.append(f"""so.docstatus = {int(filters['docstatus'])}""")
    if filters.get("workflow_state"):
        conditions.append(f"""so.workflow_state = "{filters['workflow_state']}" """)

    return " AND ".join(conditions)

