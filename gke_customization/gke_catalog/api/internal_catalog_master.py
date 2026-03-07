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


@frappe.whitelist(allow_guest=True)
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



