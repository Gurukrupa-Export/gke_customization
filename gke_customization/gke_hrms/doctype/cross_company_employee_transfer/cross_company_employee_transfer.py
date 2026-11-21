# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class CrossCompanyEmployeeTransfer(Document):
    def validate(self):
        pass

    def before_submit(self):
        pass

    def on_submit(self):
        if not self.create_new_employee_id:
            frappe.throw(_("Check Create New Employee ID box first"))

        if not self.target_site:
            frappe.throw(_("Add Target Site first"))

        employee = frappe.get_doc("Employee", self.employee)

        new_employee = frappe.copy_doc(employee)

        new_employee.name = None
        new_employee.employee_number = None

        payload = new_employee.as_dict()

        payload["company"] = self.new_company
        # -------------------------
        # Remove system fields
        # -------------------------
        remove_fields = [
            "name",
            "employee",
            "creation",
            "modified",
            "modified_by",
            "owner",
            "user_id",
            "reports_to",
            "holiday_list",
            "custom_state",
            "expense_approver",
            "leave_approver",
            "shift_request_approver",
            "branch",
            "manufacturer",
            "custom_operation",
            "designation" "default_shift",
            "department" "docstatus",
            "idx",
            "lft",
            "rgt",
            "_user_tags",
            "_comments",
            "_assign",
            "_liked_by",
        ]

        for field in remove_fields:
            payload.pop(field, None)

        # -------------------------
        # Remove child tables (first test without them)
        # -------------------------
        child_tables = [
            "education",
            "custom_employee_languages",
            "custom_employees_hobbies",
            "employee_family_background",
            "employee_relative_deails",
            "emergency_contact_details_table",
            "external_work_history",
            "internal_work_history",
        ]

        # -------------------------
        # Apply transfer changes
        # -------------------------
        field_map = {
            "Department": "department",  # ✅ fixed
            "Designation": "designation",  # ✅ fixed
            "Reports to": "reports_to",
            "Default Shift": "default_shift",  # ✅ fixed
            "Leave Approver": "leave_approver",
            "Expense Approver": "expense_approver",
            "Shift Request Approver": "shift_request_approver",
            "Holiday List": "holiday_list",
        }

        for table in child_tables:
            payload.pop(table, None)

        for row in self.transfer_details:
            if not row.property or not row.new:
                continue

            fieldname = field_map.get(row.property)

            if not fieldname:
                continue

            fieldname = field_map.get(row.property)

            if not fieldname:
                continue

            # Only Reports To / Employee fields
            if fieldname == "reports_to":
                if not row.new_value:
                    frappe.throw(
                        _("Actual value missing for {0}: {1}").format(
                            row.property, row.new
                        )
                    )
                payload[fieldname] = row.new_value

            else:
                payload[fieldname] = row.new

        payload["date_of_joining"] = self.transfer_date

        payload["attendance_device_id"] = self.attendance_device_id

        payload["doctype"] = "Employee"

        payload = frappe.parse_json(frappe.as_json(payload))

        try:
            response = requests.post(
                f"{self.target_site}/api/method/create_transfer_employee",
                json={"employee_data": payload},
                timeout=60,
            )

            response_data = response.json()

            if response_data.get("message") and response_data["message"].get(
                "employee"
            ):
                self.new_employee_id = response_data["message"]["employee"]
                self.db_set("new_employee_id", response_data["message"]["employee"])

                return response_data["message"]["employee"]

            else:
                import json

                frappe.throw(
                    _("Employee creation failed in {0}").format(self.new_company)
                    + "\n\n"
                    + "\n".join(
                        json.loads(msg)["message"]
                        for msg in json.loads(
                            response_data.get("_server_messages", "[]")
                        )
                    )
                )

        except Exception as e:
            frappe.log_error(title="Create Transfer Employee Error", message=str(e))
            raise

    def autoname(self):
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        if company_abbr:
            series = f"{company_abbr}-CSE-TRN-.#####"
            self.name = frappe.model.naming.make_autoname(series)


@frappe.whitelist(allow_guest=True)
def get_kggk_data(target_site=None, property=None, new_company=None):
    if not target_site:
        frappe.throw(_("Target Site is required"))

    target_site = str(target_site).rstrip("/")

    response = requests.get(
        f"{target_site}/api/method/get_dept_desi_reprt_leave_apr",
        params={"new_company": new_company},
        timeout=30,
    )

    return response.json()
