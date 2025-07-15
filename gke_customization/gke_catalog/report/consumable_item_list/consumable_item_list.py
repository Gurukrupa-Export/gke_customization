import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Data", "width": 180},
        {"fieldname": "image", "label": _("Image"), "fieldtype": "HTML", "width": 100},
        {"fieldname": "name", "label": _("Item Name"), "fieldtype": "Link", "options":"Item", "width": 120},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Data", "width": 150},
        {"fieldname": "gst_hsn_code", "label": _("HSN/SAC"), "fieldtype": "Data", "width": 100},
        {"fieldname": "stock_uom", "label": _("Default Unit of Measure"), "fieldtype": "Data", "width": 190},
        {"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
        {"fieldname": "tax_template_count", "label": _("Item Tax Template (Taxes)"), "fieldtype": "Int", "width": 200},
        {"fieldname": "mr_by_dept", "label": _("MR By Department"), "fieldtype": "Data", "width": 170},
        {"fieldname": "dept", "label": _("Used by Department"), "fieldtype": "Data", "width": 260},
        {"fieldname": "enabled", "label": _("Enabled"), "fieldtype": "Check", "width": 100},
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    query = f"""
        SELECT
            i.name AS name,
            i.item_code AS item_code,
            i.item_group AS item_group,
            i.image AS image,
            i.gst_hsn_code AS gst_hsn_code,
            i.stock_uom AS stock_uom,
            i.description AS description,
            CASE WHEN i.disabled = 0 THEN 1 ELSE 0 END AS enabled,
            GROUP_CONCAT(DISTINCT CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(tt.item_tax_template, ' ', 2), ' ', -1) AS DECIMAL(10))) AS tax_template_count,
            CASE WHEN i.custom_mr_by_department IN ('Yes', 1) THEN 'Yes' ELSE 'No' END AS mr_by_dept,
            GROUP_CONCAT(DISTINCT cm.department) AS dept
        FROM `tabItem` i
        LEFT JOIN `tabItem Tax` tt ON i.name = tt.parent
        LEFT JOIN `tabItem Group` ig ON i.item_group = ig.name
        LEFT JOIN `tabConsumable Item Details` cim on i.name = cim.item_code
        LEFT JOIN `tabConsumable Master` cm on cm.name = cim.parent
        WHERE ig.parent_item_group = 'Consumable' and has_variants != 1
        {f"AND " + conditions if conditions else ""}
        GROUP BY i.item_code, i.custom_mr_by_department
        ORDER BY i.item_group, i.name,  i.item_code
    """
    rows = frappe.db.sql(query, as_dict=1)

# CASE WHEN mr.transfer_status = 'Completed' THEN se.to_department ELSE '-' END AS dept
# GROUP_CONCAT(DISTINCT CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(tt.item_tax_template, ' ', 2), ' ', -1) AS DECIMAL(10)))
    
    data = []

    for row in rows:
      image_url = row.get("image")
      modal_id = "modal-{}".format(row["name"])

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

        row["image"] = thumbnail_html + modal_html

      else:
        row["image"] = "-"

      data.append(row)


    return data

def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append(f"""cm.company = "{filters['company']}" """)   

    if filters.get("branch"):
        branches = "', '".join(filters["branch"])
        conditions.append(f"cm.branch IN ('{branches}')")       
        # conditions.append(f"""mri.branch = "{filters['branch']}" """) 

    # if filters.get("item_group"):
    #     conditions.append(f"""i.item_group = "{filters['item_group']}" """)    

    if filters.get("item_group"):
        item_groups = "', '".join(filters["item_group"])
        conditions.append(f"i.item_group IN ('{item_groups}')")          
  
    return " AND ".join(conditions) if conditions else ""
