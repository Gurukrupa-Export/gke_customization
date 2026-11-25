from warnings import filters
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.password import encrypt
from gke_customization.gke_catalog.api.item_catalog import get_collection, get_rhodium
from pydantic import Secret
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
from gke_customization.gke_catalog.api.notifications import notify_user
from gke_customization.gke_catalog.api.wishlist_download import get_method
from gke_customization.gke_catalog.api.encryption_response import encrypt_response
from gke_customization.gke_catalog.api.encryption_response import SecureJSON
from cryptography.fernet import Fernet


@frappe.whitelist()
def get_customer_wishlist_items(customer=None, user_type=None, user=None):

    if user_type == "customer":
        customer = frappe.form_dict.get("customer") or customer
    elif user_type == "user":
        user = frappe.form_dict.get("user") or user

    where_clause = """
    idf.company = 'Gurukrupa Export Private Limited'
    AND bom.bom_type = 'Finish Goods'
    AND bom.name IS NOT NULL
    AND bom.is_active = 1
    AND bom.is_default = 1
    AND tci.wishlist = 1
    """

    if customer:
        where_clause += f" AND tcm.customer = '{customer}' "
    if user:
        where_clause += f" AND tcm.user = '{user}' "

    # frappe.throw(where_clause)

    db_data = frappe.db.sql(
        f"""SELECT
                MIN(item.name) AS name,
                MIN(bom.name) AS bom,
                idf.company,
                tci.trending,
                tci.name as catalog_item_details_name,
                tci.folder,
                tci.wishlist,
                tcm.allow_excel_permission,
                tci.as_per_design,
                tci.job_work,
                tci.as_per_customized,
                tci.customized_data,
                tci.customer_gold,
                tci.customer_diamond,
                tci.customer_stone,
                uid.folder as internal_catalog_folder,
                uid.wishlist as internal_catalog_wishlist,
                item.creation,
                MIN(item.name) AS item_code,
                item.item_category,
                item.stylebio,
                MIN(item.image) AS image,
                item.custom_catalogue_image,
                item.sketch_image,
                item.front_view as cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,

                CASE 
                    WHEN vc.variant_count > 1 THEN 1 
                    ELSE 0 
                END AS rn,

                CASE 
                   WHEN set_check.is_set_item = 1 THEN 1 
                   ELSE 0 
                END AS is_set_item,

                CASE 
                    WHEN similar_check.is_similar_item = 1 THEN 1 
                    ELSE 0 
                END AS is_similar_item,

                item.item_subcategory,
                bom.tag_no,
                bom.diamond_quality,
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_touch as bom_touch,
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
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
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
            FROM
                `tabItem` AS item
            LEFT JOIN
                `tabCataloge Item Details` AS tci ON tci.item_code = item.name
            LEFT JOIN (
                SELECT
                    COALESCE(i.variant_of, i.item_code) AS group_key,
                    tci2.parent AS catalog_parent,
                    COUNT(DISTINCT i.item_code) AS variant_count,
                    MAX(tci2.as_per_design) AS as_per_design,
                    MAX(tci2.job_work) AS job_work,
                    MAX(tci2.as_per_customized) AS as_per_customized
                FROM `tabItem` AS i
                INNER JOIN `tabBOM` AS b
                    ON i.item_code = b.item
                    AND b.bom_type = 'Finish Goods'
                    AND b.is_active = 1
                    # AND b.is_default = 1
                LEFT JOIN `tabCataloge Item Details` AS tci2 ON tci2.item_code = i.item_code
                LEFT JOIN `tabCataloge Master` AS tcm2 ON tcm2.name = tci2.parent
                GROUP BY COALESCE(i.variant_of, i.item_code), tci2.parent
            ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
                 AND vc.catalog_parent = tci.parent
            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
                FROM `tabSet Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci ON tci.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent
            ) AS set_check ON set_check.item_code = item.item_code
            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    tci.parent AS catalog_parent,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
                FROM `tabSimilar Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci ON tci.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent, tci.parent
            ) AS similar_check
                ON similar_check.item_code = item.item_code
                AND similar_check.catalog_parent = tci.parent
            LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
            LEFT JOIN `tabUser Item Details` AS uid ON uid.item_code = item.name
            LEFT JOIN `tabInternal Catalog Master` AS icm ON icm.name = uid.parent
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
            LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
            LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
            LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
            LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
            LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
            LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
            WHERE
                {where_clause}
            GROUP BY
                COALESCE(item.variant_of, item.item_code), tci.parent, tci.name  
            ORDER BY
                MIN(item.name) DESC
        """,
        as_dict=True
    )

    d = {}
    for row in db_data:
        if row.folder:
            for fd in row.folder.split(","):
                if fd not in d:
                    d[fd] = []
                d[fd].append(row)



    secure = SecureJSON()
    
    # enc_data = secure.encrypt(
    #         {
    #         "db_data": db_data,
    #         "total": len(db_data),
    #         "folder": d
    #     }
    # ) 
    
    # return enc_data

    return {
        "db_data": db_data,
        "total": len(db_data),
        "folder": d
    }


@frappe.whitelist(allow_guest=True)
def get_wishlist_item_for_customer_by_user(items, customers, user_type):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates.
    """

    # frappe.throw(f"customers {customers}")

    # Parse JSON if string
    if isinstance(items, str):
        items = frappe.parse_json(items)

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
            "Cataloge Master",
            filters={"customer": customer},
            fields=["name"]
        )
        
        #mansi changes
        user_id = frappe.db.get_all(
            "Cataloge Master",
            filters={"user": customer},
            fields=["name"]
        )

        # frappe.throw(f"{customer_id}")

        # ---------------------------------------------------------
        # CUSTOMER EXISTS
        # ---------------------------------------------------------
        if customer_found or user_id:

            doc_name = customer_found[0].name if customer_found else user_id[0].name
            catalog_doc = frappe.get_doc("Cataloge Master", doc_name)
            # catalog_doc.flags.ignore_permissions = True

            # Build lookup: existing item_code → trending
            existing_items = {
                row.item_code: row
                for row in catalog_doc.cataloge_item_details
            }

            added = []
            updated = []

         
            for item_code, trending_value in items_dict.items():

                # skip metadata fields
                if item_code in [
                    "item",
                    "is_folder",
                    "status",
                    "folder_name",
                    "name",
                    "as_per_customized",
                    "job_work",
                    "customized_data",
                    "customer_gold",
                    "customer_diamond",
                    "customer_stone",
                    "as_per_design",
                    "is_duplicate"
                ]:
                    continue

                is_folder = items_dict.get("is_folder")
                as_per_design = items_dict.get("as_per_design")
                job_work = items_dict.get("job_work")
                as_per_customized = items_dict.get("as_per_customized")
                customized_data = items_dict.get("customized_data")
                status = items_dict.get("status")
                #mansi changes
                folder_name = items_dict.get("folder_name") or items_dict.get("name")
                is_duplicate  = items_dict.get("is_duplicate")
                name = items_dict.get("name")
                customer_gold = items_dict.get("customer_gold")
                customer_diamond = items_dict.get("customer_diamond")
                customer_stone = items_dict.get("customer_stone")
                
                # ----------------- NEW ITEM -----------------
                if item_code not in existing_items:

                    row_data = {
                        "item_code": item_code,
                        "item_name": item_code,
                        "wishlist": trending_value,
                        "job_work": job_work,
                        "as_per_customized": as_per_customized,
                        "as_per_design": as_per_design,
                        "customized_data": customized_data,
                        "customer_stone": customer_stone,
                        "customer_diamond": customer_diamond,
                        "customer_gold": customer_gold
                    }

                    catalog_doc.append(
                        "cataloge_item_details",
                        row_data
                    )

                    added.append(item_code)

                    # =====================================================
                    # SAVE FIRST BEFORE FOLDER CREATION
                    # =====================================================

                    catalog_doc.flags.ignore_version = True

                    catalog_doc.save(
                        ignore_permissions=True,
                        ignore_version=True
                    )

                    frappe.db.commit()

                    # reload latest doc to avoid timestamp mismatch
                    # catalog_doc.reload()

                    # rebuild existing_items
                    existing_items = {
                        row.item_code: row
                        for row in catalog_doc.cataloge_item_details
                    }

                    # =====================================================
                    # ADD IN FOLDER
                    # =====================================================

                    if (
                        is_folder == "Yes"
                        and as_per_design == 1
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and as_per_customized == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and job_work == 1
                        and as_per_customized == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and job_work == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                # ----------------- UPDATE ITEM -----------------
                else:
                    old_val = existing_items[item_code]

                    if old_val != trending_value:
                        
                        if is_duplicate == 1:
                            row_data = {
                                "item_code": item_code,
                                "item_name": item_code,
                                "wishlist": trending_value,
                                "job_work": job_work,
                                "as_per_customized": as_per_customized,
                                "as_per_design": as_per_design,
                                "customized_data": customized_data,
                                "customer_stone": customer_stone,
                                "customer_diamond": customer_diamond,
                                "customer_gold": customer_gold
                            }
                            
                            catalog_doc.append(
                                "cataloge_item_details",
                                row_data
                            )

                            added.append(item_code)

                            # =====================================================
                            # SAVE FIRST BEFORE FOLDER CREATION
                            # =====================================================

                            catalog_doc.flags.ignore_version = True

                            catalog_doc.save(
                                ignore_permissions=True,
                                ignore_version=True
                            )

                            frappe.db.commit()      
                        else:
                            row = next(
                                (d for d in catalog_doc.cataloge_item_details if d.item_code == item_code),
                                None
                            )
                            # frappe.throw(f"{row.name}")
                            if row:
                                    row.wishlist = trending_value
                                    row.job_work = job_work
                                    row.as_per_customized = as_per_customized
                                    row.as_per_design = as_per_design
                                    row.customized_data = customized_data
                                    row.customer_gold = customer_gold
                                    row.customer_diamond = customer_diamond
                                    row.customer_stone = customer_stone

                                    updated.append(item_code)
                                    
                                    catalog_doc.flags.ignore_version = True
                                    
                                    catalog_doc.save(
                                        ignore_permissions=True,
                                        ignore_version=True
                                    )

                                    frappe.db.commit()
                            
                                
                                    # same conditions here
                                    if (
                                        is_folder == "Yes"
                                        and as_per_design == 1
                                    ):
                                        # if row.as_per_design == as_per_design and row.item_code == item_code:
                                        #     frappe.throw(f"Item {row.item_code} Is alreday Exist With Design and Folder")
                                        
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )

                                    elif (
                                        is_folder == "Yes"
                                        and as_per_customized == 1
                                        and customized_data
                                    ):
                                        # if row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data:
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Customized and Folder")
                                        
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )
                                        
                                    elif (
                                        is_folder == "Yes"
                                        and job_work == 1
                                        and (customer_gold == 1 
                                            or customer_diamond == 1 
                                            or customer_stone == 1
                                            )
                                        and customized_data
                                        ):
                                        
                                        # if row.job_work == job_work and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )

                                    elif (
                                        is_folder == "Yes"
                                        and job_work == 1 and as_per_customized == 1
                                        and customized_data
                                        and (customer_gold == 1 
                                            or customer_diamond == 1 
                                            or customer_stone == 1
                                        )
                                    ):
                                        # if row.job_work == job_work and row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )
                    else:
                           row.wishlist = trending_value
                           row.job_work = job_work
                           row.as_per_customized = as_per_customized
                           row.as_per_design = as_per_design
                           row.customized_data = customized_data
                           row.customer_gold = customer_gold
                           row.customer_diamond = customer_diamond
                           row.customer_stone = customer_stone 
                           
                           updated.append(item_code)
                           
                           catalog_doc.flags.ignore_version = True

                           catalog_doc.save(
                                ignore_permissions=True,
                                ignore_version=True
                            )

                           frappe.db.commit()
                           
                           add_item_in_folder(
                                status,
                                folder_name,
                                items_dict.get("item"),
                                customer
                           )

            results.append({
                "customer": customer,
                "added_items": added,
                "updated_items": updated,
                "message": f"Added {len(added)}, Updated {len(updated)} for customer {customer}"
            })

            # notify_user(customer_id[0].email_id, f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You", f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You")

        # ---------------------------------------------------------
        # NEW CUSTOMER → CREATE CATALOG
        # ---------------------------------------------------------
        else:
            catalog_doc = frappe.new_doc("Cataloge Master")
            # catalog_doc.customer = customer

            if user_type == "User":
                user_email  = frappe.db.get_value(
                    "User",
                    customer,
                    "email"
                )
                catalog_doc.user = user_email 
                full_name = user_email or ""

                # Display: Full Name - Username
                display_name = f"{full_name} - {customer}"

                # Customer field me username save karo
                # catalog_doc.customer = customer

                # Display ke liye alag field
               
            else:
                catalog_doc.customer = customer

            added_items = []

            for item_code, trending_value in items_dict.items():

                # skip metadata fields
                if item_code in [
                    "item",
                    "is_folder",
                    "status",
                    "name",
                    "folder_name",
                    "as_per_customized",
                    "job_work",
                    "customized_data",
                    "customer_gold",
                    "customer_diamond",
                    "customer_stone",
                    "as_per_design"
                ]:
                    continue

                is_folder = items_dict.get("is_folder")
                as_per_design = items_dict.get("as_per_design")
                job_work = items_dict.get("job_work")
                as_per_customized = items_dict.get("as_per_customized")
                customized_data = items_dict.get("customized_data")
                status = items_dict.get("status")
                name = items_dict.get("name")
                folder_name = items_dict.get("folder_name") or items_dict.get("name") #mansi changes

                customer_gold = items_dict.get("customer_gold")
                customer_diamond = items_dict.get("customer_diamond")
                customer_stone = items_dict.get("customer_stone")

                # if folder and design type == As Per Design
                catalog_doc.append("cataloge_item_details", {
                        "item_code": item_code,
                        "item_name": item_code,
                        "wishlist": trending_value,
                        "job_work" : job_work,
                        "as_per_customized":as_per_customized,
                        "customer_gold":customer_gold,
                        "customer_stone" : customer_stone,
                        "customer_diamond" : customer_diamond,
                        "customized_data": customized_data
                })

                added_items.append(item_code)

                catalog_doc.insert(ignore_permissions=True)
                
                catalog_doc.save(
                            ignore_permissions=True,
                            ignore_version=True
                )

                frappe.db.commit()
                
                if (
                    is_folder == "Yes"
                    and as_per_design == 1
                ):            
                    add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                    )

                elif (
                    is_folder == "Yes"
                    and as_per_customized == 1
                    and customized_data
                ):               
                    add_item_in_folder(
                        status,
                        folder_name,
                        items_dict.get("item"),
                        customer
                    )
                    
                elif (is_folder == "Yes" 
                      and job_work == 1 
                      and (customer_gold == 1 
                            or customer_diamond == 1 
                            or customer_stone == 1
                        ) 
                      and customized_data
                    ):               
                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )
                
                elif (is_folder == "Yes" 
                      and job_work == 1 and as_per_customized == 1
                      and (customer_gold == 1 
                            or customer_diamond == 1 
                            or customer_stone == 1
                        ) 
                      and customized_data
                    ):                 
                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )           

                

            results.append({
                "customer": customer,
                "added_items": added_items,
                "updated_items": [],
                "message": f"Created new Cataloge Master for {customer}"
            })
            # notify_user(customer_id[0].email_id, "Cataloge Master New Catloug Master Created For You", "Cataloge Master New Catloug Master Created For You")
            

    return {
        "status": "success",
        "results": results
    }


@frappe.whitelist()
def add_item_in_folder(status=None, name=None, item=None, customer=None):
    if not customer:
        frappe.throw("Customer is required")

    # Only required for ADD and REMOVE
    # if status in ["ADD", "REMOVE"] and not item:
    #     frappe.throw("Item list is required")
    #mansi changes
    if status in ["ADD", "REMOVE", "DELETE"] and not name:
        frappe.throw("Folder name is required")

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
        FROM `tabCataloge Master` AS ctm
        LEFT JOIN `tabCataloge Item Details` AS citm
            ON citm.parent = ctm.name
            
        # WHERE ctm.customer = %(customer)s
        WHERE (ctm.customer = %(customer)s OR ctm.user = %(customer)s)
    """
#mansi changes
    # Add condition only for ADD and REMOVE
    if status in ["ADD", "REMOVE"]:
        sql_query += " AND citm.item_code IN %(items)s"


    values = {
        "customer": customer,
        "items": items if items else None
    }

    result = frappe.db.sql(sql_query, values=values, as_dict=True)

    if not result:
        frappe.throw("No matching records found")

    parent_name = result[0]["parent_name"]

    catalog_doc = frappe.get_doc(
        "Cataloge Master",
        parent_name,
        ignore_permissions=True
    )

    # ---------------- ADD ----------------
    if status == "ADD":
        for row in catalog_doc.cataloge_item_details:
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
        for row in catalog_doc.cataloge_item_details:
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
        for row in catalog_doc.cataloge_item_details:

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