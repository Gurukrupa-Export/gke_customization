# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class InactivePayroll(Document):
    def autoname(self):
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        if not company_abbr:
            frappe.throw(
                _("Please set an Abbreviation for Company {0}").format(self.company)
            )

        prefix = f"{company_abbr}-IAP-"
        self.name = frappe.model.naming.make_autoname(prefix)


def get_relieved_employees(doc):
    if not doc.from_date or not doc.to_date:
        frappe.throw(_("Please set both From Date and To Date."))

    relieving_date_limit = doc.to_date + timedelta(days=7)
    return frappe.get_all(
        "Employee",
        filters={
            "status": ["in", ["Left", "Inactive"]],
            "relieving_date": ["between", [doc.from_date, relieving_date_limit]],
            "company": doc.company,
            "branch": doc.branch,
        },
        fields=[
            "name",
            "employee_name",
            "department",
            "designation",
            "company",
            "branch",
        ],
    )


def set_employee_rows(doc, employees):
    doc.employee = []
    for emp in employees:
        doc.append(
            "employee",
            {
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "designation": emp.designation,
                "company": emp.company,
                "branch": emp.branch,
            },
        )
    doc.save()


@frappe.whitelist()
def get_inactive_employees(docname):
    doc = frappe.get_doc("Inactive Payroll", docname)
    set_employee_rows(doc, get_relieved_employees(doc))
    return _("Employees fetched successfully.")


@frappe.whitelist()
def get_inactive_employees_list(docname):
    doc = frappe.get_doc("Inactive Payroll", docname)
    inactive_employees = get_relieved_employees(doc)

    employees_with_attendance = set()
    if inactive_employees:
        employees_with_attendance = set(
            frappe.get_list(
                "Attendance",
                filters={
                    "employee": ["in", [emp.name for emp in inactive_employees]],
                    "attendance_date": ["between", [doc.from_date, doc.to_date]],
                },
                pluck="employee",
            )
        )

    set_employee_rows(
        doc,
        [emp for emp in inactive_employees if emp.name in employees_with_attendance],
    )
    return _("Employees fetched successfully.....")


@frappe.whitelist()
def activate_employees(docname):
    doc = frappe.get_doc("Inactive Payroll", docname)
    employee_names = [row.employee for row in doc.employee if row.employee]
    inactive_employee_names = []
    if employee_names:
        inactive_employee_names = frappe.get_all(
            "Employee",
            filters={
                "name": ["in", employee_names],
                "status": ["in", ["Inactive", "Left"]],
            },
            pluck="name",
        )

    count = 0
    for employee_name in inactive_employee_names:
        emp = frappe.get_doc("Employee", employee_name)
        emp.db_set("status", "Active")
        emp.save()
        count += 1

    return _("{0} employees marked as Active.").format(count)


@frappe.whitelist()
def create_payroll_entries(docname):
    doc = frappe.get_doc("Inactive Payroll", docname)
    if not doc.employee:
        frappe.throw(_("No employees found in the Inactive Payroll record."))
    first_row = doc.employee[0]

    payroll_doc = frappe.new_doc("Payroll Entry")
    payroll_doc.employee = first_row.employee
    payroll_doc.posting_date = getdate()
    payroll_doc.payroll_frequency = "Monthly"
    payroll_doc.company = first_row.company
    payroll_doc.branch = first_row.branch
    payroll_payable_account, cost_center = frappe.get_cached_value(
        "Company", first_row.company, ["default_payroll_payable_account", "cost_center"]
    )
    payroll_doc.payroll_payable_account = payroll_payable_account
    payroll_doc.cost_center = cost_center
    payroll_doc.start_date = doc.from_date

    payroll_doc.end_date = doc.to_date
    payroll_doc.status = "Draft"
    payroll_doc.exchange_rate = 1

    payroll_doc.insert()
    frappe.msgprint(_("Payroll Entry Created"))
    return payroll_doc.name
