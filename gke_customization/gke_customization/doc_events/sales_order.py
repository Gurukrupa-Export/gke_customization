import frappe
import json

def validate(self,method=None):
    if self.company == 'Sadguru Diamond':
        for row in self.items:
            if not row.batch_no and not row.diamond_grade:
                frappe.throw("Batch no and Diamond grade are mandatory")
            elif not row.batch_no:
                frappe.throw("Batch no is mandatory")
            elif not row.diamond_grade:
                frappe.throw("Diamond grade is mandatory")

    if self.customer == 'MHCU0022':
        self.shipping_address_name = 'Gurukrupa Export Private Limited - Surat Factory-Billing'
