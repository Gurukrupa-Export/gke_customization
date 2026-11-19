# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from gke_customization.gke_hrms.report.pf_contribution_report.pf_contribution_report import (
    get_pf_data,
)

PF_WAGE_CEILING = 15000


def round_half_up(value):
    return math.floor(flt(value) + 0.5)


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")
    branch = filters.get("branch")

    conditions = []
    values = {"from_date": from_date, "to_date": to_date, "company": company}

    if branch:
        conditions.append("e.branch = %(branch)s")
        values["branch"] = branch

    condition_query = ""
    if conditions:
        condition_query = " AND " + " AND ".join(conditions)

    query = f"""
		SELECT
			ss.company AS company,
			ss.branch AS branch,
			ss.department AS department,
			ss.designation AS designation,
			ss.employee AS employee_id,
			ss.employee_name AS employee_name,
			ss.custom_gross_salary,
			ss.absent_days,
			e.date_of_birth,
			ss.payment_days,
			ss.total_working_days,

			/* Gross Pay counted once */
			MAX(ss.gross_pay) AS gross_pay,

			/* PF Amount:
			- If PF component exists → sum amount
			- If PF component NOT exists but _is_pf_applicable = 1 → 0
			*/
			COALESCE(
				SUM(
					CASE
						WHEN sd.salary_component = 'Provident Fund'
						THEN sd.amount
						ELSE 0
					END
				),
				0
			) AS pf_amount,

			/* EPF Wages */
			MAX(
				CASE
					WHEN sd.salary_component = 'Basic'
					THEN sd.amount
					ELSE 0
				END
			) AS epf_wages,

			/* Advance Refund */
			MAX(
				CASE
					WHEN sd.salary_component = 'Advance'
					THEN sd.amount
					ELSE 0
				END
			) AS refund_advance,

			e.gender AS gender

		FROM
			`tabSalary Slip` ss
		LEFT JOIN
			`tabSalary Detail` sd
				ON ss.name = sd.parent
		JOIN
			`tabEmployee` e
				ON ss.employee = e.name

		WHERE
			ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s
			AND ss._is_pf_applicable = 1
			AND ss.docstatus = 1

			{condition_query}
		GROUP BY ss.employee
	"""

    data = frappe.db.sql(query, values, as_dict=True)
    totals = get_total(data)
    data += totals

    return data


def get_total(data):
    totals = {
        "company": "Total",
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

    # Exclude Total row
    employee_data = [row for row in data if row.get("company") != "Total"]

    ac1_subscribers = len(employee_data)
    ac21_subscribers = len(employee_data)

    pf_totals = get_pf_data(filters)
    total_row = next((row for row in pf_totals if row.get("company") == "Total"), {})

    eps_wage_total = [row for row in pf_totals if row.get("company") != "Total"]

    employee_count = sum(1 for row in eps_wage_total if (row.get("eps_wage") or 0) > 0)

    ac10_subscribers = employee_count

    total_epf_amount = total_row.get("epf_wage", 0)
    total_eps_amount = total_row.get("eps_wage", 0)
    total_ee_share = total_row.get("ee_share")
    total_eps_contribution = total_row.get("eps_con")
    total_er_share = total_row.get("er_share", 0)

    ac1_wages = total_epf_amount
    ac10_wages = total_eps_amount
    ac21_wages = total_epf_amount

    ac_no_1_employee = total_ee_share
    ac_no_1_employer = total_er_share
    admin_charge = round_half_up((total_epf_amount * 0.5) / 100)
    ac_no_2 = admin_charge
    ac_no_10 = total_eps_contribution
    ac_no_21 = admin_charge
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
        "ac1": {"subscribers": ac1_subscribers, "wages": ac1_wages},
        "ac10": {"subscribers": ac10_subscribers, "wages": ac10_wages},
        "ac21": {"subscribers": ac21_subscribers, "wages": ac21_wages},
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
    columns = [
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Data", "width": 200},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 180},
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
    return columns


@frappe.whitelist()
def export_txt(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    data = get_data(filters)
    employee_details_map = get_employee_details_map(data)

    today_date = getdate(today())
    lines = []
    for row in data:
        # skip total row if present
        if row.get("company") == "Total":
            continue

        age = 0
        dob = row.get("date_of_birth")
        if dob:
            dob_date = getdate(dob)
            age = (
                today_date.year
                - dob_date.year
                - ((today_date.month, today_date.day) < (dob_date.month, dob_date.day))
            )

        if row.get("employee_id"):
            gross_pay = round_half_up(row.get("gross_pay") or 0)
            employee_details = employee_details_map.get(row["employee_id"], {})
            uan_number = employee_details.get("uan_number")
            name_as_per_aadhar = (
                (employee_details.get("name_as_per_aadhar") or "").strip().upper()
            )

            basic_ear = round_half_up(row.get("epf_wages") or 0)
            capped_wages = min(basic_ear, PF_WAGE_CEILING)

            epf_wages = capped_wages
            edli_wages = capped_wages
            eps_wages = 0 if age >= 58 else capped_wages

            if basic_ear < PF_WAGE_CEILING:
                epf_contribution = round_half_up(basic_ear * 0.12)
            else:
                epf_contribution = round_half_up(row.get("pf_amount") or 0)

            eps_contribution = 0 if age >= 58 else round_half_up(capped_wages * 0.0833)

            contribution = (epf_contribution - eps_contribution) or 0

            total_working_days = row.get("total_working_days") or 0
            payment_days = math.floor((row.get("payment_days") or 0) + 0.5)

            if row.get("absent_days"):
                ncp = round_half_up(row.get("absent_days") or 0)
            else:
                ncp = round_half_up(total_working_days - payment_days)

            refund_advance = row.get("refund_advance") or 0

            lines.append(
                f"{uan_number}#~#{name_as_per_aadhar}#~#{gross_pay}#~#{epf_wages}"
                f"#~#{eps_wages}#~#{edli_wages}#~#{epf_contribution}"
                f"#~#{eps_contribution}#~#{contribution}#~#{ncp}#~#{refund_advance}"
            )

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "pf_export.txt",
            "content": "\n".join(lines),
            "is_private": 1,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def get_employee_details_map(data):
    employee_ids = [row["employee_id"] for row in data if row.get("employee_id")]
    if not employee_ids:
        return {}

    employees = frappe.get_all(
        "Employee",
        filters={"name": ("in", employee_ids)},
        fields=["name", "uan_number", "name_as_per_aadhar"],
    )
    return {employee.name: employee for employee in employees}
