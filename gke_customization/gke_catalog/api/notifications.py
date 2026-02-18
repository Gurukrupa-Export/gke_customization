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



@frappe.whitelist(allow_guest=True)
def notify_user(for_user, subject, message=None, action_label=None, action_url=None):
    """
    Send a notification to a specific user and push realtime event.
    """
    # Create Notification Log
    notification = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": subject,
        "for_user": for_user,
        "message": message,
        "email_content": "",
        "document_type": "",
        "document_name": "",
        "type": "Alert"
    })

    notification.insert(ignore_permissions=True)

    # Publish realtime event
    frappe.publish_realtime(
        event="notification",
        user=for_user,
        message={
            "title": subject,
            "message": message,
            "action_label": action_label,
            "action_url": action_url
        }
    )

    frappe.db.commit()
    return {"status": "success"}

@frappe.whitelist(allow_guest=True)
def get_notifications_of_customer(for_user):
    """
    Fetch Notification Log entries for a specific user.
    """
    try:
        notifications = frappe.get_all(
            "Notification Log",
            filters={"for_user": for_user},
            fields=["name", "subject",  "type", "read", "creation"],
            order_by="creation desc"
        )

        return {
            "status": for_user,
            "data": notifications
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Notifications API Error")
        return {
            "status": "error",
            "message": str(e)
        }
