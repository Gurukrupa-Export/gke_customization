import frappe
from frappe import _
from datetime import datetime
from dateutil.relativedelta import relativedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 200},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 170},
        {"label": _("Book Location"), "fieldname": "book_location", "fieldtype": "Data", "width": 150},
        {"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Data", "width": 190},
        {"label": _("Purchase Amount"), "fieldname": "purchase_amount", "fieldtype": "Currency", "width": 135},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Aging"), "fieldname": "age", "fieldtype": "Data", "width": 190},
    ]

def get_data(filters):
    conds = []
    if filters.get("company"):
        conds.append(["company", "in", filters.get("company")])
    if filters.get("branch"):
        conds.append(["branch", "in", filters.get("branch")])
    if filters.get("location"):
        conds.append(["book_location", "in", filters.get("location")])    
    if filters.get("department"):
        conds.append(["department", "in", filters.get("department")])
    conds.append(["custodian", "=", ""])

    today = datetime.today()
    assets = frappe.get_all("Asset", 
        filters=conds,
        fields=["name", "asset_name", "location", "purchase_date", "total_asset_cost", "department"]
    )

    data = []
    for a in assets:
        age = ""
        formatted_date = ""
        if a.purchase_date:
            diff = relativedelta(today, a.purchase_date)
            age = f"{diff.years} yrs : {diff.months} months : {diff.days} days"
            formatted_date = a.purchase_date.strftime("%A, %B %d, %Y")

        data.append({
            "asset_id": a.name,
            "asset_name": a.asset_name,
            "book_location": a.location,
            "purchase_date": formatted_date,
            "purchase_amount": a.total_asset_cost,
            "department": a.department,
            "age": age
        })

    return data
