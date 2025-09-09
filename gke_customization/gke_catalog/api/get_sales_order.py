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

import json

# http://192.168.200.207:8001/api/method/gke_customization.gke_catalog.api.get_sales_order.get_sales_order

@frappe.whitelist()  # or True if needed
def get_sales_order():
    query = f"""
    SELECT  
    so.name,
    so.customer,
    so.delivery_date,
    so.company,
    so.branch,
    so.customer_name,
    so.po_no,
    soi.item_code,
    soi.qty,
    soi.rate,
    soi.item_category,
    soi.diamond_quality,
    soi.metal_touch,
    soi.metal_color,
    soi.setting_type,
    soi.order_form_date,
    soi.image,
    soi.gold_bom_rate,
    soi.diamond_bom_rate,
    soi.gemstone_bom_rate,
    soi.other_bom_rate,
    soi.making_charge,
    soi.finding_weight_for_chain,
    soi.amount,
    soi.custom_product_size,
    soi.salesman_name
    FROM `tabSales Order` so
    JOIN `tabSales Order Item` soi ON soi.parent = so.name
    where so.name = 'SAL-ORD-2025-02007'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_sales_order: {str(e)}")
        return {"success": False, "message": "Failed to fetch Sales Orders"}
    

@frappe.whitelist() 
def get_order_form():
    query = f"""
    SELECT  
    o.company,
    o.name,
    o.branch,
    o.customer_code,
    o.order_date,
    o.delivery_date,
    o.po_no,
    o.category,
    o.subcategory,
    o.setting_type,
    o.sub_setting_type1,
    o.qty,
    o.metal_type,
    o.metal_touch,
    o.metal_colour,
    o.diamond_type,
    o.metal_target,
    o.diamond_target,
    o.product_size,
    o.feature,
    o.rhodium,
    o.gemstone_type,
    o.design_image_1
    FROM `tabOrder`o where o.name = 'ORD/C/00001-1'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_order_form: {str(e)}")
        return {"success": False, "message": "Failed to fetch Order"}
    

@frappe.whitelist() 
def get_sketch_order():
    query = f"""
    SELECT  
    sko.name,
    sko.company,
    sko.customer_code,
    sko.order_date,
    sko.delivery_date,
    sko.po_no,
    skod.category,
    skod.subcategory,
    skod.setting_type,
    skod.sub_setting_type1,
    skod.qty,
    skod.metal_type,
    skod.metal_touch,
    skod.metal_colour,
    skod.metal_target,
    skod.diamond_target,
    skod.product_size,
    skod.gemstone_type,
    skod.design_image1
    FROM `tabSketch Order` sko 
    JOIN `tabSketch Order Form Detail` skod ON skod.parent = sko.name
    where sko.name = 'S/ORD/00001-1'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_sketch_order: {str(e)}")
        return {"success": False, "message": "Failed to fetch Sketch Order"}
    

@frappe.whitelist() 
def get_repair_order_form():
    query = f"""
    SELECT  
    name,
    branch,
    # order_details,
    customer_code
    FROM `tabRepair Order Form` where name = 'ORD/RO/00001'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_repair_order_form: {str(e)}")
        return {"success": False, "message": "Failed to fetch Repair Order Form"}

# in every apis will have to use teh check token expire logic if expired then in each apis use teh refresh token to regenarte the token again  
@frappe.whitelist(allow_guest=True) 
def get_quotation_form(id):
    user_lst = []
    latest_token = frappe.get_all("Oath Token",
        filters={
            "scope": "no_quotation"
        },
        fields=["name"],
        order_by="creation desc",
        limit=1
    )
    
    if latest_token:
        token_doc = frappe.get_doc("Oath Token", latest_token[0].name)
        user_lst = [row.customer for row in token_doc.users]  # Assuming child table has field `user`

    
    if id in user_lst:
        return frappe.msgprint("you don't have permission to see the quotation records!!")
    query = f"""
    SELECT  
    q.name,
    q.company,
    q.branch,
    q.status,
    q.quotation_to,
    q.party_name,
    q.transaction_date,
    q.gold_rate_with_gst,
    q.gold_rate,
    q.diamond_quality,
    qi.item_code,
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
    qi.custom_labour_charge,
    qi.custom_hallmarking_amount,
    qi.rate,
    qi.base_rate,
    qi.amount,
    qi.base_net_rate
    FROM `tabQuotation` q 
    JOIN `tabQuotation Item` qi ON qi.parent = q.name
    where q.name = 'GE-QTN-RP-25-00001'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_quotation_form: {str(e)}")
        return {"success": False, "message": "Failed to fetch Quotation"}
    

@frappe.whitelist() 
def get_sales_invoice():
    query = f"""
    SELECT  
    name,
    posting_time,
    total,
    paid_amount
    FROM `tabSales Invoice` where name = '1009'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_sales_invoice: {str(e)}")
        return {"success": False, "message": "Failed to fetch Sales Invoice"}
    

@frappe.whitelist() 
def get_delivery_note():
    query = f"""
    SELECT  *
    FROM `tabDelivery Note` where name = 'DN-24-00001'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_delivery_note: {str(e)}")
        return {"success": False, "message": "Failed to fetch Delivery Note"}
    

@frappe.whitelist() 
def get_item():
    query = f"""
    SELECT  
    name,
    item_category,
    item_subcategory,
    setting_type,
    sub_setting_type,
    approx_gold,
    approx_diamond
    FROM `tabItem` where name = 'EA07271-016'
    """
    rows = frappe.db.sql(query, as_dict=1)

    try:
        rows = frappe.db.sql(query, as_dict=True)
        return {"success": True, "data": rows}
    except Exception as e:
        frappe.log_error(f"Error in get_item: {str(e)}")
        return {"success": False, "message": "Failed to fetch Item"}
   
    
@frappe.whitelist(allow_guest=True)
# call this method if login acces code expired and in that fun use the update method find that oath token form oath doctyppe(Oath Token) 
# and in that update the acces and refresh token and you need to add the  column id of the customer in that same doctype uisng that you will update the records
def login_with_otp(username, password, id):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(username, password)

        token = frappe.get_all("Oath Token",
            filters={
                "cust_id": id,
            },
            fields=["name", "token", "expires_in", "refresh_token"],
            order_by="creation desc",
            limit=1
        )

        token_data = {
            "grant_type": token[0]['refresh_token'],
            "client_id": "5kbcjsfmch",
            "client_secret": "6ae38cbd32",
        }

        result = generate_token_from_data(token_data)
    
        return {
            "status": "success",
            "message": _("Login successful"),
            "user": login_manager.user,
            "data": result,
        }

    except frappe.AuthenticationError as e:
        # Frappe will throw this if credentials are invalid
        frappe.clear_messages()
        frappe.response["http_status_code"] = 401
        frappe.throw(_("Invalid username or password")) 


@frappe.whitelist()
def get_user_secret(username):
    MASTER_SECRET = b'super-secret-key-you-keep-safe'
    # derive a secret for the user without storing it
    h = hmac.new(MASTER_SECRET, msg=username.encode(), digestmod=hashlib.sha1)
    return base64.b32encode(h.digest()).decode('utf-8')


@frappe.whitelist(allow_guest=True) 
def send_otp(username, password):

    login_manager = LoginManager()
    login_manager.authenticate(username, password)

    # verified_key = f"otp_verified_{username}"
    otp_key = f"otp_{username}"

    # # If OTP already verified, no need to send again
    # if frappe.cache().get_value(verified_key):
    #     return {
    #         "status": "success",
    #         "message": "OTP already verified. No need to send again."
    #     }

    # Check if cached OTP exists
    if frappe.cache().get_value(otp_key):
        # Clear previous OTP and regenerate
        frappe.cache().delete_value(otp_key)

    # Generate new OTP
    secret = get_user_secret(username)
    otp = pyotp.TOTP(secret).now()

    # Cache OTP
    frappe.cache().set_value(otp_key, otp, expires_in_sec=90)

    frappe.sendmail(
        recipients = username,
        sender = username,
        subject= "Your One Time Password",
        template="otp",  # corresponds to otp_email.html
        args={"otp": otp}
    )

    return {
        "status": "success",
        "otp": otp  # In production, don't send this to frontend
    }


@frappe.whitelist(allow_guest=True) 
def verify_otp(username, otp, client_id, client_secret, password):
    otp_key = f"otp_{username}"
    verified_key = f"otp_verified_{username}"
    otp_used_key = f"otp_used_{username}_{otp}"  # Unique key per OTP

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

        # Proceed
        frappe.cache().set_value(verified_key, True, expires_in_sec=120)
        frappe.cache().delete_value(otp_key)

        token_data = {
            "grant_type": "password",
            "client_id": client_id ,
            "client_secret": client_secret,
            "username": username,
            "password": password
        }

        result = generate_token_from_data(token_data)

        if "access_token" in result:
            expires_at_utc = datetime.now(timezone.utc) + timedelta(seconds=result.expires_in)
            local_tz = pytz.timezone("Asia/Kolkata")
            expires_at_local = expires_at_utc.astimezone(local_tz).replace(tzinfo=None)

            token_doc = frappe.get_doc({
                "doctype": "Oath Token",
                "token": result.access_token,
                "expires_in": expires_at_local,
                "refresh_token": result.refresh_token
            })
            token_doc.insert(ignore_permissions=True)

        else:
            frappe.throw("Token generation failed", title="Login Failed")

        return {
            "status": "success",
            "message": "OTP verified successfully",
            "data": result
        }

    return {
        "status": "failed",
        "message": "Invalid or expired OTP"
    }


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


@frappe.whitelist(allow_guest=True) 
def verify_otp_without_access_token(username, otp):
    otp_key = f"otp_{username}"
    verified_key = f"otp_verified_{username}"
    otp_used_key = f"otp_used_{username}_{otp}"  # Unique key per OTP

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

        # Proceed
        frappe.cache().set_value(verified_key, True, expires_in_sec=120)
        frappe.cache().delete_value(otp_key)

        # data = frappe.db.get_value({

        # })


        return {
            "status": "success",
            "message": "OTP verified successfully",
            "data": ""
        }
    else:
        frappe.throw("failed to verify Otp", title="Login Failed")


    return {
        "status": "failed",
        "message": "Invalid or expired OTP"
    }
