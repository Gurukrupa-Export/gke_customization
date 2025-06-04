# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.form import assign_to

class EmailSegmentation(Document):
	pass
    # def before_save(self):
    #     frappe.throw(f"{self.custom_all_internal_contact}") 

	# def after_save(self):
	# 	# if self.workflow_state == 'Send For Approval':
	# 		args = {
	# 			"assign_to": [self.approval_user_id],
	# 			"doctype": self.doctype,
	# 			"name": self.name,
	# 			# "description": task.description or task.subject,
	# 			# "notify": self.notify_users_by_email,
	# 		}
	# 		assign_to.add(args)
	# 		frappe.throw(f"hiii11111") 

