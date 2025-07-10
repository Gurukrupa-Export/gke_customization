import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    if not filters or not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select both From Date and To Date")
    
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Week Ending", "fieldname": "week_ending", "fieldtype": "Date", "width": 110},
        {"label": "24KT Qty", "fieldname": "gold_24kt_qty", "fieldtype": "Data", "width": 110},
        {"label": "24KT Rate", "fieldname": "gold_24kt_rate", "fieldtype": "Currency", "width": 110},
        {"label": "24KT Value", "fieldname": "gold_24kt_value", "fieldtype": "Currency", "width": 110},
        {"label": "22KT Qty", "fieldname": "gold_22kt_qty", "fieldtype": "Data", "width": 110},
        {"label": "22KT Rate", "fieldname": "gold_22kt_rate", "fieldtype": "Currency", "width": 110},
        {"label": "22KT Value", "fieldname": "gold_22kt_value", "fieldtype": "Currency", "width": 110},
        {"label": "18KT Qty", "fieldname": "gold_18kt_qty", "fieldtype": "Data", "width": 110},
        {"label": "18KT Rate", "fieldname": "gold_18kt_rate", "fieldtype": "Currency", "width": 110},
        {"label": "18KT Value", "fieldname": "gold_18kt_value", "fieldtype": "Currency", "width": 110},
        {"label": "Other Gold Qty", "fieldname": "gold_other_qty", "fieldtype": "Data", "width": 130},
        {"label": "Other Gold Rate", "fieldname": "gold_other_rate", "fieldtype": "Currency", "width": 130},
        {"label": "Other Gold Value", "fieldname": "gold_other_value", "fieldtype": "Currency", "width": 130},
    ]

def get_data(filters):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d")
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d")

    # Get all Fridays in the range
    fridays = []
    current = from_date
    while current <= to_date:
        if current.weekday() == 4:  # Friday
            fridays.append(current)
        current += timedelta(days=1)

    data = []

    for friday in fridays:
        date_str = friday.strftime("%Y-%m-%d")

        row = frappe.db.sql("""
            SELECT
                -- 24KT
                SUM(CASE WHEN i.item_name LIKE '%%24KT%%' THEN sle.actual_qty ELSE 0 END) AS gold_24kt_qty,
                SUM(CASE WHEN i.item_name LIKE '%%24KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END) AS gold_24kt_value,
                SUM(CASE WHEN i.item_name LIKE '%%24KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END)
                / NULLIF(SUM(CASE WHEN i.item_name LIKE '%%24KT%%' THEN sle.actual_qty ELSE 0 END), 0) AS gold_24kt_rate,

                -- 22KT
                SUM(CASE WHEN i.item_name LIKE '%%22KT%%' THEN sle.actual_qty ELSE 0 END) AS gold_22kt_qty,
                SUM(CASE WHEN i.item_name LIKE '%%22KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END) AS gold_22kt_value,
                SUM(CASE WHEN i.item_name LIKE '%%22KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END)
                / NULLIF(SUM(CASE WHEN i.item_name LIKE '%%22KT%%' THEN sle.actual_qty ELSE 0 END), 0) AS gold_22kt_rate,

                -- 18KT
                SUM(CASE WHEN i.item_name LIKE '%%18KT%%' THEN sle.actual_qty ELSE 0 END) AS gold_18kt_qty,
                SUM(CASE WHEN i.item_name LIKE '%%18KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END) AS gold_18kt_value,
                SUM(CASE WHEN i.item_name LIKE '%%18KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END)
                / NULLIF(SUM(CASE WHEN i.item_name LIKE '%%18KT%%' THEN sle.actual_qty ELSE 0 END), 0) AS gold_18kt_rate,

                -- Others
                SUM(CASE WHEN i.item_name NOT LIKE '%%24KT%%' AND i.item_name NOT LIKE '%%22KT%%' AND i.item_name NOT LIKE '%%18KT%%' THEN sle.actual_qty ELSE 0 END) AS gold_other_qty,
                SUM(CASE WHEN i.item_name NOT LIKE '%%24KT%%' AND i.item_name NOT LIKE '%%22KT%%' AND i.item_name NOT LIKE '%%18KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END) AS gold_other_value,
                SUM(CASE WHEN i.item_name NOT LIKE '%%24KT%%' AND i.item_name NOT LIKE '%%22KT%%' AND i.item_name NOT LIKE '%%18KT%%' THEN sle.actual_qty * sle.valuation_rate ELSE 0 END)
                / NULLIF(SUM(CASE WHEN i.item_name NOT LIKE '%%24KT%%' AND i.item_name NOT LIKE '%%22KT%%' AND i.item_name NOT LIKE '%%18KT%%' THEN sle.actual_qty ELSE 0 END), 0) AS gold_other_rate
            FROM `tabStock Ledger Entry` sle
            JOIN `tabItem` i ON sle.item_code = i.name
            WHERE sle.posting_date = %s
              AND sle.docstatus < 2
              AND sle.actual_qty > 0
              AND i.item_name LIKE '%%-G-%%'
        """, (date_str,), as_dict=True)[0]

        def format_qty(val):
            return f"{round(val or 0, 2):.2f} g"

        data.append({
            "week_ending": date_str,
            "gold_24kt_qty": format_qty(row.gold_24kt_qty),
            "gold_24kt_rate": round(row.gold_24kt_rate or 0, 2),
            "gold_24kt_value": round(row.gold_24kt_value or 0, 2),

            "gold_22kt_qty": format_qty(row.gold_22kt_qty),
            "gold_22kt_rate": round(row.gold_22kt_rate or 0, 2),
            "gold_22kt_value": round(row.gold_22kt_value or 0, 2),

            "gold_18kt_qty": format_qty(row.gold_18kt_qty),
            "gold_18kt_rate": round(row.gold_18kt_rate or 0, 2),
            "gold_18kt_value": round(row.gold_18kt_value or 0, 2),

            "gold_other_qty": format_qty(row.gold_other_qty),
            "gold_other_rate": round(row.gold_other_rate or 0, 2),
            "gold_other_value": round(row.gold_other_value or 0, 2),
        })

    return data
