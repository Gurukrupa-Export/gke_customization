import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.personal_email, target.first_name,target.cell_number,target.gender,target.marital_status,target.date_of_birth,target.notice_number_of_days = frappe.db.get_value(
			"Job Applicant", source.job_applicant, ["email_id", "applicant_name","phone_number","gender","marital_status_new","date_of_birth","notice_period_in_days"]
		)
		target.is_new_employee = 1
	
	doc = get_mapped_doc(
		"Job Offer",
		source_name,
		{
			"Job Offer": {
				"doctype": "Employee Update",
				"field_map": {
					"applicant_name": "employee_name", 
					"offer_date": "scheduled_confirmation_date",
					"company":"company",
					"designation":"designation",
					"company":"company",
					},
			}
		},
		target_doc,
		set_missing_values,
	)
	return doc