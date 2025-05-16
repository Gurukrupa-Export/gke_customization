# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 230},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 160},
        {"label": "Warehouse", "fieldname": "t_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 230},
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Stock Entry Type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 140},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 270},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 190},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Int", "width": 100},
        {"label": "Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 120},
    ]

    allowed_groups = frappe.get_all("Item Group", filters={"parent_item_group": "Consumable"}, pluck="name")

    if filters.get("item_group"):
        selected_groups = filters["item_group"]
        if isinstance(selected_groups, str):
            selected_groups = [x.strip() for x in selected_groups.split(",") if x.strip()]
        allowed_groups = [g for g in selected_groups if g in allowed_groups]

    items = frappe.get_all("Item", filters={"item_group": ["in", allowed_groups]}, fields=["name", "item_name", "item_group"])
    item_info = {item.name: item for item in items}

    if not item_info:
        return columns, []

    se_filters = {"docstatus": 1}
    if filters.get("from_date") and filters.get("to_date"):
        se_filters["posting_date"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        se_filters["posting_date"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        se_filters["posting_date"] = ["<=", filters["to_date"]]

    stock_entries = frappe.get_all("Stock Entry", filters=se_filters, fields=["name", "posting_date", "stock_entry_type","company","branch"])
    se_map = {se.name: se for se in stock_entries}
    se_names = list(se_map.keys())

    if not se_names:
        return columns, []

    sed_filters = {
        "item_code": ["in", list(item_info.keys())],
        "parent": ["in", se_names]
    }

    if filters.get("t_warehouse"):
        sed_filters["t_warehouse"] = filters["t_warehouse"] if isinstance(filters["t_warehouse"], str) else ["in", filters["t_warehouse"]]
    
   
    
    sed_list = frappe.get_all(
        "Stock Entry Detail",
        filters=sed_filters,
        fields=["item_code", "qty", "basic_amount", "t_warehouse", "parent"]
    )

    result = {}
    for sed in sed_list:
        item = item_info[sed.item_code]
        se = se_map.get(sed.parent, {})
        key = (sed.item_code, sed.t_warehouse, se.get("posting_date"), se.get("stock_entry_type"),se.get("company"),se.get("branch"))

        if key not in result:
            result[key] = {
                "item_code": sed.item_code,
                "item_name": item.item_name,
                "item_group": item.item_group,
                "t_warehouse": sed.t_warehouse,
                "posting_date": se.get("posting_date"),
                "stock_entry_type": se.get("stock_entry_type"),
                "company": se.get("company"),
                "branch": se.get("branch"),               
                "qty": 0,
                "cost": 0
            }

        result[key]["qty"] += sed.qty or 0
        result[key]["cost"] += sed.basic_amount or 0

    # data = list(result.values())
    data = sorted(result.values(), key=lambda x: (x["posting_date"], x["cost"]), reverse=True)
    summary = get_report_summary(data)
    # report_summary = get_report_summary(data)
    
    return columns, data,None,None, summary

def get_report_summary(data):
    total_qty = sum(row.get("qty", 0) for row in data)
    total_cost = sum(row.get("cost", 0) for row in data)
    total_entries = len(set(row.get("item_code") for row in data if row.get("item_code")))


    summary = [
        {"label": "Total Items", "value": total_entries, "indicator": "Red"},
        {"label": "Total Qty", "value": total_qty, "indicator": "Blue"},
        {"label": "Total Cost", "value":"{:,.2f}".format(total_cost), "indicator": "Green"},
    ]

    return summary




# GE-SE-MT-24-00141 , GE-SE-MI-24-00029


