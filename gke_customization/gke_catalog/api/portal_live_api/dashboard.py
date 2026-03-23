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


@frappe.whitelist()
def get_created_issue_by_customer_and_supplier(customer):
    if isinstance(customer, str):
        try:
            customer = json.loads(customer)
        except Exception:
            customer = [customer]  # fallback if not valid JSON string

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
    if isinstance(customer, str):
        try:
            customer = json.loads(customer)
        except Exception:
            customer = [customer]  # fallback if not valid JSON string

    format_strings = ','.join(['%s'] * len(customer))
    current_date = datetime.now().date().strftime('%Y-%m-%d')

    conditions = f"q.party_name IN ({format_strings}) and q.transaction_date between '2025-01-01' and '{current_date}'"
    params = list(customer)

    if id:
        conditions += " AND q.name = %s"
        params.append(id)

    query = f"""
        SELECT  
            q.name,
            q.company,
            q.customer_name,
            q.branch,
            q.status,
            q.docstatus,
            q.total_qty,
            q.quotation_to,
            q.party_name,
            q.transaction_date,
            q.gold_rate_with_gst,
            q.gold_rate, 
            qi.item_code,
            qi.item_category,
            qi.item_subcategory,
            qi.setting_type, 
            qi.serial_no,
            qi.quotation_bom,
            qi.diamond_quality,
            qi.metal_type,
            qi.metal_touch,
            qi.metal_purity,
            qi.metal_colour,
            qi.gold_bom_rate,
            qi.diamond_bom_rate,
            qi.other_bom_rate,
            qi.gemstone_bom_rate,
            qi.image,
            qi.custom_hallmarking_amount,
            qi.rate,
            qi.base_rate,
            qi.amount,
            qi.base_net_rate
        FROM `tabQuotation` q 
        JOIN `tabQuotation Item` qi ON qi.parent = q.name
        where {conditions}
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
                        'customer': row['party_name'],
                        'transaction_date': row['transaction_date'],
                        'company': row['company'],
                        'branch': row['branch'],
                        'customer_name': row['customer_name'],
                        'quotation_bom': row['quotation_bom'],
                        'status': row['status'], 
                        'docstatus':row['docstatus'],
                        'gold_rate': row['gold_rate'],
                        'items': []
                    } 
                item = {
                    'item_code': row['item_code'],
                    'image': row['image'],
                    'qty': row['total_qty'],
                    'rate': row['rate'],
                    'item_category': row['item_category'],
                    'item_subcategory': row['item_subcategory'],
                    'setting_type': row['setting_type'],
                    'base_rate': row['base_rate'],
                    'diamond_quality' : row['diamond_quality'],
                    'metal_type': row['metal_type'],
                    'metal_color': row['metal_colour'],
                    'metal_touch': row['metal_touch'],
                    'metal_touch': row['metal_touch'],
                    'gold_bom_rate': row['gold_bom_rate'],
                    'diamond_bom_rate': row['diamond_bom_rate'],
                    'other_bom_rate': row['other_bom_rate'],
                    'gemstone_bom_rate': row['gemstone_bom_rate'],  
                    'amount': row['amount']
                }
                orders_dict[so_name]['items'].append(item)
 
        data = list(orders_dict.values())

        count = {
            0: {},
            1: {}
        }

        for row in data:
            docstatus = row.get("docstatus")
            status = row.get("status")

            if docstatus in (0, 1):
                count[docstatus][status] = count[docstatus].get(status, 0) + 1


        return count
    except Exception as e:
        frappe.log_error(f"Error in get_quotation_form: {str(e)}")
        return {"success": False, "message": "Failed to fetch Quotation"}
    


@frappe.whitelist()
def get_sales_order(customer, id=None):
    if isinstance(customer, str):
        try:
            customer = json.loads(customer)
        except Exception:
            customer = [customer]  # fallback if not valid JSON string

    current_date = datetime.now().date().strftime('%Y-%m-%d')

    format_strings = ','.join(['%s'] * len(customer))
    conditions = f"so.customer IN ({format_strings}) AND so.transaction_date BETWEEN '2025-01-01' AND '{current_date}'"
    params = list(customer)

    if id:
        conditions += " AND so.name = %s"
        params.append(id)

    query = f"""
        SELECT 
            so.name, so.status, so.docstatus, so.customer, so.transaction_date, so.delivery_date, so.custom_updated_delivery_date, 
            so.company, so.branch, so.customer_name, so.po_no, soi.diamond_quality, 
            soi.item_code, soi.qty, soi.rate, soi.item_category, soi.metal_touch, soi.metal_color, 
            soi.setting_type, soi.order_form_date, soi.image, soi.gold_bom_rate, soi.diamond_bom_rate, 
            soi.gemstone_bom_rate, soi.other_bom_rate, soi.making_charge, soi.finding_weight_for_chain, 
            soi.amount, soi.custom_product_size, soi.salesman_name, soi.serial_no 
        FROM `tabSales Order` so
        JOIN `tabSales Order Item` soi ON soi.parent = so.name 
        WHERE {conditions}
    """

    try:
        rows = frappe.db.sql(query, params, as_dict=True)
        orders_dict = {}
        for row in rows:
            so_name = row['name']
            status = ''
            delivery_date = ''
            if row['status'] == 'Draft':
                status = 'Draft'
            if row['status'] in ('To Deliver and Bill','To Bill','To Deliver'):
                status = 'WIP'
            elif row['status'] == 'Completed':
                status = 'Completed'
            elif row['status'] == 'Closed':
                status = 'Closed'
            else:
                status = row['status']

            if row['custom_updated_delivery_date']:
                delivery_date = row['custom_updated_delivery_date']
            else:
                delivery_date = row['delivery_date']

            # Prepare sales order details if not already done
            if so_name not in orders_dict:
                orders_dict[so_name] = {
                    'name': so_name,
                    'customer': row['customer'],
                    'status': status,
                    'transaction_date': row['transaction_date'],
                    'delivery_date': delivery_date,
                    'company': row['company'],
                    'branch': row['branch'],
                    'customer_name': row['customer_name'],
                    'po_no': row['po_no'], 
                    'docstatus':row['docstatus'],
                    'items': []
                }
            item = {
                'item_code': row['item_code'],
                'qty': row['qty'],
                'rate': row['rate'],
                'item_category': row['item_category'],
                'diamond_quality': row['diamond_quality'],
                'metal_touch': row['metal_touch'],
                'metal_color': row['metal_color'],
                'setting_type': row['setting_type'],
                'order_form_date': row['order_form_date'],
                'image': row['image'],
                'gold_bom_rate': row['gold_bom_rate'],
                'diamond_bom_rate': row['diamond_bom_rate'],
                'gemstone_bom_rate': row['gemstone_bom_rate'],
                'other_bom_rate': row['other_bom_rate'],
                'making_charge': row['making_charge'],
                'finding_weight_for_chain': row['finding_weight_for_chain'],
                'amount': row['amount'],
                'custom_product_size': row['custom_product_size'],
                'salesman_name': row['salesman_name'],
                'serial_no': row['serial_no']
            }
            orders_dict[so_name]['items'].append(item)

        # Convert to list for response
        data = list(orders_dict.values())

        count = {
            0: {},
            1: {}
        }

        for row in data:
            docstatus = row.get("docstatus")
            status = row.get("status")

            if docstatus in (0, 1):
                count[docstatus][status] = count[docstatus].get(status, 0) + 1
 
        return count
    except Exception as e:
        frappe.log_error(f"Error in get_sales_order: {str(e)}", "get_sales_order")
        return {"success": False, "message": f"Internal error: {str(e)}"}
        

@frappe.whitelist()
def get_sales_invoice(customer, id=None):
    if isinstance(customer, str):
        try:
            customer = json.loads(customer)
        except Exception:
            customer = [customer]  # fallback if not valid JSON string

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
    