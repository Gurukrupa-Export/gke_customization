# Copyright (c) 2025, Gurukrupa Export
# For license information, please see license.txt

import frappe
from frappe import _


# -------------------------------------------------------
# Execute
# -------------------------------------------------------

def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data()
    message = get_message()

    return columns, data, message


# -------------------------------------------------------
# Columns
# -------------------------------------------------------

def get_columns():
    return [
        {
            "label": _("Employee Grade"),
            "fieldname": "employee_grade",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Number of Employees"),
            "fieldname": "number_of_employees",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Designations"),
            "fieldname": "designations",
            "fieldtype": "Data",
            "width": 1080,
        },
        
    ]


# -------------------------------------------------------
# Data
# -------------------------------------------------------

def get_data():
    query = """
        SELECT
            eg.name AS employee_grade,
            GROUP_CONCAT(
                DISTINCT d.name
                ORDER BY d.name
                SEPARATOR ', '
            ) AS designations,
            COUNT(e.name) AS number_of_employees
        FROM
            `tabEmployee Grade` eg
        LEFT JOIN
            `tabDesignation` d
            ON d.custom_grade = eg.name
        LEFT JOIN
            `tabEmployee` e
            ON e.designation = d.name
            AND e.status = 'Active'
            AND e.relieving_date IS NULL
        GROUP BY
            eg.name
        ORDER BY
            CAST(SUBSTRING_INDEX(eg.name, '-', -1) AS UNSIGNED) 
    """

    return frappe.db.sql(query, as_dict=True)


# -------------------------------------------------------
# Message
# -------------------------------------------------------

def get_message():
    return """
        <span class="indicator" style="font-weight:bold;font-size:15px;">
            Note :
        </span>
        <span class="indicator blue" style="font-size:15px;">
            Designations are shown grade-wise and separated by commas.
        </span>
    """
