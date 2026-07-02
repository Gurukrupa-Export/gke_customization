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
        IFNULL(SUM(CASE WHEN mbld.loss_type='Broken' THEN mbld.proportionally_loss*IFNULL(dr.diamond_rate,0) ELSE 0 END),0) AS broken_amt,
        IFNULL(SUM(CASE WHEN mbld.loss_type='Loss' THEN mbld.proportionally_loss ELSE 0 END),0) AS lost_wt,
        IFNULL(SUM(CASE WHEN mbld.loss_type='Loss' THEN mbld.pcs ELSE 0 END),0) AS lost_pcs,
        IFNULL(SUM(CASE WHEN mbld.loss_type='Loss' THEN mbld.proportionally_loss*IFNULL(dr.diamond_rate,0) ELSE 0 END),0) AS lost_amt,
        IFNULL(SUM(CASE WHEN mbld.loss_type IN ('Broken','Loss') THEN mbld.proportionally_loss ELSE 0 END),0) AS total_wt,
        IFNULL(SUM(CASE WHEN mbld.loss_type IN ('Broken','Loss') THEN mbld.pcs ELSE 0 END),0) AS total_pcs,
        IFNULL(SUM(CASE WHEN mbld.loss_type IN ('Broken','Loss') THEN mbld.proportionally_loss*IFNULL(dr.diamond_rate,0) ELSE 0 END),0) AS total_amt,
        dop.department AS lost_department
    FROM `tabEmployee IR` eir
    LEFT JOIN `tabEmployee` emp ON emp.name=eir.employee
    LEFT JOIN `tabSupplier` sup ON sup.name=eir.subcontractor
    LEFT JOIN `tabManually Book Loss Details` mbld ON mbld.parent=eir.name
    LEFT JOIN `tabDepartment Operation` dop ON dop.operation=eir.operation
    LEFT JOIN `tabEmployee IR Operation` eiro ON eiro.parent=eir.name
    LEFT JOIN (
        SELECT manufacturing_operation, MAX(basic_rate) AS diamond_rate
        FROM `tabMOP Balance Table`
        WHERE item_code LIKE 'D-%%'
        GROUP BY manufacturing_operation
    ) dr ON dr.manufacturing_operation=eiro.manufacturing_operation
    WHERE eir.docstatus=1
      AND mbld.loss_type IN ('Broken','Loss')
      {conditions}
    GROUP BY
        emp.employee_name,
        sup.supplier_name,
        eir.subcontracting,
        dop.department
    ORDER BY
        CASE
            WHEN eir.subcontracting='Yes' THEN sup.supplier_name
            ELSE emp.employee_name
        END
    """
    return frappe.db.sql(sql, params, as_dict=True)
