"""
Who may read which customer's documents through the portal APIs.

The portal sends customer codes from the browser, so every API that returns a
customer's documents must check them here. The rules match what the portal
offers each login (see login.verify_otp_using_customer_name and
login.get_address_by_link_name):

- a customer login may read the customers it is a Portal User of;
- a staff login may read the customers it is listed under in Customer
  Representatives (the portal's "Linked customers");
- Administrator and System Managers may read every customer.
"""
import json

import frappe
from frappe import _

FULL_ACCESS_ROLES = {"System Manager"}


def parse_customers(customer):
	"""Customer codes from the request: a JSON list, a list, or one code."""
	if isinstance(customer, str):
		try:
			customer = json.loads(customer)
		except Exception:
			customer = [customer]
	if isinstance(customer, str):
		customer = [customer]
	return [c for c in (customer or []) if c]


def customers_of_user(user=None):
	"""Customer codes the user may read (ignores roles)."""
	user = user or frappe.session.user
	own = set(
		frappe.get_all("Portal User", filters={"parenttype": "Customer", "user": user}, pluck="parent")
	)
	own |= set(frappe.get_all("Customer Representatives", filters={"user_id": user}, pluck="parent"))
	return own


def has_full_access(user=None):
	"""Administrator and System Managers may read every customer."""
	user = user or frappe.session.user
	return user == "Administrator" or bool(FULL_ACCESS_ROLES.intersection(frappe.get_roles(user)))


def allowed_customers(customer):
	"""Returns the requested customer codes, or raises if any is not allowed for this login."""
	requested = parse_customers(customer)
	user = frappe.session.user

	if user == "Guest":
		frappe.throw(_("Please log in."), frappe.AuthenticationError)
	if not requested:
		frappe.throw(_("No customer given."), frappe.ValidationError)
	if has_full_access(user):
		return requested

	own = customers_of_user(user)
	if any(c not in own for c in requested):
		frappe.throw(_("Not permitted for this customer."), frappe.PermissionError)
	return requested
