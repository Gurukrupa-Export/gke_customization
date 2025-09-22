# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data

def get_columns():
    return [
        {"label": "Manufacturing Work Order", "fieldname": "manufacturing_work_order", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 250},
        {"label": "Waxset Diamond Quantity", "fieldname": "waxing_diamond_wt", "fieldtype": "Float", "width": 150},
        {"label": "Waxing Diamond PCS", "fieldname": "waxing_diamond_pcs", "fieldtype": "Int", "width": 150},
        {"label": "Goldset Diamond Quantity", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 150},
        {"label": "Goldset Diamond PCS", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 150},
        {"label": "Total Quantity", "fieldname": "setting_total_wt", "fieldtype": "Float", "width": 150},
        {"label": "Total PCS", "fieldname": "setting_total_pcs", "fieldtype": "Int", "width": 150},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": "Item Category", "fieldname": "item_category", "fieldtype": "Data", "width": 130},
        {"label": "Item Sub Category", "fieldname": "item_sub_category", "fieldtype": "Data", "width": 130},
        {"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Link","options": "Serial No","width": 130}
    ]

def get_data(filters):
    condition_sql, values = get_conditions(filters or {})

    base_conditions = "wx.waxing_count IS NOT NULL AND ds.setting_count IS NOT NULL"
    if condition_sql:
        full_conditions = f"{base_conditions} AND {condition_sql}"
    else:
        full_conditions = base_conditions

    query = f"""
    SELECT 
        mwo.name AS manufacturing_work_order,
        mwo.item_code AS item_code,
        mwo.item_category,
        mwo.item_sub_category,
        wx.waxing_diamond_wt AS waxing_diamond_wt,
        wx.waxing_diamond_pcs AS waxing_diamond_pcs,
        ds.setting_total_wt AS setting_total_wt,
        ds.setting_total_pcs AS setting_total_pcs,
        (ds.setting_total_wt - wx.waxing_diamond_wt) AS diamond_wt,
        (ds.setting_total_pcs - wx.waxing_diamond_pcs) AS diamond_pcs,
        bom.tag_no AS serial_no
    FROM `tabManufacturing Work Order` mwo
    LEFT JOIN (
        SELECT
            manufacturing_work_order,
            COUNT(*) AS waxing_count,
            SUM(diamond_wt) AS waxing_diamond_wt,
            SUM(diamond_pcs) AS waxing_diamond_pcs
        FROM `tabManufacturing Operation`
        WHERE department = 'Waxing 2 - GEPL'
          AND previous_operation = 'D Wax'
          AND operation IS NULL
        GROUP BY manufacturing_work_order
    ) wx ON wx.manufacturing_work_order = mwo.name
    LEFT JOIN (
        SELECT
            manufacturing_work_order,
            COUNT(*) AS setting_count,
            SUM(diamond_wt) AS setting_total_wt,
            SUM(diamond_pcs) AS setting_total_pcs
        FROM `tabManufacturing Operation`
        WHERE operation IN ('Diamond Setting TR', 'Diamond Setting RU', 'Diamond Setting SW')
        GROUP BY manufacturing_work_order
    ) ds ON ds.manufacturing_work_order = mwo.name
    LEFT JOIN `tabSerial Number Creator` snc
      ON mwo.manufacturing_order = snc.parent_manufacturing_order
      AND mwo.department = 'Tagging - GEPL'
    LEFT JOIN `tabBOM` bom ON snc.name = bom.custom_serial_number_creator
    WHERE {full_conditions}
    ORDER BY mwo.creation DESC
    """

    data = frappe.db.sql(query, values, as_dict=True)
    return data

def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get('manufacturing_work_order'):
        conditions.append("mwo.name = %(manufacturing_work_order)s")
        values['manufacturing_work_order'] = filters['manufacturing_work_order']

    if filters.get('serial_no'):
        conditions.append("bom.tag_no = %(serial_no)s")
        values['serial_no'] = filters['serial_no']

    if filters.get('item_category'):
        conditions.append("mwo.item_category = %(item_category)s")
        values['item_category'] = filters['item_category']

    if filters.get('from_date'):
        conditions.append("mwo.creation >= %(from_date)s")
        values['from_date'] = filters['from_date']

    if filters.get('to_date'):
        conditions.append("mwo.creation <= %(to_date)s")
        values['to_date'] = filters['to_date']

    condition_sql = " AND ".join(conditions) if conditions else ""
    return condition_sql, values