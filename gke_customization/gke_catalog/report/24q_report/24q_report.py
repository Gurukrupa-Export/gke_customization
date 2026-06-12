# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "pan_number",
			"label": _("PAN No"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "section",
			"label": _("Section"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "gross_pay",
			"label": _("Gross Pay"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "net_pay",
			"label": _("Net Pay"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "tds_amount",
			"label": _("TDS Amount"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "salary_without_tds",
			"label": _("Salary W/O TDS (Gross)"),
			"fieldtype": "Currency",
			"width": 180,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			ss.employee            AS employee,
			ss.employee_name       AS employee_name,
			e.pan_number           AS pan_number,
			es.custom_tax_withholding_category AS section,
			SUM(ss.gross_pay)                          AS gross_pay,
			SUM(ss.net_pay)                            AS net_pay,
			SUM(COALESCE(es.amount, 0))                AS tds_amount,
			SUM(ss.gross_pay) - SUM(COALESCE(es.amount, 0)) AS salary_without_tds
		FROM `tabSalary Slip` ss
		LEFT JOIN `tabAdditional Salary` es
			ON ss.employee = es.employee
			AND ss.end_date = es.payroll_date
		LEFT JOIN `tabEmployee` e
			ON ss.employee = e.name
		WHERE
			ss.docstatus = 1
			{conditions}
		GROUP BY
			ss.employee,
			ss.employee_name
			# e.pan_number,
			# es.custom_tax_withholding_category
		HAVING
			SUM(es.amount) != 0
		ORDER BY
			ss.employee
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	return data


def get_conditions(filters):
	conditions = []

	if filters.get("from_date"):
		conditions.append("AND ss.end_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("AND ss.end_date <= %(to_date)s")

	if filters.get("employee"):
		conditions.append("AND ss.employee = %(employee)s")

	return " ".join(conditions)