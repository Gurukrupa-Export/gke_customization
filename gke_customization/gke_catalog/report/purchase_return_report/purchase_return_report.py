# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        # Sr No will be auto index in UI, so we start from Purchase Return No
        {
            "label": _("Purchase Return No"),
            "fieldname": "purchase_return_no",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 150,
        },
        {
            "label": _("Return Date"),
            "fieldname": "return_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 120,
        },
        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Return Against Purchase Receipt"),
            "fieldname": "return_against",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 180,
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 130,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Purchased Qty"),
            "fieldname": "purchased_qty",
            "fieldtype": "Float",
            "width": 110,
        },
        {
            "label": _("Returned Qty"),
            "fieldname": "returned_qty",
            "fieldtype": "Float",
            "width": 110,
        },
    ]


def get_conditions(filters):
    conditions = []
    params = {}

    # Company
    if filters.get("company"):
        conditions.append("pr.company = %(company)s")
        params["company"] = filters.get("company")

    # Branch (assuming custom field 'branch' on Purchase Receipt)
    if filters.get("branch"):
        conditions.append("pr.branch = %(branch)s")
        params["branch"] = filters.get("branch")

    # Manufacturer (assuming custom field on Purchase Receipt Item)
    if filters.get("manufacturer"):
        conditions.append("pri.manufacturer = %(manufacturer)s")
        params["manufacturer"] = filters.get("manufacturer")

    # Date range - From Date and To Date
    if filters.get("from_date"):
        conditions.append("pr.posting_date >= %(from_date)s")
        params["from_date"] = filters.get("from_date")
    
    if filters.get("to_date"):
        conditions.append("pr.posting_date <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    # Item Code
    if filters.get("item_code"):
        conditions.append("pri.item_code = %(item_code)s")
        params["item_code"] = filters.get("item_code")

    where = ""
    if conditions:
        where = " AND " + " AND ".join(conditions)

    return where, params


def get_data(filters):
    conditions, params = get_conditions(filters)

    sql = """
        SELECT
            pr.name AS purchase_return_no,
            pr.posting_date AS return_date,
            pr.supplier AS supplier,
            pr.supplier_name AS supplier_name,
            pr.return_against AS return_against,
            pri.item_code AS item_code,
            pri.item_name AS item_name,
            orig_pri.qty AS purchased_qty,
            pri.qty AS returned_qty
        FROM `tabPurchase Receipt` pr
        INNER JOIN `tabPurchase Receipt Item` pri
            ON pri.parent = pr.name
        INNER JOIN `tabPurchase Receipt Item` orig_pri
            ON orig_pri.parent = pr.return_against
            AND orig_pri.item_code = pri.item_code
        WHERE
            pr.docstatus = 1
            AND pr.is_return = 1
            {conditions}
        ORDER BY
            pr.posting_date DESC,
            pr.name
    """.format(conditions=conditions)

    data = frappe.db.sql(sql, params, as_dict=True)

    return data
