# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Unsecuredloans(Document):
	pass

@frappe.whitelist()
def get_email_id(unsecuredloans_name):
	email_id = frappe.db.sql(f"""select email_id from `tabContact Email` where parent = '{unsecuredloans_name}'""",as_dict=1)

	return email_id

@frappe.whitelist()
def get_phone(unsecuredloans_name):
	phone = frappe.db.sql(f"""select phone from `tabContact Phone` where parent = '{unsecuredloans_name}'""",as_dict=1)

	return phone