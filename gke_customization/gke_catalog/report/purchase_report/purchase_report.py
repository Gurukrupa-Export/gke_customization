# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Purchase ID", "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 150},
        {"label": "Date & Time", "fieldname": "creation", "fieldtype": "Datetime", "width": 160},
        {"label": "Supplier Challan No", "fieldname": "custom_supplier_challan_no", "fieldtype": "Data", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Data", "width": 160},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 140},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        # {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},  # optional
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "precision": 3, "width": 100},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 120},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": "Remark", "fieldname": "remarks", "fieldtype": "Data", "width": 200},
    ]


def get_conditions(filters):
    conditions = ""

    if filters.get("company"):
        conditions += " AND pr.company = %(company)s"

    if filters.get("branch"):
        conditions += " AND pr.branch = %(branch)s"

    if filters.get("from_date"):
        conditions += " AND pr.creation >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND pr.creation <= %(to_date)s"

    if filters.get("supplier"):
        conditions += " AND pr.supplier = %(supplier)s"

    if filters.get("item_code"):
        conditions += " AND pri.item_code = %(item_code)s"

    if filters.get("item_group"):
        conditions += " AND pri.item_group = %(item_group)s"

    if filters.get("department"):
        conditions += " AND wh.department = %(department)s"

    conditions += " AND mr.docstatus = 1"

    conditions += " AND IFNULL(pr.is_return, 0) = 0"

    return conditions


def get_data(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(f"""
        SELECT
        pr.name AS purchase_receipt,
        pr.creation,
        pr.custom_supplier_challan_no,
        pr.supplier,
        pr.supplier_name,
        pri.item_group,
        pri.item_code,
        pri.qty,
        pri.uom,
        pri.rate,
        pri.amount,
        wh.department,
        pr.remarks

    FROM `tabPurchase Receipt` pr

    INNER JOIN `tabPurchase Receipt Item` pri
        ON pr.name = pri.parent

    LEFT JOIN `tabWarehouse` wh
        ON pri.warehouse = wh.name

    LEFT JOIN `tabPurchase Order Item` poi
        ON pri.purchase_order_item = poi.name

    LEFT JOIN `tabMaterial Request Item` mri
        ON poi.material_request_item = mri.name

    LEFT JOIN `tabMaterial Request` mr
        ON mri.parent = mr.name

    WHERE pr.docstatus = 1
    {conditions}

    ORDER BY pr.creation DESC
""", filters, as_dict=1)

    return data