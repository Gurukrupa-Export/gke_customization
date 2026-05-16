import frappe
from frappe import _
import hashlib
import time
from frappe.utils import cstr
from frappe.core.doctype.user.user import User

def get_context(context):
    # Strict session validation
    if not frappe.local.session or not frappe.local.session.sid:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    # Get user from session
    user = frappe.session.user

    # Multiple validation checks
    if not user or user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    # Verify user exists and is enabled
    try:
        user_doc = frappe.get_doc("User", user)
        if not user_doc.enabled:
            frappe.throw(_("Your account is disabled. Please contact administrator."))
    except:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    # Check if user has System Manager role or is Administrator
    if "Metabase Viewer" not in frappe.get_roles(user) and user != "Administrator":
        frappe.throw(_("You are not permitted to view this page."), frappe.PermissionError)

    # Generate secure tokens
    session_token = generate_session_token(user)
    csrf_token = frappe.session.csrf_token
    
    # Add strict security headers
    frappe.local.response["headers"] = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
        "X-XSS-Protection": "1; mode=block"
    }

    # Add context variables with additional security
    context.update({
        "session_token": session_token,
        "csrf_token": csrf_token,
        "user": user,
        "timestamp": int(time.time()),
        "session_id": frappe.local.session.sid
    })

    return context

def generate_session_token(user):
    """Generate a secure token for the current session"""
    timestamp = int(time.time())
    secret = frappe.conf.get("secret_key", "your-secret-key")
    session_id = frappe.local.session.sid
    token_string = f"{user}:{timestamp}:{secret}:{session_id}"
    return hashlib.sha256(token_string.encode()).hexdigest()

@frappe.whitelist()
def get_current_user_roles():
    """Returns the roles of the current logged-in user."""
    if frappe.session.user and frappe.session.user != "Guest":
        return frappe.get_roles(frappe.session.user)
    return [] 
