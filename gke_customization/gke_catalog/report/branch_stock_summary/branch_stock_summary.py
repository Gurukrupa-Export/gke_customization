# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
import json
import re


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if filters.get("company") == "Gurukrupa Export Private Limited" and not filters.get("branch"):
        frappe.throw(_("Branch is required for Gurukrupa Export Private Limited"))
    if not filters.get("raw_material_type"):
        frappe.throw(_("Raw Material Type is required"))

    return get_branch_stock_summary_optimized(filters)


def get_branch_stock_summary_optimized(filters=None):
    columns = [
        {"fieldname": "section_name", "label": "Department", "fieldtype": "Data", "width": 400},
        {"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "pure_gold_weight", "label": "Pure Gold Weight", "fieldtype": "Float", "width": 170, "precision": 3},
        {"fieldname": "view_details", "label": "View Details", "fieldtype": "Data", "width": 120}
    ]

    raw_material_types = [filters.get("raw_material_type")]
    item_groups = get_item_groups(raw_material_types)
    variant_codes = get_variant_codes(raw_material_types)
    item_group_str = "', '".join(item_groups) if item_groups else ""
    variant_code_str = "', '".join(variant_codes) if variant_codes else ""
    today = getdate()
    company = filters.get("company")
    manufacturer = filters.get("manufacturer", "")

    departments = get_departments_list(filters)
    if not departments:
        return columns, []

    dept_list = [d["db_department"] for d in departments]
    dept_str = "', '".join(dept_list)

    bulk_stock_data = get_bulk_stock_data(
        company, dept_str, item_group_str, variant_code_str,
        today, manufacturer, raw_material_types, dept_list
    )

    data = []
    grand_total = 0.0
    grand_total_pure_gold = 0.0

    for dept_info in departments:
        dept_name = dept_info["department"]
        dept_with_suffix = dept_info["db_department"]

        stock_values = extract_dept_stock_from_bulk(dept_with_suffix, bulk_stock_data)
        section_data = build_department_section_simplified(dept_name, stock_values)
        data.extend(section_data)

        dept_total, dept_total_pure_gold = add_department_total_row_simplified(
            data, section_data, f"{dept_name} Total"
        )
        grand_total += dept_total
        grand_total_pure_gold += dept_total_pure_gold

    if grand_total > 0 or grand_total_pure_gold > 0:
        data.append({
            "section_name": "Grand Total",
            "section": "Grand Total",
            "parent_section": None,
            "indent": 0.0,
            "quantity": grand_total if grand_total != 0 else "",
            "pure_gold_weight": grand_total_pure_gold if grand_total_pure_gold != 0 else "",
            "view_details": "",
            "is_grand_total": True
        })

    return columns, data


def get_bulk_stock_data(company, dept_str, item_group_str, variant_code_str, today, manufacturer, raw_material_types, dept_list):
    bulk_data = {
        "work_order": {},
        "employee_wip": {},
        "supplier_wip": {},
        "employee_msl": {},
        "supplier_msl": {},
        "employee_msl_hold": {},
        "supplier_msl_hold": {},
        "transit": {},
        "raw_material": {},
        "reserve": {},
        "scrap": {},
        "finished_goods": {}
    }

    is_metal = "Metal" in raw_material_types

    weight_fields = []
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            weight_fields.append("COALESCE(mop.net_wt, 0)")
        elif rm_type == "Diamond":
            weight_fields.append("COALESCE(mop.diamond_wt, 0)")
        elif rm_type == "Gemstone":
            weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
        elif rm_type == "Finding":
            weight_fields.append("COALESCE(mop.finding_wt, 0)")
        elif rm_type == "Aloy":
            weight_fields.append("COALESCE(mop.alloy_wt, 0)")
        elif rm_type == "Other":
            weight_fields.append("COALESCE(mop.other_wt, 0)")

    weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
    manufacturer_condition = f" AND mop.manufacturer = '{manufacturer}'" if manufacturer else ""

    try:
        wo_result = frappe.db.sql(f"""
            SELECT
                mop.department,
                SUM({weight_sum}) as total_balance,
                SUM(
                    CASE
                        WHEN {1 if is_metal else 0} = 1
                        THEN COALESCE(mop.net_wt, 0) * COALESCE(mwo.metal_purity, 0) / 100
                        ELSE 0
                    END
                ) as pure_gold_weight
            FROM `tabManufacturing Operation` mop
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'Not Started'
              AND mop.department IN ('{dept_str}')
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              {manufacturer_condition}
            GROUP BY mop.department
        """, as_dict=True)

        for row in wo_result:
            bulk_data["work_order"][row.department] = {
                "quantity": flt(row.total_balance),
                "pure_gold_weight": flt(row.pure_gold_weight)
            }

        emp_wip_result = frappe.db.sql(f"""
            SELECT
                mop.department,
                SUM({weight_sum}) as total_balance,
                SUM(
                    CASE
                        WHEN {1 if is_metal else 0} = 1
                        THEN COALESCE(mop.net_wt, 0) * COALESCE(mwo.metal_purity, 0) / 100
                        ELSE 0
                    END
                ) as pure_gold_weight
            FROM `tabManufacturing Operation` mop
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 0
              AND mop.department IN ('{dept_str}')
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              {manufacturer_condition}
            GROUP BY mop.department
        """, as_dict=True)

        for row in emp_wip_result:
            bulk_data["employee_wip"][row.department] = {
                "quantity": flt(row.total_balance),
                "pure_gold_weight": flt(row.pure_gold_weight)
            }

        sup_wip_result = frappe.db.sql(f"""
            SELECT
                mop.department,
                SUM({weight_sum}) as total_balance,
                SUM(
                    CASE
                        WHEN {1 if is_metal else 0} = 1
                        THEN COALESCE(mop.net_wt, 0) * COALESCE(mwo.metal_purity, 0) / 100
                        ELSE 0
                    END
                ) as pure_gold_weight
            FROM `tabManufacturing Operation` mop
            INNER JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 1
              AND mop.department IN ('{dept_str}')
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              {manufacturer_condition}
            GROUP BY mop.department
        """, as_dict=True)

        for row in sup_wip_result:
            bulk_data["supplier_wip"][row.department] = {
                "quantity": flt(row.total_balance),
                "pure_gold_weight": flt(row.pure_gold_weight)
            }

        if variant_code_str:
            manufacturer_condition_ms = f" AND ms.manufacturer = '{manufacturer}'" if manufacturer else ""

            emp_msl_result = frappe.db.sql(f"""
                SELECT
                    ms.department,
                    SUM(mse.qty) as total_qty,
                    SUM(
                        CASE
                            WHEN {1 if is_metal else 0} = 1
                            THEN COALESCE(mse.qty, 0) * COALESCE(ms.metal_purity, 0) / 100
                            ELSE 0
                        END
                    ) as pure_gold_weight
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use'
                  AND ms.for_subcontracting = 0
                  AND ms.department IN ('{dept_str}')
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, as_dict=True)

            for row in emp_msl_result:
                bulk_data["employee_msl"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight)
                }

            emp_msl_hold_result = frappe.db.sql(f"""
                SELECT
                    ms.department,
                    SUM(mse.qty) as total_qty,
                    SUM(
                        CASE
                            WHEN {1 if is_metal else 0} = 1
                            THEN COALESCE(mse.qty, 0) * COALESCE(ms.metal_purity, 0) / 100
                            ELSE 0
                        END
                    ) as pure_gold_weight
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold'
                  AND ms.for_subcontracting = 0
                  AND ms.department IN ('{dept_str}')
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, as_dict=True)

            for row in emp_msl_hold_result:
                bulk_data["employee_msl_hold"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight)
                }

            sup_msl_result = frappe.db.sql(f"""
                SELECT
                    ms.department,
                    SUM(mse.qty) as total_qty,
                    SUM(
                        CASE
                            WHEN {1 if is_metal else 0} = 1
                            THEN COALESCE(mse.qty, 0) * COALESCE(ms.metal_purity, 0) / 100
                            ELSE 0
                        END
                    ) as pure_gold_weight
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use'
                  AND ms.for_subcontracting = 1
                  AND ms.department IN ('{dept_str}')
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, as_dict=True)

            for row in sup_msl_result:
                bulk_data["supplier_msl"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight)
                }

            sup_msl_hold_result = frappe.db.sql(f"""
                SELECT
                    ms.department,
                    SUM(mse.qty) as total_qty,
                    SUM(
                        CASE
                            WHEN {1 if is_metal else 0} = 1
                            THEN COALESCE(mse.qty, 0) * COALESCE(ms.metal_purity, 0) / 100
                            ELSE 0
                        END
                    ) as pure_gold_weight
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold'
                  AND ms.for_subcontracting = 1
                  AND ms.department IN ('{dept_str}')
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, as_dict=True)

            for row in sup_msl_hold_result:
                bulk_data["supplier_msl_hold"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight)
                }

        if item_group_str:
            for dept_with_suffix in dept_list:
                dept_clean = dept_with_suffix.split(' - ')[0].strip()

                transit_result = frappe.db.sql(f"""
                    SELECT
                        sle.item_code,
                        SUM(sle.actual_qty) as weight
                    FROM `tabStock Ledger Entry` sle
                    INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = '{company}'
                      AND (
                            w.warehouse_name = '{dept_clean} Transit - GEPL'
                            OR w.warehouse_name = '{dept_clean} Transit - KGJPL'
                            OR w.warehouse_name = '{dept_clean} Transit'
                          )
                      AND i.item_group IN ('{item_group_str}')
                      AND sle.posting_date <= '{today}'
                      AND sle.docstatus < 2
                      AND sle.is_cancelled = 0
                    GROUP BY sle.item_code
                    HAVING SUM(sle.actual_qty) > 0
                """, as_dict=True)

                if transit_result:
                    qty = sum(flt(d.weight) for d in transit_result)
                    pure_gold = sum(get_pure_gold_from_item_code(d.item_code, d.weight) for d in transit_result) if is_metal else 0.0
                    bulk_data["transit"][dept_with_suffix] = {
                        "quantity": qty,
                        "pure_gold_weight": pure_gold
                    }

                raw_result = frappe.db.sql(f"""
                    SELECT
                        w.department,
                        sle.item_code,
                        SUM(sle.actual_qty) as weight
                    FROM `tabStock Ledger Entry` sle
                    INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = '{company}'
                      AND w.department = '{dept_with_suffix}'
                      AND w.warehouse_type = 'Raw Material'
                      AND i.item_group IN ('{item_group_str}')
                      AND sle.posting_date <= '{today}'
                      AND sle.docstatus < 2
                      AND sle.is_cancelled = 0
                    GROUP BY w.department, sle.item_code
                    HAVING SUM(sle.actual_qty) > 0
                """, as_dict=True)

                if raw_result:
                    qty = sum(flt(d.weight) for d in raw_result)
                    pure_gold = sum(get_pure_gold_from_item_code(d.item_code, d.weight) for d in raw_result) if is_metal else 0.0
                    bulk_data["raw_material"][dept_with_suffix] = {
                        "quantity": qty,
                        "pure_gold_weight": pure_gold
                    }

                reserve_result = frappe.db.sql(f"""
                    SELECT
                        sle.item_code,
                        SUM(sle.actual_qty) as weight
                    FROM `tabStock Ledger Entry` sle
                    INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = '{company}'
                      AND (
                            (w.warehouse_type = 'Reserve' AND w.department = '{dept_with_suffix}')
                            OR w.warehouse_name = '{dept_clean} Reserve - GEPL'
                            OR w.warehouse_name = '{dept_clean} Reserve - KGJPL'
                            OR w.warehouse_name = '{dept_clean} Reserve'
                          )
                      AND i.item_group IN ('{item_group_str}')
                      AND sle.posting_date <= '{today}'
                      AND sle.docstatus < 2
                      AND sle.is_cancelled = 0
                    GROUP BY sle.item_code
                    HAVING SUM(sle.actual_qty) > 0
                """, as_dict=True)

                if reserve_result:
                    qty = sum(flt(d.weight) for d in reserve_result)
                    pure_gold = sum(get_pure_gold_from_item_code(d.item_code, d.weight) for d in reserve_result) if is_metal else 0.0
                    bulk_data["reserve"][dept_with_suffix] = {
                        "quantity": qty,
                        "pure_gold_weight": pure_gold
                    }

                scrap_result = frappe.db.sql(f"""
                    SELECT
                        sle.item_code,
                        SUM(sle.actual_qty) as weight
                    FROM `tabStock Ledger Entry` sle
                    INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                    INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = '{company}'
                      AND (
                            (w.warehouse_type = 'Scrap' AND w.department = '{dept_with_suffix}')
                            OR w.warehouse_name = '{dept_clean} Scrap - GEPL'
                            OR w.warehouse_name = '{dept_clean} Scrap - KGJPL'
                            OR w.warehouse_name = '{dept_clean} Scrap'
                          )
                      AND i.item_group IN ('{item_group_str}')
                      AND sle.posting_date <= '{today}'
                      AND sle.docstatus < 2
                      AND sle.is_cancelled = 0
                    GROUP BY sle.item_code
                    HAVING SUM(sle.actual_qty) > 0
                """, as_dict=True)

                if scrap_result:
                    qty = sum(flt(d.weight) for d in scrap_result)
                    pure_gold = sum(get_pure_gold_from_item_code(d.item_code, d.weight) for d in scrap_result) if is_metal else 0.0
                    bulk_data["scrap"][dept_with_suffix] = {
                        "quantity": qty,
                        "pure_gold_weight": pure_gold
                    }

        for dept_with_suffix in dept_list:
            dept_clean = dept_with_suffix.replace(" - GEPL", "").replace(" - KGJPL", "")
            fg_result = frappe.db.sql(f"""
                SELECT COUNT(*) as total_count
                FROM `tabSerial No` sn
                INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
                WHERE sn.company = '{company}'
                  AND sn.status = 'Active'
                  AND w.warehouse_type = 'Finished Goods'
                  AND w.warehouse_name LIKE '%{dept_clean}%'
                  AND w.warehouse_name NOT LIKE '%MU%'
            """, as_dict=True)

            if fg_result and fg_result[0].get("total_count"):
                bulk_data["finished_goods"][dept_with_suffix] = {
                    "quantity": float(fg_result[0]["total_count"]),
                    "pure_gold_weight": 0.0
                }

    except Exception as e:
        frappe.log_error("Bulk stock data error", frappe.get_traceback())

    return bulk_data


def extract_dept_stock_from_bulk(dept_with_suffix, bulk_data):
    return {
        "work_order_stock": bulk_data["work_order"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "employee_wip_stock": bulk_data["employee_wip"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "supplier_wip_stock": bulk_data["supplier_wip"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "employee_msl_stock": bulk_data["employee_msl"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "supplier_msl_stock": bulk_data["supplier_msl"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "employee_msl_hold_stock": bulk_data["employee_msl_hold"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "supplier_msl_hold_stock": bulk_data["supplier_msl_hold"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "raw_material_stock": bulk_data["raw_material"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "reserve_stock": bulk_data["reserve"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "transit_stock": bulk_data["transit"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "scrap_stock": bulk_data["scrap"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "finished_goods": bulk_data["finished_goods"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0})
    }


def build_department_section_simplified(dept_name, stock_values):
    section_data = [{
        "section_name": f"{dept_name}",
        "parent_section": None,
        "indent": 0.0,
        "section": dept_name,
        "quantity": "",
        "pure_gold_weight": "",
        "view_details": "",
        "is_department_header": True
    }]

    stock_types = [
        {"key": "work_order_stock", "label": "Work Order Stock"},
        {"key": "employee_wip_stock", "label": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "label": "Supplier WIP Stock"},
        {"key": "employee_msl_stock", "label": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "label": "Supplier MSL Stock"},
        {"key": "employee_msl_hold_stock", "label": "Employee MSL Hold Stock"},
        {"key": "supplier_msl_hold_stock", "label": "Supplier MSL Hold Stock"},
        {"key": "raw_material_stock", "label": "Raw Material Stock"},
        {"key": "reserve_stock", "label": "Reserve Stock"},
        {"key": "transit_stock", "label": "Transit Stock"},
        {"key": "scrap_stock", "label": "Scrap Stock"},
        {"key": "finished_goods", "label": "Finished Goods"}
    ]

    for stock_type in stock_types:
        stock_entry = stock_values.get(stock_type["key"], {"quantity": 0.0, "pure_gold_weight": 0.0})
        stock_value = flt(stock_entry.get("quantity", 0.0))
        pure_gold_weight = flt(stock_entry.get("pure_gold_weight", 0.0))

        display_value = "" if stock_value == 0 else stock_value
        display_pure_gold = "" if pure_gold_weight == 0 else pure_gold_weight

        view_button = f'<button class="btn btn-xs btn-primary view-stock-details" data-department="{dept_name}" data-stock-type="{stock_type["label"]}" data-stock-key="{stock_type["key"]}">View</button>'

        section_data.append({
            "section_name": stock_type["label"],
            "section": stock_type["label"],
            "parent_section": dept_name,
            "indent": 1.0,
            "quantity": display_value,
            "pure_gold_weight": display_pure_gold,
            "view_details": view_button,
            "is_stock_type": True
        })

    return section_data


def add_department_total_row_simplified(data, section_data, label):
    total_quantity = sum(
        float(row.get("quantity", 0.0))
        for row in section_data
        if row.get("parent_section") and row.get("quantity") != "" and row.get("quantity") != 0
    )

    total_pure_gold = sum(
        float(row.get("pure_gold_weight", 0.0))
        for row in section_data
        if row.get("parent_section") and row.get("pure_gold_weight") != "" and row.get("pure_gold_weight") != 0
    )

    display_total = "" if total_quantity == 0 else total_quantity
    display_pure_gold = "" if total_pure_gold == 0 else total_pure_gold

    data.append({
        "section_name": f"{label}",
        "section": label,
        "parent_section": None,
        "indent": 0.0,
        "quantity": display_total,
        "pure_gold_weight": display_pure_gold,
        "view_details": "",
        "is_department_total": True
    })

    return total_quantity, total_pure_gold


def extract_purity_from_item_code(item_code):
    if not item_code:
        return 0.0

    match = re.search(r'-(\d+(?:\.\d+)?)($|-)', item_code)
    if match:
        return flt(match.group(1))

    return 0.0


def get_pure_gold_from_item_code(item_code, weight):
    purity = extract_purity_from_item_code(item_code)
    return flt(weight) * purity / 100 if purity else 0.0


def get_departments_list(filters):
    company = filters.get("company")
    branch = filters.get("branch", "")
    manufacturer = filters.get("manufacturer", "")
    department = filters.get("department")

    excluded_departments = ["Canteen", "HR", "Admin", "Security", "Housekeeping", "IT", "Transport", "Maintenance"]
    excluded_condition = " AND " + " AND ".join([f"mop.department NOT LIKE '%{dept}%'" for dept in excluded_departments])

    manufacturer_dept_condition = ""
    if manufacturer:
        allowed_departments = get_manufacturer_departments(manufacturer, company)
        if allowed_departments:
            dept_filter = "', '".join(allowed_departments)
            manufacturer_dept_condition = f" AND mop.department IN ('{dept_filter}')"

    dept_query = f"""
        SELECT DISTINCT
            REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') as department,
            mop.department as db_department
        FROM `tabManufacturing Operation` mop
        LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
        WHERE mwo.company = '{company}'
          AND mwo.docstatus = 1
          AND mop.department IS NOT NULL
          AND mop.department != ''
          {excluded_condition}
          {manufacturer_dept_condition}
    """

    if company == "Gurukrupa Export Private Limited" and branch:
        dept_query += f" AND mwo.branch = '{branch}'"

    if department:
        clean_department = department.replace(" - GEPL", "").replace(" - KGJPL", "").strip()
        dept_query += f" AND REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') = '{clean_department}'"

    dept_query += " ORDER BY mop.department"

    try:
        return frappe.db.sql(dept_query, as_dict=True)
    except Exception:
        frappe.log_error("Department query error", frappe.get_traceback())
        return []


def get_manufacturer_departments(manufacturer, company):
    dept_mapping = {
        "Siddhi": ["Nandi"],
        "Service Center": ["Product Repair Center"],
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"],
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"],
        "Labh": ["Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Diamond Setting", "Final Polish", "Manufacturing Plan & Management", "Model Making", "Pre Polish", "Product Certification", "Sub Contracting", "Tagging", "Waxing"],
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology Data Analysis", "Item Bom Management", "Learning Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales", "Sales Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }

    base_departments = dept_mapping.get(manufacturer, [])
    if not base_departments:
        return []

    if company == "Gurukrupa Export Private Limited":
        return [f"{dept} - GEPL" for dept in base_departments]
    elif company == "KG GK Jewellers Private Limited":
        return [f"{dept} - KGJPL" for dept in base_departments]
    return base_departments


def get_item_groups(raw_material_types):
    item_groups = []
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            item_groups.extend(["Metal - V", "Metal DNU"])
        elif rm_type == "Diamond":
            item_groups.extend(["Diamond - V", "Diamond DNU"])
        elif rm_type == "Gemstone":
            item_groups.extend(["Gemstone - V", "Gemstone DNU"])
        elif rm_type == "Finding":
            item_groups.extend(["Finding - V", "Finding DNU", "Finding - T"])
        elif rm_type == "Aloy":
            item_groups.extend(["Alloy"])
        elif rm_type == "Other":
            item_groups.extend(["Other Material - V", "Other Material - T", "Other - V", "Other DNU", "Other Material"])
    return item_groups


def get_variant_codes(raw_material_types):
    variant_codes = []
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            variant_codes.append("M")
        elif rm_type == "Diamond":
            variant_codes.append("D")
        elif rm_type == "Gemstone":
            variant_codes.append("G")
        elif rm_type == "Finding":
            variant_codes.append("F")
        elif rm_type == "Aloy":
            variant_codes.append("A")
        elif rm_type == "Other":
            variant_codes.append("O")
    return variant_codes


@frappe.whitelist()
def get_stock_details(department, stock_type, stock_key, filters):
    filters = json.loads(filters) if isinstance(filters, str) else filters

    company = filters.get("company")
    branch = filters.get("branch", "")
    manufacturer = filters.get("manufacturer", "")
    raw_material_types = [filters.get("raw_material_type")]

    if company == "Gurukrupa Export Private Limited":
        dept_with_suffix = f"{department} - GEPL" if " - GEPL" not in department else department
    elif company == "KG GK Jewellers Private Limited":
        dept_with_suffix = f"{department} - KGJPL" if " - KGJPL" not in department else department
    else:
        dept_with_suffix = department

    detail_functions = {
        "work_order_stock": get_work_order_details,
        "employee_wip_stock": get_employee_wip_details,
        "supplier_wip_stock": get_supplier_wip_details,
        "employee_msl_stock": get_employee_msl_details,
        "supplier_msl_stock": get_supplier_msl_details,
        "employee_msl_hold_stock": get_employee_msl_hold_details,
        "supplier_msl_hold_stock": get_supplier_msl_hold_details,
        "raw_material_stock": get_raw_material_details,
        "reserve_stock": get_reserve_stock_details,
        "transit_stock": get_transit_stock_details,
        "scrap_stock": get_scrap_stock_details,
        "finished_goods": get_finished_goods_details
    }

    detail_func = detail_functions.get(stock_key)
    if detail_func:
        return detail_func(dept_with_suffix, company, branch, manufacturer, raw_material_types)
    return []


@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    dept_mapping = {
        "Siddhi": ["Nandi"],
        "Service Center": ["Product Repair Center"],
        "Amrut": ["Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish", "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish", "Close Waxing", "Rudraksha"],
        "Mangal": ["Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU", "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU"],
        "Labh": ["Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing", "Diamond Setting", "Final Polish", "Manufacturing Plan & Management", "Model Making", "Pre Polish", "Product Certification", "Sub Contracting", "Tagging", "Waxing"],
        "Shubh": ["Accounts", "Administration", "BL - Purchase", "Canteen", "Casting", "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting", "Close Final Polish", "Close Model Making", "Close Pre Polish", "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing", "Computer Aided Manufacturing", "Computer Hardware Networking", "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology", "Information Technology Data Analysis", "Item Bom Management", "Learning Development - GEPL", "Legal", "Management", "Manufacturing", "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making", "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish", "Product Allocation", "Product Certification", "Product Development", "Production", "Purchase", "Quality Assessment", "Quality Management", "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales", "Sales Marketing", "Security - GEPL", "Selling", "Serial Number", "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik", "Tagging", "Trishul", "Waxing", "Waxing 2"]
    }
    return dept_mapping.get(manufacturer, [])


def get_raw_material_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            return frappe.db.sql(f"""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}'
                  AND w.department = '{department}'
                  AND w.warehouse_type = 'Raw Material'
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{getdate()}'
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Raw material details error", frappe.get_traceback())
        return []


def get_reserve_stock_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            dept_clean = department.split(' - ')[0].strip()

            return frappe.db.sql(f"""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}'
                  AND (
                        (w.warehouse_type = 'Reserve' AND w.department = '{department}')
                        OR w.warehouse_name = '{dept_clean} Reserve - GEPL'
                        OR w.warehouse_name = '{dept_clean} Reserve - KGJPL'
                        OR w.warehouse_name = '{dept_clean} Reserve'
                      )
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{getdate()}'
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Reserve stock details error", frappe.get_traceback())
        return []


def get_transit_stock_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            dept_clean = department.split(' - ')[0].strip()

            return frappe.db.sql(f"""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}'
                  AND (
                        w.warehouse_name = '{dept_clean} Transit - GEPL'
                        OR w.warehouse_name = '{dept_clean} Transit - KGJPL'
                        OR w.warehouse_name = '{dept_clean} Transit'
                      )
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{getdate()}'
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Transit stock details error", frappe.get_traceback())
        return []


def get_scrap_stock_details(department, company, branch, manufacturer, raw_material_types):
    try:
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            item_group_str = "', '".join(item_groups)
            dept_clean = department.split(' - ')[0].strip()

            return frappe.db.sql(f"""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = '{company}'
                  AND (
                        (w.warehouse_type = 'Scrap' AND w.department = '{department}')
                        OR w.warehouse_name = '{dept_clean} Scrap - GEPL'
                        OR w.warehouse_name = '{dept_clean} Scrap - KGJPL'
                        OR w.warehouse_name = '{dept_clean} Scrap'
                      )
                  AND i.item_group IN ('{item_group_str}')
                  AND sle.posting_date <= '{getdate()}'
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Scrap stock details error", frappe.get_traceback())
        return []


def get_work_order_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal":
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond":
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone":
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding":
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy":
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")

        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        manufacturer_condition = f" AND mop.manufacturer = '{manufacturer}'" if manufacturer else ""

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'Not Started'
              AND mop.department = '{department}'
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Work order details error", frappe.get_traceback())
        return []


def get_employee_wip_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal":
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond":
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone":
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding":
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy":
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")

        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        manufacturer_condition = f" AND mop.manufacturer = '{manufacturer}'" if manufacturer else ""

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 0
              AND mop.department = '{department}'
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Employee WIP details error", frappe.get_traceback())
        return []


def get_supplier_wip_details(department, company, branch, manufacturer, raw_material_types):
    try:
        weight_fields = []
        for rm_type in raw_material_types:
            if rm_type == "Metal":
                weight_fields.append("COALESCE(mop.net_wt, 0)")
            elif rm_type == "Diamond":
                weight_fields.append("COALESCE(mop.diamond_wt, 0)")
            elif rm_type == "Gemstone":
                weight_fields.append("COALESCE(mop.gemstone_wt, 0)")
            elif rm_type == "Finding":
                weight_fields.append("COALESCE(mop.finding_wt, 0)")
            elif rm_type == "Aloy":
                weight_fields.append("COALESCE(mop.alloy_wt, 0)")
            elif rm_type == "Other":
                weight_fields.append("COALESCE(mop.other_wt, 0)")

        weight_sum = " + ".join(weight_fields) if weight_fields else "COALESCE(mop.net_wt, 0)"
        manufacturer_condition = f" AND mop.manufacturer = '{manufacturer}'" if manufacturer else ""

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                'Supplier Operation' as 'Supplier Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 1
              AND mop.department = '{department}'
              AND mwo.company = '{company}'
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Supplier WIP details error", frappe.get_traceback())
        return []


def get_employee_msl_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            manufacturer_condition = f" AND ms.manufacturer = '{manufacturer}'" if manufacturer else ""

            return frappe.db.sql(f"""
                SELECT
                    ms.name as 'Main Slip',
                    COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1),
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'In Use'
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  AND ms.for_subcontracting = 0
                  {manufacturer_condition}
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Employee MSL details error", frappe.get_traceback())
        return []


def get_supplier_msl_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            manufacturer_condition = f" AND ms.manufacturer = '{manufacturer}'" if manufacturer else ""

            return frappe.db.sql(f"""
                SELECT
                    ms.name as 'Main Slip',
                    COALESCE(ms.subcontractor, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1),
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'In Use'
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition}
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Supplier MSL details error", frappe.get_traceback())
        return []


def get_employee_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            manufacturer_condition = f" AND ms.manufacturer = '{manufacturer}'" if manufacturer else ""

            return frappe.db.sql(f"""
                SELECT
                    ms.name as 'Main Slip',
                    COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1),
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
                WHERE ms.workflow_state = 'On Hold'
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  AND ms.for_subcontracting = 0
                  {manufacturer_condition}
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Employee MSL Hold details error", frappe.get_traceback())
        return []


def get_supplier_msl_hold_details(department, company, branch, manufacturer, raw_material_types):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if variant_codes:
            variant_code_str = "', '".join(variant_codes)
            manufacturer_condition = f" AND ms.manufacturer = '{manufacturer}'" if manufacturer else ""

            return frappe.db.sql(f"""
                SELECT
                    ms.name as 'Main Slip',
                    COALESCE(ms.subcontractor, 'Not Assigned') as 'Supplier Name',
                    ms.department as 'Department',
                    COALESCE(
                        (SELECT mop.operation FROM `tabMain Slip Operation` mso
                         INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                         WHERE mso.parent = ms.name LIMIT 1),
                        'N/A'
                    ) as 'Operation',
                    mse.qty as 'Weight'
                FROM `tabMain Slip` ms
                INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
                WHERE ms.workflow_state = 'On Hold'
                  AND ms.for_subcontracting = 1
                  AND ms.department = '{department}'
                  AND mse.variant_of IN ('{variant_code_str}')
                  AND mse.qty > 0
                  {manufacturer_condition}
                ORDER BY mse.qty DESC
            """, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Supplier MSL Hold details error", frappe.get_traceback())
        return []


def get_finished_goods_details(department, company, branch, manufacturer, raw_material_types):
    try:
        dept_clean = department.replace(' - GEPL', '').replace(' - KGJPL', '')

        return frappe.db.sql(f"""
            SELECT
                sn.name as 'Serial No',
                sn.item_code as 'Item Code',
                sn.warehouse as 'Warehouse'
            FROM `tabSerial No` sn
            INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
            WHERE sn.company = '{company}'
              AND sn.status = 'Active'
              AND w.warehouse_type = 'Finished Goods'
              AND w.warehouse_name LIKE '%{dept_clean}%'
              AND w.warehouse_name NOT LIKE '%MU%'
            ORDER BY sn.name
        """, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Finished goods details error", frappe.get_traceback())
        return []