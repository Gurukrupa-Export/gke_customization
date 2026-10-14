# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data, None, None, None


def get_columns():
    return [
        {"label": _("MWO"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 140},
        {"label": _("To Department"), "fieldname": "to_department", "fieldtype": "Link", "options": "Department", "width": 130},
        {"label": _("Manager"), "fieldname": "manager", "fieldtype": "Data", "width": 120},
        {"label": _("To Manager"), "fieldname": "to_manager", "fieldtype": "Data", "width": 120},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": _("PMO"), "fieldname": "order_no", "fieldtype": "Link", "options": "Parent Manufacturing Order", "width": 150},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": _("Touch"), "fieldname": "touch", "fieldtype": "Data", "width": 90},
        {"label": _("Dia Type"), "fieldname": "dia_type", "fieldtype": "Data", "width": 120},
        {"label": _("Setting"), "fieldname": "setting", "fieldtype": "Data", "width": 120},
        {"label": _("Style Bio"), "fieldname": "style_bio", "fieldtype": "Data", "width": 130},
        {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
        {"label": _("Sub Category"), "fieldname": "sub_category", "fieldtype": "Data", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
    ]


def get_data(filters):
    conditions, values = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            MWO.name AS batch_no,
            MWO.department AS to_department,
            '' AS manager,
            '' AS to_manager,
            '' AS employee,
            PMO.name AS order_no,
            PMO.sales_order AS sales_order,
            MWO.delivery_date AS due_date,
            PMO.metal_purity AS touch,
            PMO.diamond_grade AS dia_type,
            MWO.setting_type AS setting,
            MO.item_code AS style_bio,
            MWO.item_category AS category,
            MWO.item_sub_category AS sub_category,
            MWO.status AS status,
            MWO.company AS company
        FROM `tabManufacturing Work Order` MWO
        LEFT JOIN `tabParent Manufacturing Order` PMO
            ON MWO.manufacturing_order = PMO.name
        LEFT JOIN `tabManufacturing Operation` MO
            ON MWO.manufacturing_operation = MO.name
        WHERE MWO.manufacturing_order IS NOT NULL {conditions}
        AND EXISTS (
            SELECT 1 FROM `tabManufacturing Work Order` MWO2
            WHERE MWO2.manufacturing_order = MWO.manufacturing_order
            AND NOT (MWO2.status = 'Completed' AND MWO2.docstatus = 1)
        )
        ORDER BY MWO.delivery_date ASC, MWO.name ASC
        """,
        values,
        as_dict=1,
    )

    return data


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("sales_order"):
        conditions += " AND PMO.sales_order = %(sales_order)s"
        values["sales_order"] = filters.get("sales_order")

    if filters.get("to_department"):
        conditions += " AND MWO.department = %(to_department)s"
        values["to_department"] = filters.get("to_department")

    if filters.get("status"):
        conditions += " AND MWO.status = %(status)s"
        values["status"] = filters.get("status")

    if filters.get("company"):
        conditions += " AND MWO.company = %(company)s"
        values["company"] = filters.get("company")

    if filters.get("from_due_date"):
        conditions += " AND MWO.delivery_date >= %(from_due_date)s"
        values["from_due_date"] = filters.get("from_due_date")

    if filters.get("to_due_date"):
        conditions += " AND MWO.delivery_date <= %(to_due_date)s"
        values["to_due_date"] = filters.get("to_due_date")

    return conditions, values


@frappe.whitelist()
def get_batch_detail(batch_no):
    rows = frappe.db.sql(
        """
        SELECT
            SED.parent AS stock_entry,
            SED.item_code AS item_code,
            SED.item_name AS item_name,
            SED.s_warehouse AS s_warehouse,
            SED.t_warehouse AS t_warehouse,
            SED.batch_no AS batch_no,
            SED.qty AS qty,
            SED.uom AS uom,
            SED.basic_rate AS basic_rate,
            SED.amount AS amount
        FROM `tabStock Entry Detail` SED
        INNER JOIN `tabStock Entry` SE ON SE.name = SED.parent
        WHERE SE.manufacturing_work_order = %(batch_no)s
        ORDER BY SED.parent ASC, SED.idx ASC
        """,
        {"batch_no": batch_no},
        as_dict=True,
    )
    return rows


@frappe.whitelist()
def get_batch_history(batch_no):
    rows = frappe.db.sql(
    """
    SELECT
        MO.manufacturing_work_order AS batch_no,
        TDIR.previous_department AS from_department,
        TDIR.current_department AS to_department,
        DATE(TDIR.date_time) AS receive_date,
        TIME(TDIR.date_time) AS receive_time,
        MO.employee AS employee_name,
        COALESCE(MO.operation, MO.name) AS current_operation
    FROM `tabManufacturing Operation` MO
    LEFT JOIN `tabDepartment IR Operation` DIRO
        ON DIRO.manufacturing_operation = MO.name
    LEFT JOIN `tabDepartment IR` TDIR
        ON DIRO.parent = TDIR.name
    WHERE MO.manufacturing_work_order = %s
    AND MO.department_ir_status ='Received'
    ORDER BY TDIR.date_time ASC
    """,
    (batch_no,),
    as_dict=True,
)
    return rows