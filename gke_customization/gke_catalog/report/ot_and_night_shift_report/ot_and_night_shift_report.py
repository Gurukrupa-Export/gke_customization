# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data

def get_columns():
    return [
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": "Unit", "fieldname": "unit", "fieldtype": "Data", "width": 80},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 220},
        {"label": "Shift End", "fieldname": "shift_end_time", "fieldtype": "Time", "width": 100},
        {"label": "OT Hours", "fieldname": "formatted_ot_hours", "fieldtype": "Data", "width": 125},
        {"label": "OT Employee Count", "fieldname": "ot_employee_count", "fieldtype": "Int", "width": 190},
        # {"label": "Full Night", "fieldname": "full_night", "fieldtype": "Data", "width": 170},
        {"label": "Full Night Employee Count", "fieldname": "fn_employee_count", "fieldtype": "Int", "width": 200},
        {"label": "Total Employees", "fieldname": "total", "fieldtype": "Int", "width": 150},
        {"label": "OT Reason", "fieldname": "remark", "fieldtype": "Data", "width": 180},
        {"label": "Food Eligibility", "fieldname": "food_eligibility", "fieldtype": "Data", "width": 130},
    ]

def get_data(filters):
    condition_sql, values = get_conditions(filters)

    raw_data = frappe.db.sql(f"""
        SELECT
            emp.manufacturer AS unit,
            otr.department AS department,
            sf.end_time AS shift_end_time,
            otrd.reason_for_ot AS remark,
            otrd.ot_hours AS ot_hours,
            otr.date AS date,
            COUNT(CASE WHEN otrd.food_eligibility = 'Eligible' THEN 1 ELSE 0 END) AS food_eligibility,
            COUNT(otrd.employee_id) AS ot_employee_count
        FROM `tabOT Request` otr
        LEFT JOIN `tabOvertime Request Details` otrd ON otrd.parent = otr.name
        LEFT JOIN `tabEmployee` emp ON otrd.employee_id = emp.name
        LEFT JOIN `tabShift Type` sf ON emp.default_shift = sf.name
        WHERE otr.workflow_state = 'Approved'
        {condition_sql} 
        GROUP BY otr.name, otrd.ot_hours,otrd.reason_for_ot,sf.end_time
        ORDER BY otr.date DESC
    """, values, as_dict=True)


    for row in raw_data:
        row["formatted_ot_hours"] = format_ot_hours(row["ot_hours"])
        row["total"] = row["ot_employee_count"] + 0

    return raw_data


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("date"):
        conditions.append("otr.date = %(date)s")
        values["date"] = filters["date"]

    if filters.get("manufacturer"):
        conditions.append("emp.manufacturer = %(manufacturer)s")
        values["manufacturer"] = filters["manufacturer"]

    if filters.get("department"):
        conditions.append("emp.department IN %(department)s")
        values["department"] = tuple(filters["department"])

    if filters.get("branch"):
        conditions.append("emp.branch IN %(branch)s")
        values["branch"] = tuple(filters["branch"])
        
    return " AND " + " AND ".join(conditions) if conditions else "", values


from datetime import timedelta

def format_ot_hours(time_str):
    if not time_str:
        return ""
    try:
        h, m, s = map(int, str(time_str).split(":"))
    except Exception:
        return str(time_str)
    parts = []
    if h:
        parts.append(f"{h} h")
    if m:
        parts.append(f"{m} m")
    if s:
        parts.append(f"{s} s")

    return ": ".join(parts) if parts else "0 sec"

