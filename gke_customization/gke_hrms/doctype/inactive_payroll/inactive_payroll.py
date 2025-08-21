# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from datetime import timedelta


class InactivePayroll(Document):
	def autoname(self): 
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")

		prefix = f"{company_abbr}-IAP-"
		self.name = frappe.model.naming.make_autoname(prefix)
		
@frappe.whitelist()
def get_inactive_employees(docname):
		doc = frappe.get_doc("Inactive Payroll", docname)
		if not doc.from_date or not doc.to_date:
			frappe.throw("Please set both From Date and To Date.")

		doc.employees = []  
		date = doc.to_date + timedelta(days=7)
		inactive_employees = frappe.get_all("Employee",
			filters={
				"status": "Inactive",
				"relieving_date": ["between", [doc.from_date, date]],
				"company":doc.company,
				"branch":doc.branch
			},
			fields=["name", "employee_name", "department","designation","company","branch"]
		)

		for emp in inactive_employees:
			doc.append("employee", {
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"department": emp.department,
				"designation": emp.designation,
				"company": emp.company,
				"branch": emp.branch,
			})
		doc.save()
		return "Employees fetched successfully."

@frappe.whitelist()
def activate_employees(docname):
	doc = frappe.get_doc("Inactive Payroll", docname)
	count = 0
	for row in doc.employee:  
		emp = frappe.get_doc("Employee", row.employee)
		if emp.status == "Inactive":
			emp.db_set('status', 'Active')
			emp.save()
			count += 1

	return f"{count} employees marked as Active."


@frappe.whitelist()
def create_payroll_entries(docname):
	doc = frappe.get_doc("Inactive Payroll", docname)
	if not doc.employee:
		frappe.throw("No employees found in the Inactive Payroll record.")
	first_row = doc.employee[0]
	
	payroll_doc = frappe.new_doc("Payroll Entry")
	payroll_doc.employee = first_row.employee
	payroll_doc.posting_date = getdate()  
	payroll_doc.payroll_frequency = "Monthly"  
	payroll_doc.company = first_row.company
	payroll_doc.branch = first_row.branch
	company_doc = frappe.get_doc("Company", first_row.company)
	payroll_doc.payroll_payable_account=company_doc.default_payroll_payable_account
	payroll_doc.cost_center=company_doc.cost_center
	payroll_doc.start_date=doc.from_date

	payroll_doc.end_date =doc.to_date
	payroll_doc.status = "Draft"
	payroll_doc.exchange_rate = 1
	
	try:
		payroll_doc.insert()
		frappe.msgprint("Payroll Entry Created")
		return payroll_doc.name 
	except Exception as e:
		frappe.throw(f"Failed to create payroll entry")

	 
	