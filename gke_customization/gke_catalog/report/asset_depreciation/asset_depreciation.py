import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters=None):
    columns = [
        {"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 100},
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 210},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
        {"label": _("Category"), "fieldname": "asset_category", "fieldtype": "Data", "width": 160},
        {"label": _("Depreciation Method"), "fieldname": "depreciation_method", "fieldtype": "Data", "width": 160},
        {"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 140},
        {"label": _("Depreciation Rate (%)"), "fieldname": "depreciation_rate", "fieldtype": "Percent", "width": 160},
        {"label": _("Accumulated Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 180},
        {"label": _("Net Book Value"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 180},
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
    SELECT 
        a.name AS asset_id,
        a.asset_name AS asset_name,
        a.company AS company,
        a.branch AS branch,
        a.location AS location,
        a.department AS department,
        DATE_FORMAT(ds.schedule_date, "%b-%y") AS period,
        a.asset_category AS asset_category,
        afb.depreciation_method AS depreciation_method,
        a.branch AS branch,
        afb.rate_of_depreciation AS depreciation_rate,
        SUM(ds.depreciation_amount) AS accumulated_depreciation,
        (a.total_asset_cost - ds.accumulated_depreciation_amount) AS net_book_value
    FROM `tabAsset Depreciation Schedule` ads
    LEFT JOIN `tabDepreciation Schedule` ds
    ON ads.name = ds.parent
    LEFT JOIN tabAsset a
    ON ads.asset = a.name
    LEFT JOIN  `tabAsset Finance Book` afb
    ON a.name = afb.parent
    where ads.docstatus = 1
    {conditions}
    GROUP BY a.name,a.asset_name, Month(ds.schedule_date), Year(ds.schedule_date)
    """
    data = frappe.db.sql(query, as_dict=1)

    return data

def get_conditions(filters):
    filter_list = []

    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        filter_list.append(f"""a.company IN ({companies})""")
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        filter_list.append(f"""a.branch IN ({branches})""")
    if filters.get("location"):
        locations = ', '.join([f'"{location}"' for location in filters.get("location")])
        filter_list.append(f"""a.location IN ({locations})""")        
    if filters.get("department"):
        departments = ', '.join([f'"{department}"' for department in filters.get("department")])
        filter_list.append(f"""a.department IN ({departments})""")
    if filters.get("asset"):
        assets = ', '.join([f'"{asset}"' for asset in filters.get("asset")])
        filter_list.append(f"""a.name IN ({assets})""")

    
    conditions = ""
    if filter_list:
        conditions = " AND "+" AND ".join(filter_list)

    return conditions
