# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class EmployeeResignation(Document):
	def validate(self):
		workflow_state = frappe.db.get_value("Employee Resignation", {'employee': self.employee, 'workflow_state': 'Rejected' } , ['workflow_state'] )
		if workflow_state == 'Rejected':
			frappe.throw(f'{self.employee} can not fill the Resignation Form')
			
		if self.workflow_state == 'Send to Manager':
			if self.reporting_manager_approval:
				if self.reporting_manager_approval == 'Approved':
					if self.waive_off_notice_period == 'Yes': 
						notice_days = int(self.reduce_notice_day or 0)
				
					if self.date_resignation:
						resignation_date = datetime.strptime(str(self.date_resignation), "%Y-%m-%d")
						if self.waive_off_notice_period == 'Yes': 
							if notice_days:
								if int(self.notice_period) > int(notice_days):
									notice_days = self.notice_period - notice_days
									last_working_day = resignation_date + timedelta(days=notice_days)
						else:
							last_working_day = resignation_date + timedelta(days=self.notice_period)

						self.last_working_day = last_working_day.strftime("%Y-%m-%d")
		
		conf_date = frappe.db.get_value("Employee", {'name': self.employee } , ['final_confirmation_date'] )
		if conf_date:
			self.is_employee_on_probation = 'Yes'
		else:
			self.is_employee_on_probation = 'No'
			
@frappe.whitelist()
def create_employee_resignation(source_name, target_doc=None):
	doc = frappe.get_doc("Employee Resignation", source_name)

	doc = get_mapped_doc(
        "Employee Resignation",
        source_name,
        {
            "Employee Resignation": {
                "doctype": "Employee Separation",
                "field_map": {
                    "employee": "employee",
                    "department": "department",
                    "company": "company",
                    "designation": "designation", 
					"resignation_letter_date": "date_resignation",
					"last_working_day": "boarding_begins_on"
                },
            }
        },
        target_doc,
    )
	return doc
