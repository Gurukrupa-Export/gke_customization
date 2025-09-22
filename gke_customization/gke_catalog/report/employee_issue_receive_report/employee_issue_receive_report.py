# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data

def get_columns():
    return [
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Employee IR ID", "fieldname": "employee_ir_id", "fieldtype": "Link", "options": "Employee IR", "width": 150},
        {"label": "Manufacturer", "fieldname": "manufacturer", "fieldtype": "Link", "options": "Manufacturer", "width": 150},
        {"label": "Datetime", "fieldname": "date_time", "fieldtype": "Datetime", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 120},
        {"label": "Operation", "fieldname": "operation", "fieldtype": "Link", "options": "Operation", "width": 120},
        {"label": "Subcontractor", "fieldname": "subcontractor", "fieldtype": "Link", "options": "Supplier", "width": 120},
        {"label": "Main Slip", "fieldname": "main_slip", "fieldtype": "Link", "options": "Main Slip", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Gross Wt", "fieldname": "gross_wt", "fieldtype": "Float", "width": 100},
        {"label": "Net Wt", "fieldname": "net_wt", "fieldtype": "Float", "width": 100},
        {"label": "Finding Wt", "fieldname": "finding_wt", "fieldtype": "Float", "width": 100},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 100},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Gemstone pcs", "fieldname": "gemstone_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Gemstone Wt", "fieldname": "gemstone_wt", "fieldtype": "Float", "width": 100},
        {"label": "Other Wt", "fieldname": "other_wt", "fieldtype": "Float", "width": 100},
        {"label": "Received Gross Wt", "fieldname": "received_gross_wt", "fieldtype": "Float", "width": 120},
        {"label": "Loss Qty", "fieldname": "loss_qty", "fieldtype": "Float", "width": 100},
        {"label": "Manual Loss", "fieldname": "manual_loss", "fieldtype": "Float", "width": 100},
        
        {"label": "Time Between Issue receive MOP", "fieldname": "time_between", "fieldtype": "Data", "width": 150},
    ]

def get_data(filters):
    condition_sql, values = get_conditions(filters)
    raw_data = frappe.db.sql(f"""
    SELECT
        EIR.company,
        EIR.name AS employee_ir_id,
        EIR.manufacturer,
        EIR.date_time,
        EIR.department,
        EIR.type,
        EIR.operation,
        EIR.subcontractor AS subcontractor,
        EIR.main_slip,
        EIR.employee,
        ROUND(COALESCE(EIRO.gross_wt, 0), 3) AS gross_wt,
        ROUND(COALESCE(EIRO.net_wt, 0), 3) AS net_wt,
        ROUND(COALESCE(EIRO.finding_wt, 0), 3) AS finding_wt,
        COALESCE(EIRO.diamond_pcs, 0) AS diamond_pcs,
        ROUND(COALESCE(EIRO.diamond_wt, 0), 3) AS diamond_wt,
        COALESCE(EIRO.gemstone_pcs, 0) AS gemstone_pcs,
        ROUND(COALESCE(EIRO.gemstone_wt, 0), 3) AS gemstone_wt,
        ROUND(COALESCE(EIRO.other_wt, 0), 3) AS other_wt,
        ROUND(COALESCE(EIRO.received_gross_wt, 0), 3) AS received_gross_wt,
        ROUND(COALESCE(ELD.loss_qty, 0), 3) AS loss_qty,
        ROUND(COALESCE(MBLD.manual_loss, 0), 3) AS manual_loss,
        MOP.status,
        CONCAT(
    LPAD(HOUR(TIME(MOPTL.time_in_hour)), 2, '0'), 'h:',
    LPAD(MINUTE(TIME(MOPTL.time_in_hour)), 2, '0'), 'm:',
    LPAD(SECOND(TIME(MOPTL.time_in_hour)), 2, '0'), 's'
    ) AS time_between
    FROM `tabEmployee IR` EIR
    LEFT JOIN (
        SELECT 
            parent,
            SUM(gross_wt) AS gross_wt,
            SUM(net_wt) AS net_wt,
            SUM(finding_wt) AS finding_wt,
            SUM(diamond_pcs) AS diamond_pcs,
            SUM(diamond_wt) AS diamond_wt,
            SUM(gemstone_pcs) AS gemstone_pcs,
            SUM(gemstone_wt) AS gemstone_wt,
            SUM(other_wt) AS other_wt,
            SUM(received_gross_wt) AS received_gross_wt
        FROM `tabEmployee IR Operation`
        GROUP BY parent
    ) EIRO ON EIR.name = EIRO.parent
    LEFT JOIN (
        SELECT 
            parent,
            SUM(proportionally_loss) AS loss_qty
        FROM `tabEmployee Loss Details`
        GROUP BY parent
    ) ELD ON EIR.name = ELD.parent
    LEFT JOIN (
        SELECT 
            parent,
            SUM(proportionally_loss) AS manual_loss
    FROM `tabManually Book Loss Details`
        GROUP BY parent
    ) MBLD ON EIR.name = MBLD.parent
    LEFT JOIN `tabEmployee IR Operation` EIROLOOKUP ON EIR.name = EIROLOOKUP.parent
    LEFT JOIN `tabManufacturing Operation` MOP ON EIROLOOKUP.manufacturing_operation = MOP.name
    LEFT JOIN `tabManufacturing Operation Time Log` MOPTL ON MOP.name = MOPTL.parent
    {condition_sql}
    GROUP BY
        EIR.name,
        EIR.company,
        EIR.manufacturer,
        EIR.date_time,
        EIR.department,
        EIR.type,
        EIR.operation,
        EIR.subcontractor,
        EIR.main_slip,
        EIR.employee,
        MOP.status,
        EIRO.gross_wt,
        EIRO.net_wt,
        EIRO.finding_wt,
        EIRO.diamond_pcs,
        EIRO.diamond_wt,
        EIRO.gemstone_pcs,
        EIRO.gemstone_wt,
        EIRO.other_wt,
        EIRO.received_gross_wt,
        ELD.loss_qty,
        MBLD.manual_loss
        ORDER BY EIR.date_time DESC
    """, values, as_dict=True)
    return raw_data

from datetime import datetime, timedelta

def get_conditions(filters):
    conditions = []
    values = {}

    if not filters.get("from_date"):
        today = datetime.today().date()
        last_10_days = today - timedelta(days=10)
        conditions.append("EIR.date_time >= %(last_10_days)s")
        values["last_10_days"] = last_10_days.strftime("%Y-%m-%d")

    if filters.get("type"):
        conditions.append("EIR.type = %(type)s")
        values["type"] = filters["type"]

    if filters.get("department"):
        conditions.append("EIR.department = %(department)s")
        values["department"] = filters["department"]

    if filters.get("employee"):
        conditions.append("EIR.employee = %(employee)s")
        values["employee"] = filters["employee"]

    if filters.get("from_date"):
        conditions.append("EIR.date_time >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("EIR.date_time <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    condition_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
    return condition_sql, values