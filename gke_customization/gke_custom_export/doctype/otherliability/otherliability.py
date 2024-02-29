# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OtherLiability(Document):
	pass

@frappe.whitelist()
def get_email_id(otherliability_name):
	email_id = frappe.db.sql(f"""select email_id from `tabContact Email` where parent = '{otherliability_name}'""",as_dict=1)

	return email_id

@frappe.whitelist()
def get_phone(otherliability_name):
	phone = frappe.db.sql(f"""select phone from `tabContact Phone` where parent = '{otherliability_name}'""",as_dict=1)

	return phone