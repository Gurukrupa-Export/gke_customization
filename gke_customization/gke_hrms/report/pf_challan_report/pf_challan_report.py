# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Max, Sum
from frappe.utils import get_site_path

from gke_customization.gke_hrms.report.pf_contribution_report.pf_contribution_report import (
    get_pf_data,
)
from gke_customization.gke_hrms.report.pf_esic_utils import (
    get_age_in_years,
    get_employee_details_map,
)


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_salary_slip_rows(filters):
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_detail = frappe.qb.DocType("Salary Detail")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(salary_slip)
        .left_join(salary_detail)
        .on(salary_slip.name == salary_detail.parent)
        .join(employee)
        .on(salary_slip.employee == employee.name)
        .select(
            salary_slip.company.as_("company"),
            salary_slip.branch.as_("branch"),
            salary_slip.department.as_("department"),
            salary_slip.designation.as_("designation"),
            salary_slip.employee.as_("employee_id"),
            salary_slip.employee_name.as_("employee_name"),
            salary_slip.custom_gross_salary,
            salary_slip.absent_days,
            employee.date_of_birth,
            salary_slip.payment_days,
            salary_slip.total_working_days,
            Max(salary_slip.gross_pay).as_("gross_pay"),
            Coalesce(
                Sum(
                    Case()
                    .when(
                        salary_detail.salary_component == "Provident Fund",
                        salary_detail.amount,
                    )
                    .else_(0)
                ),
                0,
            ).as_("pf_amount"),
            Max(
                Case()
                .when(salary_detail.salary_component == "Basic", salary_detail.amount)
                .else_(0)
            ).as_("epf_wages"),
            Max(
                Case()
                .when(salary_detail.salary_component == "Advance", salary_detail.amount)
                .else_(0)
            ).as_("refund_advance"),
            employee.gender.as_("gender"),
        )
        .where(
            (salary_slip.docstatus < 2)
            & (salary_slip.company == filters.get("company"))
            & (salary_slip.start_date == filters.get("from_date"))
            & (salary_slip.end_date == filters.get("to_date"))
            & (salary_slip._is_pf_applicable == 1)
        )
        .groupby(salary_slip.employee)
    )

    if filters.get("branch"):
        query = query.where(employee.branch == filters.get("branch"))

    return query.run(as_dict=True)


def get_data(filters=None):
    data = get_salary_slip_rows(filters)
    data += get_total(data, filters.get("employee"), filters)
    return data


def get_total(data, employee=None, filters=None):
    totals = {
        "company": _("Total"),
        "branch": "",
        "employee_id": "",
        "employee_name": _("Employee Count: {0}").format(len(data)),
        "employee_count": len(data),
        "gross_pay": sum((row.get("gross_pay") or 0) for row in data),
        "pf_amount": sum((row.get("pf_amount") or 0) for row in data),
    }
    return [totals]


@frappe.whitelist()
def get_account_total_summary(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}

    data = get_data(filters)
    employee_data = [row for row in data if row.get("employee_id")]

    pf_data = get_pf_data(filters)
    pf_employee_rows = [row for row in pf_data if row.get("employee")]
    total_row = next((row for row in pf_data if not row.get("employee")), {})

    ac1_subscribers = len(employee_data)
    ac10_subscribers = sum(
        1 for row in pf_employee_rows if (row.get("eps_wage") or 0) > 0
    )
    ac21_subscribers = len(employee_data)

    total_epf_amount = total_row.get("epf_wage", 0)
    total_eps_amount = total_row.get("eps_wage", 0)
    total_ee_share = total_row.get("ee_share")
    total_eps_contribution = total_row.get("eps_con")
    total_er_share = total_row.get("er_share", 0)

    ac_no_1_employee = total_ee_share
    ac_no_1_employer = total_er_share
    ac_no_2 = round((total_epf_amount * 0.5) / 100)
    ac_no_10 = total_eps_contribution
    ac_no_21 = round((total_epf_amount * 0.5) / 100)
    ac_no_22 = 0

    total_amount = (
        (ac_no_1_employee or 0)
        + (ac_no_1_employer or 0)
        + (ac_no_2 or 0)
        + (ac_no_10 or 0)
        + (ac_no_21 or 0)
        + (ac_no_22 or 0)
    )

    return {
        "ac1": {"subscribers": ac1_subscribers, "wages": total_epf_amount},
        "ac10": {"subscribers": ac10_subscribers, "wages": total_eps_amount},
        "ac21": {"subscribers": ac21_subscribers, "wages": total_epf_amount},
        "contribution": {
            "ac_no_1_employee": ac_no_1_employee,
            "ac_no_1_employer": ac_no_1_employer,
            "ac_no_2": ac_no_2,
            "ac_no_10": ac_no_10,
            "ac_no_21": ac_no_21,
            "ac_no_22": ac_no_22,
        },
        "grand_total": total_amount,
        "employee_count": len(employee_data),
        "gross_pay": sum((row.get("gross_pay") or 0) for row in data),
        "pf_amount": sum((row.get("pf_amount") or 0) for row in data),
    }


def get_columns(filters=None):
    return [
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee_id",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Gross Pay"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 200,
        },
        {
            "label": _("PF Amount"),
            "fieldname": "pf_amount",
            "fieldtype": "Currency",
            "width": 200,
        },
    ]


@frappe.whitelist()
def export_txt(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    rows = [row for row in get_salary_slip_rows(filters) if row.get("employee_id")]
    employee_details = get_employee_details_map(
        [row.get("employee_id") for row in rows], ["uan_number", "name_as_per_aadhar"]
    )

    lines = []
    for row in rows:
        employee = employee_details.get(row.get("employee_id")) or {}
        uan_number = employee.get("uan_number")
        name_as_per_aadhar = (employee.get("name_as_per_aadhar") or "").strip().upper()

        age = get_age_in_years(row.get("date_of_birth"))
        gross_pay = round(row.get("gross_pay") or 0)
        basic_ear = round(row.get("epf_wages") or 0)

        epf_wages = min(basic_ear, 15000)
        edli_wages = min(basic_ear, 15000)
        eps_wages = 0 if age >= 58 else epf_wages

        if basic_ear < 15000:
            epf_contribution = round(basic_ear * 0.12)
            eps_contribution = 0 if age >= 58 else round(basic_ear * 0.0833)
        else:
            epf_contribution = round(row.get("pf_amount") or 0)
            eps_contribution = 0 if age >= 58 else round(15000 * 0.0833)

        contribution = (epf_contribution - eps_contribution) or 0

        total_working_days = row.get("total_working_days") or 0
        payment_days = math.floor((row.get("payment_days") or 0) + 0.5)
        if row.get("absent_days"):
            ncp = round(row.get("absent_days") or 0)
        else:
            ncp = round(total_working_days - payment_days)

        refund_advance = row.get("refund_advance") or 0

        lines.append(
            f"{uan_number}#~#{name_as_per_aadhar}#~#{gross_pay}#~#{epf_wages}"
            f"#~#{eps_wages}#~#{edli_wages}#~#{epf_contribution}"
            f"#~#{eps_contribution}#~#{contribution}#~#{ncp}#~#{refund_advance}"
        )

    file_name = "pf_export.txt"
    file_path = get_site_path("public", "files", file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return f"/files/{file_name}"
