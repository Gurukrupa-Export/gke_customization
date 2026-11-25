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

from gke_customization.gke_catalog.api.encryption_response import SecureJSON    # shubham encrypted fun

from cryptography.fernet import Fernet



@frappe.whitelist()
def get_selected_item_for_customer_by_user(items, customers, user_type):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates item added by user to the customer.
    """

    # Parse JSON if string
    if isinstance(items, str):
        items = json.loads(items)

    if isinstance(customers, str):
        customers = json.loads(customers)

    if not items or not customers:
        frappe.throw("Both 'items' and 'customers' are required.")

    # items = [ { item1: trending1, item2: trending2 } ]
    items_dict = items[0]

    results = []

    for customer in customers:

        customer_found = frappe.db.get_list(
            "Cataloge Master",
            filters={"customer": customer},
            fields=["name"]
        )

        customer_id = frappe.db.get_list(
            "Customer",
            filters={"name": customer},
            fields=["email_id"]
        )

        # frappe.throw(f"{customer_id}")

        # ---------------------------------------------------------
        # CUSTOMER EXISTS
        # ---------------------------------------------------------
        if customer_found:

            catalog_doc = frappe.get_doc("Cataloge Master", customer_found[0].name)

            # Build lookup: existing item_code → trending
            existing_items = {
                row.item_code: row.trending
                for row in catalog_doc.cataloge_item_details
            }

            added = []
            updated = []

            for item_code, trending_value in items_dict.items():

                # ----------------- NEW ITEM -----------------
                if item_code not in existing_items:
                    catalog_doc.append("cataloge_item_details", {
                        "item_code": item_code,
                        "item_name": item_code,
                        "trending": trending_value
                    })
                    added.append(item_code)

                # ----------------- UPDATE TRENDING -----------------
                # else:
                #     if row.item_code == item_code:
                #         if row.trending == 1:
                #             frappe.throw("Item already exists.")
                #     old_val = existing_items[item_code]
                #     if old_val != trending_value:
                #         for row in catalog_doc.cataloge_item_details:
                #             if row.item_code == item_code:
                #                 row.trending = trending_value
                #                 updated.append(item_code)
                #                 break
                else:
                    old_val = existing_items[item_code]
                
                    for row in catalog_doc.cataloge_item_details:
                        if row.item_code == item_code:
                
                            if row.trending == 1:
                                frappe.throw("Item already exists.")
                
                            if old_val != trending_value:
                                row.trending = trending_value
                                updated.append(item_code)
                
                            break

            catalog_doc.save()
            frappe.db.commit()

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
            catalog_doc.customer = customer

            if user_type == "User":
                user_data = frappe.db.get_value(
                    "User",
                    customer,
                    "full_name"
                )

                full_name = user_data or ""

                # Display: Full Name - Username
                display_name = f"{full_name} - {customer}"

                # Customer field me username save karo
                # catalog_doc.customer = customer

                # Display ke liye alag field
                catalog_doc.user = display_name

            for item_code, trending_value in items_dict.items():
                catalog_doc.append("cataloge_item_details", {
                    "item_code": item_code,
                    "item_name": item_code,
                    "trending": trending_value
                })

            catalog_doc.insert()
            frappe.db.commit()

            results.append({
                "customer": customer,
                "added_items": list(items_dict.keys()),
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