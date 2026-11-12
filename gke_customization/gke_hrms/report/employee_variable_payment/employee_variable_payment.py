# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import CustomFunction, Round


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    employee = frappe.qb.DocType("Employee")
    salary_slip = frappe.qb.DocType("Salary Slip")

    Month = CustomFunction("MONTH", ["date_value"])

    month_name = (
        Case()
        .when(Month(salary_slip.start_date) == 1, "January")
        .when(Month(salary_slip.start_date) == 2, "February")
        .when(Month(salary_slip.start_date) == 3, "March")
        .when(Month(salary_slip.start_date) == 4, "April")
        .when(Month(salary_slip.start_date) == 5, "May")
        .when(Month(salary_slip.start_date) == 6, "June")
        .when(Month(salary_slip.start_date) == 7, "July")
        .when(Month(salary_slip.start_date) == 8, "August")
        .when(Month(salary_slip.start_date) == 9, "September")
        .when(Month(salary_slip.start_date) == 10, "October")
        .when(Month(salary_slip.start_date) == 11, "November")
        .when(Month(salary_slip.start_date) == 12, "December")
    )

    query = (
        frappe.qb.from_(employee)
        .join(salary_slip)
        .on(salary_slip.employee == employee.name)
        .select(
            month_name.as_("month_name"),
            salary_slip.start_date.as_("date"),
            employee.ctc,
            employee.variable_in,
            Round(salary_slip.gross_pay, 0).as_("gross_pay"),
            Round(salary_slip.gross_pay * (employee.variable_in / 100), 0).as_(
                "gross_pay_amt"
            ),
        )
        .where(salary_slip.status == "Submitted")
    )

    if filters and filters.get("employee"):
        query = query.where(employee.name == filters.get("employee"))

    return query.run(as_dict=True)


def get_columns(filters=None):
    columns = [
        {
            "label": _("Month"),
            "fieldname": "month_name",
            "fieldtype": "Data",
            "width": 100,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 130},
        {"label": _("CTC"), "fieldname": "ctc", "fieldtype": "Currency", "width": 100},
        {
            "label": _("Variable"),
            "fieldname": "variable_in",
            "fieldtype": "Percent",
            "width": 100,
        },
        {
            "label": _("Gross Pay"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": _("Variable Amount"),
            "fieldname": "gross_pay_amt",
            "fieldtype": "Currency",
            "width": 180,
        },
    ]
    return columns
