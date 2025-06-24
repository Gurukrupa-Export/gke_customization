import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Movement Date"), "fieldname": "movement_date", "fieldtype": "Date", "width": 130},
        {"label": _("Asset ID"), "fieldname": "asset_id", "fieldtype": "Link", "options": "Asset", "width": 200},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 170},
        # {"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Asset Category", "width": 150},
        {"label": _("Purpose"), "fieldname": "purpose", "fieldtype": "Data", "width": 130},
        {"label": _("From Location"), "fieldname": "source_location", "fieldtype": "Data", "width": 150},
        {"label": _("From Department"), "fieldname": "from_department", "fieldtype": "Link", "options": "Department", "width": 170},
        {"label": _("To Location"), "fieldname": "target_location", "fieldtype": "Data", "width": 150},
        {"label": _("To Department"), "fieldname": "to_department", "fieldtype": "Link", "options": "Department", "width": 170},
        {"label": _("Approved By"), "fieldname": "modified_by", "fieldtype": "Link", "options": "User", "width": 190},
    ]

def get_data(filters=None):
    data = []

    conds = []
    if filters.get("company"):
        conds.append(["company", "in", filters.get("company")])
    if filters.get("branch"):
        conds.append(["branch", "in", filters.get("branch")])
    if filters.get("from_date"):
        conds.append(["transaction_date", ">=", filters.get("from_date")])
    if filters.get("to_date"):
        conds.append(["transaction_date", "<=", filters.get("to_date")])         
    conds.append(["docstatus", "=", "1"])

    asset_movements = frappe.get_all("Asset Movement",
        filters=conds,
        fields=["name", "purpose", "transaction_date","modified_by"]
    )

    for movement in asset_movements:
        asset_movement_filter = []
        if filters.get("asset"):
            asset_movement_filter.append(["asset", "in", filters.get("asset")])
        asset_movement_filter.append(["parent","=",movement.name])    

        movement_items = frappe.get_all("Asset Movement Item",
            filters=asset_movement_filter,
            fields=["asset", "source_location", "target_location", "from_employee", "to_employee"]
        )

        for item in movement_items:
            asset = frappe.get_doc("Asset", item.asset)
            from_dept = frappe.db.get_value("Employee", item.from_employee, "department") if item.from_employee else None
            to_dept = frappe.db.get_value("Employee", item.to_employee, "department") if item.to_employee else None

            data.append({
                "asset_id": asset.name,
                "asset_name": asset.asset_name,
                "category": asset.asset_category,
                "purpose": movement.purpose,
                "movement_date": movement.transaction_date,
                "source_location": item.source_location,
                "target_location": item.target_location,
                "from_department": from_dept,
                "to_department": to_dept,
                "modified_by":movement.modified_by,
            })

    return data
