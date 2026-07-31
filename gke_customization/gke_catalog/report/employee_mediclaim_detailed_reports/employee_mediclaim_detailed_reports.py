# Copyright (c) 2026, Gurukrupa Export
# License information in license.txt

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
            "label": _("Employee Code"),
            "fieldname": "employee_code",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Name of the Insured Person"),
            "fieldname": "insured_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Relationship"),
            "fieldname": "relationship",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Gender"),
            "fieldname": "gender",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Marital Status"),
            "fieldname": "marital_status",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("DOB"),
            "fieldname": "dob",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Age"),
            "fieldname": "age",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Employment Status"),
            "fieldname": "employment_status",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Sum Insured"),
            "fieldname": "sum_insured",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Company - Branch"),
            "fieldname": "company_branch",
            "fieldtype": "Data",
            "width": 200,
        },
    ]


def get_conditions(filters):
    conditions = []
    params = {}

    if filters.get("company"):
        conditions.append("eme.company = %(company)s")
        params["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("eme.branch = %(branch)s")
        params["branch"] = filters.get("branch")

    if filters.get("department"):
        conditions.append("eme.department = %(department)s")
        params["department"] = filters.get("department")

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    return where_clause, params


def get_data(filters):
    conditions, params = get_conditions(filters)

    query = f"""
        SELECT
            eme.punch_id AS employee_code,
            eme.employee_name AS insured_name,
            'SELF' AS relationship,
            eme.gender,
            eme.marital_status,
            eme.department,
            eme.designation,
            eme.date_of_birth AS dob,
            eme.age,
            eme.employment_status,
            eme.total AS sum_insured,
            CONCAT(eme.company, ' - ', br.branch_name) AS company_branch,
            1 AS relation_order
        FROM `tabEmployee Mediclaim Enrollment` eme
        LEFT JOIN `tabBranch` br
            ON br.name = eme.branch
        WHERE 1=1
            {conditions}

        UNION ALL

        SELECT
            eme.punch_id,
            fd.full_name,
            fd.relation,
            fd.gender,
            eme.marital_status,
            eme.department,
            eme.designation,
            fd.date_of_birth,
            fd.age,
            eme.employment_status,
            eme.total,
            CONCAT(eme.company, ' - ', br.branch_name),
            2 AS relation_order
        FROM `tabEmployee Mediclaim Enrollment` eme
        INNER JOIN `tabEmployee Mediclaim Table` fd
            ON fd.parent = eme.name
        LEFT JOIN `tabBranch` br
            ON br.name = eme.branch
        WHERE 1=1
            {conditions}

        ORDER BY employee_code, relation_order
    """

    return frappe.db.sql(query, params, as_dict=True)
