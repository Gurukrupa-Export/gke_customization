# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccessRequest(Document):
	def autoname(self): 
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if self.request_purpose == "Employee Access":
			type_code = "EA"
		else :
			type_code = "DA"

		prefix = f"{company_abbr}-{type_code}-"
		self.name = frappe.model.naming.make_autoname(prefix)


	def validate(self):
		
		if self.workflow_state == 'Send For Approval':
			self.status = 'Requested'
			for row in self.platform_access:
				row.status = 'Requested'
			

		elif self.workflow_state == 'Approved':
			self.status = 'Approved'
			for row in self.platform_access:
				row.status = 'Approved'
	

	def on_update_after_submit(self):
	       	# self.set_value('status','Completed')
			# frappe.throw("hi")
			frappe.db.set_value("Access Request", self.name, "status", 'Completed')
			self.status = 'Completed'
			frappe.db.commit()
			self.reload()
			# frappe.throw("hi")
			for row in self.platform_access:
				frappe.db.set_value("Platform Access", row.name, "status", "Completed")
				row.status = 'Completed'
				frappe.db.commit()
				self.reload()

			# self.db_update()	

@frappe.whitelist()
def auto_department(user_id, request_purpose):
    if request_purpose == 'Department Access':
        employee = frappe.get_value('Employee', {'user_id': user_id}, ['department'], as_dict=True)
        if employee and employee.department:
            return employee.department
    return None


@frappe.whitelist()
def get_designation_query(doctype, txt, searchfield, start, page_len, filters):
    department = filters.get("department")

    if department:
        designation_count = frappe.db.count("Designation Details", {"parent": department})

        if designation_count > 0:
            return frappe.db.sql("""
                SELECT designation 
                FROM `tabDesignation Details`
                WHERE parent = %s AND designation LIKE %s
                ORDER BY designation
                LIMIT %s OFFSET %s
            """, (department, f"%{txt}%", page_len, start))

    return frappe.db.sql("""
        SELECT name 
        FROM `tabDesignation`
        WHERE name LIKE %s
        ORDER BY name
        LIMIT %s OFFSET %s
    """, (f"%{txt}%", page_len, start))
