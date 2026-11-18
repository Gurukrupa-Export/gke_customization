# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.model.workflow import apply_workflow

@frappe.whitelist()
def check_bonus_overlap(from_date, to_date, employees, name=None):
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    employees = frappe.parse_json(employees)

    overlapping_bonus = frappe.db.sql("""
        SELECT b.name, bd.employee
        FROM `tabBonus` b
        JOIN `tabBonus Details` bd ON bd.parent = b.name
        WHERE b.docstatus != 2 
        AND b.from_date <= %s
        AND b.to_date >= %s
    """, (to_date, from_date), as_dict=True)

    # remove current document employees while editing
    if name:
        overlapping_bonus = [d for d in overlapping_bonus if d.name != name]

    overlapping_employees = list({
        d.employee for d in overlapping_bonus if d.employee in employees
    })
    return overlapping_employees

@frappe.whitelist()
def employee_salary(employee, from_date, to_date, wage_eligibility_limit):
    salary = frappe.db.sql("""
        SELECT 
            sd.amount,
            ss.start_date
        FROM 
            `tabSalary Slip` ss
        LEFT JOIN
            `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE
            sd.salary_component = "Basic"
            AND ss.employee = %s
            AND ss.start_date BETWEEN %s AND %s
            AND sd.default_amount < %s
    """, (employee, from_date, to_date, wage_eligibility_limit), as_dict=True)

    return salary

@frappe.whitelist()
def release_hold_bonus(docname, row_names):
    row_names = frappe.parse_json(row_names)
    doc = frappe.get_doc("Bonus", docname)

    # Remove hold from selected rows
    for row in doc.bonus_details:
        if row.name in row_names:
            row.hold_bonus = 0
            # row.jv = 1

    # ✅ Check if any row is still on hold
    any_hold = any(row.hold_bonus for row in doc.bonus_details)

    # ✅ Set status based on condition
    if any_hold:
        doc.status = "Hold"
    else:
        doc.status = "Completed"

    doc.save(ignore_permissions=True)

    # ✅ If all released → trigger workflow / submit
    if not any_hold:
        # Option 1: Workflow (Recommended)
        apply_workflow(doc, "Approve")

        # Option 2 (if no workflow):
        # if doc.docstatus == 0:
        #     doc.submit()

    return "Success"


class Bonus(Document):
    def on_cancel(self):
        je_list = frappe.get_all("Journal Entry Account",
            filters={
                "reference_type": "Bonus",
                "reference_name": self.name
            },
            pluck="parent"
        )
        for je in set(je_list):
            je_doc = frappe.get_doc("Journal Entry", je)
            if je_doc.docstatus == 1:
                je_doc.cancel()

        self.ignore_linked_doctypes = ("GL Entry")

    def before_save(self):
        self.status = "Hold" if any(emp.hold_bonus for emp in self.bonus_details) else "Completed"



