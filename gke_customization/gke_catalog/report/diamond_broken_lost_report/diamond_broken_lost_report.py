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
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 220},
        {"label": _("Broken WT"), "fieldname": "broken_wt", "fieldtype": "Float", "width": 110},
        {"label": _("Broken PCS"), "fieldname": "broken_pcs", "fieldtype": "Int", "width": 110},
        {"label": _("Broken Amount"), "fieldname": "broken_amt", "fieldtype": "Currency", "width": 130},
        {"label": _("Lost WT"), "fieldname": "lost_wt", "fieldtype": "Float", "width": 110},
        {"label": _("Lost PCS"), "fieldname": "lost_pcs", "fieldtype": "Int", "width": 110},
        {"label": _("Lost Amount"), "fieldname": "lost_amt", "fieldtype": "Currency", "width": 130},
        {"label": _("Total WT"), "fieldname": "total_wt", "fieldtype": "Float", "width": 110},
        {"label": _("Total PCS"), "fieldname": "total_pcs", "fieldtype": "Int", "width": 110},
        {"label": _("Total Amount"), "fieldname": "total_amt", "fieldtype": "Currency", "width": 130},
        {"label": _("Lost Department"), "fieldname": "lost_department", "fieldtype": "Data", "width": 200},
    ]

def get_conditions(filters):
    conditions=[]; params={}
    if filters.get("company"):
        conditions.append("eir.company = %(company)s"); params["company"]=filters["company"]
    if filters.get("branch"):
        conditions.append("emp.branch = %(branch)s"); params["branch"]=filters["branch"]
    if filters.get("manufacturer"):
        conditions.append("eir.manufacturer = %(manufacturer)s"); params["manufacturer"]=filters["manufacturer"]
    if filters.get("employee"):
        conditions.append("eir.employee = %(employee)s")
        params["employee"]=filters["employee"]
    if filters.get("department"):
        conditions.append("eir.department = %(department)s"); params["department"]=filters["department"]
    if filters.get("from_date"):
        conditions.append("DATE(eir.creation) >= %(from_date)s"); params["from_date"]=filters["from_date"]
    if filters.get("to_date"):
        conditions.append("DATE(eir.creation) <= %(to_date)s"); params["to_date"]=filters["to_date"]
    where=""
    if conditions:
        where=" AND "+" AND ".join(conditions)
    return where, params

def get_data(filters):
    conditions, params = get_conditions(filters)
    sql=f"""
    SELECT
        CASE
            WHEN eir.subcontracting='Yes' THEN sup.supplier_name
            ELSE emp.employee_name
        END AS employee,

        IFNULL(SUM(CASE WHEN mbld.loss_type='Broken' THEN mbld.proportionally_loss ELSE 0 END),0) AS broken_wt,
        IFNULL(SUM(CASE WHEN mbld.loss_type='Broken' THEN mbld.pcs ELSE 0 END),0) AS broken_pcs,
        IFNULL(SUM(
            CASE
                WHEN mbld.loss_type='Broken'
                THEN mbld.proportionally_loss * IFNULL(fg_bom_item.rate, design_bom_item.rate)
                ELSE 0
            END
        ),0) AS broken_amt,

        IFNULL(SUM(CASE WHEN mbld.loss_type='Missing' THEN mbld.proportionally_loss ELSE 0 END),0) AS lost_wt,
        IFNULL(SUM(CASE WHEN mbld.loss_type='Missing' THEN mbld.pcs ELSE 0 END),0) AS lost_pcs,
        IFNULL(SUM(
            CASE
                WHEN mbld.loss_type = 'Missing'
                THEN mbld.proportionally_loss * IFNULL(fg_bom_item.rate, design_bom_item.rate)
                ELSE 0
            END
        ),0) AS lost_amt,

        IFNULL(SUM(CASE WHEN mbld.loss_type IN ('Broken','Missing') THEN mbld.proportionally_loss ELSE 0 END),0) AS total_wt,
        IFNULL(SUM(CASE WHEN mbld.loss_type IN ('Broken','Missing') THEN mbld.pcs ELSE 0 END),0) AS total_pcs,
        IFNULL(SUM(
            CASE
                WHEN mbld.loss_type IN ('Broken','Missing')
                THEN mbld.proportionally_loss * IFNULL(fg_bom_item.rate, design_bom_item.rate)
                ELSE 0
            END
        ),0) AS total_amt,

        dop.department AS lost_department

    FROM `tabEmployee IR` eir

    LEFT JOIN `tabEmployee` emp
        ON emp.name = eir.employee

    LEFT JOIN `tabSupplier` sup
        ON sup.name = eir.subcontractor

    LEFT JOIN `tabManually Book Loss Details` mbld
        ON mbld.parent = eir.name

    LEFT JOIN `tabItem` item
        ON item.name = mbld.item_code

    LEFT JOIN `tabDepartment Operation` dop
        ON dop.operation = eir.operation

    
    LEFT JOIN (
        SELECT
            manufacturing_work_order,
            MAX(name) AS mop_name
        FROM `tabManufacturing Operation`
        WHERE
            department LIKE 'Tagging%%'
            AND status = 'Finished'
        GROUP BY manufacturing_work_order
    ) tm
        ON tm.manufacturing_work_order = mbld.manufacturing_work_order

    LEFT JOIN `tabManufacturing Operation` mop
        ON mop.name = tm.mop_name

   
    LEFT JOIN `tabSerial Number Creator` snc
        ON snc.manufacturing_operation = mop.name
       AND snc.docstatus = 1


    LEFT JOIN `tabBOM` fg_bom
        ON fg_bom.custom_serial_number_creator = snc.name
       AND fg_bom.bom_type = 'Finish Goods'
       AND fg_bom.docstatus = 1

    LEFT JOIN `tabBOM Item` fg_bom_item
        ON fg_bom_item.parent = fg_bom.name
       AND fg_bom_item.item_code = mbld.item_code

  
    LEFT JOIN `tabBOM Item` design_bom_item
        ON design_bom_item.parent = mop.design_id_bom
       AND design_bom_item.item_code = mbld.item_code

    WHERE
        eir.docstatus = 1
        AND item.variant_of = 'D'
        AND mbld.loss_type IN ('Broken','Missing')
        {conditions}

    GROUP BY
        emp.employee_name,
        sup.supplier_name,
        eir.subcontracting,
        dop.department

    ORDER BY
        CASE
            WHEN eir.subcontracting = 'Yes' THEN sup.supplier_name
            ELSE emp.employee_name
        END
    """
    return frappe.db.sql(sql, params, as_dict=True)