from frappe.utils import flt
import frappe
from frappe import _
import json


def execute(filters=None):
    columns, data = [], []
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    return [
        {
            "label": _("Creation Date & Time"),
            "fieldname": "creation_datetime",
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "label": _("Metal Conversion ID"),
            "fieldname": "metal_conversion_id",
            "fieldtype": "Link",
            "options": "Metal Conversions",
            "width": 160
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "width": 120
        },
        {
            "label": _("Manufacturer"),
            "fieldname": "manufacturer",
            "fieldtype": "Link",
            "options": "Manufacturer",
            "width": 120
        },
        {
            "label": _("User"),
            "fieldname": "user_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 120
        },
        {
            "label": _("Source Item"),
            "fieldname": "source_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Source Item Qty"),
            "fieldname": "source_qty",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        },
        {
            "label": _("Source Alloy"),
            "fieldname": "source_alloy",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Source Alloy Qty"),
            "fieldname": "source_alloy_qty",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3
        },
        {
            "label": _("Target Item"),
            "fieldname": "target_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Target Item Qty"),
            "fieldname": "target_qty",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3
        },
        {
            "label": _("Is Customer Metal"),
            "fieldname": "is_customer_metal",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Stock Entry ID"),
            "fieldname": "stock_entry",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 150
        }
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    
    query = f"""
        SELECT 
            mc.creation as creation_datetime,
            mc.name as metal_conversion_id,
            mc.company,
            mc.branch,
            mc.manufacturer,
            COALESCE(u.full_name, u.first_name, mc.owner) as user_name,
            mc.department,
            mc.source_item,
            mc.source_qty,
            mc.source_alloy,
            mc.source_alloy_qty,
            mc.target_item,
            mc.target_qty,
            CASE 
                WHEN mc.is_customer_metal = 1 THEN 'Yes'
                ELSE 'No'
            END as is_customer_metal,
            se.name as stock_entry
        FROM 
            `tabMetal Conversions` mc
        LEFT JOIN 
            `tabUser` u ON mc.owner = u.name
        LEFT JOIN 
            `tabStock Entry` se ON se.custom_metal_conversion_reference = mc.name 
                AND se.purpose = 'Repack'
        WHERE 
            mc.docstatus = 1
            {conditions}
        ORDER BY 
            mc.creation DESC
    """
    
    data = frappe.db.sql(query, filters, as_dict=1)
    return data


def get_conditions(filters):
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND mc.company = %(company)s"
    
    if filters.get("branch"):
        conditions += " AND mc.branch = %(branch)s"
    
    if filters.get("manufacturer"):
        conditions += " AND mc.manufacturer = %(manufacturer)s"
    
    if filters.get("department"):
        conditions += " AND mc.department = %(department)s"
    
    if filters.get("is_customer_metal"):
        if filters.get("is_customer_metal") == "Yes":
            conditions += " AND mc.is_customer_metal = 1"
        elif filters.get("is_customer_metal") == "No":
            conditions += " AND (mc.is_customer_metal = 0 OR mc.is_customer_metal IS NULL)"
    
    if filters.get("from_date"):
        conditions += " AND DATE(mc.creation) >= %(from_date)s"
    
    if filters.get("to_date"):
        conditions += " AND DATE(mc.creation) <= %(to_date)s"
    
    return conditions
