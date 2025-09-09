# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import timedelta
from frappe.utils import getdate

class EmployeeUpdate(Document):
	def validate(self):
		self.full_name = " ".join(
			filter(lambda x: x, [self.first_name, self.middle_name, self.last_name])
		)
		if self.date_of_joining and self.custom_probation_period_days:
			probation_days = int(self.custom_probation_period_days)
			joining_date = getdate(self.date_of_joining)  
			self.final_confirmation_date = joining_date + timedelta(days=probation_days)

		if self.allowed_personal_hours:
			self.allowed_personal_hours = timedelta(hours=3)

		# if self.is_new_employee:
		# 	if self.health_insurance_status:

		# 		frappe.msgprint(f"{self.health_insurance_status}")
		# if self.employee_onboarding:
		# 	job_appliacnt=frappe.db.get_value('Employee Onboarding',self.employee_onboarding,'job_applicant')
		# 	image=frappe.db.get_value('Job Applicant',job_appliacnt,'custom_image')
		# 	self.image=image
		# 	frappe.throw(f"{image}")
	def on_submit(self):
		field_list = [
			"first_name", "middle_name", "last_name", "image", "date_of_birth", "grade","job_applicant",
			"salutation","gender","custom_notice_dayes", "employment_type","custom_probation_period_days",
			"date_of_joining","contract_end_date", "old_employee_code", "old_punch_id","status",
			"company", "department", "designation","operation","branch","apprentice_contract_no",
			"apprentice_register_no","scheduled_confirmation_date","final_confirmation_date","date_of_retirement",
			"prefered_contact_email","prefered_email","unsubscribed","expense_approver","leave_approver","salary_currency",
			"branch_name","reports_to","reporting_employee_name_",
			"cell_number", "personal_email", "company_email", "current_address", "current_accommodation_type",
			"same_as_current_address", "permanent_address","permanent_accommodation_type","city", "state", 
			"health_insurance_status","sum_assured_","accident_insurance_provider","accident_insurance_status",
			"sum_assured_accident_insurance_","accident_insurance_no","is_esic_applicable","_esic_number",
			"attendance_device_id","allowed_personal_hours","product_incentive_applicable","default_shift",
			"holiday_list","shift_request_approver","salary_mode","ctc",
			"employee_name_as_per_bank_account", "bank_name", "bank_ac_no", "ifsc_code", "micr_code", "iban", "marital_status",
			"family_background", "blood_group", "health_details", "health_insurance_provider", "health_insurance_no", "passport_number", 
			"valid_upto", "date_of_issue", "place_of_issue","religon", "employee_cast", "reference_type", 
			"reference_employee_code", "reference_employee_name", "reference_contact",
			"reference_address", "aadhar_number", "name_as_per_aadhar", "driving_licence_no", "name_as_per_driving_license", 
			"driving_license_valid_upto_date","relative_employee_code", "relative_employee_name",
			"employee_relative_relation", "resignation_letter_date", "relieving_date", "held_on", "new_workplace", 
			"leave_encashed", "encashment_date", "reason_for_leaving", "feedback", "is_pf_applicable",
			"pf_joining_date","pan_number", "name_as_pe_pan", "provident_fund_account", "handicap_certificate_date", 
			"handicap_percenatge", "is_physical_handicap", "uan_number","variable_end_date","variable_start_date","variable_in"
		]
		
		field_mapping = {
			"full_name": "employee_name",
			"operation": "custom_operation",
			"city": "custom_city",
			"state": "custom_state",
			"health_insurance_status": "custom_health_insurance_status",
			"sum_assured_": "custom_sum_assured_",
			"accident_insurance_provider": "custom_accident_insurance_provider",
			"accident_insurance_status": "custom_accident_insurance_status",
			"sum_assured_accident_insurance_": "custom_sum_assured_accident_insurance_",
			"accident_insurance_no": "custom_accident_insurance_no",
			"is_esic_applicable": "custom_is_esic_applicable",
			
			}
		
		if self.is_new_employee:
			# Create new employee
			emp_doc = frappe.get_doc({"doctype": "Employee"})

			for field in field_list:
				source_field = field
				target_field = field_mapping.get(field, field)

				value = frappe.db.get_value("Employee Update", self.name, source_field)
				emp_doc.set(target_field, value)

			allowed_personal_hours = self.get("allowed_personal_hours")
			if allowed_personal_hours:
				emp_doc.set("allowed_personal_hours", timedelta(hours=3))
			# emp_doc.insert()
			doc_ = emp_doc
		else:
			# Update existing employee
			for field in field_list:
				target_field = field_mapping.get(field, field)
				emp_value = frappe.db.get_value("Employee", self.employee, target_field)
				update_value = frappe.db.get_value("Employee Update", {"employee": self.employee}, field)

				if emp_value != update_value:
					frappe.db.set_value("Employee", self.employee, target_field, update_value)

			doc_ = frappe.get_doc("Employee", self.employee)
		

		doc_.set("custom_employee_languages", [])
		if self.employee_languages:
			for lan in self.employee_languages:
				employee_languages = doc_.append("custom_employee_languages", {})
				employee_languages.language = lan.language
				employee_languages.read = lan.read
				employee_languages.speak = lan.speak
				employee_languages.write = lan.write

		doc_.set("custom_employees_hobbies", [])
		for hobbie in self.employees_hobbies:
			employees_hobbies = doc_.append("custom_employees_hobbies", {})
			employees_hobbies.hobbies = hobbie.hobbies

		doc_.set("education", [])
		for edu in self.education:
			education = doc_.append("education", {})
			education.school_univ = edu.school_univ
			education.qualification = edu.qualification
			education.level = edu.level
			education.year_of_passing = edu.year_of_passing
			education.class_per = edu.class_per
			education.maj_opt_subj = edu.maj_opt_subj

		doc_.set("external_work_history", [])
		for ewh in self.external_work_history:
			external_work_history = doc_.append("external_work_history", {})
			external_work_history.company_name = ewh.company_name
			external_work_history.designation = ewh.designation
			external_work_history.salary = ewh.salary
			external_work_history.address = ewh.address
			external_work_history.contact = ewh.contact
			external_work_history.total_experience = ewh.total_experience

		doc_.set("internal_work_history", [])
		for iwh in self.internal_work_history:
			internal_work_history = doc_.append("internal_work_history", {})
			internal_work_history.branch = iwh.branch
			internal_work_history.department = iwh.department
			internal_work_history.designation = iwh.designation
			internal_work_history.from_date = iwh.from_date
			internal_work_history.to_date = iwh.to_date
		
		doc_.set("employee_family_background", [])
		for efb in self.employee_family_background:
			employee_family_background = doc_.append("employee_family_background", {})
			employee_family_background.name1 = efb.name1
			employee_family_background.relation = efb.relation
			employee_family_background.occupation = efb.occupation
			employee_family_background.birth_date = efb.birth_date
			employee_family_background.age = efb.age
			employee_family_background.document_name = efb.document_name
			employee_family_background.document_number = efb.document_number
			employee_family_background.same_as_present = efb.same_as_present
			employee_family_background.same_as_permanent = efb.same_as_permanent
			employee_family_background.address = efb.address
			employee_family_background.is_nominee = efb.is_nominee
			employee_family_background.nominee_share = efb.nominee_share

		doc_.set("employee_relative_deails", [])
		for erd in self.employee_relative_deails:
			employee_relative_deails = doc_.append("employee_relative_deails", {})
			employee_relative_deails.relative_name = erd.relative_name
			employee_relative_deails.relation = erd.relation
			employee_relative_deails.contact_number = erd.contact_number
			employee_relative_deails.same_as_present = erd.same_as_present
			employee_relative_deails.address = erd.address
			employee_relative_deails.same_as_permanent = erd.same_as_permanent

		doc_.set("emergency_contact_details_table", [])
		for ecdt in self.emergency_contact_details_table:
			emergency_contact_details_table = doc_.append("emergency_contact_details_table", {})
			emergency_contact_details_table.emergency_contact_name = ecdt.emergency_contact_name
			emergency_contact_details_table.emergency_phone = ecdt.emergency_phone
			emergency_contact_details_table.relation = ecdt.relation

		doc_.save()
		# frappe.throw(f"{doc_.name}")
		frappe.db.commit()

		if not self.is_new_employee:
			frappe.msgprint("Employee has been updated...")
		else:
			frappe.msgprint("Employee has been created...")