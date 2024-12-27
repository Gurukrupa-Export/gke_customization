# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeUpdate(Document):
	def on_submit(self):
		filed_list = [
			"first_name","gender", "middle_name", "last_name", "image", "date_of_birth", "salutation","date_of_joining", "contract_end_date", "old_employee_code", "old_punch_id",
			"company", "department", "designation", "cell_number", "personal_email", "company_email", "current_address", "current_accommodation_type", "same_as_current_address", "permanent_address",
			"permanent_accommodation_type", "salary_mode", "employee_name_as_per_bank_account", "bank_name", "bank_ac_no", "ifsc_code", "micr_code", "iban", "marital_status",
			"family_background", "blood_group", "health_details", "health_insurance_provider", "health_insurance_no", "passport_number", "valid_upto", "date_of_issue", "place_of_issue",
			"religon", "employee_cast", "reference_type", "reference_employee_code", "reference_employee_name", "reference_contact",
			"reference_address", "aadhar_number", "name_as_per_aadhar", "driving_licence_no", "name_as_per_driving_license", "driving_license_valid_upto_date", "relative_employee_code", "relative_employee_name",
			"employee_relative_relation", "resignation_letter_date", "relieving_date", "held_on", "new_workplace", "leave_encashed", "encashment_date", "reason_for_leaving", "feedback", "is_pf_applicable",
			"pf_joining_date","pan_number", "name_as_pe_pan", "provident_fund_account", "handicap_certificate_date", "handicap_percenatge", "is_physical_handicap", "uan_number"
		]

		e_json = {
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
			"variable_end_date": "custom_contract_end_date",
			"variable_start_date": "custom_contract_start_date",
			"variable_in": "custom_variable_in",
			"esic_number": "_esic_number"
			}
		
		e_diff_filed = [
			"full_name", "operation", "city", "state", "health_insurance_status", "sum_assured_",
			"accident_insurance_provider", "accident_insurance_status", "sum_assured_accident_insurance_",
			"accident_insurance_no", "is_esic_applicable", "variable_end_date", "variable_start_date",
			"variable_in", "esic_number"
			]

		if not self.is_new_employee:
			for i in filed_list:
				if i in e_diff_filed:
					i = e_json[i]
				emp_value = frappe.db.get_value("Employee",self.employee,i)
				uemp_value = frappe.db.get_value("Employee Update",self.employee,i)
				if emp_value == uemp_value:
					continue
				frappe.db.set_value("Employee",self.employee,i,uemp_value)
		else:
			emp_doc = frappe.get_doc({
				'doctype': 'Employee'
			})
			
			for field in filed_list:
				if field in e_diff_filed:
					field = e_json[field]
				value = frappe.db.get_value("Employee Update", self.name, field)
				emp_doc.set(field, value)
			
			emp_doc.insert()

		if not self.is_new_employee:
			doc_ = frappe.get_doc('Employee', self.employee)
		else:
			doc_ = frappe.get_doc('Employee', emp_doc.name)

		doc_.set("employee_languages", [])
		for lan in self.employee_languages:
			employee_languages = doc_.append("employee_languages", {})
			employee_languages.language = lan.language
			employee_languages.read = lan.read
			employee_languages.speak = lan.speak
			employee_languages.write = lan.write

		doc_.set("employees_hobbies", [])
		for hobbie in self.employees_hobbies:
			employees_hobbies = doc_.append("employees_hobbies", {})
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


		if not self.is_new_employee:
			frappe.msgprint("Employee has been updated...")
		else:
			frappe.msgprint("Employee has been created...")





			
