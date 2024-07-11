# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeBRecord(Document):
	pass

@frappe.whitelist()
def get_salary_slip(employee):
	salary_slip = frappe.db.sql(f"""select name,start_date,payment_days,net_pay,total_working_days from `tabSalary Slip` where employee = '{employee}' and docstatus = 1 """,as_dict=1)
	return salary_slip