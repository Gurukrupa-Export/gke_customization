# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Max, Sum
from frappe.utils import get_site_path
from openpyxl import Workbook

from gke_customization.gke_hrms.report.pf_esic_utils import (
    get_age_in_years,
    get_employee_details_map,
    get_latest_employee_promotions,
)

ESIC_COMPONENT = "Employees State Insurance Corporation"


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def apply_conditions(query, salary_slip, employee, filters):
    query = query.where(
        (salary_slip.docstatus < 2)
        & (salary_slip.company == filters.get("company"))
        & (salary_slip.start_date == filters.get("from_date"))
        & (salary_slip.end_date == filters.get("to_date"))
    )

    if filters.get("branch"):
        query = query.where(employee.branch == filters.get("branch"))

    return query


def get_salary_slip_rows(filters):
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_detail = frappe.qb.DocType("Salary Detail")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(salary_slip)
        .join(salary_detail)
        .on(salary_slip.name == salary_detail.parent)
        .join(employee)
        .on(salary_slip.employee == employee.employee)
        .select(
            salary_slip.company.as_("company"),
            salary_slip.branch.as_("branch"),
            salary_slip.department.as_("department"),
            salary_slip.designation.as_("designation"),
            salary_slip.employee.as_("employee_id"),
            salary_slip.employee_name.as_("employee_name"),
            Max(salary_slip.gross_pay).as_("gross_pay"),
            Max(salary_slip.net_pay).as_("net_pay"),
            salary_detail.amount.as_("esic_amount"),
            salary_slip.payment_days.as_("present_days"),
            salary_slip.absent_days,
            salary_slip.custom_gross_salary.as_("ctc"),
            salary_slip.total_working_days,
            salary_slip.leave_without_pay.as_("leave_days"),
            salary_slip.custom_month,
            employee.status,
            employee.relieving_date,
            employee.date_of_birth,
        )
        .where(salary_detail.salary_component == ESIC_COMPONENT)
        .groupby(salary_slip.employee)
    )
    query = apply_conditions(query, salary_slip, employee, filters)

    return query.run(as_dict=True)


def get_data(filters=None):
    data = get_salary_slip_rows(filters)
    data += get_totals(data, filters.get("employee"), filters)
    return data


def get_totals(data, employee=None, filters=None):
    totals = {
        "company": "",
        "branch": _("Total"),
        "employee_id": "",
        "employee_name": _("Employee Count: {0}").format(len(data)),
        "employee_count": len(data),
        "gross_pay": sum((row.get("gross_pay") or 0) for row in data),
        "esic_amount": sum((row.get("esic_amount") or 0) for row in data),
    }

    blank_row = {
        "company": "",
        "branch": "",
        "employee_id": "",
        "employee_name": "",
        "gross_pay": None,
        "esic_amount": None,
    }

    esic = get_esic_total(filters)[0]

    employer_contribution = 0
    if esic.get("employee_cont"):
        employer_contribution = round(esic.get("employee_cont") * 433.33 / 100)

    def summary_row(branch, employee_id, employee_name, gross_pay):
        return {
            "company": "",
            "branch": branch,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "gross_pay": gross_pay,
            "esic_amount": None,
        }

    return [
        totals,
        blank_row,
        blank_row,
        summary_row(
            _("Total Employees"),
            esic.get("total_emp"),
            _("Total Gross"),
            esic.get("total_gross"),
        ),
        summary_row(
            _("Excepted Employees"),
            esic.get("excepted_emp"),
            _("Excepted Gross"),
            esic.get("excepted_gross"),
        ),
        summary_row(
            _("ESIC Members"),
            esic.get("esic_member"),
            _("ESIC Wages"),
            esic.get("esic_wages"),
        ),
        summary_row("", "", _("Employee Contribution"), esic.get("employee_cont")),
        summary_row("", "", _("Employer Contribution"), employer_contribution),
        summary_row(
            "",
            "",
            _("Total Contribution"),
            (esic.get("employee_cont") or 0) + employer_contribution,
        ),
    ]


def get_esic_total(filters=None):
    salary_slip = frappe.qb.DocType("Salary Slip")
    esic = frappe.qb.DocType("Salary Detail")
    employee = frappe.qb.DocType("Employee")

    is_esic_exempted = (esic.amount == 0) | esic.amount.isnull()
    is_esic_member = esic.amount > 0

    query = (
        frappe.qb.from_(salary_slip)
        .left_join(esic)
        .on(
            (salary_slip.name == esic.parent)
            & (esic.salary_component == ESIC_COMPONENT)
        )
        .join(employee)
        .on(salary_slip.employee == employee.employee)
        .select(
            Count(salary_slip.employee).distinct().as_("total_emp"),
            Sum(salary_slip.gross_pay).as_("total_gross"),
            Count(Case().when(is_esic_exempted, salary_slip.employee))
            .distinct()
            .as_("excepted_emp"),
            Sum(Case().when(is_esic_exempted, salary_slip.gross_pay).else_(0)).as_(
                "excepted_gross"
            ),
            Count(Case().when(is_esic_member, salary_slip.employee))
            .distinct()
            .as_("esic_member"),
            Sum(Case().when(is_esic_member, salary_slip.gross_pay).else_(0)).as_(
                "esic_wages"
            ),
            Sum(Case().when(is_esic_member, esic.amount).else_(0)).as_("employee_cont"),
        )
    )
    query = apply_conditions(query, salary_slip, employee, filters)

    return query.run(as_dict=True)


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
            "width": 200,
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
            "width": 200,
        },
        {
            "label": _("Gross Pay"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 120,
            "default": "",
        },
        {
            "label": _("ESIC Amount"),
            "fieldname": "esic_amount",
            "fieldtype": "Currency",
            "width": 120,
        },
    ]


def get_reason_code(row, age, promotion):
    """Return (reason_code, last_working_day) for the ESIC monthly contribution upload."""
    relieving_date = row.get("relieving_date")
    last_working_day = ""

    if row.get("present_days") == 0:
        return 1, last_working_day

    if row.get("status") == "Left" or (
        row.get("status") == "Inactive" and relieving_date
    ):
        if (row.get("present_days") or 0) > 1 and relieving_date:
            last_working_day = relieving_date.strftime("%d-%m-%Y")
        return 2, last_working_day

    if relieving_date and age > 58:
        return 3, relieving_date.strftime("%d-%m-%Y")

    if row.get("custom_month") in [4, 10] and promotion:
        promotion_date = promotion.get("promotion_date")
        current_ctc = promotion.get("current_ctc")
        revised_ctc = promotion.get("revised_ctc")
        if (
            promotion_date
            and promotion_date.month == row.get("custom_month")
            and current_ctc
            and revised_ctc
            and revised_ctc > current_ctc
            and revised_ctc >= 21000
        ):
            return 4, last_working_day

    return 0, last_working_day


@frappe.whitelist()
def export_txt(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    rows = get_salary_slip_rows(filters)
    employee_ids = [row.get("employee_id") for row in rows]
    employee_details = get_employee_details_map(
        employee_ids, ["_esic_number", "name_as_per_aadhar"]
    )
    promotions = get_latest_employee_promotions(
        [row.get("employee_id") for row in rows if row.get("custom_month") in [4, 10]],
        filters.get("from_date"),
        filters.get("to_date"),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "ESIC Report"
    ws.append(
        [
            "IP Number \n (10 Digits)",
            "IP Name IP Name \n (Only alphabets and space)",
            "No of Days for which wages paid/payable during the month",
            "Total Monthly Wages",
            "Reason Code",
            "Last Working Day \n (Format DD/MM/YYYY  or DD-MM-YYYY)",
        ]
    )

    for row in rows:
        employee = employee_details.get(row.get("employee_id")) or {}
        age = get_age_in_years(row.get("date_of_birth"))
        reason_code, last_working_day = get_reason_code(
            row, age, promotions.get(row.get("employee_id"))
        )

        ws.append(
            [
                employee.get("_esic_number"),
                employee.get("name_as_per_aadhar"),
                round(row.get("present_days") or 0),
                round(row.get("gross_pay") or 0),
                reason_code,
                last_working_day,
            ]
        )

    file_name = "esic_export.xlsx"
    wb.save(get_site_path("public", "files", file_name))

    return f"/files/{file_name}"
