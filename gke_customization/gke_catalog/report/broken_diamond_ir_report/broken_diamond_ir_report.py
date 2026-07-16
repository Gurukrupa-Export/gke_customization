# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Jangad No"),
            "fieldname": "jangad_no",
            "fieldtype": "Link",
            "options": "Employee IR",
            "width": 150,
        },
        {
            "label": _("Transaction Date"),
            "fieldname": "transfer_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": _("From Dept"),
            "fieldname": "from_department",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("From Manager"),
            "fieldname": "from_manager",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Shape"),
            "fieldname": "shape",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Quality"),
            "fieldname": "quality",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Size"),
            "fieldname": "size",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Size mm"),
            "fieldname": "size_mm",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Pcs"),
            "fieldname": "pcs",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Weight"),
            "fieldname": "weight",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Issue Confirm Employee"),
            "fieldname": "issue_confirm_employee",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Receive Confirm Employee"),
            "fieldname": "receive_confirm_employee",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Issue Date"),
            "fieldname": "issue_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": _("Receive Date"),
            "fieldname": "receive_date",
            "fieldtype": "Date",
            "width": 150,
        },
    ]


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("receive_ir.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("from_date"):
        conditions.append("DATE(receive_ir.creation) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(receive_ir.creation) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("jangad_no"):
        conditions.append("receive_ir.name = %(jangad_no)s")
        values["jangad_no"] = filters.get("jangad_no")

    if filters.get("manufacturer"):
        conditions.append("receive_ir.manufacturer = %(manufacturer)s")
        values["manufacturer"] = filters.get("manufacturer")

    if filters.get("to_department"):
        conditions.append("receive_ir.department = %(to_department)s")
        values["to_department"] = filters.get("to_department")

    if filters.get("from_department"):
        conditions.append("iim.from_department = %(from_department)s")
        values["from_department"] = filters.get("from_department")

    if filters.get("branch"):
        conditions.append("receive_emp.branch = %(branch)s")
        values["branch"] = filters.get("branch")

    if filters.get("to_manager"):
        conditions.append("receive_emp.name = %(to_manager)s")
        values["to_manager"] = filters.get("to_manager")

    if filters.get("from_manager"):
        conditions.append("issue_emp.name = %(from_manager)s")
        values["from_manager"] = filters.get("from_manager")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    return condition_sql, values


def get_data(filters):
    conditions, values = get_conditions(filters)

    sql = f"""
        WITH issue_ir_mapping AS (
            SELECT
                mbl.parent AS receive_ir,
                issue_ir.name AS issue_ir,
                DATE(issue_ir.creation) AS issue_date,
                issue_ir.department AS from_department,
                issue_ir.employee AS issue_confirm_emp,
                ROW_NUMBER() OVER (
                    PARTITION BY mbl.parent
                    ORDER BY issue_ir.creation DESC
                ) AS rn
            FROM `tabManually Book Loss Details` mbl

            INNER JOIN `tabEmployee IR Operation` issue_op
                ON issue_op.manufacturing_work_order = mbl.manufacturing_work_order
                AND IFNULL(issue_op.manufacturing_operation, '')
                    = IFNULL(mbl.manufacturing_operation, '')

            INNER JOIN `tabEmployee IR` issue_ir
                ON issue_ir.name = issue_op.parent
                AND issue_ir.type = 'Issue'

            WHERE mbl.loss_type = 'Broken'
        )

        SELECT
            receive_ir.name AS jangad_no,
            DATE(receive_ir.creation) AS transfer_date,
            iim.from_department AS from_department,
            issue_emp.employee_name AS from_manager,
            MAX(CASE WHEN iva.attribute = 'Stone Shape' THEN iva.attribute_value END) AS shape,
            MAX(CASE WHEN iva.attribute = 'Diamond Grade' THEN iva.attribute_value END) AS quality,
            MAX(CASE WHEN iva.attribute = 'Diamond Sieve Size' THEN iva.attribute_value END) AS size,
            MAX(CASE WHEN iva.attribute = 'Size MM' THEN iva.attribute_value END) AS size_mm,
            mbl.pcs AS pcs,
            mbl.proportionally_loss AS weight,
            'Received' AS status,
            issue_emp.employee_name AS issue_confirm_employee,
            receive_emp.employee_name AS receive_confirm_employee,
            iim.issue_date AS issue_date,
            DATE(receive_ir.creation) AS receive_date,
            receive_ir.department AS to_department

        FROM `tabManually Book Loss Details` mbl

        INNER JOIN `tabEmployee IR` receive_ir
            ON receive_ir.name = mbl.parent

        LEFT JOIN issue_ir_mapping iim
            ON iim.receive_ir = receive_ir.name
            AND iim.rn = 1

        LEFT JOIN `tabEmployee` issue_emp
            ON issue_emp.name = iim.issue_confirm_emp

        LEFT JOIN `tabEmployee` receive_emp
            ON receive_emp.name = receive_ir.employee

        LEFT JOIN `tabItem Variant Attribute` iva
            ON iva.parent = mbl.item_code

        WHERE
            mbl.loss_type = 'Broken'
            {conditions}

        GROUP BY
            receive_ir.name,
            receive_ir.creation,
            iim.from_department,
            issue_emp.employee_name,
            mbl.pcs,
            mbl.proportionally_loss,
            receive_emp.employee_name,
            iim.issue_date,
            receive_ir.department

        ORDER BY
            receive_ir.creation DESC
    """

    return frappe.db.sql(sql, values, as_dict=True)