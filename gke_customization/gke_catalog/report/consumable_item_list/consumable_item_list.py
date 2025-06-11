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
        {"fieldname": "dept", "label": _("Used by Department"), "fieldtype": "Data", "width": 170},
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
            COUNT(tt.name) AS tax_template_count,
            Case WHEN mr.custom_transfer_type = 'Transfer To Department' THEN 'Yes' ELSE 'No' END AS mr_by_dept,
            CASE WHEN mr.transfer_status = 'Completed' THEN se.to_department ELSE '-' END AS dept
        FROM `tabItem` i
        LEFT JOIN `tabItem Tax` tt ON i.name = tt.parent
        LEFT JOIN `tabItem Group` ig ON i.item_group = ig.name
        LEFT JOIN `tabMaterial Request Item` mri on i.name = mri.item_code
        LEFT JOIN `tabMaterial Request` mr on mr.name = mri.parent
        LEFT JOIN `tabStock Entry Detail` se on se.material_request = mr.name
        WHERE ig.parent_item_group = 'Consumable'
        {f"AND " + conditions if conditions else ""}
        GROUP BY i.name
        ORDER BY i.item_group, i.name,  i.item_code
    """
    rows = frappe.db.sql(query, as_dict=1)

    # Group image URLs under each item
    grouped = {}
    for row in rows:
        name = row["name"]
        image_url = row["image"]

        if not name:
            continue

        if name not in grouped:
            grouped[name] = row.copy()
            grouped[name]["images"] = []

        if image_url and image_url not in grouped[name]["images"]:
            grouped[name]["images"].append(image_url)

    data = []
    # For each grouped item, build thumbnails and modal HTML
    for name, row in grouped.items():
        urls = row["images"]
        modal_id = f"modal-{name}"

# Creating HTML thumbnails for all images
        thumbnails = f"""
                <div style="display: flex; justify-content: center; align-items: center; padding: 0; margin: 0; height: 100%;">
                    {''.join([
                        f'<img src="{url}" '
                        f'style="height: 50px; width: auto; padding: 0; margin: 0; border-radius: 6px; cursor: pointer; '
                        f'object-fit: contain; display: block;" '
                        f'onclick="document.getElementById(\'{modal_id}\').style.display=\'flex\'" />'
                        for url in urls
                    ])}
                </div>
"""
# Making HTML for full-size images inside modal
        full_images = "".join([
            f"""
            <img src="{url}" style="max-width: 100%; max-height: 90vh; border-radius: 12px;" />
            """ for url in urls
        ])
# Modal HTML that shows full images on click
        modal_html = f"""
        <div id="{modal_id}" class="custom-image-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background-color: rgba(0,0,0,0.9); z-index:1000; overflow-y: auto;"
            onclick="this.style.display='none'">

            <div style="display: flex; flex-direction: column; align-items: center; gap: 20px;
                max-width: 90%; margin: auto; padding: 40px 10px;"
                onclick="event.stopPropagation()">
                {full_images}
            </div>
        </div>
        """
# Combine thumbnails and modal HTML
        image_html = f"""
        <div style="white-space: nowrap; overflow-x: auto; max-width: 600px; padding: 5px;">
            {thumbnails}
        </div>
        {modal_html}
        """

        # row["image"] = image_html
        row["image"] = image_html if urls else "-"
        data.append(row)

    return data

def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append(f"""mr.company = "{filters['company']}" """)   

    if filters.get("branch"):
        branches = "', '".join(filters["branch"])
        conditions.append(f"mri.branch IN ('{branches}')")       
        # conditions.append(f"""mri.branch = "{filters['branch']}" """) 

    # if filters.get("item_group"):
    #     conditions.append(f"""i.item_group = "{filters['item_group']}" """)    

    if filters.get("item_group"):
        item_groups = "', '".join(filters["item_group"])
        conditions.append(f"i.item_group IN ('{item_groups}')")          
  
    return " AND ".join(conditions) if conditions else ""
