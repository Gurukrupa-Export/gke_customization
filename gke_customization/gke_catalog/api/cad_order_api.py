import json
import frappe
from frappe.utils import getdate

@frappe.whitelist()
def get_update_item_orders(from_date, to_date, order_id=None):
    """ 
        Fetch orders where workflow_state changed to 'Update Item'
        within given date range (based on Version creation date)
    """

    from_date = getdate(from_date)
    to_date = getdate(to_date)
    target_state = "Update Item"

    result = []
    processed_orders = set()

    conditions = """
        ref_doctype = 'Order'
        AND DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
    """

    params = {
        "from_date": from_date,
        "to_date": to_date
    }

    if order_id:
        conditions += " AND docname = %(order_id)s"
        params["order_id"] = order_id

    versions = frappe.db.sql(f"""
        SELECT
            name, docname, data, creation
        FROM `tabVersion`
        WHERE {conditions}
        ORDER BY creation ASC
    """, params, as_dict=True)

    if not versions:
        return []

    order_names = list({v.docname for v in versions if v.docname})

    orders = frappe.db.get_all(
        "Order",
        filters={
            "name": ["in", order_names],
            "workflow_type": "CAD",
            "bom_or_cad": "CAD",
            "company": "Gurukrupa Export Private Limited"
        },
        fields=[
            "name", "modified", "bom_or_cad", "workflow_type", "company",
            "design_type","category","subcategory","setting_type","order_type"
        ]
    )

    order_map = {o.name: o for o in orders}
 
    # 5️⃣ Cross-check workflow change
    for v in versions:
        if not v.data or v.docname not in order_map:
            continue
        
        if v.docname in processed_orders:
            continue

        try:
            data = json.loads(v.data)
        except Exception:
            continue

        for change in data.get("changed", []):
            if len(change) < 3:
                continue

            field, old, new = change

            if field == "workflow_state" and new == target_state:
                order = order_map[v.docname]

                result.append({
                    "order_id": order.name,
                    "order_modified_date": order.modified.date(),
                    "bom_or_cad": order.bom_or_cad,
                    "workflow_type": order.workflow_type,
                    "company": order.company,
                    "design_type": order.design_type,
                    "category": order.category,
                    "subcategory": order.subcategory,
                    "setting_type": order.setting_type,
                    "order_type": order.order_type,
                    "version_id": v.name,
                    "version_creation_date": v.creation
                })

                processed_orders.add(v.docname)
                break

    return result



@frappe.whitelist()
def get_orders_details(order_id):
    order = frappe.db.get_all("Order", 
        filters={ "name": order_id },
        fields=[
            "name","item","rating","category","setting_type","cad_image",
            "product_size","diamond_part_length",
            "metal_weight","diamond_weight","gemstone_weight","other_weight",
            "casting_pcs","gross_weight","diamond_ratio","metal_to_diamond_ratio_excl_of_finding",
        ]
    )
    order_data = order[0]
    
    diamond_detail = frappe.db.get_all("Order BOM Diamond Detail", filters={ "parent": order_id },
        fields=[
            "stone_shape","sieve_size_color","diamond_sieve_size","size_in_mm",
            "pcs","quantity"
        ]
    )

    gemstone_detail = frappe.db.get_all("Order BOM Gemstone Detail", filters={ "parent": order_id },
        fields=[
            "gemstone_type","stone_shape","cut_or_cab","pcs","gemstone_size","quantity"
        ]
    )

    finding_detail = frappe.db.get_all("Order BOM Finding Detail", filters={ "parent": order_id },
        fields=[
            "metal_type","metal_touch","metal_purity","metal_colour","finding_category",
            "finding_type", "finding_size","qty","quantity"
        ]
    )

    other_detail = frappe.db.get_all("Order BOM Other Detail", filters={ "parent": order_id },
        fields=[
            "item_code","qty","uom","quantity" 
        ]
    )

    order_data["diamond_detail"] = diamond_detail
    order_data["gemstone_detail"] = gemstone_detail
    order_data["finding_detail"] = finding_detail
    order_data["other_detail"] = other_detail

    return order
