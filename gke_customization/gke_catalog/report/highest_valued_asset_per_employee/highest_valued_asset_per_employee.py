import frappe
from frappe import _
from collections import defaultdict
from frappe.utils import today

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 210},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
        # {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 160},
        # {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
        {"label": _("Custodian"), "fieldname": "custodian", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 190},
        # {"label": _("Acquisition Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 140},
        {"label": _("Cost (₹)"), "fieldname": "cost", "fieldtype": "Currency", "width": 120},
        # {"label": _("Useful Life (Years)"), "fieldname": "useful_life", "fieldtype": "Data", "width": 160},
        # {"label": _("Accumulated Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 180},
        {"label": _("NRV as on Date"), "fieldname": "nrv", "fieldtype": "Currency", "width": 160},
        # {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters):

    conds = []
    if filters.get("company"):
        conds.append(["company", "in", filters.get("company")])
    if filters.get("branch"):
        conds.append(["branch", "in", filters.get("branch")])
    if filters.get("location"):
        conds.append(["location", "in", filters.get("location")])    
    if filters.get("department"):
        conds.append(["department", "in", filters.get("department")])
    conds.append(["custodian", "!=", ""])
    today_date = today()
    
	
    assets = frappe.get_all("Asset",
        filters=conds, 
        fields=["name", "asset_name", "asset_category", "branch","location", "department", "custodian", "purchase_date", "total_asset_cost", "status"],
        order_by="total_asset_cost desc"
    )
    asset_ids = [a.name for a in assets]

    afb_rows = frappe.get_all("Asset Finance Book",
        filters={"parent": ["in", asset_ids]},
        fields=["parent", "total_number_of_depreciations", "frequency_of_depreciation"]
    )
    afb_map = defaultdict(lambda: {"total_number_of_depreciations": 0, "frequency_of_depreciation": 1})
    for row in afb_rows:
        afb_map[row.parent] = {
            "total_number_of_depreciations": row.total_number_of_depreciations or 0,
            "frequency_of_depreciation": row.frequency_of_depreciation or 1
        }

    ads_rows = frappe.get_all("Asset Depreciation Schedule",
        filters={"asset": ["in", asset_ids]},
        fields=["name", "asset"]
    )
    ads_to_asset = {}
    for row in ads_rows:
        ads_to_asset[row.name] = row.asset

    ds_rows = frappe.get_all("Depreciation Schedule",
        filters={"schedule_date": ["<=", today_date], "parent": ["in", list(ads_to_asset.keys())]},
        fields=["parent", "schedule_date", "accumulated_depreciation_amount"]
    )

    max_depreciation_map = {}
    for row in ds_rows:
        asset = ads_to_asset.get(row.parent)
        if not asset:
            continue
        current_max = max_depreciation_map.get(asset, 0)
        if (row.accumulated_depreciation_amount or 0) > current_max:
            max_depreciation_map[asset] = row.accumulated_depreciation_amount or 0

    data = []
    for a in assets:
        afb = afb_map.get(a.name)
        useful_life =(afb["total_number_of_depreciations"] * afb["frequency_of_depreciation"]) / 12 if afb else 0

        accumulated = max_depreciation_map.get(a.name, 0)
        nrv = (a.total_asset_cost or 0) - accumulated

        data.append({
            "asset_id": a.name,
            "asset_name": a.asset_name,
            "category": a.asset_category,
            "location": a.location,
            "department": a.department,
            "custodian": a.custodian,
            "cost": a.total_asset_cost,
            "nrv": nrv,
            "status": a.status
        })

    return data
