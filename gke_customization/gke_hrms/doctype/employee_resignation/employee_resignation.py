# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_days, getdate


class EmployeeResignation(Document):
    def validate(self):
        # 16-06-2026
        self.validate_duplicate_resignation()  # shubham
        if (
            self.workflow_state == "Send to Manager"
            and self.reporting_manager_approval == "Approved"
            and self.date_resignation
        ):
            resignation_date = getdate(self.date_resignation)

            notice_days = int(self.notice_period or 0)

            if self.waive_off_notice_period == "Yes":
                reduced_days = int(self.reduce_notice_day or 0)
                notice_days = max(0, notice_days - reduced_days)

                if self.requested_relieving_date:
                    self.last_working_day = getdate(self.requested_relieving_date)
            else:
                self.last_working_day = add_days(resignation_date, notice_days)

        conf_date = frappe.db.get_value(
            "Employee", {"name": self.employee}, ["final_confirmation_date"]
        )
        if conf_date:
            self.is_employee_on_probation = "Yes"
        else:
            self.is_employee_on_probation = "No"

    def validate_duplicate_resignation(self):  # shubham
        existing = frappe.db.exists(
            "Employee Resignation",
            {
                "employee": self.employee,
                "docstatus": ["!=", 2],
                "workflow_state": ["not in", ["Rejected"]],
                "name": ["!=", self.name],
            },
        )

        if existing:
            frappe.throw(
                ("Employee Resignation already exists for Employee {0}").format(
                    self.employee
                )
            )


@frappe.whitelist()
def create_employee_resignation(source_name, target_doc=None):
    doc = frappe.get_doc("Employee Resignation", source_name)

    doc = get_mapped_doc(
        "Employee Resignation",
        source_name,
        {
            "Employee Resignation": {
                "doctype": "Employee Separation",
                "field_map": {
                    "employee": "employee",
                    "department": "department",
                    "company": "company",
                    "designation": "designation",
                    "resignation_letter_date": "date_resignation",
                    "last_working_day": "boarding_begins_on",
                },
            }
        },
        target_doc,
    )
    return doc
