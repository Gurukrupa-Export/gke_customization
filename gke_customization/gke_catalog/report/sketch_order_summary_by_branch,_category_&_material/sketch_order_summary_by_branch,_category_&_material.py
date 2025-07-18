# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe


import frappe
from collections import defaultdict

def get_columns(group_key):
    return [
        {"label": group_key.title(), "fieldname": group_key, "fieldtype": "Data", "width": 180},
        {"label": "Assigned Qty", "fieldname": "assigned_qty", "fieldtype": "Int", "width": 120},
        {"label": "Rough Approved Qty", "fieldname": "rough_approved_qty", "fieldtype": "Int", "width": 180},
        {"label": "Rough Rejected Qty", "fieldname": "rough_rejected_qty", "fieldtype": "Int", "width": 180},
        {"label": "Final Approved Qty", "fieldname": "final_approved_qty", "fieldtype": "Int", "width": 180},
        {"label": "Final Rejected Qty", "fieldname": "final_rejected_qty", "fieldtype": "Int", "width": 180},
    ]

def execute(filters=None):
    filters = filters or {}
    subcategory_filter = filters.get("subcategory") or []

    label_map = {
    "category": "category",
    "branch": "branch",
    "diamond target range": "diamond_target_range",
    "metal target range": "metal_target_range"
}

    selected_label = (filters.get("group_by_type") or "Category").strip().lower()
    group_by_type = label_map.get(selected_label)

    if not group_by_type:
        frappe.throw("Invalid Group By option")

    # Sketch Orders
    sketch_filters = {}
    if subcategory_filter:
        sketch_filters["subcategory"] = ["in", subcategory_filter]

    sketch_orders = frappe.get_all(
        "Sketch Order",
        filters=sketch_filters,
        fields=["name", "branch", "category", "subcategory", "diamond_target_range","metal_target_range"]
    )
    if not sketch_orders:
        return get_columns(group_by_type), [], None, {}

    so_map = {so["name"]: so for so in sketch_orders}

    # designer assign
    designer_assignments = frappe.get_all(
        "Designer Assignment",
        filters={"parent": ["in", list(so_map)]},
        fields=["parent", "designer", "count_1"]
    )

    # branch of the designers 
    designer_ids = list({d["designer"] for d in designer_assignments if d.get("designer")})
    designer_branch_map = {}

    if designer_ids:
        employee_branches = frappe.get_all(
            "Employee",
            filters={"name": ["in", designer_ids]},
            fields=["name", "branch"]
        )
        designer_branch_map = {emp["name"]: emp["branch"] for emp in employee_branches}

    # 
    group_map = defaultdict(lambda: {
        "assigned_qty": 0,
        "rough_approved_qty": 0,
        "rough_rejected_qty": 0,
        "final_approved_qty": 0,
        "final_rejected_qty": 0
    })

    def get_group(parent, designer=None):
        # if group_by_type == "branch" and designer:
        #     return designer_branch_map.get(designer) or "Unknown"
        # # return so_map[parent].get(group_by_type) or "Unknown"

        if group_by_type == "branch":
            return designer_branch_map.get(designer) or "Not Defined"
        elif group_by_type in {"category", "diamond_target_range", "metal_target_range"}:
            return so_map.get(parent, {}).get(group_by_type) or "Not Defined"
        return "Not Defined"

    #  assigned qty
    for ds in designer_assignments:
        parent = ds["parent"]
        if parent in so_map:
            group = get_group(parent, designer=ds.get("designer"))
            group_map[group]["assigned_qty"] += ds.get("count_1", 0)

    def update(data_list, field, key, use_designer=False):
        for doc in data_list:
            parent = doc.get("parent")
            if parent in so_map:
                designer = doc.get("designer") if use_designer else None
                group = get_group(parent, designer)
                group_map[group][key] += doc.get(field, 0)

    # rough sketch approved and rejected 
    rsa = frappe.get_all(
        "Rough Sketch Approval",
        filters={"parent": ["in", list(so_map)]},
        fields=["parent", "approved", "reject", "designer"]
    )
    update(rsa, "approved", "rough_approved_qty", use_designer=True)
    update(rsa, "reject", "rough_rejected_qty", use_designer=True)

    # final sketch approved and rejected 
    fsa = frappe.get_all(
        "Final Sketch Approval HOD",
        filters={"parent": ["in", list(so_map)]},
        fields=["parent", "approved", "reject", "designer"]
    )
    update(fsa, "approved", "final_approved_qty", use_designer=True)
    update(fsa, "reject", "final_rejected_qty", use_designer=True)

    #  sorting 
    data = [{group_by_type: group, **counts} for group, counts in group_map.items()]
    # data = sorted(data, key=lambda x: x[group_by_type])
    data = sorted(data, key=lambda x: extract_range_start(x[group_by_type]) if group_by_type in ("metal_target_range", "diamond_target_range") else x[group_by_type])


   #  chart
    chart = {
        "data": {
            "labels": [row[group_by_type] for row in data],
            "datasets": [
                {"name": "Assigned Qty", "values": [row["assigned_qty"] for row in data]},
                {"name": "Rough Approved", "values": [row["rough_approved_qty"] for row in data]},
                {"name": "Rough Rejected", "values": [row["rough_rejected_qty"] for row in data]},
                {"name": "Final Approved", "values": [row["final_approved_qty"] for row in data]},
                {"name": "Final Rejected", "values": [row["final_rejected_qty"] for row in data]},
            ]
        },
        "type": "bar",
        # "barOptions": {"stacked": True},
         "colors": ["#e07991","#1982c4", "#83603e", "#79a862", "#ff595e"]
    #  "colors": ["#007bff","#28a745", "#ffc107", "#20c997", "#e74a3b"],



    }

    return get_columns(group_by_type), data, None, chart


import re
# for metal and diamond range in ascending order
def extract_range_start(label):
    match = re.search(r'\d+\.?\d*', label)
    return float(match.group()) if match else float('inf') 

