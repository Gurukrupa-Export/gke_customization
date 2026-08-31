# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "label": _("Manufacturing Work Order"),
            "fieldname": "manufacturing_work_order",
            "fieldtype": "Link",
            "options": "Manufacturing Work Order",
            "width": 180
        },
        {
            "label": _("Manufacturing Operation"),
            "fieldname": "manufacturing_operation",
            "fieldtype": "Link",
            "options": "Manufacturing Operation",
            "width": 180
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150
        },
        {
            "label": _("Operation"),
            "fieldname": "operation",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Main Slip"),
            "fieldname": "main_slip",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Gross Wt"),
            "fieldname": "gross_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Receive Gross Wt"),
            "fieldname": "received_gross_wt",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3
        },
        {
            "label": _("Net Wt"),
            "fieldname": "net_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Metal Wt (Net Wt + Finding Wt)"),
            "fieldname": "metal_wt",
            "fieldtype": "Float",
            "width": 150,
            "precision": 3
        },
        # {
        #     "label": _("Allow Loss"),
        #     "fieldname": "allow_loss",
        #     "fieldtype": "Float",
        #     "width": 110,
        #     "precision": 2
        # },
        {
            "label": _("Loss Wt"),
            "fieldname": "loss_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Finding Wt"),
            "fieldname": "finding_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Diamond Wt"),
            "fieldname": "diamond_wt",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3
        },
        {
            "label": _("Diamond Pcs"),
            "fieldname": "diamond_pcs",
            "fieldtype": "Int",
            "width": 110
        },
        {
            "label": _("Gemstone Wt"),
            "fieldname": "gemstone_wt",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        },
        {
            "label": _("Gemstone Pcs"),
            "fieldname": "gemstone_pcs",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Other Wt"),
            "fieldname": "other_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Issue By"),
            "fieldname": "issue_by",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Issue Date"),
            "fieldname": "issue_date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("Receive By"),
            "fieldname": "receive_by",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Receive Date"),
            "fieldname": "receive_date",
            "fieldtype": "Datetime",
            "width": 150
        }
    ]


def get_data(filters):
    main_data = get_main_data(filters)

    frappe.log_error(
        f"Main data count: {len(main_data)}\nFilters: {json.dumps(filters)}",
        "Employee Issue Receive Reports - Main Data"
    )

    ir_data = get_employee_ir_data(filters)

    frappe.log_error(
        f"IR data count: {len(ir_data)}",
        "Employee Issue Receive Reports - IR Data"
    )

    ir_mapping = {}
    for ir_row in ir_data:
        key = (ir_row.get("manufacturing_operation"), ir_row.get("employee"))
        if key not in ir_mapping:
            ir_mapping[key] = {"issue": None, "receive": None}

        if ir_row.get("type") == "Issue":
            ir_mapping[key]["issue"] = ir_row
        elif ir_row.get("type") == "Receive":
            ir_mapping[key]["receive"] = ir_row

    for row in main_data:
        key = (row.get("manufacturing_operation"), row.get("employee_id"))
        if key in ir_mapping:
            if ir_mapping[key]["issue"]:
                row["issue_date"] = ir_mapping[key]["issue"].get("date_time")
                row["issue_by"] = ir_mapping[key]["issue"].get("full_name") or ir_mapping[key]["issue"].get("owner")

            if ir_mapping[key]["receive"]:
                row["receive_date"] = ir_mapping[key]["receive"].get("date_time")
                row["receive_by"] = ir_mapping[key]["receive"].get("full_name") or ir_mapping[key]["receive"].get("owner")

    frappe.log_error(
        f"Final data count: {len(main_data)}\nFirst 5 MOPs: {[r.get('manufacturing_operation') for r in main_data[:5]]}",
        "Employee Issue Receive Reports - Final Data"
    )

    return main_data


def get_main_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            mwo.customer,
            mo.manufacturing_work_order,
            mo.name as manufacturing_operation,
            mo.status,
            mo.department,
            mo.operation,
            mo.employee as employee_id,
            emp.employee_name,
            mo.main_slip_no as main_slip,
            mo.gross_wt,
            mo.received_gross_wt,
            mo.net_wt,
            (COALESCE(mo.net_wt, 0) + COALESCE(mo.finding_wt, 0)) as metal_wt,
            CASE
                WHEN mo.loss_wt < 0 THEN ABS(mo.loss_wt)
                ELSE NULL
            END as loss_wt,
            mo.finding_wt,
            mo.diamond_wt,
            mo.diamond_pcs,
            mo.gemstone_wt,
            mo.gemstone_pcs,
            mo.other_wt
        FROM
            `tabManufacturing Operation` mo
        LEFT JOIN
            `tabManufacturing Work Order` mwo ON mo.manufacturing_work_order = mwo.name
        LEFT JOIN
            `tabEmployee` emp ON mo.employee = emp.name
        WHERE
            mo.operation IS NOT NULL
            AND mo.operation != ''
            AND mo.status IN ('WIP', 'Finished')
            AND mwo.for_fg = 0
            {conditions}
        ORDER BY
            mo.creation DESC
        LIMIT 10000
    """

    frappe.log_error(
        f"Conditions: {conditions}\n\nFilters: {json.dumps(filters)}\n\nFull Query:\n{query}",
        "Employee Issue Receive Reports - SQL Query"
    )

    result = frappe.db.sql(query, filters, as_dict=True)

    frappe.log_error(
        f"Query returned {len(result)} rows\nFirst 10 MOPs: {[r.get('manufacturing_operation') for r in result[:10]]}",
        "Employee Issue Receive Reports - Query Result"
    )

    return result


def get_employee_ir_data(filters):
    date_condition = ""
    operation_conditions = ""

    if filters.get("from_date") and filters.get("to_date"):
        date_condition = """
            AND DATE(eir.date_time) >= %(from_date)s
            AND DATE(eir.date_time) <= %(to_date)s
        """

    if filters.get("operation"):
        operation_conditions += " AND mo.operation = %(operation)s"

    if filters.get("department"):
        operation_conditions += " AND mo.department = %(department)s"

    if filters.get("employee_id"):
        operation_conditions += " AND eir.employee = %(employee_id)s"

    if filters.get("company"):
        operation_conditions += " AND mo.company = %(company)s"

    query = f"""
        SELECT
            eiro.manufacturing_operation,
            eir.employee,
            eir.type,
            eir.date_time,
            eir.owner,
            u.full_name
        FROM
            `tabEmployee IR` eir
        INNER JOIN
            `tabEmployee IR Operation` eiro ON eiro.parent = eir.name
        INNER JOIN
            `tabManufacturing Operation` mo ON mo.name = eiro.manufacturing_operation
        LEFT JOIN
            `tabUser` u ON eir.owner = u.name
        WHERE
            eir.type IN ('Issue', 'Receive')
            AND eiro.manufacturing_operation IS NOT NULL
            AND eir.docstatus = 1
            {date_condition}
            {operation_conditions}
        ORDER BY
            eir.date_time DESC
    """

    result = frappe.db.sql(query, filters, as_dict=True)

    return result


def get_conditions(filters):
    conditions = ""

    if filters.get("company"):
        conditions += " AND mo.company = %(company)s"

    if filters.get("branch"):
        conditions += " AND (mwo.branch = %(branch)s OR mwo.branch IS NULL)"

    if filters.get("manufacturer"):
        conditions += " AND mo.manufacturer = %(manufacturer)s"

    if filters.get("department"):
        conditions += " AND mo.department = %(department)s"

    if filters.get("operation"):
        conditions += " AND mo.operation = %(operation)s"

    if filters.get("employee_id"):
        conditions += " AND mo.employee = %(employee_id)s"

    if filters.get("from_date") and filters.get("to_date"):
        conditions += """
            AND mo.creation >= %(from_date)s
            AND mo.creation <= DATE_ADD(%(to_date)s, INTERVAL 1 DAY)
        """

    return conditions


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employees_by_operation(doctype, txt, searchfield, start, page_len, filters):
    department = filters.get("department")
    operation = filters.get("operation")
    company = filters.get("company")

    if not operation:
        return frappe.db.sql("""
            SELECT DISTINCT
                emp.name,
                emp.employee_name
            FROM `tabEmployee` emp
            WHERE
                emp.company = %(company)s
                AND emp.status = 'Active'
                AND (emp.name LIKE %(txt)s OR emp.employee_name LIKE %(txt)s)
            ORDER BY emp.employee_name
            LIMIT %(start)s, %(page_len)s
        """, {
            "company": company,
            "txt": "%" + txt + "%",
            "start": start,
            "page_len": page_len
        })

    conditions = "mo.operation = %(operation)s"

    if department:
        conditions += " AND mo.department = %(department)s"

    if company:
        conditions += " AND mo.company = %(company)s"

    return frappe.db.sql(f"""
        SELECT DISTINCT
            emp.name,
            emp.employee_name
        FROM `tabEmployee` emp
        INNER JOIN `tabManufacturing Operation` mo
            ON mo.employee = emp.name
        WHERE
            {conditions}
            AND emp.status = 'Active'
            AND (emp.name LIKE %(txt)s OR emp.employee_name LIKE %(txt)s)
        ORDER BY emp.employee_name
        LIMIT %(start)s, %(page_len)s
    """, {
        "department": department,
        "operation": operation,
        "company": company,
        "txt": "%" + txt + "%",
        "start": start,
        "page_len": page_len
    })
