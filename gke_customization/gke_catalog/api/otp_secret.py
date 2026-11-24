"""
Per-user OTP secret for portal login.

The secret is derived from a master key kept in the site config
(`portal_otp_master_secret`). Keep secrets out of code.

Set it once per site, to a long random value, e.g.:
    bench --site <site> set-config portal_otp_master_secret "$(openssl rand -hex 32)"
On Frappe Cloud: Site -> Site Config -> add key `portal_otp_master_secret`.
Changing it only affects OTPs that were sent but not yet entered.

This is not an API (no @frappe.whitelist).
"""
import base64
import hashlib
import hmac

import frappe
from frappe import _


def otp_user_secret(username):
	master = frappe.conf.get("portal_otp_master_secret")
	if not master:
		frappe.log_error("portal_otp_master_secret is missing in site config", "Portal login")
		frappe.throw(_("Login is temporarily unavailable. Please contact support."))
	h = hmac.new(master.encode(), msg=username.encode(), digestmod=hashlib.sha1)
	return base64.b32encode(h.digest()).decode("utf-8")
