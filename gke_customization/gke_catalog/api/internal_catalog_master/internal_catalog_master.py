import frappe
from frappe import _
from frappe.utils import flt
import pyotp
import hmac
import hashlib
import base64
from frappe.auth import LoginManager
from datetime import datetime, timedelta, timezone
import pytz
from frappe.integrations.oauth2 import get_oauth_server
import requests
import json


@frappe.whitelist(allow_guest=True)
def get_wishlist_item_by_user(items, customers):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates.
    """
    
    # Parse JSON if string
    if isinstance(items, str):
        items = json.loads(items)

    if isinstance(customers, str):
        customers = json.loads(customers)

    if not items or not customers:
        frappe.throw("Both 'items' and 'customers' are required.")

    # if user_type == "User":
    #     frappe.throw("User is not allowed to add the item to wishlist.")

    # items = [ { item1: trending1, item2: trending2 } ]
    items_dict = items[0]

    results = []

    for customer in customers:

        customer_found = frappe.db.get_all(
            "Internal Catalog Master",
            filters={"user": customer},
            fields=["name"]
        )

        # frappe.throw(f"{customer_id}")

        # ---------------------------------------------------------
        # CUSTOMER EXISTS
        # ---------------------------------------------------------
        if customer_found:
            
            catalog_doc = frappe.get_doc("Internal Catalog Master", customer_found[0].name)
            # catalog_doc.flags.ignore_permissions = True

            # Build lookup: existing item_code → trending
            existing_items = {
                row.item_code: row.wishlist
                for row in catalog_doc.user_item_details
            }

            added = []
            updated = []

            for item_code, trending_value in items_dict.items():

                # ----------------- NEW ITEM -----------------
                if item_code not in existing_items:
                    catalog_doc.append("user_item_details", {
                        "item_code": item_code,
                        "item_name": item_code,
                        "wishlist": trending_value,
                    })
                    added.append(item_code)

                # ----------------- UPDATE TRENDING -----------------
                else:
                    old_val = existing_items[item_code]
                    if old_val != trending_value:
                        for row in catalog_doc.user_item_details:
                            if row.item_code == item_code:
                                row.wishlist = trending_value
                                updated.append(item_code)
                                break

            catalog_doc.save(ignore_permissions=True)

            frappe.db.commit()

            results.append({
                "user": customer,
                "added_items": added,
                "updated_items": updated,
                "message": f"Added {len(added)}, Updated {len(updated)} for customer {customer}"
            })

            
        # ---------------------------------------------------------
        # NEW CUSTOMER → CREATE CATALOG
        # ---------------------------------------------------------
        else:
            catalog_doc = frappe.new_doc("Internal Catalog Master")
            catalog_doc.user = customer

            for item_code, trending_value in items_dict.items():
                catalog_doc.append("user_item_details", {
                    "item_code": item_code,
                    "item_name": item_code,
                    "wishlist": trending_value
                })

            catalog_doc.insert(ignore_permissions=True)

            frappe.db.commit()

            results.append({
                "user": customer,
                "added_items": list(items_dict.keys()),
                "updated_items": [],
                "message": f"Created new Cataloge Master for {customer}"
            })

           
    return {
        "status": "success",
        "results": results
    }



@frappe.whitelist(allow_guest=True)
def add_item_in_folder_user(status=None, name=None, item=None, customer=None):

    if not customer:
        frappe.throw("Customer is required")

    # Only required for ADD and REMOVE
    if status in ["ADD", "REMOVE"] and not item:
        frappe.throw("Item list is required")

    # Convert JSON string to list safely
    if isinstance(item, str):
        item = frappe.parse_json(item)

    item = item or []
    items = tuple(item)

    sql_query = """
        SELECT 
            citm.folder, 
            citm.item_code, 
            citm.wishlist,
            ctm.name as parent_name
        FROM `tabInternal Catalog Master` AS ctm
        LEFT JOIN `tabUser Item Details` AS citm
            ON citm.parent = ctm.name
        WHERE ctm.user = %(user)s
    """

    # Add condition only for ADD and REMOVE
    if status in ["ADD", "REMOVE"]:
        sql_query += " AND citm.item_code IN %(items)s"


    values = {
        "user": customer,
        "items": items if items else None
    }

    result = frappe.db.sql(sql_query, values=values, as_dict=True)

    if not result:
        frappe.throw("No matching records found")

    parent_name = result[0]["parent_name"]

    catalog_doc = frappe.get_doc(
        "Internal Catalog Master",
        parent_name,
        ignore_permissions=True
    )

    # ---------------- ADD ----------------
    if status == "ADD":
        for row in catalog_doc.user_item_details:
            if row.wishlist == 1 and row.item_code in item:

                if not row.folder:
                    row.folder = name
                else:
                    folders = row.folder.split(",")
                    if name not in folders:
                        folders.append(name)
                        row.folder = ",".join(folders)

    # ---------------- REMOVE ----------------
    if status == "REMOVE":
        for row in catalog_doc.user_item_details:
            if row.wishlist == 1 and row.item_code in item and row.folder:

                folders = row.folder.split(",")

                if name in folders:
                    folders.remove(name)

                    if folders:
                        row.folder = ",".join(folders)
                    else:
                        row.folder = None

    # ---------------- DELETE ----------------
    if status == "DELETE" and name:
        for row in catalog_doc.user_item_details:

            if row.wishlist == 1 and row.folder:

                folders = row.folder.split(",")

                if name in folders:
                    folders.remove(name)

                    if folders:
                        row.folder = ",".join(folders)
                    else:
                        row.folder = None

    catalog_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"message": "Updated successfully"}


@frappe.whitelist()
def get_attribute_data_for_user():
    Sizer_Type = frappe.get_doc("Item Attribute", "Sizer Type")
    
    sizer_type =  [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Sizer_Type.item_attribute_values
    ]

    Lock_Type = frappe.get_doc("Item Attribute", "Lock Type")

    lock_type =  [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Lock_Type.item_attribute_values
    ]

    Feature = frappe.get_doc("Item Attribute", "Feature")

    feature = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Feature.item_attribute_values
    ]

    Enamal = frappe.get_doc("Item Attribute", "Enamal")

    enamal = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Enamal.item_attribute_values
    ]

    Rhodium = frappe.get_doc("Item Attribute", "Rhodium")

    rhodium = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Rhodium.item_attribute_values
    ]

    Animal_Birds = frappe.get_doc("Item Attribute", "Animal/Birds")

    animal_birds = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Animal_Birds.item_attribute_values
    ]

    Alphabet_Number = frappe.get_doc("Item Attribute", "Alphabet/Number")

    alphabet_number = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Alphabet_Number.item_attribute_values
    ]

    Collection = frappe.get_doc("Item Attribute", "Collection")

    collection = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Collection.item_attribute_values
    ]


    Design_Style = frappe.get_doc("Item Attribute", "Design Style")

    design_style = [
        {
            "value": row.attribute_value,
            "abbr": row.abbr
        }
        for row in Design_Style.item_attribute_values
    ]

    return {
        "sizer_type": sizer_type,
        "rhodium":rhodium,
        "enamal": enamal,
        "feature": feature,
        "lock_type" : lock_type,
        "animal_birds": animal_birds,
        "alphabet_number": alphabet_number,
        "collection": collection,
        "design_style": design_style
    }


@frappe.whitelist(allow_guest=True)
def user_wise_item(user, company=None):

    conditions = []
    filters = {}

    if company:
        conditions.append("idf.company = %(company)s")
        filters["company"] = company
    else:
        conditions.append("idf.company = 'Gurukrupa Export Private Limited'")

    if user:
        conditions.append("icm.user = %(user)s")
        filters["user"] = user

    where_clause = " AND ".join(conditions)

    db_data = frappe.db.sql(f"""
        SELECT
            item.name,
            bom.name AS bom_name,
            idf.company,
            uid.folder AS internal_catalog_folder,
            uid.wishlist AS internal_catalog_wishlist,
            item.creation,
            item.item_code,
            item.item_category,
            item.stylebio,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,
            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,
            item.item_subcategory,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,
            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,
            bom.metal_touch AS bom_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
            bom.navratna,
            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,
            bom.sizer_type,
            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,
            item.variant_of,
            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,

            GROUP_CONCAT(DISTINCT item.name) AS variant_name,
            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN `tabUser Item Details` AS uid
            ON uid.item_code = item.item_code

        LEFT JOIN `tabInternal Catalog Master` AS icm
            ON icm.name = uid.parent

        LEFT JOIN `tabBOM` AS bom
            ON item.item_code = bom.item

        LEFT JOIN `tabDesign Attributes` AS td
            ON item.item_code = td.parent

        LEFT JOIN `tabBOM Metal Detail` AS mt
            ON bom.name = mt.parent

        LEFT JOIN `tabBOM Gemstone Detail` AS gd
            ON bom.name = gd.parent

        LEFT JOIN `tabBOM Diamond Detail` AS dd
            ON bom.name = dd.parent

        LEFT JOIN `tabBOM Finding Detail` AS fd
            ON bom.name = fd.parent

        LEFT JOIN `tabBOM Other Detail` AS od
            ON bom.name = od.parent

        LEFT JOIN `tabItem Default` AS idf
            ON item.item_name = idf.parent

        WHERE {where_clause}

        GROUP BY
            item.item_code, item.variant_of

        ORDER BY
            item.name DESC
    """, filters, as_dict=True)

    # Folder grouping logic
    int_c_f = {}

    for row in db_data:
        if row.internal_catalog_folder:
            folders = row.internal_catalog_folder.split(",")
            for fd in folders:
                fd = fd.strip()
                if fd not in int_c_f:
                    int_c_f[fd] = []
                int_c_f[fd].append(row)

    return {
        "db_data": db_data,
        "internal_catalog_folder": int_c_f
    }   