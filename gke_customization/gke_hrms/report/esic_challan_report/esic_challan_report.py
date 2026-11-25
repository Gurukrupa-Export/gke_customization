# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

from io import BytesIO

import frappe
from frappe import _
from frappe.utils import getdate, today
from openpyxl import Workbook


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
			MAX(ss.gross_pay) AS gross_pay,
			MAX(ss.net_pay) AS net_pay,
			SUM(sd.amount) AS esic_amount,
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
    		sd.salary_component = 'Employees State Insurance Corporation'
			AND ss.docstatus = 1
			AND ss.company = %(company)s
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s

			{condition_query}
		GROUP BY
			ss.employee
	"""

    data = frappe.db.sql(query, values, as_dict=True)
    totals = get_totals(data, filters)
    data += totals

    return data


def get_totals(data, filters=None):
    totals = {
        "company": "",
        "branch": "Total",
        "employee_id": "",
        "employee_name": _("Employee Count: {0}").format(len(data)),
        "employee_count": len(data),
        "gross_pay": sum((row.get("gross_pay") or 0) for row in data),
        "esic_amount": sum((row.get("esic_amount") or 0) for row in data),
    }

    total1 = {
        "company": "",
        "branch": "",
        "employee_id": "",
        "employee_name": "",
        "gross_pay": None,
        "esic_amount": None,
    }
    esic = get_esic_total(filters)
    esic_total = {
        "company": "",
        "branch": "Total Employees",
        "employee_id": esic[0].get("total_emp"),
        "employee_name": "Total Gross",
        "gross_pay": esic[0].get("total_gross"),
        "esic_amount": None,
    }

    esic_total1 = {
        "company": "",
        "branch": "Excepted Employees",
        "employee_id": esic[0].get("excepted_emp"),
        "employee_name": "Excepted Gross",
        "gross_pay": esic[0].get("excepted_gross"),
        "esic_amount": None,
    }

    esic_total2 = {
        "company": "",
        "branch": "ESIC Members",
        "employee_id": esic[0].get("esic_member"),
        "employee_name": "ESIC Wages",
        "gross_pay": esic[0].get("esic_wages"),
        "esic_amount": None,
    }
    esic_total3 = {
        "company": "",
        "branch": "",
        "employee_id": "",
        "employee_name": "Employee Contribution",
        "gross_pay": esic[0].get("employee_cont"),
        "esic_amount": None,
    }
    employer_contribution = 0
    if esic[0].get("employee_cont"):
        employer_contribution = round(esic[0].get("employee_cont") * 433.33 / 100)

    esic_total4 = {
        "company": "",
        "branch": "",
        "employee_id": "",
        "employee_name": "Employer Contribution",
        "gross_pay": employer_contribution,
        "esic_amount": None,
    }
    esic_total5 = {
        "company": "",
        "branch": "",
        "employee_id": "",
        "employee_name": "Total Contribution",
        "gross_pay": (esic[0].get("employee_cont") or 0) + employer_contribution,
        "esic_amount": None,
    }

    return [
        totals,
        total1,
        total1,
        esic_total,
        esic_total1,
        esic_total2,
        esic_total3,
        esic_total4,
        esic_total5,
    ]


def get_esic_total(filters=None):
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
			AND esic.salary_component = 'Employees State Insurance Corporation'
		JOIN
    		`tabEmployee` AS e ON ss.employee = e.employee
		WHERE
   			ss.company = %(company)s
			AND ss.docstatus = 1
			AND ss.start_date = %(from_date)s
			AND ss.end_date = %(to_date)s
			{condition_query}
	"""
    data = frappe.db.sql(query, values, as_dict=True)

    return data


def get_columns(filters=None):
    columns = [
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
    return columns


@frappe.whitelist()
def export_txt(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    data = get_data(filters)
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Create workbook & sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "ESIC Report"

    # Column Headers
    headers = [
        "IP Number \n (10 Digits)",
        "IP Name IP Name \n (Only alphabets and space)",
        "No of Days for which wages paid/payable during the month",
        "Total Monthly Wages",
        "Reason Code",
        "Last Working Day \n (Format DD/MM/YYYY  or DD-MM-YYYY)",
    ]

    ws.append(headers)

    # Summary rows appended by get_totals have no company
    data = [row for row in data if row.get("company")]
    employee_details_map = get_employee_details_map(data)
    promotion_map = get_promotion_map(data, from_date, to_date)
    today_date = getdate(today())

    for row in data:
        employee_details = employee_details_map.get(row.get("employee_id"), {})
        esic_number = employee_details.get("_esic_number")
        emp_name = employee_details.get("name_as_per_aadhar")
        dob = row.get("date_of_birth")
        age = 0
        if dob:
            dob_date = getdate(dob)
            age = (
                today_date.year
                - dob_date.year
                - ((today_date.month, today_date.day) < (dob_date.month, dob_date.day))
            )

        code = 0  # Reason Code
        date = ""
        if row.get("present_days") == 0:
            code = 1
        elif row.get("status") == "Left" or (
            row.get("status") == "Inactive" and row.get("relieving_date")
        ):
            if (row.get("present_days") or 0) > 1 and row.get("relieving_date"):
                code = 2
                date = row.get("relieving_date").strftime("%d-%m-%Y")
            else:
                code = 2
        elif row.get("relieving_date") and age > 58:
            code = 3
            date = row.get("relieving_date").strftime("%d-%m-%Y")
        elif row.get("custom_month") in [4, 10]:
            if row.get("employee_id"):
                emp_promotion = promotion_map.get(row.get("employee_id"))
                if emp_promotion:
                    promotion_date = emp_promotion.get("promotion_date")
                    if promotion_date and promotion_date.month == row.get(
                        "custom_month"
                    ):
                        if (
                            promotion_date
                            and emp_promotion.get("current_ctc")
                            and emp_promotion.get("revised_ctc")
                            and emp_promotion.get("revised_ctc")
                            > emp_promotion.get("current_ctc")
                            and emp_promotion.get("revised_ctc") >= 21000
                        ):
                            code = 4

        ws.append(
            [
                esic_number,
                emp_name,
                round(row.get("present_days") or 0),
                round(row.get("gross_pay") or 0),
                code,
                date,
            ]
        )

    file_content = BytesIO()
    wb.save(file_content)

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "esic_export.xlsx",
            "content": file_content.getvalue(),
            "is_private": 1,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def get_employee_details_map(data):
    employee_ids = list(
        {row.get("employee_id") for row in data if row.get("employee_id")}
    )
    if not employee_ids:
        return {}

    employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", employee_ids]},
        fields=["name", "_esic_number", "name_as_per_aadhar"],
    )
    return {employee.name: employee for employee in employees}


def get_promotion_map(data, from_date, to_date):
    employee_ids = list(
        {
            row.get("employee_id")
            for row in data
            if row.get("employee_id") and row.get("custom_month") in [4, 10]
        }
    )
    if not employee_ids:
        return {}

    promotions = frappe.get_all(
        "Employee Promotion",
        filters={
            "employee": ["in", employee_ids],
            "promotion_date": ["between", [from_date, to_date]],
        },
        fields=["employee", "current_ctc", "revised_ctc", "promotion_date"],
        order_by="creation desc",
    )

    promotion_map = {}
    for promotion in promotions:
        promotion_map.setdefault(promotion.employee, promotion)
    return promotion_map
