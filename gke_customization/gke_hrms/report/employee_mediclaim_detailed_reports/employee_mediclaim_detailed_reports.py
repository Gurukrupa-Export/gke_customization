# Copyright (c) 2026, Gurukrupa Export
# License information in license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Concat
from pypika.terms import Field, ValueWrapper


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


def apply_filters(query, enrollment, filters):
    for fieldname in ("company", "branch", "department"):
        if filters.get(fieldname):
            query = query.where(enrollment[fieldname] == filters.get(fieldname))
    return query


def get_data(filters):
    enrollment = frappe.qb.DocType("Employee Mediclaim Enrollment")
    family = frappe.qb.DocType("Employee Mediclaim Table")
    branch = frappe.qb.DocType("Branch")
    company_branch = Concat(enrollment.company, " - ", branch.branch_name)

    self_query = (
        frappe.qb.from_(enrollment)
        .left_join(branch)
        .on(branch.name == enrollment.branch)
        .select(
            enrollment.punch_id.as_("employee_code"),
            enrollment.employee_name.as_("insured_name"),
            ValueWrapper("SELF").as_("relationship"),
            enrollment.gender,
            enrollment.marital_status,
            enrollment.department,
            enrollment.designation,
            enrollment.date_of_birth.as_("dob"),
            enrollment.age,
            enrollment.employment_status,
            enrollment.total.as_("sum_insured"),
            company_branch.as_("company_branch"),
            ValueWrapper(1).as_("relation_order"),
        )
    )

    family_query = (
        frappe.qb.from_(enrollment)
        .inner_join(family)
        .on(
            (family.parent == enrollment.name)
            & (family.parenttype == "Employee Mediclaim Enrollment")
            & (family.parentfield == "family_details")
        )
        .left_join(branch)
        .on(branch.name == enrollment.branch)
        .select(
            enrollment.punch_id,
            family.full_name,
            family.relation,
            family.gender,
            enrollment.marital_status,
            enrollment.department,
            enrollment.designation,
            family.date_of_birth,
            family.age,
            enrollment.employment_status,
            enrollment.total,
            company_branch,
            ValueWrapper(2),
        )
    )

    self_query = apply_filters(self_query, enrollment, filters)
    family_query = apply_filters(family_query, enrollment, filters)

    query = (
        self_query.union_all(family_query)
        .orderby(Field("employee_code"))
        .orderby(Field("relation_order"))
    )
    return query.run(as_dict=True)
