# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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


def get_conditions(filters):
    values = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
        "company": filters.get("company"),
        "esic_component": ESIC_COMPONENT,
    }

    condition_query = ""
    if filters.get("branch"):
        condition_query = "AND e.branch = %(branch)s"
        values["branch"] = filters.get("branch")

    return condition_query, values


def get_salary_slip_rows(filters):
    condition_query, values = get_conditions(filters)

    return frappe.db.sql(
        f"""
		SELECT
			ss.company AS company,
			ss.branch AS branch,
			ss.department AS department,
			ss.designation AS designation,
			ss.employee AS employee_id,
			ss.employee_name AS employee_name,
			MAX(ss.gross_pay) AS gross_pay,
			MAX(ss.net_pay) AS net_pay,
			sd.amount AS esic_amount,
			ss.payment_days as present_days,
			ss.absent_days,
			ss.custom_gross_salary as ctc,
			ss.total_working_days,
			ss.leave_without_pay as leave_days,
			ss.custom_month,
			e.status,
			e.relieving_date,
			e.date_of_birth
		FROM
			`tabSalary Slip` AS ss
		JOIN
			`tabSalary Detail` AS sd ON ss.name = sd.parent
		JOIN
			`tabEmployee` AS e ON ss.employee = e.employee
		WHERE
			sd.salary_component = %(esic_component)s
			AND ss.docstatus = 1
			AND ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s
			{condition_query}
		GROUP BY
			ss.employee
		""",
        values,
        as_dict=True,
    )


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
    condition_query, values = get_conditions(filters)

    return frappe.db.sql(
        f"""
		SELECT
			COUNT(DISTINCT ss.employee) AS total_emp,
			SUM(ss.gross_pay) AS total_gross,

			COUNT(DISTINCT CASE WHEN esic.amount = 0 OR esic.amount IS NULL THEN ss.employee END) AS excepted_emp,
			SUM(CASE WHEN esic.amount = 0 OR esic.amount IS NULL THEN ss.gross_pay ELSE 0 END) AS excepted_gross,

			COUNT(DISTINCT CASE WHEN esic.amount > 0 THEN ss.employee END) AS esic_member,
			SUM(CASE WHEN esic.amount > 0 THEN ss.gross_pay ELSE 0 END) AS esic_wages,

			SUM(CASE WHEN esic.amount > 0 THEN esic.amount ELSE 0 END) AS employee_cont
		FROM
			`tabSalary Slip` AS ss
		LEFT JOIN
			`tabSalary Detail` AS esic ON ss.name = esic.parent
			AND esic.salary_component = %(esic_component)s
		JOIN
			`tabEmployee` AS e ON ss.employee = e.employee
		WHERE
			ss.docstatus = 1
			AND ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s
			{condition_query}
		""",
        values,
        as_dict=True,
    )


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
