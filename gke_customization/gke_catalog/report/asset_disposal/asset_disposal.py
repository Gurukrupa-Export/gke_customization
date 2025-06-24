import frappe
from frappe import _
from collections import defaultdict
from frappe.sessions import datetime
from frappe.utils import today

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Disposal Date"), "fieldname": "disposal_date", "fieldtype": "Date", "width": 150},
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 150},
        {"label": _("Asset Description"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
        {"label": _("Method"), "fieldname": "method", "fieldtype": "Data", "width": 100},
        {"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 120},
        {"label": _("Original Cost (₹)"), "fieldname": "cost", "fieldtype": "Currency", "width": 140},
        {"label": _("Accumulated Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 160},
        {"label": _("Sale Value"), "fieldname": "sale_value", "fieldtype": "Currency", "width": 120},
        {"label": _("Gain/Loss"), "fieldname": "gain_loss", "fieldtype": "Currency", "width": 120},
        {"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 140},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 140},
        {"label": _("Custodian"), "fieldname": "custodian", "fieldtype": "Link", "options": "Employee", "width": 140},
    ]

def get_data(filters):
    conds = [["status", "in", ["Sold", "Scrapped"]]]

    if filters.get("company"):
        conds.append(["company", "in", filters["company"]])
    if filters.get("branch"):
        conds.append(["branch", "in", filters["branch"]])
    if filters.get("location"):
        conds.append(["location", "in", filters["location"]])
    if filters.get("asset"):
        conds.append(["name", "in", filters["asset"]])

    assets = frappe.get_all("Asset",
        filters=conds,
        fields=["name", "asset_name", "branch", "department", "custodian", "purchase_date","location", "total_asset_cost", "status", "modified"]
    )

    # ✅ Convert string to date object
    from_date = (
        datetime.strptime(filters["from_date"], "%Y-%m-%d").date()
        if filters.get("from_date") else None
    )
    to_date = (
        datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
        if filters.get("to_date") else None
    )

    if from_date or to_date:
        filtered_assets = []
        for a in assets:
            modified_date = a.modified.date()
            if (not from_date or modified_date >= from_date) and (not to_date or modified_date <= to_date):
                filtered_assets.append(a)
        assets = filtered_assets

    asset_ids = [a.name for a in assets]

    ads_rows = frappe.get_all("Asset Depreciation Schedule",
        filters={"asset": ["in", asset_ids]},
        fields=["name", "asset"]
    )
    ads_to_asset = {row.name: row.asset for row in ads_rows}

    ds_rows = frappe.get_all("Depreciation Schedule",
        filters={"schedule_date": ["<=", today()], "parent": ["in", list(ads_to_asset.keys())]},
        fields=["parent", "accumulated_depreciation_amount"]
    )

    max_depreciation_map = {}
    for row in ds_rows:
        asset = ads_to_asset.get(row.parent)
        if asset:
            current_max = max_depreciation_map.get(asset, 0)
            max_depreciation_map[asset] = max(current_max, row.accumulated_depreciation_amount or 0)

    # Sale Value Map for Sold Assets
    sale_value_map = {}
    if asset_ids:
        invoice_items = frappe.get_all("Sales Invoice Item",
            filters={"asset": ["in", asset_ids]},
            fields=["asset", "base_net_amount"]
        )
        for item in invoice_items:
            if item.asset:
                sale_value_map[item.asset] = item.base_net_amount or 0

    data = []
    for a in assets:
        accumulated = max_depreciation_map.get(a.name, 0)
        nrv = (a.total_asset_cost or 0) - accumulated

        if a.status == "Sold":
            method = "Sale"
            sale_value = sale_value_map.get(a.name, 0)
        else:
            method = "Scrapped"
            sale_value = 0

        gain_loss = sale_value - nrv

        data.append({
            "disposal_date": a.modified.date() if a.modified else None,
            "asset_id": a.name,
            "asset_name": a.asset_name,
            "method": method,
            "purchase_date": a.purchase_date,
            "cost": a.total_asset_cost,
            "accumulated_depreciation": accumulated,
            "sale_value": sale_value,
            "gain_loss": gain_loss,
            "location": a.location,
            "department": a.department,
            "custodian": a.custodian,
        })

    return data
