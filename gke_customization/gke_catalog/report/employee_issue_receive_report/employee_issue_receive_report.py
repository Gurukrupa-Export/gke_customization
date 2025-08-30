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
        {"label": "Manufacturer", "fieldname": "manufacturer", "fieldtype": "Link", "options": "Manufacturer", "width": 150},
        {"label": "Datetime", "fieldname": "date_time", "fieldtype": "Datetime", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 120},
        {"label": "Operation", "fieldname": "operation", "fieldtype": "Link", "options": "Operation", "width": 120},
        {"label": "Subcontracting", "fieldname": "subcontracting", "fieldtype": "Data", "width": 120},
        {"label": "Subcontractor", "fieldname": "subcontractor", "fieldtype": "Link", "options": "Supplier", "width": 120},
        {"label": "Main Slip", "fieldname": "main_slip", "fieldtype": "Link", "options": "Main Slip", "width": 120},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Gross Wt", "fieldname": "gross_wt", "fieldtype": "Float", "width": 100},
        {"label": "Net Wt", "fieldname": "net_wt", "fieldtype": "Float", "width": 100},
        {"label": "Finding Wt", "fieldname": "finding_wt", "fieldtype": "Float", "width": 100},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 100},
        {"label": "Gemstone pcs", "fieldname": "gemstone_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Gemstone Wt", "fieldname": "gemstone_wt", "fieldtype": "Float", "width": 100},
        {"label": "Other Wt", "fieldname": "other_wt", "fieldtype": "Float", "width": 100},
        {"label": "Received Gross Wt", "fieldname": "received_gross_wt", "fieldtype": "Float", "width": 120},
        {"label": "Loss Qty", "fieldname": "loss_qty", "fieldtype": "Float", "width": 100},
        {"label": "Manual Loss", "fieldname": "manual_loss", "fieldtype": "Float", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Time Between Issue receive MOP", "fieldname": "time_between", "fieldtype": "Data", "width": 150},
    ]

def get_data(filters):
    condition_sql, values = get_conditions(filters)
    raw_data = frappe.db.sql(f"""
        SELECT
            EIR.company,
            EIR.manufacturer,
            EIR.date_time,
            EIR.department,
            EIR.type,
            EIR.operation,
            EIR.subcontracting,
            EIR.subcontractor AS subcontractor,
            EIR.main_slip,
            EIR.employee,
            SUM(EIRO.gross_wt) AS gross_wt,
            SUM(EIRO.net_wt) AS net_wt,
            SUM(EIRO.finding_wt) AS finding_wt,
            SUM(EIRO.diamond_pcs) AS diamond_pcs,
            SUM(EIRO.diamond_wt) AS diamond_wt,
            SUM(EIRO.gemstone_pcs) AS gemstone_pcs,
            SUM(EIRO.gemstone_wt) AS gemstone_wt,
            SUM(EIRO.other_wt) AS other_wt,
            SUM(EIRO.received_gross_wt) AS received_gross_wt,
            SUM(ELD.proportionally_loss) AS loss_qty,
            SUM(MBLD.proportionally_loss) AS manual_loss,
            MOP.status,
            CONCAT(
                LPAD(HOUR(SEC_TO_TIME(SUM(TIMESTAMPDIFF(SECOND, MOPTL.from_time, MOPTL.to_time)))), 2, '0'), 'h:',
                LPAD(MINUTE(SEC_TO_TIME(SUM(TIMESTAMPDIFF(SECOND, MOPTL.from_time, MOPTL.to_time)))), 2, '0'), 'm:',
                LPAD(SECOND(SEC_TO_TIME(SUM(TIMESTAMPDIFF(SECOND, MOPTL.from_time, MOPTL.to_time)))), 2, '0'), 's'
            ) AS time_between
        FROM `tabEmployee IR` EIR
        LEFT JOIN `tabEmployee IR Operation` EIRO ON EIR.name = EIRO.parent
        LEFT JOIN `tabEmployee Loss Details` ELD ON EIR.name = ELD.parent
        LEFT JOIN `tabManually Book Loss Details` MBLD ON EIR.name = MBLD.parent
        LEFT JOIN `tabManufacturing Operation` MOP ON EIRO.manufacturing_operation = MOP.name
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
            EIR.subcontracting,
            EIR.subcontractor,
            EIR.main_slip,
            EIR.employee,
            MOP.status
    """, values, as_dict=True)
    return raw_data

def get_conditions(filters):
    conditions = []
    values = {}

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
