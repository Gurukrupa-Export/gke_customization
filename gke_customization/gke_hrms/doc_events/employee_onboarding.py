import frappe 
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def employee_update(source_name, target_doc=None):
    # Fetch the source document
    doc = frappe.get_doc("Employee Onboarding", source_name)
    
    job_applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
    job_offer = frappe.get_doc("Job Offer", doc.job_offer)
    job_opening = frappe.get_doc("Job Opening", job_applicant.job_title)
    
    # Map the source document to the target document
    doc = get_mapped_doc(
        "Employee Onboarding",
        source_name,
        {
            "Employee Onboarding": {
                "doctype": "Employee Update",
                "field_map": {
                    "company": "company",
                    "department": "department",
                    "designation": "designation",
                    "date_of_joining": "date_of_joining",
                    "employee_name": "full_name",
                    "holiday_list": "holiday_list",
                    "employee_onboarding": "name",
                    "employee_grade": "grade",
                    "job_applicant": "job_applicant"
                },
            }
        },
        target_doc,
    )
    # frappe.throw(f"{doc}")
    doc.is_new_employee = 1
    doc.date_of_birth = job_applicant.date_of_birth
    doc.custom_notice_dayes = job_applicant.notice_period_in_days
    
    doc.scheduled_confirmation_date = job_offer.offer_date

    doc.gender = job_applicant.gender
    doc.employment_type = job_opening.employment_type
    doc.branch = job_opening.location
    doc.designation = job_offer.designation
    doc.department = job_offer.custom_department
    doc.cell_number = job_applicant.phone_number
    doc.personal_email = job_applicant.email_id
    doc.current_address = job_applicant.current_address
    doc.permanent_address = job_applicant.native_or_permanent_address
    # doc.ctc = frappe.db.get_value('Job Offer Term',{'parent': job_offer.name,'offer_term': 'Monthly Gross Salary'},['value'])
    doc.marital_status = job_applicant.marital_status_new
    doc.ctc = frappe.db.get_value("Employee Annexure", {'employee_job_offer': job_offer.name},['ctc'])
    
    for lan in job_applicant.language_known:
        employee_languages = doc.append("employee_languages", {})
        employee_languages.language = lan.language
        employee_languages.read = lan.read
        employee_languages.speak = lan.speak
        employee_languages.write = lan.write
    
    for edu in job_applicant.employee_education_:
        education = doc.append("education", {})
        education.school_univ = edu.school_univ
        education.qualification = edu.qualification
        education.level = edu.level
        education.year_of_passing = edu.year_of_passing
        education.class_per = edu.class_per
        education.maj_opt_subj = edu.maj_opt_subj

    external_work_history = doc.append("external_work_history", {})
    external_work_history.company_name = job_applicant.custom_present_work_place
    external_work_history.salary = job_applicant.current_salary

    doc.reference_type = job_applicant.source
    doc.reference_employee_code = job_applicant.source_name
    doc.aadhar_number = job_applicant.custom_aadhar_card_number



    return doc

# right empl
# left emp update