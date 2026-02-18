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
from frappe.utils import validate_email_address


@frappe.whitelist()
def get_user_secret(username):
    MASTER_SECRET = b'super-secret-key-you-keep-safe'
    # derive a secret for the user without storing it
    h = hmac.new(MASTER_SECRET, msg=username.encode(), digestmod=hashlib.sha1)
    return base64.b32encode(h.digest()).decode('utf-8')


@frappe.whitelist(allow_guest=True)
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
def send_otp_for_login_user(username, password):
    login_manager = LoginManager()
    login_manager.authenticate(username, password)
    
    # verified_key = f"otp_verified_{username}"
    otp_key = f"otp_{username}"

    # Check if cached OTP exists
    if frappe.cache().get_value(otp_key):
        # Clear previous OTP and regenerate
        frappe.cache().delete_value(otp_key)

    # Generate new OTP
    secret = get_user_secret(username)
    otp = pyotp.TOTP(secret).now()

    # Cache OTP
    frappe.cache().set_value(otp_key, otp, expires_in_sec=90)


    valid_email = validate_email_address(username, throw=False)

    fallback_email = "mansi_g@gkexport.com"

    # If valid_email is None or False, use fallback, otherwise use valid_email
    if valid_email:
        recipient = valid_email
    else:
        recipient = fallback_email

    frappe.sendmail(
        recipients = recipient,
        # recipients = fallback_email,
        # recipients = "mitali_s@gkexport.com",
        sender = "shubham_s@gkexport.com",  #"customer_portal@gkexport.com",
        subject= "Your One Time Password",
        template="otp",  # corresponds to otp_email.html
        args={"otp": otp},
        now=True
    )

    frappe.sendmail(
        recipients = "bhavika_p@gkexport.com",
        # recipients = fallback_email,
        # recipients = "mitali_s@gkexport.com", 
        sender = "shubham_s@gkexport.com",
        subject= "Your One Time Password",
        template="user_otp",  # corresponds to otp_email.html
        args={"otp": otp, "login_id": recipient},
        now=True
    )

    return {
        "status": "success",
        "otp": otp  # In production, don't send this to frontend
    }


@frappe.whitelist(allow_guest=True)
def sent_alert_email_for_screen_shot(username):
    frappe.sendmail(
        recipients = "bhavika_p@gkexport.com",
        sender = "customer_portal@gkexport.com",
        subject= "Screen Shot Alert",
        message="You can not take Screen Shot"
    )
    return {
        "status": "success"
    }


@frappe.whitelist(allow_guest=True)
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



@frappe.whitelist(allow_guest=True)
def get_address_by_link_name(user_type, link_name):
    try:
        if not user_type or not link_name:
            return {"success": False, "message": "Missing user_type or link_name."}

        if user_type == 'Customer':
            customer_info = frappe.db.get_value("Customer", link_name,["name", "customer_name"], as_dict=True) or {}

            address_parents = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": link_name}, fields=["parent"])

            address_data = {}
            if address_parents:
                for add in address_parents:
                    addr = frappe.db.get_value(
                        "Address", add['parent'],
                        [
                            "name", "address_line1", "address_line2", "city", "state",
                            "pincode", "country", "phone", "email_id", "gstin", "gst_state_number"
                        ],
                        as_dict=True
                    )
                    if addr:
                        address_data.update(addr) # Merge multiple addresses if needed

            customer_represent = frappe.get_all(
                "Customer Representatives",
                filters={
                    "parent": link_name 
                },
                fields=["full_name","user_id","user_contact_no"]
            )
            # Merge both dicts together
            merged_data = {**customer_info, **address_data,"customer_representatives": customer_represent}

            return merged_data
        if user_type == "User": 
            emp_info = frappe.db.get_value(
                "Employee",
                filters={"user_id": link_name},
                fieldname=["name", "user_id", "employee_name", "company", "designation", "branch_name"],
                as_dict=True
            )

            if not emp_info:
                return {"success": False, "message": f"No employee found for user {link_name}"}
    
            customer_represent = frappe.get_all(
                "Customer Representatives",
                filters={
                    "employee": emp_info.name,
                    "user_id": link_name
                },
                fields=["parent"]
            )

            customer_info = []
            for cus in customer_represent:
                cust_details = frappe.db.get_value("Customer", cus.parent, ["name as customer", "customer_name","email_id"], as_dict=True)
                if cust_details:
                    customer_info.append(cust_details)
    
            merged_data = {**emp_info, "customer_representatives": customer_info}

            return merged_data
    except Exception as e:
        frappe.log_error(f"Error in getting user or customer: {str(e)}")
        return {"success": False, "message": "Failed to user or customer"}


@frappe.whitelist(allow_guest=True)
def update_last_active(user_id):
    """
    Returns current server timestamp in milliseconds
    for frontend to compare with localStorage.
    """
    if not user_id:
        return None

    # Current time in milliseconds
    current_timestamp = int(datetime.utcnow().timestamp() * 1000)
    
    return current_timestamp