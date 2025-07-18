# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class EmployeeBRecord(Document):
	def before_save(self):
		set_data(self)
		calculate_bond_amount(self)

def get_salary_slip(employee):
	salary_slip = frappe.db.sql(f"""
		select name,start_date,payment_days,net_pay,total_working_days,custom_month ,custom_extra_payment_days
		    from `tabSalary Slip` 
			where employee = '{employee}' and docstatus = 1 
	""",as_dict=1)
	
	return salary_slip

def set_data(self):
    salary_slip = get_salary_slip(self.employee)  
    bond_amount = float(self.bond_amount) if self.bond_amount else 0  

    if isinstance(self.bond_end_date, str):
        bond_end_date = datetime.strptime(self.bond_end_date, "%Y-%m-%d").date()
    else:
        bond_end_date = self.bond_end_date 
	
    if salary_slip:
        for row in salary_slip:
            slip_date = row['start_date'] 

            if slip_date >= bond_end_date:
                total_working_days = int(row['total_working_days']) if row['total_working_days'] else 1  
                bond_value = (bond_amount / total_working_days) * row['payment_days']  
                rounded_bond_value = round(bond_value, 2)  

                total_pay_days = row['payment_days'] + row['custom_extra_payment_days']
                self.append("employee_b_record_details", {
                    "salary_slip": row["name"],
                    "date": row["start_date"],
                    "net_days": total_pay_days,
                    "net_pay_inr": row['net_pay'],
                    "working_days": total_working_days,
                    "bond_amount": rounded_bond_value,  
                })
            else:
                frappe.msgprint(_("Salary not created for this Employee"))
				

def calculate_bond_amount(self):
	total_bond_amount = 0
	for i in self.employee_b_record_details:
		total_bond_amount += i.bond_amount
	self.summary_amount = total_bond_amount