import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt,fmt_money

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


@frappe.whitelist()
def employee_annexure(source_name, target_doc=None):
	job_offer = frappe.get_doc("Job Offer", source_name)
	annexure = get_mapped_doc(
        "Job Offer",
        source_name,
        {
            "Job Offer": {
                "doctype": "Employee Annexure",
                "field_map": {
                    "applicant_name": "employee_name",
                    "designation": "designation",
                    "custom_department": "department",
                    "company": "company",
                    # "status": "offer_status",
                    "offer_date": "offer_date",
                },
            }
        },
        target_doc,
    )
	annexure.employee_job_offer = source_name
	# annexure.ctc =0
	for term in job_offer.offer_terms:
		if term.offer_term == "Monthly Gross Salary":
			ctc = term.value.replace("/-", "").replace(",", "").strip()
			annexure.ctc = flt(ctc)
			# annexure.ctc = fmt_money(term.value,currency="INR")
			# frappe.throw(f"{annexure.ctc}")

			break
	job_applicant = frappe.get_doc("Job Applicant", job_offer.job_applicant)
	job_opening = frappe.get_doc("Job Opening", job_applicant.job_title)
	annexure.branch = job_opening.location
	return annexure