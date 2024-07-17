# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OTRequest(Document):
	pass

@frappe.whitelist()
def fill_employee_details(department):
	employees = frappe.db.sql(f"""select name,employee_name from `tabEmployee` where department = '{department}' """,as_dict=1)
	
	return employees