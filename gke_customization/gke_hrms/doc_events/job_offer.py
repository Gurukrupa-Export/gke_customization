import re

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import DocType
from frappe.utils import flt


@frappe.whitelist()
def make_employee(source_name, target_doc=None):
    def set_missing_values(source, target):
        target.is_new_employee = 1
        if not source.job_applicant:
            return

        job_applicant = frappe.db.get_value(
            "Job Applicant",
            source.job_applicant,
            [
                "email_id",
                "applicant_name",
                "phone_number",
                "gender",
                "marital_status_new",
                "date_of_birth",
                "notice_period_in_days",
            ],
            as_dict=True,
        )
        if not job_applicant:
            return

        target.personal_email = job_applicant.email_id
        target.first_name = job_applicant.applicant_name
        target.cell_number = job_applicant.phone_number
        target.gender = job_applicant.gender
        target.marital_status = job_applicant.marital_status_new
        target.date_of_birth = job_applicant.date_of_birth
        target.notice_number_of_days = job_applicant.notice_period_in_days

    doc = get_mapped_doc(
        "Job Offer",
        source_name,
        {
            "Job Offer": {
                "doctype": "Employee Update",
                "field_map": {
                    "applicant_name": "employee_name",
                    "offer_date": "scheduled_confirmation_date",
                    "company": "company",
                    "designation": "designation",
                },
            }
        },
        target_doc,
        set_missing_values,
    )
    return doc


@frappe.whitelist()
def employee_annexure(source_name, target_doc=None):
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
                    "offer_date": "offer_date",
                },
            }
        },
        target_doc,
    )
    annexure.employee_job_offer = source_name
    monthly_gross_salary = frappe.db.get_value(
        "Job Offer Term",
        {
            "parent": source_name,
            "parenttype": "Job Offer",
            "offer_term": "Monthly Gross Salary",
        },
        "value",
        order_by="idx asc",
    )
    if monthly_gross_salary:
        salary_amount = re.search(r"\d[\d,]*(?:\.\d+)?", monthly_gross_salary)
        if salary_amount:
            annexure.ctc = flt(salary_amount.group().replace(",", ""))

    annexure.branch = get_job_opening_location(source_name)
    return annexure


def get_job_opening_location(job_offer):
    JobOffer = DocType("Job Offer")
    JobApplicant = DocType("Job Applicant")
    JobOpening = DocType("Job Opening")

    location = (
        frappe.qb.from_(JobOffer)
        .inner_join(JobApplicant)
        .on(JobApplicant.name == JobOffer.job_applicant)
        .inner_join(JobOpening)
        .on(JobOpening.name == JobApplicant.job_title)
        .select(JobOpening.location)
        .where(JobOffer.name == job_offer)
        .run()
    )

    return location[0][0] if location else None
