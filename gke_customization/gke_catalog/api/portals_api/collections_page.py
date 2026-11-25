import frappe
from frappe import _
import json

@frappe.whitelist()
def get_catalogue_collection_details(customers, collection=None, username=None):
    
    customer_list = []

    if customers:
        if isinstance(customers, str):
            try:
                customer_list = json.loads(customers)
            except Exception:
                customer_list = [customers]
        else:
            customer_list = customers
    
    elif username:
        user_customers = frappe.db.sql("""
            SELECT parent AS customer
            FROM `tabCustomer Representatives`
            WHERE user_id = %s
        """, (username,), as_dict=True)
        customer_list = [row["customer"] for row in user_customers]

    if not customer_list:
        return {"success": False, "message": "No customers found"}

    catalogue_list = frappe.get_all(
        "Cataloge Master",
        filters={"customer": ["in", customer_list]},
        fields=["name"],
    )

    data = get_data_for_multiple_customer_collections_details(
        catalogue_list=catalogue_list,
        # item_category=item_category,
        collection=collection,
    )
    
    
    #mansi 25-11-2026
    catalogue_names = [c["name"] for c in catalogue_list]
    
    if catalogue_names:
            # child table se items
            child_filters = {"parent": ["in", catalogue_names]}
            if collection:
                child_filters["collection"] = collection
    
            child_rows = frappe.get_all(
                "Catalogue Collection Details",
                filters=child_filters,
                fields=["item_code"],
            )
            item_codes = list({r["item_code"] for r in child_rows if r.get("item_code")})
    
            image_map = {}
            if item_codes:
                images = frappe.get_all(
                    "Item",
                    filters={"name": ["in", item_codes]},
                    fields=["name", "custom_catalogue_image", "custom_silver_image"],
                )
                image_map = {i["name"]: i for i in images}
    
          
            if isinstance(data, list):
                for row in data:
                    img = image_map.get(row.get("item_code"), {})
                    row["custom_catalogue_image"] = img.get("custom_catalogue_image")
                    row["custom_silver_image"] = img.get("custom_silver_image")
        #mansi 25-11-2026
    # frappe.throw(f"hii {data}")
    # return {
        # "success": True,
        # "data": data,
    # }
    return data


def get_data_for_multiple_customer_collections_details(catalogue_list, collection=None):
    final_data = []

    for row_doc in catalogue_list:
        doc = frappe.get_doc("Cataloge Master", row_doc.name)

        rows = []
        l = []
        for row in doc.catalogue_collection_details:
            if not collection or row.collection == collection:
                item = frappe.db.get_value(
                    "Item",
                    # {'name': row.item_code, 'item_category': item_category},
                    {'name': row.item_code},
                    ["item_category","item_subcategory", "image"],  # fetch fields you need
                    as_dict=True
                )

                if item and item.get("item_category"):
                    rows.append({
                        "idx": row.idx,
                        "item_code": row.item_code,
                        "collection": row.collection,
                        "name": row.name,
                        "image": item.get("image") if item else "",
                        "item_category": item.get("item_category") if item else "",
                        "item_subcategory": item.get("item_subcategory") if item else "",
                    })

        final_data.append({
            "customer": doc.customer,
            "catalogue_collection_details": rows,
        })
    return final_data

@frappe.whitelist()
def get_selected_item_count_for_customet_wise(customer_id, collection):
    try:
        # Get all Catalogue Masters for this customer
        catalogue_master_names = frappe.get_all(
            "Cataloge Master",
            filters={"customer": customer_id},
            pluck="name"
        )

        if not catalogue_master_names:
            return []
        
        # Get item codes from child table
        data = frappe.get_all(
            "Catalogue Collection Details",
            filters={
                "parent": ["in", catalogue_master_names],
                "collection": collection 
            },
            fields=["item_code"]
        )

        c = {}

        for i in data:
            get_category = frappe.db.get_value(
                "Item",
                i.item_code,
                ["item_category", "item_code"],
                as_dict=True
            )
            if get_category.item_category in c:
                c[get_category.item_category] += 1
            else:
                c[get_category.item_category] = 1
          
        return c

    except Exception as e:
        frappe.log_error(f"Error in get_selected_item_count_for_customet_wise: {e}")
        return e