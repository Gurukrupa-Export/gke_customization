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


# # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)

# #format_strings = ','.join(['%s'] * len(customer))


# # http://192.168.200.207:8001/api/method/gke_customization.gke_catalog.api.get_sales_order.get_sales_order

# @frappe.whitelist()
# def get_sales_order(customer, id=None):
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string

#     current_date = datetime.now().date().strftime('%Y-%m-%d')

#     format_strings = ','.join(['%s'] * len(customer))
#     conditions = f"so.customer IN ({format_strings}) AND so.transaction_date BETWEEN '2025-01-01' AND '{current_date}'"
#     params = list(customer)

#     if id:
#         conditions += " AND so.name = %s"
#         params.append(id)

#     query = f"""
#         SELECT 
#             so.name, so.status, so.customer, so.transaction_date, so.delivery_date, so.custom_updated_delivery_date, 
#             so.company, so.branch, so.customer_name, so.po_no, soi.diamond_quality, 
#             soi.item_code, soi.qty, soi.rate, soi.item_category, soi.metal_touch, soi.metal_color, 
#             soi.setting_type, soi.order_form_date, soi.image, soi.gold_bom_rate, soi.diamond_bom_rate, 
#             soi.gemstone_bom_rate, soi.other_bom_rate, soi.making_charge, soi.finding_weight_for_chain, 
#             soi.amount, soi.custom_product_size, soi.salesman_name, soi.serial_no 
#         FROM `tabSales Order` so
#         JOIN `tabSales Order Item` soi ON soi.parent = so.name 
#         WHERE {conditions}
#     """

#     try:

#         rows = frappe.db.sql(query, params, as_dict=True)
#         orders_dict = {}
#         for row in rows:
#             so_name = row['name']
#             status = ''
#             delivery_date = ''
#             if row['status'] == 'Draft':
#                 status = 'Draft'
#             if row['status'] in ('To Deliver and Bill','To Bill','To Deliver'):
#                 status = 'WIP'
#             elif row['status'] == 'Completed':
#                 status = 'Completed'
#             elif row['status'] == 'Closed':
#                 status = 'Closed'
#             else:
#                 status = row['status']

#             if row['custom_updated_delivery_date']:
#                 delivery_date = row['custom_updated_delivery_date']
#             else:
#                 delivery_date = row['delivery_date']

#             # Prepare sales order details if not already done
#             if so_name not in orders_dict:
#                 orders_dict[so_name] = {
#                     'name': so_name,
#                     'customer': row['customer'],
#                     'status': status,
#                     'transaction_date': row['transaction_date'],
#                     'delivery_date': delivery_date,
#                     'company': row['company'],
#                     'branch': row['branch'],
#                     'customer_name': row['customer_name'],
#                     'po_no': row['po_no'], 
#                     'items': []
#                 }
#             item = {
#                 'item_code': row['item_code'],
#                 'qty': row['qty'],
#                 'rate': row['rate'],
#                 'item_category': row['item_category'],
#                 'diamond_quality': row['diamond_quality'],
#                 'metal_touch': row['metal_touch'],
#                 'metal_color': row['metal_color'],
#                 'setting_type': row['setting_type'],
#                 'order_form_date': row['order_form_date'],
#                 'image': row['image'],
#                 'gold_bom_rate': row['gold_bom_rate'],
#                 'diamond_bom_rate': row['diamond_bom_rate'],
#                 'gemstone_bom_rate': row['gemstone_bom_rate'],
#                 'other_bom_rate': row['other_bom_rate'],
#                 'making_charge': row['making_charge'],
#                 'finding_weight_for_chain': row['finding_weight_for_chain'],
#                 'amount': row['amount'],
#                 'custom_product_size': row['custom_product_size'],
#                 'salesman_name': row['salesman_name'],
#                 'serial_no': row['serial_no']
#             }
#             orders_dict[so_name]['items'].append(item)

#         # Convert to list for response
#         data = list(orders_dict.values())
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_sales_order: {str(e)}", "get_sales_order")
#         return {"success": False, "message": f"Internal error: {str(e)}"}
        

# @frappe.whitelist()
# def get_order_form(customer, id=None):
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string

#     format_strings = ','.join(['%s'] * len(customer))

#     query = (
#     "SELECT "
#     "o.company, "
#     "o.name, "
#     "o.branch, "
#     "o.customer_code, "
#     "o.order_date, "
#     "o.order_type, "
#     "o.delivery_date, "
#     "o.diamond_quality, o.workflow_state,"
#     "o.po_no, "
#     "ofd.category, "
#     "ofd.subcategory, "
#     "ofd.setting_type, "
#     "ofd.qty, "
#     "ofd.metal_type, "
#     "ofd.metal_touch, "
#     "ofd.metal_colour, "
#     "ofd.product_size, "
#     "ofd.metal_target, "
#     "ofd.diamond_target, "
#     "ofd.sizer_type, "
#     "ofd.design_image_1 "
#     "FROM `tabOrder Form` o "
#     "JOIN `tabOrder Form Detail` ofd ON ofd.parent = o.name "
#     f"WHERE o.customer_code = {format_strings}"
#     )
    
#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)

#         order_dict = {}
#         for row in rows:
#             name = row['name']
#             if name not in order_dict:
#                 # Parent order structure
#                 order_dict[name] = {
#                     "company": row["company"],
#                     "name": name,
#                     "branch": row["branch"],
#                     "customer_code": row["customer_code"],
#                     "workflow_state": row["workflow_state"],
#                     "order_date": row["order_date"],
#                     "order_type": row["order_type"],
#                     "delivery_date": row["delivery_date"],
#                     "diamond_quality": row["diamond_quality"],
#                     "po_no": row["po_no"],
#                     "items": []
#                 }
#             # Child row (item) structure
#             item = {
#                 "category": row["category"],
#                 "subcategory": row["subcategory"],
#                 "setting_type": row["setting_type"],
#                 "qty": row["qty"],
#                 "metal_type": row["metal_type"],
#                 "metal_touch": row["metal_touch"],
#                 "metal_colour": row["metal_colour"],
#                 "product_size": row["product_size"],
#                 "metal_target": row["metal_target"],
#                 "diamond_target": row["diamond_target"],
#                 "sizer_type": row["sizer_type"],
#                 "design_image_1": row["design_image_1"]
#             }
#             order_dict[name]["items"].append(item)

#         data = list(order_dict.values())
#         return data

#     except Exception as e:
#         frappe.log_error(f"Error in get_order_form: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Order"}


# @frappe.whitelist() 
# def get_quotation_form(customer):    
#     # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))

#     query = f"""
#         SELECT  
#             q.name,
#             q.company,
#             q.customer_name,
#             q.branch,
#             q.status,
#             q.total_qty,
#             q.quotation_to,
#             q.party_name,
#             q.transaction_date,
#             q.gold_rate_with_gst,
#             q.gold_rate, 
#             qi.item_code,
#             qi.item_category,
#             qi.item_subcategory,
#             qi.setting_type, 
#             qi.serial_no,
#             qi.quotation_bom,
#             qi.diamond_quality,
#             qi.metal_type,
#             qi.metal_touch,
#             qi.metal_purity,
#             qi.metal_colour,
#             qi.gold_bom_rate,
#             qi.diamond_bom_rate,
#             qi.other_bom_rate,
#             qi.gemstone_bom_rate,
#             qi.image,
#             qi.custom_hallmarking_amount,
#             qi.rate,
#             qi.base_rate,
#             qi.amount,
#             qi.base_net_rate
#         FROM `tabQuotation` q 
#         JOIN `tabQuotation Item` qi ON qi.parent = q.name
#         where q.party_name IN ({format_strings}) and
#             q.transaction_date between '2025-01-01' and '{datetime.now().date().strftime('%Y-%m-%d')}'
#     """

#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         orders_dict = {}
#         for row in rows:
#                 so_name = row['name']
#                 # Prepare sales order details if not already done
#                 if so_name not in orders_dict: 
#                     orders_dict[so_name] = {
#                         'name': so_name,
#                         'customer': row['party_name'],
#                         'transaction_date': row['transaction_date'],
#                         'company': row['company'],
#                         'branch': row['branch'],
#                         'customer_name': row['customer_name'],
#                         'quotation_bom': row['quotation_bom'],
#                         'status': row['status'], 
#                         'gold_rate': row['gold_rate'],
#                         'items': []
#                     } 
#                 item = {
#                     'item_code': row['item_code'],
#                     'image': row['image'],
#                     'qty': row['total_qty'],
#                     'rate': row['rate'],
#                     'item_category': row['item_category'],
#                     'item_subcategory': row['item_subcategory'],
#                     'setting_type': row['setting_type'],
#                     'base_rate': row['base_rate'],
#                     'diamond_quality' : row['diamond_quality'],
#                     'metal_type': row['metal_type'],
#                     'metal_color': row['metal_colour'],
#                     'metal_touch': row['metal_touch'],
#                     'metal_touch': row['metal_touch'],
#                     'gold_bom_rate': row['gold_bom_rate'],
#                     'diamond_bom_rate': row['diamond_bom_rate'],
#                     'other_bom_rate': row['other_bom_rate'],
#                     'gemstone_bom_rate': row['gemstone_bom_rate'],  
#                     'amount': row['amount']
#                 }
#                 orders_dict[so_name]['items'].append(item)
 
#         data = list(orders_dict.values())
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_quotation_form: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Quotation"}
    

# @frappe.whitelist()
# def get_sketch_order(customer):
#     # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))

#     query = f"""
#         SELECT 
#             sko.name,
#             sko.company,
#             sko.customer_code,
#             sko.order_date,
#             sko.delivery_date,
#             sko.po_no,
#             sko.workflow_state,
#             skod.category,
#             skod.subcategory,
#             skod.setting_type, 
#             skod.qty,
#             skod.metal_type,
#             skod.metal_touch,
#             skod.metal_colour,
#             skod.metal_target,
#             skod.diamond_target,
#             skod.product_size,
#             skod.gemstone_type,
#             skod.design_image1
#         FROM `tabSketch Order Form` sko 
#         JOIN `tabSketch Order Form Detail` skod ON skod.parent = sko.name
#         WHERE sko.customer_code IN ({format_strings})
#     """

#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)

#         # Build nested result
#         order_dict = {}
#         for row in rows:
#             name = row["name"]
#             if name not in order_dict:
#                 order_dict[name] = {
#                     "name": name,
#                     "company": row["company"],
#                     "customer_code": row["customer_code"],
#                     "order_date": row["order_date"],
#                     "delivery_date": row["delivery_date"],
#                     "po_no": row["po_no"],
#                     "workflow_state": row["workflow_state"],
#                     "items": []
#                 }
#             child = {
#                 "category": row["category"],
#                 "subcategory": row["subcategory"],
#                 "setting_type": row["setting_type"], 
#                 "qty": row["qty"],
#                 "metal_type": row["metal_type"],
#                 "metal_touch": row["metal_touch"],
#                 "metal_colour": row["metal_colour"],
#                 "metal_target": row["metal_target"],
#                 "diamond_target": row["diamond_target"],
#                 "product_size": row["product_size"],
#                 "gemstone_type": row["gemstone_type"],
#                 "design_image1": row["design_image1"]
#             }
#             order_dict[name]["items"].append(child)
        
#         # Output is list of parent orders with nested items
#         data = list(order_dict.values())
#         # data = rows
#         return data
        
#     except Exception as e:
#         frappe.log_error(f"Error in get_sketch_order: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Sketch Order"}


# @frappe.whitelist() 
# def get_repair_order_form(customer):
#     query = f"""
#     SELECT  
#     name,
#     branch,
#     # order_details,
#     customer_code
#     FROM `tabRepair Order Form` where customer = %s
#     """

#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         data = rows
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_repair_order_form: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Repair Order Form"}

# # in every apis will have to use teh check token expire logic if expired then in each apis use teh refresh token to regenarte the token again  
# @frappe.whitelist() 
# def get_quotation_form(customer):
    
#     # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))

#     query = f"""
#         SELECT  
#             q.name,
#             q.company,
#             q.customer_name,
#             q.branch,
#             q.status,
#             q.total_qty,
#             q.quotation_to,
#             q.party_name,
#             q.transaction_date,
#             q.gold_rate_with_gst,
#             q.gold_rate, 
#             qi.item_code,
#             qi.item_category,
#             qi.item_subcategory,
#             qi.setting_type, 
#             qi.serial_no,
#             qi.quotation_bom,
#             qi.diamond_quality,
#             qi.metal_type,
#             qi.metal_touch,
#             qi.metal_purity,
#             qi.metal_colour,
#             qi.gold_bom_rate,
#             qi.diamond_bom_rate,
#             qi.other_bom_rate,
#             qi.gemstone_bom_rate,
#             qi.image,
#             qi.custom_hallmarking_amount,
#             qi.rate,
#             qi.base_rate,
#             qi.amount,
#             qi.base_net_rate
#         FROM `tabQuotation` q 
#         JOIN `tabQuotation Item` qi ON qi.parent = q.name
#         where q.party_name IN ({format_strings})
#     """

#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         orders_dict = {}
#         for row in rows:
#                 so_name = row['name']
#                 # Prepare sales order details if not already done
#                 if so_name not in orders_dict: 
#                     orders_dict[so_name] = {
#                         'name': so_name,
#                         'customer': row['party_name'],
#                         'transaction_date': row['transaction_date'],
#                         'company': row['company'],
#                         'branch': row['branch'],
#                         'customer_name': row['customer_name'],
#                         'quotation_bom': row['quotation_bom'],
#                         'status': row['status'], 
#                         'gold_rate': row['gold_rate'],
#                         'items': []
#                     } 
#                 item = {
#                     'item_code': row['item_code'],
#                     'image': row['image'],
#                     'qty': row['total_qty'],
#                     'rate': row['rate'],
#                     'item_category': row['item_category'],
#                     'item_subcategory': row['item_subcategory'],
#                     'setting_type': row['setting_type'],
#                     'base_rate': row['base_rate'],
#                     'diamond_quality' : row['diamond_quality'],
#                     'metal_type': row['metal_type'],
#                     'metal_color': row['metal_colour'],
#                     'metal_touch': row['metal_touch'],
#                     'metal_touch': row['metal_touch'],
#                     'gold_bom_rate': row['gold_bom_rate'],
#                     'diamond_bom_rate': row['diamond_bom_rate'],
#                     'other_bom_rate': row['other_bom_rate'],
#                     'gemstone_bom_rate': row['gemstone_bom_rate'],  
#                     'amount': row['amount']
#                 }
#                 orders_dict[so_name]['items'].append(item)
 
#         data = list(orders_dict.values())
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_quotation_form: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Quotation"}
    

# @frappe.whitelist()
# def get_sales_invoice(customer):

#     # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))

#     query = f"""
#         SELECT
#         Sa.name,
#         Sa.customer,
#         Sa.company,
#         Sa.due_date,
#         Sa.posting_date,
#         Sa.paid_amount,
#         Sa.status,
#         Sa.total,
#         SaItm.item_code,
#         SaItm.item_name,
#         SaItm.qty,
#         SaItm.rate,
#         SaItm.amount
#         # Item.image AS item_image,
#         # Item.item_category,
#         # Item.item_subcategory
#         FROM `tabSales Invoice` AS Sa
#         JOIN `tabSales Invoice Item` AS SaItm ON SaItm.parent = Sa.name
#         WHERE 
#             Sa.customer IN ({format_strings}) and
#             Sa.docstatus !=2
#     """
#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         orders_dict = {}
#         for row in rows:
#                 so_name = row['name']
#                 # Prepare sales order details if not already done
#                 if so_name not in orders_dict: 
#                     orders_dict[so_name] = {
#                         'name': so_name,
#                         'customer': row['customer'],
#                         'posting_date': row['posting_date'],
#                         'paid_amount': row['paid_amount'],
#                         'amount': row['amount'],
#                         'status': row['status'], 
#                         'due_date': row['due_date'],
#                         'items': []
#                     } 
#                 item = {
#                     'item_code': row['item_code'],
#                     'item_name': row['item_name'],
#                     # 'image': row['image'],
#                     'qty': row['qty'],
#                     'rate': row['rate'],
#                     # 'item_category': row['item_category'],
#                     # 'base_rate': row['base_rate'],
#                     # 'diamond_quality' : row['diamond_quality'],
#                     # 'metal_type': row['metal_type'],
#                     # 'metal_color': row['metal_colour'],
#                     # 'metal_touch': row['metal_touch'],
#                     # 'metal_touch': row['metal_touch'],
#                     # 'gold_bom_rate': row['gold_bom_rate'],
#                     # 'diamond_bom_rate': row['diamond_bom_rate'],
#                     # 'other_bom_rate': row['other_bom_rate'],
#                     # 'gemstone_bom_rate': row['gemstone_bom_rate'],  
#                     # 'amount': row['amount']
#                 }
#                 orders_dict[so_name]['items'].append(item)
 
#         data = list(orders_dict.values())
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_sales_invoice: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Sales Invoice"}
    

# @frappe.whitelist()
# def get_delivery_note(customer):
#     # user_customers = frappe.db.sql(f"""
#     #     SELECT parent AS customer
#     #     FROM `tabCustomer Representatives`
#     #     WHERE user_id = %s
#     #     """, (username,), as_dict=True)

#     # customer_names = [row["customer"] for row in user_customers]

#     # if not customer_names:
#     #     customer_names.append(customer)
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))

#     query = f"""
#     SELECT
#     DD.name,
#     DD.place_of_supply,
#     DD.customer,
#     DD.total,
#     DD.posting_date,
#     DD.status,
#     DN_ITM.item_code,
#     DN_ITM.item_name,
#     DN_ITM.image,
#     DN_ITM.qty,
#     DN_ITM.stock_qty,
#     DN_ITM.rate,
#     DN_ITM.uom,
#     DN_ITM.amount
#     FROM `tabDelivery Note` as DD
#     JOIN `tabDelivery Note Item` DN_ITM ON DN_ITM.parent = DD.name
#     WHERE DD.customer IN ({format_strings})
#     """
#     # rows = frappe.db.sql(query, as_dict=1)

#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         orders_dict = {}
#         for row in rows:
#                 so_name = row['name']
#                 # Prepare sales order details if not already done
#                 if so_name not in orders_dict: 
#                     orders_dict[so_name] = {
#                         'name': so_name,
#                         'customer': row['customer'],
#                         'posting_date': row['posting_date'],
#                         'place_of_supply' : row['place_of_supply'],
#                         'status': row['status'], 
#                         'total': row['total'],
#                         'items': []
#                     } 
#                 item = {
#                     'item_code': row['item_code'],
#                     'item_name': row['item_name'],
#                     'image': row['image'],
#                     'qty': row['qty'],
#                     'uom': row['uom'],
#                     'stock_qty': row['stock_qty'],
#                     'amount' : row['amount'],
#                     'rate': row['rate'],
#                 }
#                 orders_dict[so_name]['items'].append(item)
 
#         data = list(orders_dict.values())
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_delivery_note: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Delivery Note"}
    

# @frappe.whitelist()
# def get_item(customer):
#     query = f"""
#     SELECT  
#     name,
#     item_category,
#     item_subcategory,
#     setting_type,
#     sub_setting_type,
#     approx_gold,
#     approx_diamond
#     FROM `tabItem` where customer = %s
#     """
#     try:
#         rows = frappe.db.sql(query, customer, as_dict=True)
#         data = rows
#         return data
#     except Exception as e:
#         frappe.log_error(f"Error in get_item: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Item"}

# @frappe.whitelist()
# def get_created_issue_by_customer_and_supplier(customer):
#     if isinstance(customer, str):
#         try:
#             customer = json.loads(customer)
#         except Exception:
#             customer = [customer]  # fallback if not valid JSON string


#     format_strings = ','.join(['%s'] * len(customer))
#     try:
#         query = f"""
#         SELECT  
#             name,
#             subject,
#             raised_by,
#             status,
#             priority,
#             issue_type,
#             description,
#             opening_date,
#             response_by,
#             resolution_details,
#             opening_time,
#             resolution_date,
#             customer_name,
#             company,
#             attachment
#         FROM `tabIssue` 
#         where customer IN ({format_strings})
#         """
#         get_issue_list = frappe.db.sql(query, customer, as_dict=True)
#         data = get_issue_list
#         return data
    
#     except Exception as e:
#         frappe.log_error(f"Error in get_item: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Item"}

# @frappe.whitelist()
# def add_issues_by_customer(data):
#     try:
#         subject = data.get('subject')
#         priority = data.get('priority')
#         issue_type = data.get('issue_type')
#         description = data.get('description')

#         frappe.throw("{subject} {priority} {issue_type} {description}")

#         if not subject or not priority or not issue_type or not description:
#             return {"success": False, "message": "Missing required fields"}

#         query = """
#                 INSERT INTO `tabIssue` (subject, priority, issue_type, description)
#                 VALUES (%s, %s, %s, %s)
#             """
#         values = (subject, priority, issue_type, description)

#         frappe.db.sql(query, values)
#         frappe.db.commit()

#             # Query the inserted record to return it (assuming subject + description uniquely identifies it)
#         select_query = """
#                 SELECT * FROM `tabIssue`
#                 WHERE subject = %s AND priority = %s AND issue_type = %s AND description = %s
#                 ORDER BY creation DESC
#                 LIMIT 1
#             """
#         inserted_data = frappe.db.sql(select_query, values, as_dict=True)

#         return inserted_data

#     except Exception as e:
#         frappe.log_error(f"Error in add_issues_by_customer: {str(e)}")
#         return {"success": False, "message": "Failed to create Issue"}

# # call this method if login acces code expired and in that fun use the update method find that oath token form oath doctyppe(Oath Token) 
# # and in that update the acces and refresh token and you need to add the  column id of the customer in that same doctype uisng that you will update the records
# def login_with_otp(username, password, id):
#     try:
#         login_manager = LoginManager()
#         login_manager.authenticate(username, password)

#         token = frappe.get_all("Oath Token",
#             filters={
#                 "cust_id": id,
#             },
#             fields=["name", "token", "expires_in", "refresh_token"],
#             order_by="creation desc",
#             limit=1
#         )

#         token_data = {
#             "grant_type": token[0]['refresh_token'],
#             "client_id": "5kbcjsfmch",
#             "client_secret": "6ae38cbd32",
#         }

#         result = generate_token_from_data(token_data)
    
#         return {
#             "status": "success",
#             "message": _("Login successful"),
#             "user": login_manager.user,
#             "data": result,
#         }

#     except frappe.AuthenticationError as e:
#         # Frappe will throw this if credentials are invalid
#         frappe.clear_messages()
#         frappe.response["http_status_code"] = 401
#         frappe.throw(_("Invalid username or password")) 


# @frappe.whitelist()
# def get_user_secret(username):
#     MASTER_SECRET = b'super-secret-key-you-keep-safe'
#     # derive a secret for the user without storing it
#     h = hmac.new(MASTER_SECRET, msg=username.encode(), digestmod=hashlib.sha1)
#     return base64.b32encode(h.digest()).decode('utf-8')


# # @frappe.whitelist() 
# # def send_otp(customer):
# #     query = """
# #     select 
# #     name,
# #     customer_name,
# #     email_id,
# #     from `tabCustomer` 
# #     where name = %s
# #     """
# #     try:
# #         row = frappe.db.sql(query, customer, as_dict=True)
# #         # return {"success": True, "data": row[0]}
# #     except Exception as e:
# #         # frappe.log_error(f"Error in : {str(e)}")
# #         return {"success": False, "message": "Customer not found"}
    

# #     # login_manager = LoginManager()
# #     # login_manager.authenticate(username, password)
    

# #     # verified_key = f"otp_verified_{username}"
# #     otp_key = f"otp_{customer}"

# #     # # If OTP already verified, no need to send again
# #     # if frappe.cache().get_value(verified_key):
# #     #     return {
# #     #         "status": "success",
# #     #         "message": "OTP already verified. No need to send again."
# #     #     }

# #     # Check if cached OTP exists
# #     if frappe.cache().get_value(otp_key):
# #         # Clear previous OTP and regenerate
# #         frappe.cache().delete_value(otp_key)

# #     # Generate new OTP
# #     secret = get_user_secret(customer)
# #     otp = pyotp.TOTP(secret).now()

# #     # Cache OTP
# #     frappe.cache().set_value(otp_key, otp, expires_in_sec=90)

# #     frappe.sendmail(
# #         recipients = "shubham_s@gkexport.com",
# #         sender = "shubham_s@gkexport.com",
# #         subject= "Your One Time Password",
# #         template="otp",  # corresponds to otp_email.html
# #         args={"otp": otp}
# #     )

# #     return {
# #         "status": "success",
# #         "otp": otp  # In production, don't send this to frontend
# #     }


# # @frappe.whitelist() 
# # def verify_otp(username, otp, client_id, client_secret, password):
# #     otp_key = f"otp_{username}"
# #     verified_key = f"otp_verified_{username}"
# #     otp_used_key = f"otp_used_{username}_{otp}"  # Unique key per OTP

# #     # Prevent OTP reuse
# #     if frappe.cache().get_value(otp_used_key):
# #         return {
# #             "status": "failed",
# #             "message": "This OTP has already been used."
# #         }
# #     # Validate OTP
# #     secret = get_user_secret(username)
# #     totp = pyotp.TOTP(secret)
# #     is_valid = totp.verify(otp, valid_window=1)

# #     if is_valid:
# #         # Mark OTP as used
# #         frappe.cache().set_value(otp_used_key, True, expires_in_sec=120)

# #         # Proceed
# #         frappe.cache().set_value(verified_key, True, expires_in_sec=120)
# #         frappe.cache().delete_value(otp_key)

# #         token_data = {
# #             "grant_type": "password",
# #             "client_id": client_id ,
# #             "client_secret": client_secret,
# #             "username": username,
# #             "password": password
# #         }

# #         result = generate_token_from_data(token_data)

# #         if "access_token" in result:
# #             expires_at_utc = datetime.now(timezone.utc) + timedelta(seconds=result.expires_in)
# #             local_tz = pytz.timezone("Asia/Kolkata")
# #             expires_at_local = expires_at_utc.astimezone(local_tz).replace(tzinfo=None)

# #             token_doc = frappe.get_doc({
# #                 "doctype": "Oath Token",
# #                 "token": result.access_token,
# #                 "expires_in": expires_at_local,
# #                 "refresh_token": result.refresh_token
# #             })
# #             token_doc.insert(ignore_permissions=True)

# #         else:
# #             frappe.throw("Token generation failed", title="Login Failed")

# #         return {
# #             "status": "success",
# #             "message": "OTP verified successfully",
# #             "data": result
# #         }

# #     return {
# #         "status": "failed",
# #         "message": "Invalid or expired OTP"
# #     }


# def generate_token_from_data(data):
#     method = "POST"
#     url = "/api/method/frappe.integrations.oauth2.get_token"

#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded"
#     }

#     oauth_server = get_oauth_server()

#     _, body, _ = oauth_server.create_token_response(
#         url, method, data, headers, frappe.flags.oauth_credentials
#     )

#     return frappe._dict(json.loads(body))


# # @frappe.whitelist() 
# # def verify_otp_without_access_token(customer, otp):
# #     query = """
# #     select 
# #     name,
# #     customer_name
# #     from `tabCustomer` 
# #     where  name = %s
# #     """
# #     try:
# #         row = frappe.db.sql(query, customer, as_dict=True)
# #         # return {"success": True, "data": row[0]}
# #     except Exception as e:
# #         # frappe.log_error(f"Error in : {str(e)}")
# #         return {"success": False, "message": "Customer not found"}
    
# #     otp_key = f"otp_{customer}"
# #     verified_key = f"otp_verified_{customer}"
# #     otp_used_key = f"otp_used_{customer}_{otp}"  # Unique key per OTP

# #     # Prevent OTP reuse
# #     if frappe.cache().get_value(otp_used_key):
# #         return {
# #             "status": "failed",
# #             "message": "This OTP has already been used."
# #         }
# #     # Validate OTP
# #     secret = get_user_secret(customer)
# #     totp = pyotp.TOTP(secret)
# #     is_valid = totp.verify(otp, valid_window=1)

# #     if is_valid:
# #         # Mark OTP as used
# #         frappe.cache().set_value(otp_used_key, True, expires_in_sec=120)

# #         # Proceed
# #         frappe.cache().set_value(verified_key, True, expires_in_sec=120)
# #         frappe.cache().delete_value(otp_key)

# #         # get_customer = frappe.db.get_list("Customer", username)

# #         # get_supplire = frappe.db.get_list("Supplier", username)

# #         return {
# #             "status": "success",
# #             "message": "OTP verified successfully",
# #             "data": row[0]
# #         }
# #     else:
# #         frappe.throw("failed to verify Otp", title="Login Failed")


# #     return {
# #         "status": "failed",
# #         "message": "Invalid or expired OTP"
# #     }


# ############################################################################################################

# @frappe.whitelist()
# def send_otp_for_login_user(username, password):
#     login_manager = LoginManager()
#     login_manager.authenticate(username, password)
    
#     # verified_key = f"otp_verified_{username}"
#     otp_key = f"otp_{username}"

#     # Check if cached OTP exists
#     if frappe.cache().get_value(otp_key):
#         # Clear previous OTP and regenerate
#         frappe.cache().delete_value(otp_key)

#     # Generate new OTP
#     secret = get_user_secret(username)
#     otp = pyotp.TOTP(secret).now()

#     # Cache OTP
#     frappe.cache().set_value(otp_key, otp, expires_in_sec=90)

#     # frappe.db.set_value("Email Queue", {"status": "Not Sent"}, "status", "Sent")

#     frappe.sendmail(
#         recipients = username,
#         sender = "shubham_s@gkexport.com",
#         subject= "Your One Time Password",
#         template="otp",  # corresponds to otp_email.html
#         args={"otp": otp},
#         now=True
#     )

#     return {
#         "status": "success",
#         # "otp": otp  # In production, don't send this to frontend
#     }


@frappe.whitelist()
def get_user_secret(username):
    MASTER_SECRET = b'super-secret-key-you-keep-safe'
    # derive a secret for the user without storing it
    h = hmac.new(MASTER_SECRET, msg=username.encode(), digestmod=hashlib.sha1)
    return base64.b32encode(h.digest()).decode('utf-8')


def generate_token_from_data(data):
    method = "POST"
    url = "/api/method/frappe.integrations.oauth2.get_token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    oauth_server = get_oauth_server()

    _, body, _ = oauth_server.create_token_response(
        url, method, data, headers, frappe.flags.oauth_credentials
    )

    return frappe._dict(json.loads(body))


# @frappe.whitelist()
@frappe.whitelist()
def verify_otp_using_customer_name(username, password, otp):
    otp_key = f"otp_{username}"
    verified_key = f"otp_verified_{username}"
    otp_used_key = f"otp_used_{username}_{otp}"  # Unique key per OTP

    otp_value = frappe.cache().get_value(otp_key)
    otp_used = frappe.cache().get_value(otp_used_key)

    # -------------------------
    # 🔴 1. OTP Expired (missing in cache)
    # -------------------------
    if not otp_value:
        frappe.throw("OTP has expired. Please request a new OTP.")

    # -------------------------
    # 🔴 2. OTP already used
    # -------------------------
    if otp_used:
        frappe.throw("This OTP has already been used. Please request a new OTP.")

    # -------------------------
    # Prevent OTP reuse
    if frappe.cache().get_value(otp_used_key):
        return {
            "status": "failed",
            "message": "This OTP has already been used."
        }

    # Validate OTP
    secret = get_user_secret(username)
    totp = pyotp.TOTP(secret)
    is_valid = totp.verify(otp, valid_window=1)

    if is_valid:
        # Mark OTP as used
        frappe.cache().set_value(otp_used_key, True, expires_in_sec=120)
        frappe.cache().set_value(verified_key, True, expires_in_sec=120)
        frappe.cache().delete_value(otp_key)

        # Generate token
        token_data = {
            "grant_type": "password",
            "client_id": "e3cktidb7o",
            "client_secret": "6ae38cbd32",
            "username": username,
            "password": password
        }

        result = generate_token_from_data(token_data)

        if "access_token" in result:
            expires_at_utc = datetime.now(timezone.utc) + timedelta(seconds=result["expires_in"])
            local_tz = pytz.timezone("Asia/Kolkata")
            expires_at_local = expires_at_utc.astimezone(local_tz).replace(tzinfo=None)

            # 🔍 Fetch Customer linked to this username (email_id) using customer id

            query_1 = """
                SELECT
                    c.name,
                    c.customer_name,
                    pu.user AS user_email,
                    u.full_name,
                    u.enabled
                FROM `tabCustomer` AS c
                JOIN `tabPortal User` AS pu ON pu.parent = c.name
                JOIN `tabUser` AS u ON u.name = pu.user
                WHERE u.email = %s
            """

            data = frappe.db.sql(query_1, (username,), as_dict=True)

            name_list = [record["name"] for record in data]

            for record in data:
                record["user_type"] = "Customer"
                record['name'] = name_list

    
            # --- If not found, try Customer Representatives using user id---
            if not data:
                query_2 = """
                    SELECT
                        c.name,
                        # c.customer_name, //// remove this comment to get customet name in the responses if needed 
                        pu.user_id AS user_email,
                        u.full_name,
                        u.enabled
                    FROM `tabCustomer` AS c
                    JOIN `tabCustomer Representatives` AS pu ON pu.parent = c.name
                    JOIN `tabUser` AS u ON u.name = pu.user_id
                    WHERE u.email = %s
                """
                data = frappe.db.sql(query_2, (username,), as_dict=True)

                user_customers = frappe.db.sql(f"""
                SELECT parent AS customer
                FROM `tabCustomer Representatives`
                WHERE user_id = %s
                """, (username,), as_dict=True)

                customer_names = [row["customer"] for row in user_customers]

                # Fetch name of each customer properly
                customer_map = frappe.db.sql("""
                    SELECT name, customer_name, email_id
                    FROM `tabCustomer`
                    WHERE name IN (%s)
                """ % (", ".join(["%s"] * len(customer_names))), customer_names, as_dict=True)

                # Convert list to dictionary {id: name}
                customer_dict = {
                    row["name"]: {
                        "email_id": row.get("email_id"),
                        "customer_name": row["customer_name"]
                    }
                    for row in customer_map
                }

                for record in data:
                    record["user_type"] = "Customer"
                    record['name'] = customer_dict

                for record in data:
                    record["user_type"] = "User"

            try:
                # row = frappe.db.sql(query, (username,), as_dict=True)
                if not data:
                    return {"status": "failed", "message": "Customer not found"}
                
                # frappe.throw(f"{data}")
                
                get_login_time = frappe.db.get_value(
                        "User",
                        {"name": username},
                        ["login_after", "login_before"]
                    )

                login_after = get_login_time[0] 
                login_before = get_login_time[1]

                login_after = int(login_after)    
                login_before = int(login_before)   
                # dict = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10, 11:11, 12:12, 13:1, 14:2, 15: 3, 16: 4, 17: 5, 18: 6 , 19: 7, 20: 8, 21: 9, 22:10, 23:11, 24: 12 }

                # get current system hour
                current_time = datetime.now()
                total_hours = (current_time.hour + 5) + (current_time.minute + 30) / 60 + (current_time.second / 3600)
                # frappe.throw(f"{login_after}, {   new_hour}, {login_before}")
#
                # if not(login_after <= total_hours <= login_before):
                #     return {
                #         "status": "failed",
                #         "message": f"Access not allowed: current time is outside allowed login window."
                #     }
                        
                return {
                        "status": "success",
                        "message": "OTP verified successfully",
                        "access_token": result["access_token"],
                        "refresh_token": result.get("refresh_token"),
                        "expires_in": result.get("expires_in"),
                        "customer": data[0]
                }
               
            except Exception as e:
                frappe.log_error(f"Error fetching customer: {str(e)}")
                return {"status": "failed", "message": "Database error while fetching customer"}

        else:
            frappe.throw("Token generation failed", title="Login Failed")

    else:
        frappe.throw("Failed to verify OTP", title="Login Failed")

    return {"status": "failed", "message": "Invalid or expired OTP"}



# @frappe.whitelist()
# def get_address_by_link_name(user_type, link_name):
#     try:
#         if not user_type or not link_name:
#             return {"success": False, "message": "Missing user_type or link_name."}

#         if user_type == 'Customer':
#             customer_info = frappe.db.get_value("Customer", link_name,["name", "customer_name"], as_dict=True) or {}

#             address_parents = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": link_name}, fields=["parent"])

#             address_data = {}
#             if address_parents:
#                 for add in address_parents:
#                     addr = frappe.db.get_value(
#                         "Address", add['parent'],
#                         [
#                             "name", "address_line1", "address_line2", "city", "state",
#                             "pincode", "country", "phone", "email_id", "gstin", "gst_state_number"
#                         ],
#                         as_dict=True
#                     )
#                     if addr:
#                         address_data.update(addr) # Merge multiple addresses if needed

#             # Merge both dicts together
#             merged_data = {**customer_info, **address_data}

#             return merged_data
#         if user_type == "User": 
#             emp_info = frappe.db.get_value(
#                 "Employee",
#                 filters={"user_id": link_name},
#                 fieldname=["name", "user_id", "employee_name", "company", "designation", "branch_name"],
#                 as_dict=True
#             )

#             if not emp_info:
#                 return {"success": False, "message": f"No employee found for user {link_name}"}
    
#             customer_represent = frappe.get_all(
#                 "Customer Representatives",
#                 filters={
#                     "employee": emp_info.name,
#                     "user_id": link_name
#                 },
#                 fields=["parent"]
#             )

#             customer_info = []
#             for cus in customer_represent:
#                 cust_details = frappe.db.get_value("Customer", cus.parent, ["name as customer", "customer_name","email_id"], as_dict=True)
#                 if cust_details:
#                     customer_info.append(cust_details)
    
#             merged_data = {**emp_info, "customer_representatives": customer_info}

#             return merged_data
#     except Exception as e:
#         frappe.log_error(f"Error in get_sales_invoice: {str(e)}")
#         return {"success": False, "message": "Failed to fetch Sales Invoice"}

# @frappe.whitelist()
# def get_selected_item_for_customer_by_user(items, customer):

#     if isinstance(items, str):
#         try:
#             items = json.loads(items)
#         except Exception:
#             frappe.throw("Invalid items format — expected JSON list of item codes.")

#     customer_found = frappe.db.get_list(
#         "Cataloge Master",
#         filters={"customer": customer},
#         fields=["name"]
#     )

#     if customer_found:
        
#         catalog_doc = frappe.get_doc("Cataloge Master", customer_found[0].name)
       
#         filter_item_code = [row.item_code for row in catalog_doc.cataloge_item_details]
        
#         missing_items = list(set(items) - set(filter_item_code))
        
#         if missing_items:
#             for miss_item in missing_items:
#                 catalog_doc.append("cataloge_item_details", {
#                     "item_code": miss_item,
#                     "item_name": miss_item
#                 })        
          
#             catalog_doc.save()

#             frappe.db.commit()

#             return f"Added {len(missing_items)} {missing_items} new items to Cataloge Master."
#         else:
#             return "All items already exist in Cataloge Master."
#     else:
#         catalog_doc = frappe.new_doc("Cataloge Master")
#         catalog_doc.customer = customer

#         for item in items:
#             catalog_doc.append("cataloge_item_details", {
#                 "item_code": item,
#                 "item_name": item
#             })

#         catalog_doc.insert()
#         frappe.db.commit()

#         return f"New Cataloge Master created for {customer} with {len(items)} items."

