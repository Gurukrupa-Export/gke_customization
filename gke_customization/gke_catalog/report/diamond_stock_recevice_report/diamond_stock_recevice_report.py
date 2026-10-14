# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Employee IR",
            "fieldname": "employee_ir",
            "fieldtype": "Link",
            "options": "Employee IR",
            "width": 170,
        },
        {
            "label": "Batch No",
            "fieldname": "batch_no",
            "fieldtype": "Link",
            "options": "Manufacturing Work Order",
            "width": 220,
        },
        {
            "label": "Employee",
            "fieldname": "employee_display",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 160,
        },
        {
            "label": "Manager",
            "fieldname": "manager",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Shape",
            "fieldname": "shape",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Purity",
            "fieldname": "purity",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": "Size",
            "fieldname": "size",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Weight",
            "fieldname": "weight",
            "fieldtype": "Float",
            "precision": 3,
            "width": 90,
        },
        {
            "label": "Pcs",
            "fieldname": "pcs",
            "fieldtype": "Float",
            "precision": 0,
            "width": 70,
        },
        {
            "label": "Type",
            "fieldname": "type",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": "Entry Date",
            "fieldname": "entry_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Entry User",
            "fieldname": "entry_user",
            "fieldtype": "Data",
            "width": 180,
        },
    ]


def get_conditions(filters):
    conditions = ["ir.docstatus < 2"]
    values = {}

    if filters.get("company"):
        conditions.append("ir.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("department"):
        conditions.append("ir.department = %(department)s")
        values["department"] = filters.get("department")

    if filters.get("manufacturer"):
        conditions.append("ir.manufacturer = %(manufacturer)s")
        values["manufacturer"] = filters.get("manufacturer")

    if filters.get("manager"):
        conditions.append("emp.reports_to = %(manager)s")
        values["manager"] = filters.get("manager")

    if filters.get("employee"):
        conditions.append("ir.employee = %(employee)s")
        values["employee"] = filters.get("employee")

    if filters.get("batch_no"):
        conditions.append("iro.manufacturing_work_order = %(batch_no)s")
        values["batch_no"] = filters.get("batch_no")

    if filters.get("employee_ir"):
        conditions.append("ir.name = %(employee_ir)s")
        values["employee_ir"] = filters.get("employee_ir")

    if filters.get("from_date"):
        conditions.append("DATE(ir.creation) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(ir.creation) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    status_list = filters.get("status")
    if status_list:
        if isinstance(status_list, str):
            status_list = [s.strip() for s in status_list.split(",") if s.strip()]
        elif not isinstance(status_list, (list, tuple)):
            status_list = [status_list]

        status_list = [s for s in status_list if s]
        if status_list:
            conditions.append("ir.type IN %(status)s")
            values["status"] = tuple(status_list)

    return " AND ".join(conditions), values


def get_data(filters):
    conditions, values = get_conditions(filters)

    query = f"""
        SELECT
            ir.name AS employee_ir,
            iro.manufacturing_work_order AS batch_no,

            CASE
                WHEN COALESCE(emp.employee_name, '') != '' THEN emp.employee_name
                WHEN COALESCE(ir.employee, '') != '' THEN ir.employee
                WHEN (
                    COALESCE(ir.subcontracting, '') IN ('Yes', '1')
                    OR COALESCE(ir.main_slip, '') != ''
                ) AND COALESCE(ir.subcontractor, '') != '' THEN ir.subcontractor
                ELSE ''
            END AS employee_display,

            ir.department AS department,
            COALESCE(mgr.employee_name, emp.reports_to, '') AS manager,

            MAX(
                CASE
                    WHEN iva.attribute IN ('Shape', 'Stone Shape')
                    THEN iva.attribute_value
                END
            ) AS shape,

            MAX(
                CASE
                    WHEN iva.attribute IN ('Purity', 'Diamond Grade', 'Quality')
                    THEN iva.attribute_value
                END
            ) AS purity,

            MAX(
                CASE
                    WHEN iva.attribute IN ('Size', 'Sieve Size', 'Diamond Sieve Size', 'Sieve Size Range')
                    THEN iva.attribute_value
                END
            ) AS size,

            COALESCE(bdd.weight_in_gms, 0) AS weight,
            COALESCE(bdd.pcs, 0) AS pcs,

            COALESCE(ir.transfer_type, ir.custom_transfer_type, '') AS type,
            ir.type AS status,
            DATE(ir.creation) AS entry_date,
            ir.owner AS entry_user

        FROM `tabEmployee IR` ir

        LEFT JOIN `tabEmployee IR Operation` iro
            ON iro.parent = ir.name

        LEFT JOIN `tabManufacturing Work Order` mwo
            ON mwo.name = iro.manufacturing_work_order

        LEFT JOIN `tabBOM` bom
            ON bom.name = mwo.master_bom

        LEFT JOIN `tabBOM Diamond Detail` bdd
            ON bdd.parent = bom.name

        LEFT JOIN `tabItem Variant Attribute` iva
            ON iva.parent = bdd.item_variant

        LEFT JOIN `tabEmployee` emp
            ON emp.name = ir.employee

        LEFT JOIN `tabEmployee` mgr
            ON mgr.name = emp.reports_to

        WHERE {conditions}
          AND bdd.item_variant IS NOT NULL

        GROUP BY
            ir.name,
            iro.manufacturing_work_order,
            CASE
                WHEN COALESCE(emp.employee_name, '') != '' THEN emp.employee_name
                WHEN COALESCE(ir.employee, '') != '' THEN ir.employee
                WHEN (
                    COALESCE(ir.subcontracting, '') IN ('Yes', '1')
                    OR COALESCE(ir.main_slip, '') != ''
                ) AND COALESCE(ir.subcontractor, '') != '' THEN ir.subcontractor
                ELSE ''
            END,
            ir.department,
            COALESCE(mgr.employee_name, emp.reports_to, ''),
            bdd.weight_in_gms,
            bdd.pcs,
            COALESCE(ir.transfer_type, ir.custom_transfer_type, ''),
            ir.type,
            DATE(ir.creation),
            ir.owner,
            bdd.item_variant

        ORDER BY
            DATE(ir.creation) DESC,
            ir.name DESC,
            iro.manufacturing_work_order DESC,
            bdd.item_variant ASC
    """

    return frappe.db.sql(query, values, as_dict=True)