# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, getdate
from frappe.model.document import Document
import re

class EmployeeMediclaimEnrollment(Document):

    def before_validate(self):
        fields = ["name", "date_of_birth", "old_employee_code", "gender", "employee_name", "company", "department", "designation", "branch", "date_of_joining", "marital_status", "aadhar_number", "name_as_per_aadhar", "current_address"]
        employee_details = frappe.db.get_value("Employee", {"old_punch_id": self.punch_id}, fields, as_dict=True)
        if employee_details:
            self.update({
                "employee": employee_details.get("name"),
                "employee_name": employee_details.get("employee_name"),
                "old_employee_code": employee_details.get("old_employee_code"),
                
                "company": employee_details.get("company"),
                "department": employee_details.get("department"),
                "designation": employee_details.get("designation"),
                "branch": employee_details.get("branch"),

                "gender": employee_details.get("gender"),
                "date_of_birth": employee_details.get("date_of_birth"),
                "date_of_joining": employee_details.get("date_of_joining"),
                "marital_status": employee_details.get("marital_status"),
                "aadhaar_number": employee_details.get("aadhar_number"),
                "name_as_per_aadhaar": employee_details.get("name_as_per_aadhar"),
                "address": employee_details.get("current_address")
            })

    def validate(self):
        self.validate_aadhar_number()
        self.validate_dependent_age()
        self.set_gender()
        self.set_total()

    def validate_dependent_age(self):
        
        self.age = calculate_age(self.date_of_birth)

        for row in self.family_details:

            if not row.relation or not row.date_of_birth:
                continue

            row.age = calculate_age(row.date_of_birth)

            # Son / Daughter Validation
            if row.relation in ["Son", "Daughter"]:
                if row.age >= 25:
                    frappe.throw(_(f"Row {row.idx}: Age for Son/Daughter cannot be more than 25 years."))

            # Mother / Father Validation
            if row.relation in ["Mother", "Father", "Mother In Law", "Father In Law"]:
                if row.age >= 80:
                    frappe.throw(_(f"Row {row.idx}: Age for Mother/Father cannot be more than 80 years."))


    def validate_aadhar_number(self):
        if self.aadhaar_number:
            if not re.match(r"^\d{12}$", self.aadhaar_number.strip()):
                frappe.throw(_("Aadhar Number is invalid, please enter a valid 12 digit number"))
        
        if self.family_details:
            for row in self.family_details:
                if row.document_type and row.document_type == "Aadhaar Card" and row.document_number:
                    if not re.match(r"^\d{12}$", row.document_number.strip()):
                        frappe.throw(f"Row {row.idx}: Aadhar Number is invalid, please enter a valid 12 digit number")

    def set_gender(self):
        for row in self.family_details:
            if row.relation in ["Son", "Father", "Father In Law"]:
                    row.gender = "Male"
            if row.relation in ["Daughter", "Mother", "Mother In Law"]:
                    row.gender = "Female"
    
    def set_total(self):
        """
        Backend validation for Additional Insured coverage.
        Ensures value is between 1 and 15 Lakh.
        """
        additional_cover = 0
        if self.additional_insured:

            # Extract numeric part
            match = re.search(r"\d+", self.additional_insured)

            if not match:
                frappe.throw("Invalid Additional Insured value.")

            additional_cover = int(match.group())

            if additional_cover < 0 or additional_cover > 15:
                frappe.throw("Additional Insured must be between 1 and 15 Lakh.")

        company_cover = self.insured_by_company or 0
        self.total = company_cover + additional_cover * 100000

def calculate_age(dob):
    if not dob:
        return 0
    end_date = getdate(f"{getdate().year}-03-31")  # 31 March of current year
    dob = getdate(dob)
    age = end_date.year - dob.year - ((end_date.month, end_date.day) < (dob.month, dob.day))
    return age
    
