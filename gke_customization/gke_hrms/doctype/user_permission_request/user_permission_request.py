# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserPermissionRequest(Document):
    def autoname(self): 
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        type_code='UPR'
        prefix = f"{company_abbr}-{type_code}-"
        self.name = frappe.model.naming.make_autoname(prefix)

    def on_submit(self):
        if self.workflow_state == 'Create user ID':

            if frappe.db.exists('User', self.username):
                frappe.throw("User already exists")
                return
            
            user = frappe.new_doc('User')
            user.email = self.username
            user.first_name = self.first_name
            user.last_name = self.last_name
            user.last_name = self.last_name
            user.module_profile=self.module_profile
            user.role_profile_name=self.role_profie
            user.insert(ignore_permissions=True)
            
            # frappe.get_doc(self.doctype, self.name).db_set('user_id', self.username)
            # self.user_id=self.username

            frappe.db.set_value("User Permission Request", self.name, "user_id", user.name)
            self.reload()
            
            frappe.msgprint(f"User has been created.")

    def validate(self):
        if self.task_id:
            existing = frappe.db.exists(
            "User Permission Request",
            {
                "task_id": self.task_id,
                "name": ["!=", self.name]
            }
        )

            if existing:
                frappe.throw(f"Task ID {self.task_id} is already used in another record")
        
@frappe.whitelist()
def update_employee(job_applicant, username):
    # if self.workflow_state == 'Update Employee':
        employee = frappe.get_all('Employee', filters={'job_applicant': job_applicant}, fields=['name'])

        if employee:
            emp_doc = frappe.get_doc('Employee', employee[0].name)
            emp_doc.user_id=username
            emp_doc.create_user_permission=0
            emp_doc.save(ignore_permissions=True)
            frappe.msgprint(f"user id updated")
        else:
            frappe.msgprint("No Employee found for Job Applicant.")
@frappe.whitelist()
def get_task_data(task_id):
    if not task_id:
        return frappe.throw("Task ID is required")

    activity = frappe.get_all(
        'Employee Boarding Activity',
        filters={'task': task_id},
        fields=['parent'],
        limit=1
    )

    if not activity:
        return frappe.throw("No onboarding task")

    onboarding = frappe.get_doc('Employee Onboarding', activity[0].parent)
    Job_applicant=frappe.get_doc('Job Applicant',onboarding.job_applicant)
    # job_title = Job_applicant.job_title
    location=onboarding.custom_branch
    # location = frappe.db.get_value('Job Opening', job_title, 'location')
    # first_name = onboarding.employee_name.split()[0]
    # last_name = onboarding.employee_name.split()[-1]
    
    employee = frappe.get_all(
    'Employee',
    filters={'job_applicant': onboarding.job_applicant},
    fields=['name','first_name','last_name','employee_name']
    # limit=1
)       
    # frappe.throw(f"{employee}")
    if not employee:
        frappe.throw("No Employee found for this Job Applicant.")
    employee_id = employee[0].name
    first_name=employee[0].first_name
    last_name=employee[0].last_name
    employee_name=employee[0].employee_name
    username = f"{first_name.lower()}_{last_name[0].lower()}@gkexport.com"
    employee_doc = frappe.get_doc('Employee', employee_id)
    
    department=onboarding.department if onboarding.department else Job_applicant.custom_department
    designation=onboarding.designation if onboarding.designation else Job_applicant.designation
    # employee_name=onboarding.employee_name if onboarding.employee_name else Job_applicant.applicant_name


    return {
        'job_applicant': onboarding.job_applicant,
        'employee_name': employee_name,
        'department': department,
        'designation': designation,
        'company': onboarding.company,
        'first_name': first_name,
        'last_name': last_name,
        'branch': location,
        'username': username,
        'employee':employee_id
        # 'operation':employee_doc.custom_operation

    }
