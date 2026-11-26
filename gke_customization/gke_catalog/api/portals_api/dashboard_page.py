import frappe
from frappe import _
from frappe.utils import flt
import pyotp
import hmac
import hashlib
import base64
from frappe.auth import LoginManager
from datetime import datetime, timedelta, timezone, date
import pytz
from frappe.integrations.oauth2 import get_oauth_server
import requests
import json
from frappe.utils import validate_email_address, now_datetime


from gke_customization.gke_catalog.api.notifications import notify_user
from gke_customization.gke_catalog.api.login import get_address_by_link_name
from gke_customization.gke_catalog.api.encryption_response import SecureJSON
from gke_customization.gke_catalog.api.portal_access import allowed_customers


@frappe.whitelist()
def get_created_issue_by_customer_and_supplier(customer):
    customer = allowed_customers(customer)

    format_strings = ','.join(['%s'] * len(customer))
    try: 
        query = f"""
            SELECT
                ti.name,
                ti.subject,
                ti.raised_by,
                ti.status,
                ti.priority,
                ti.issue_type,
                ti.description,
                ti.opening_date,
                ti.response_by,
                ti.resolution_details,
                ti.opening_time,
                ti.resolution_date,
                ti.customer,
                tc.customer_name,
                ti.company,
                ti.attachment
            FROM `tabIssue` as ti
            JOIN `tabCustomer` as tc ON ti.customer = tc.name
            WHERE ti.customer IN ({format_strings})
            ORDER BY
                ti.creation DESC, 
                CASE
                    WHEN ti.priority = 'High' THEN 1
                    WHEN ti.priority = 'Medium' THEN 2
                    WHEN ti.priority = 'Low' THEN 3 
                END ASC;
        """
        get_issue_list = frappe.db.sql(query, customer, as_dict=True)

        count = {}

        for row in get_issue_list:
            if row.status in count:
                count[row.status] +=1
            else:
                count[row.status] =1
        
        return count


    except Exception as e:
        frappe.log_error(f"Error in get_item: {str(e)}")
        return {"success": False, "message": "Failed to fetch Item"}
    

@frappe.whitelist()
def get_quotation_form(customer, id=None):
    customer = allowed_customers(customer)

    format_strings = ','.join(['%s'] * len(customer))
    current_date = datetime.now().date().strftime('%Y-%m-%d')

    conditions = f"q.party_name IN ({format_strings}) and q.transaction_date between '2025-01-01' and '{current_date}'"
    params = list(customer)

    if id:
        conditions += " AND q.name = %s"
        params.append(id)

    # Only the status counts are returned, so one row per quotation is enough.
    # (Loading every item line of every quotation took ~1 s.) EXISTS keeps the
    # old rule that a quotation without items is not counted.
    query = f"""
        SELECT q.name, q.status, q.docstatus
        FROM `tabQuotation` q
        WHERE {conditions}
          AND EXISTS (SELECT 1 FROM `tabQuotation Item` qi WHERE qi.parent = q.name)
    """

    try:
        rows = frappe.db.sql(query, params, as_dict=True)

        count = {
            0: {},
            1: {}
        }

        for row in rows:
            docstatus = row.get("docstatus")
            status = row.get("status")

            if docstatus in (0, 1):
                count[docstatus][status] = count[docstatus].get(status, 0) + 1

        secure = SecureJSON()
        enc_data = secure.encrypt(count)
        return enc_data
    except Exception as e:
        frappe.log_error(f"Error in get_quotation_form: {str(e)}")
        return {"success": False, "message": "Failed to fetch Quotation"}
    

@frappe.whitelist()
def get_sales_order(customer, id=None):
    customer = allowed_customers(customer)

    current_date = datetime.now().date().strftime('%Y-%m-%d')

    format_strings = ','.join(['%s'] * len(customer))
    conditions = f"so.customer IN ({format_strings}) AND so.transaction_date BETWEEN '2025-01-01' AND '{current_date}'"
    params = list(customer)

    if id:
        conditions += " AND so.name = %s"
        params.append(id)

    # Only the status counts are returned, so one row per sales order is enough.
    # (Loading every item line of every order took ~1.6 s.) EXISTS keeps the old
    # rule that an order without items is not counted.
    query = f"""
        SELECT so.name, so.status, so.docstatus
        FROM `tabSales Order` so
        WHERE {conditions}
          AND EXISTS (SELECT 1 FROM `tabSales Order Item` soi WHERE soi.parent = so.name)
    """

    try:
        rows = frappe.db.sql(query, params, as_dict=True)

        count = {
            0: {},
            1: {}
        }

        for row in rows:
            if row['status'] in ('To Deliver and Bill', 'To Bill', 'To Deliver'):
                status = 'WIP'
            else:
                status = row['status']

            docstatus = row.get("docstatus")
            if docstatus in (0, 1):
                count[docstatus][status] = count[docstatus].get(status, 0) + 1

        return count
    except Exception as e:
        frappe.log_error(f"Error in get_sales_order: {str(e)}", "get_sales_order")
        return {"success": False, "message": f"Internal error: {str(e)}"}
        

@frappe.whitelist()
def get_sales_invoice(customer, id=None):
    customer = allowed_customers(customer)

    format_strings = ','.join(['%s'] * len(customer))
    current_date = datetime.now().date().strftime('%Y-%m-%d')
    conditions = f"Sa.customer IN ({format_strings}) and Sa.posting_date between '2025-01-01' and '{current_date}'"
    params = list(customer)

    if id:
        conditions += " AND Sa.name = %s"
        params.append(id)

    query = f"""
        SELECT
            Sa.name,
            Sa.customer,
            Sa.company,
            Sa.due_date,
            Sa.posting_date,
            Sa.paid_amount,
            Sa.status,
            Sa.docstatus,
            Sa.total,
            SaItm.item_code,
            SaItm.item_name,
            SaItm.qty,
            SaItm.rate,
            SaItm.uom,
            SaItm.amount
            # Item.image AS item_image,
            # Item.item_category,
            # Item.item_subcategory
        FROM `tabSales Invoice` AS Sa
        JOIN `tabSales Invoice Item` AS SaItm ON SaItm.parent = Sa.name
        WHERE {conditions}
            
    """
    try:
        rows = frappe.db.sql(query, params, as_dict=True)
        orders_dict = {}
        for row in rows:
                so_name = row['name']
                # Prepare sales order details if not already done
                if so_name not in orders_dict: 
                    orders_dict[so_name] = {
                        'name': so_name,
                        'customer': row['customer'],
                        'posting_date': row['posting_date'],
                        'paid_amount': row['paid_amount'],
                        'status': row['status'], 
                        'docstatus':row['docstatus'],
                        'due_date': row['due_date'],
                        'items': []
                    } 
                item = {
                    'item_code': row['item_code'],
                    'item_name': row['item_name'],
                    # 'image': row['image'],
                    'qty': row['qty'],
                    'uom': row['uom'],
                    'rate': row['rate'],
                    'amount': row['amount'],
                    # 'item_category': row['item_category'],
                    # 'base_rate': row['base_rate'],
                    # 'diamond_quality' : row['diamond_quality'],
                    # 'metal_type': row['metal_type'],
                    # 'metal_color': row['metal_colour'],
                    # 'metal_touch': row['metal_touch'],
                    # 'metal_touch': row['metal_touch'],
                    # 'gold_bom_rate': row['gold_bom_rate'],
                    # 'diamond_bom_rate': row['diamond_bom_rate'],
                    # 'other_bom_rate': row['other_bom_rate'],
                    # 'gemstone_bom_rate': row['gemstone_bom_rate'],  
                    # 'amount': row['amount']
                }
                orders_dict[so_name]['items'].append(item)
 
        data = list(orders_dict.values())


        total_amount = 0
        
        for row in data:
            if row.get("docstatus") == 1:
                total_amount += row.get("paid_amount") or 0
 
        return {
            "total_amount": total_amount
        }
    except Exception as e:
        frappe.log_error(f"Error in get_sales_invoice: {str(e)}")
        return {"success": False, "message": "Failed to fetch Sales Invoice"}



@frappe.whitelist()
def get_customer_wise_count(customer):
    allowed_customers(customer)

    get_catalogue_data = frappe.get_all(
        "Cataloge Master",
        filters={"customer": customer},
        fields=["name"]
    )

    parent_names = [d.name for d in get_catalogue_data]

    assigned_items = frappe.get_all(
        "Cataloge Item Details",
        filters={
            "parent": ["in", parent_names]
        },
        fields=["item_code"],
        distinct=True
    )

    trending_items = frappe.get_all(
        "Cataloge Item Details",
        filters={
            "parent": ["in", parent_names],
            "trending": 1
        },
        fields=["item_code"],
        distinct=True
    )

    wishlist_items = frappe.get_all(
        "Cataloge Item Details",
        filters={
            "parent": ["in", parent_names],
            "wishlist": 1
        },
        fields=["item_code"],
        distinct=True
    )

    data =  {
        "get_catalouge_item_details_count": len(assigned_items),
        "trending_count": len(trending_items),
        "wishlist_count": len(wishlist_items)
    }
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data