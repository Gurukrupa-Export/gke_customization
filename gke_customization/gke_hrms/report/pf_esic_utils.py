# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today


def get_employee_details_map(employee_ids, fields):
    """Return {employee: row} with the given Employee fields for every id in employee_ids."""
    employee_ids = list({employee for employee in employee_ids if employee})
    if not employee_ids:
        return {}

    rows = frappe.get_all(
        "Employee",
        filters={"name": ["in", employee_ids]},
        fields=["name", *fields],
    )
    return {row.name: row for row in rows}


def get_latest_employee_promotions(employee_ids, from_date, to_date):
    """Return {employee: promotion} for promotions dated in the period, keeping the most recently created one."""
    employee_ids = list({employee for employee in employee_ids if employee})
    if not employee_ids:
        return {}

    promotions = frappe.get_all(
        "Employee Promotion",
        filters=[
            ["employee", "in", employee_ids],
            ["promotion_date", "between", [from_date, to_date]],
        ],
        fields=["name", "employee", "current_ctc", "revised_ctc", "promotion_date"],
        order_by="creation desc",
    )

    promotion_map = {}
    for promotion in promotions:
        promotion_map.setdefault(promotion.employee, promotion)

    return promotion_map


def get_age_in_years(date_of_birth):
    """Completed years from date_of_birth to today, or 0 when date_of_birth is not set."""
    if not date_of_birth:
        return 0

    today_date = getdate(today())
    dob_date = getdate(date_of_birth)
    return (
        today_date.year
        - dob_date.year
        - ((today_date.month, today_date.day) < (dob_date.month, dob_date.day))
    )
