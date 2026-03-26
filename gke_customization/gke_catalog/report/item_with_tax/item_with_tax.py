# Copyright (c) 2026, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "fieldname": "item_image",
            "label": _("Image"),
            "fieldtype": "HTML",
            "width": 80
        },
        {
            "fieldname": "item_code",
            "label": _("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "item_group",
            "label": _("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 150
        },
        {
            "fieldname": "batch_number_series",
            "label": _("Batch Number Series"),
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "item_taxes",
            "label": _("Item Taxes"),
            "fieldtype": "Data",
            "width": 250
        },
        {
            "fieldname": "valid_from",
            "label": _("Valid From"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "fieldname": "default_warehouse",
            "label": _("Default Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180
        },
        {
            "fieldname": "stock_uom",
            "label": _("UOM"),
            "fieldtype": "Link",
            "options": "UOM",
            "width": 80
        }
    ]


def get_allowed_item_groups():
    """Return list of allowed item groups"""
    return [
        "Consumable", "Chemicals", "Tools & Accessories", "Medical Supplies", 
        "Stationary", "Electric Accessories", "Spare Accessories", "Wax", 
        "Office Supplies", "Machinery", "Services", "Subcontracting", 
        "IT Software Services", "Expenses", "Administrative Expense", 
        "Business Promotion Expense", "Employee Benefits Expense", "Finance Expense", 
        "Interest and Penalty Expense", "Repairs and Maintance Expense", 
        "Selling and Distribution Expense", "Utility Expense", 
        "Product Certification Expense", "Dine & Stay Expense", "Assets", 
        "Communication Devices", "Landline Phones", "Mobile", "Computing Devices", 
        "Access Control", "Ajax", "Board", "Computers", "CPU", "Keyboards", 
        "Laptop", "Mice", "Monitors", "Printers", "TV", "Furniture", "Chairs", 
        "Sofa", "Lighting", "Lamps", "Networking Devices", "Fire Safety", 
        "Network Equipment", "Server", "WiFi Routers", "Surveillance", 
        "CCTV Cameras", "CCTV Recorder", "Weighing Scale", "Vehicle", 
        "Four-Wheeler", "Automated Screening Machine", "Electronics", "Machineries"
    ]


def get_data(filters):
    """Fetch and process report data"""
    
    # Build WHERE conditions
    conditions, filter_values = get_conditions(filters)
    
    # Main query
    query = f"""
        SELECT 
            i.name AS item_code,
            i.image AS item_image,
            COALESCE(NULLIF(iva.attribute_value, 'None'), i.item_name) AS item_name,
            i.item_group,
            CASE 
                WHEN i.batch_number_series IS NOT NULL 
                THEN i.batch_number_series 
                ELSE 'NULL' 
            END AS batch_number_series,
            IFNULL(GROUP_CONCAT(DISTINCT it.item_tax_template SEPARATOR ', '), 'None') AS item_taxes,
            IFNULL(MIN(it.valid_from), 'None') AS valid_from,
            idd.company,
            idd.default_warehouse,
            i.stock_uom


        FROM `tabItem` i
        
        LEFT JOIN (
            SELECT parent, attribute, attribute_value
            FROM `tabItem Variant Attribute`
            WHERE attribute LIKE '%%Type%%'
            AND attribute != 'Gemstone Type1'
            GROUP BY parent
        ) iva ON iva.parent = i.name
        
        LEFT JOIN `tabItem Default` idd 
            ON idd.parent = i.name
        
        LEFT JOIN `tabItem Tax` it 
            ON it.parent = i.name
        
        WHERE i.disabled = 0
        {conditions}
        
        GROUP BY 
            i.name,
            i.image,
            iva.attribute_value,
            i.item_name,
            i.item_group,
            idd.company,
            idd.default_warehouse,
            i.stock_uom
        
        ORDER BY 
            i.item_group,
            i.name
    """
    
    rows = frappe.db.sql(query, filter_values, as_dict=1)
    
    # Process data and add image modals
    data = []
    for row in rows:
        image_url = row.get("item_image")
        modal_id = "modal-{}".format(row["item_code"].replace(" ", "-"))
        
        if image_url:
            thumbnail_html = (
                '<img src="{0}" style="height:50px; border-radius:6px; cursor:pointer; object-fit:contain;" '
                'onclick="document.getElementById(\'{1}\').style.display=\'flex\'">'.format(image_url, modal_id)
            )
            modal_html = (
                '<div id="{0}" class="custom-image-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; '
                'background-color:rgba(0,0,0,0.8); align-items:center; justify-content:center; z-index:1000;" '
                'onclick="this.style.display=\'none\'">'
                '<img src="{1}" style="max-width:90%; max-height:90%; border-radius:8px;" '
                'onclick="event.stopPropagation()">'
                '</div>'.format(modal_id, image_url)
            )
            row["item_image"] = thumbnail_html + modal_html
        else:
            row["item_image"] = "-"
        
        data.append(row)
    
    return data


def get_conditions(filters):
    """Build WHERE clause based on filters"""
    conditions = []
    filter_values = {}
    
    # Get allowed item groups
    item_groups = get_allowed_item_groups()
    
    # Override with filter if provided (multiselect support)
    if filters.get("item_group"):
        selected_groups = filters.get("item_group")
        
        # Handle both list and comma-separated string
        if isinstance(selected_groups, str):
            selected_groups = [g.strip() for g in selected_groups.split(",") if g.strip()]
        
        # Filter only valid groups
        valid_groups = [g for g in selected_groups if g in item_groups]
        
        if valid_groups:
            item_groups = valid_groups
        else:
            # No valid groups selected, return no results
            item_groups = []
    
    if item_groups:
        groups_str = "', '".join(item_groups)
        conditions.append(f"AND i.item_group IN ('{groups_str}')")
    else:
        # No valid item groups, return no results
        conditions.append("AND 1=0")
    
    # Company filter
    if filters.get("company"):
        conditions.append("AND idd.company = %(company)s")
        filter_values["company"] = filters.get("company")
    
    # Item Code filter
    if filters.get("item_code"):
        conditions.append("AND i.name = %(item_code)s")
        filter_values["item_code"] = filters.get("item_code")
    
    return " ".join(conditions), filter_values
