# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class MonthlyAttendanceResigter(Document):
    def autoname(self):
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        if company_abbr:
            if self.branch:
                branch_parts = self.branch.split("-")
                branch_short = branch_parts[-2] if len(branch_parts) > 1 else self.branch
                series = f"HR-{company_abbr}-{branch_short}-MAR-.#####"
            else:
                series = f"HR-{company_abbr}-MAR-.#####"

            self.name = frappe.model.naming.make_autoname(series)


@frappe.whitelist()
def get_attendance_data(company, from_date, to_date, branch=None):
    payroll_entry = frappe.db.exists(
        "Payroll Entry",
        {
            "company": company,
            "branch": branch,
            "start_date": from_date,
            "end_date": to_date,
            "docstatus": 1,
        },
    )
    has_salary_slips = payroll_entry and frappe.db.exists(
        "Salary Slip",
        {"company": company, "payroll_entry": payroll_entry, "docstatus": 1},
    )

    if not has_salary_slips:
        frappe.throw(_("No submitted Salary Slip found for this Payroll Period."))

    return fetch_attendance_from_api(company, from_date, to_date)


@frappe.whitelist()
def get_attendance_data_btn(company, from_date, to_date):
    return fetch_attendance_from_api(company, from_date, to_date)


def fetch_attendance_from_api(company, from_date, to_date):
    url = "http://3.108.219.130:7000/attendance"

    params = {"company": company, "from_att_date": from_date, "to_att_date": to_date}

    try:
        response = requests.get(url, params=params, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        frappe.throw(_("Error fetching API: {0}").format(e))
