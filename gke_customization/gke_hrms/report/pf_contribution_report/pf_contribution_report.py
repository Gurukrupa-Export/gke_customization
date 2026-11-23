# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_pf_data(filters)
    return columns, data


def get_employee_filter_list(employee):
    if not employee:
        return []

    if isinstance(employee, str):
        employee = employee.strip()
        if employee.startswith("["):
            employee = frappe.parse_json(employee)
        else:
            employee = [employee]

    return [emp for emp in employee if emp]


def get_pf_data(filters=None):
    values = {
        "start_date": filters.get("from_date"),
        "end_date": filters.get("to_date"),
        "company": filters.get("company"),
    }

    emp_condition = ""
    employees = get_employee_filter_list(filters.get("employee"))
    if employees:
        emp_condition = "AND ss.employee IN %(employees)s"
        values["employees"] = tuple(employees)

    data = frappe.db.sql(
        f"""
		SELECT
			ss.employee,
			ss.employee_name,
			ss.department,
			ss.designation,
			ss.total_working_days,
			ss.payment_days,
			ss.actual_working_hours,
			ss.gross_pay,
			ss.total_deduction,
			ss.rounded_total,
			emp.uan_number AS uan, ss.absent_days,
			Least(Ifnull(basic.basic, 0), 15000) AS epf_wage,
			Least(Ifnull(basic.basic, 0), 15000) AS edli_wage,
			CASE WHEN Timestampdiff(year, emp.date_of_birth, Curdate()) < 58 THEN Least(Ifnull(basic.basic, 0), 15000) ELSE 0 end AS eps_wage,
			Round(Least(Ifnull(basic.basic, 0), 15000) * 0.12, 0) AS ee_share,
			CASE WHEN Timestampdiff(year, emp.date_of_birth, Curdate()) < 58 THEN Round(Least(Ifnull(basic.basic, 0), 15000) * 0.0833, 0) ELSE 0 end AS eps_con,
			ROUND(
				ROUND(LEAST(IFNULL(basic.basic, 0), 15000) * 0.12,0)
				-
				CASE
					WHEN TIMESTAMPDIFF(YEAR, emp.date_of_birth, CURDATE()) < 58
					THEN ROUND(LEAST(IFNULL(basic.basic, 0), 15000) * 0.0833,0)
					ELSE 0
				END
			) AS er_share,
			CASE
				WHEN IFNULL(ss.absent_days, 0) > 0
					THEN ROUND(ss.absent_days, 0)
				ELSE
					GREATEST(
						ROUND(
							IFNULL(ss.total_working_days, 0)
							- IFNULL(ss.payment_days, 0),
							0
						),
						0
					)
			END AS ncp_days,
			0 as Refund
		FROM `tabSalary Slip` ss
		LEFT JOIN `tabEmployee` emp ON emp.name = ss.employee
		LEFT JOIN (
			SELECT sd.parent, Sum(CASE WHEN sd.salary_component = 'Basic' THEN sd.amount ELSE 0 end) AS basic
			FROM `tabSalary Detail` sd
			JOIN `tabSalary Slip` slip ON slip.name = sd.parent
			WHERE slip.docstatus = 1
				AND slip.start_date >= %(start_date)s
				AND slip.end_date <= %(end_date)s
				AND slip.company = %(company)s
			GROUP BY sd.parent
		) basic ON basic.parent = ss.name
		WHERE ss.docstatus = 1
			AND ss.start_date >= %(start_date)s
			AND ss.end_date <= %(end_date)s
			AND ss.company = %(company)s
			AND emp.uan_number IS NOT NULL
			AND ss._is_pf_applicable = 1
			{emp_condition}
		ORDER BY ss.employee_name
		""",
        values,
        as_dict=True,
    )

    data += get_totals(data, filters.get("employee"), filters)
    return data


def get_totals(data, employee=None, filters=None):
    totals = {
        "company": _("Total"),
        "branch": "",
        "employee_name": _("Total Employees: {0}").format(len(data)),
        "gross_pay": sum(row.get("gross_pay", 0) for row in data),
        "epf_wage": sum(row.get("epf_wage", 0) for row in data),
        "edli_wage": sum(row.get("edli_wage", 0) for row in data),
        "eps_wage": sum(row.get("eps_wage", 0) for row in data),
        "ee_share": sum(row.get("ee_share", 0) for row in data),
        "eps_con": sum(row.get("eps_con", 0) for row in data),
        "er_share": sum(row.get("er_share", 0) for row in data),
        "ncp_days": sum(row.get("ncp_days", 0) for row in data),
    }
    return [totals]


def get_columns(filters=None):
    return [
        {"fieldname": "uan", "label": _("UAN"), "fieldtype": "Data", "width": 120},
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "fieldname": "gross_pay",
            "label": _("Gross Pay"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "epf_wage",
            "label": _("EPF Wage"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "edli_wage",
            "label": _("EDLI Wage"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "eps_wage",
            "label": _("EPS Wage"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "ee_share",
            "label": _("EE Share"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "eps_con",
            "label": _("EPS Contr."),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "er_share",
            "label": _("ER Share"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "ncp_days",
            "label": _("NCP Days"),
            "fieldtype": "Float",
            "width": 80,
        },
        {"fieldname": "Refund", "label": _("Refund"), "fieldtype": "Int", "width": 80},
    ]
