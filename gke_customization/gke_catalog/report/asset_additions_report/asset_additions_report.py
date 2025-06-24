import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 180},
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 220},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 190},
        {"label": _("Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 180},
        {"label": _("Vendor"), "fieldname": "vendor", "fieldtype": "Data", "width": 160},
        {"label": _("Invoice No"), "fieldname": "invoice_no", "fieldtype": "Link", "options": "Purchase Invoice", "width": 160},
        {"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 160},
        {"label": _("Cost (₹)"), "fieldname": "cost", "fieldtype": "Data", "width": 130},
        {"label": _("Capitalized Date"), "fieldname": "capitalized_date", "fieldtype": "Date", "width": 180},
        {"label": _("PO Number"), "fieldname": "po_no", "fieldtype": "Link", "options": "Purchase Order", "width": 210},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 160},
        {"label": _("Custodian"), "fieldname": "custodian", "fieldtype": "Link", "options": "Employee", "width": 160},
    ]

def get_data(filters):
    conds = []

    if filters.get("from_date"):
        conds.append(["purchase_date", ">=", filters.get("from_date")])
    if filters.get("to_date"):
        conds.append(["purchase_date", "<=", filters.get("to_date")])
    if filters.get("company"):
        conds.append(["company", "in", filters.get("company")])
    if filters.get("branch"):
        conds.append(["branch", "in", filters.get("branch")])
    if filters.get("location"):
        conds.append(["location", "in", filters.get("location")])    
    if filters.get("department"):
        conds.append(["department", "in", filters.get("department")])

    assets = frappe.get_all("Asset",
        filters=conds,
        fields=[
            "name", "purchase_date", "asset_name", "asset_category", "supplier", "purchase_invoice",
            "purchase_receipt", "branch", "total_asset_cost", "available_for_use_date","location",
            "department", "custodian"
        ],
    )

    data = []
    for asset in assets:
        # Initialize values
        vendor = ""
        vendor_name = ""
        invoice_no = asset.purchase_invoice
        po_no = ""

        # Fetch Purchase Receipt
        if asset.purchase_receipt:
            pr = frappe.db.get_value("Purchase Receipt", asset.purchase_receipt, ["supplier", "supplier_name"], as_dict=True)
            if pr:
                vendor = pr.supplier or asset.supplier
                vendor_name = pr.supplier_name
            # Fetch PO from Purchase Receipt Item
            po = frappe.db.get_value("Purchase Receipt Item", {"parent": asset.purchase_receipt, "docstatus": ("<", 2)}, "purchase_order")
            if po:
                po_no = po
            # Attempt to get invoice from PRI
            pi = frappe.db.get_value("Purchase Invoice Item", {"purchase_receipt": asset.purchase_receipt}, "parent")
            if pi:
                invoice_no = pi
        else:
            vendor = asset.supplier

        data.append({
            "purchase_date": asset.purchase_date,
            "asset_id": asset.name,
            "asset_name": asset.asset_name,
            "asset_category": asset.asset_category,
            "vendor": vendor,
            "invoice_no": invoice_no,
            "location": asset.location,
            "cost": frappe.utils.fmt_money(asset.total_asset_cost, currency="INR"),
            "capitalized_date": asset.available_for_use_date,
            "po_no": po_no,
            "department": asset.department,
            "custodian": asset.custodian,
        })

    return data
