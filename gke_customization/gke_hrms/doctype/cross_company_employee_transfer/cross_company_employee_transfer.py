# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import nowdate

from datetime import date, datetime


class CrossCompanyEmployeeTransfer(Document):

		def validate(self):
			pass
				
					
		def before_submit(self):
			pass

		
		def on_submit(self):

			if not self.create_new_employee_id :
				frappe.throw("Check Create New Employee Id Box First")

			if not self.target_site :
				frappe.throw("Add Target Site First")


			employee = frappe.get_doc("Employee", self.employee)

			new_employee = frappe.copy_doc(employee)

			new_employee.name = None
			new_employee.employee_number = None


			payload = new_employee.as_dict()

			payload["company"] = self.new_company
			# -------------------------
			# Remove system fields
			# -------------------------
			remove_fields = [
				"name",
				"employee",
				"creation",
				"modified",
				"modified_by",
				"owner",
				"user_id",
				"reports_to",
				"holiday_list",
				"custom_state",
				"expense_approver",
				"leave_approver",
				"shift_request_approver",
				"branch",
				"manufacturer",
				"custom_operation",
				"designation"
				"default_shift",
				"department"
				"docstatus",
				"idx",
				"lft",
				"rgt",
				"_user_tags",
				"_comments",
				"_assign",
				"_liked_by"
			]

			for field in remove_fields:
				payload.pop(field, None)

			# frappe.throw(payload.get("reports_to"))

			# -------------------------
			# Remove child tables (first test without them)
			# -------------------------
			child_tables = [
				"education",
				"custom_employee_languages",
				"custom_employees_hobbies",
				"employee_family_background",
				"employee_relative_deails",
				"emergency_contact_details_table",
				"external_work_history",
				"internal_work_history"
			]

			# -------------------------
			# Apply transfer changes
			# -------------------------
			field_map = {
				"Department": "department",              # ✅ fixed
				"Designation": "designation",             # ✅ fixed
				"Reports to": "reports_to",
				"Default Shift": "default_shift",         # ✅ fixed
				"Leave Approver": "leave_approver",
				"Expense Approver": "expense_approver",
				"Shift Request Approver": "shift_request_approver"
			}

			# def get_property_data_by_property():
			# 		property_data = {}
			# 		for row in self.transfer_details:
			# 			property_data[row.property] = row.new
			
			# 		return property_data
			

			# property_data = get_property_data_by_property()

			for table in child_tables:
				# if table == "internal_work_history":
				# 	payload.setdefault(table, []).append({
				# 		"branch": property_data.get("Branch", ""),
				# 		"department": property_data.get("Department", ""),
				# 		"designation": property_data.get("Designation", ""),
				# 		"from_date": payload.get("date_of_joining"),
				# 		"to_date": nowdate()
				# 	})
				# else:
				payload.pop(table, None)

		
			for row in self.transfer_details:

				if not row.property or not row.new:
					continue

				fieldname = field_map.get(row.property)

				if not fieldname:
					continue

				if fieldname in ["expense_approver", "reports_to", "shift_request_approver", "leave_approver"]:

					# "KGJPL - 00628 - Alpeshbhai Sureshbhai Rathod"
					parts = row.new.split(" - ")

					if len(parts) >= 2:
						payload[fieldname] = f"{parts[0]} - {parts[1]}"
					else:
						payload[fieldname] = row.new

				else:
					payload[fieldname] = row.new

			payload["holiday_list"] = "KGJPL-Holiday"

			payload["date_of_joining"] = self.transfer_date
			
			payload["doctype"] = "Employee"

			payload = frappe.parse_json(frappe.as_json(payload))

			# frappe.throw(frappe.as_json(payload))

			try:
				response = requests.post(
					"https://kggk-uat.m.frappe.cloud/api/method/create_transfer_employee",
					
					json={
						"employee_data": payload
					},
					timeout=60
				)

				# response.raise_for_status()

				response_data = response.json()
				# frappe.throw(frappe.as_json(response_data))

				if response_data.get("message") and response_data["message"].get("name"):

					self.new_employee_id = response_data["message"].get("name")
					self.db_set("new_employee_id", response_data["message"].get("name"))

					return response_data["message"].get("name")

				else:
					import json
					frappe.throw(
						"Employee creation failed in KGGK\n\n" +
						"\n".join(
							json.loads(msg)["message"]
							for msg in json.loads(response_data.get("_server_messages", "[]"))
						)
					)

			except Exception as e:

				frappe.log_error(
					title="Create Transfer Employee Error",
					message=str(e)
				)
				raise

@frappe.whitelist()
def get_kggk_data(property=None):

    response = requests.get(
        "https://kggk-uat.m.frappe.cloud/api/method/get_dept_desi_reprt_leave_apr_from_kggk"
    )

    return response.json()	