# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.query_report import get_report_doc, validate_filters_permissions
from frappe.utils import flt, getdate, cint
import json
import re


def get_winning_operation_subquery():
    """
    A Manufacturing Work Order can have several concurrently open
    (Not Started / WIP) operations across different departments as an item
    moves through its routing, each carrying the item's full weight. To avoid
    counting that weight once per open operation, only the furthest-progressed
    open operation (WIP beats Not Started; later routing step wins ties) is
    treated as the one holding the stock. The calling query must bind `company`.
    """
    return """
        SELECT mop2.name
        FROM (
            SELECT mop3.name,
                   ROW_NUMBER() OVER (
                       PARTITION BY mop3.manufacturing_work_order
                       ORDER BY
                           CASE mop3.status WHEN 'WIP' THEN 2 WHEN 'Not Started' THEN 1 ELSE 0 END DESC,
                           mop3.idx DESC
                   ) as rn
            FROM `tabManufacturing Operation` mop3
            INNER JOIN `tabManufacturing Work Order` mwo3 ON mop3.manufacturing_work_order = mwo3.name
            WHERE mop3.status IN ('Not Started', 'WIP')
              AND mwo3.company = %(company)s
              AND mwo3.docstatus = 1
        ) mop2
        WHERE mop2.rn = 1
    """


def get_bom_weight_sum_sql(raw_material_types):
    """Weight of a finished piece, sourced from its BOM, for the selected raw material type(s)."""
    fields = []
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            fields.append("COALESCE(b.metal_weight, 0)")
        elif rm_type == "Diamond":
            fields.append("COALESCE(b.diamond_weight, 0)")
        elif rm_type == "Gemstone":
            fields.append("COALESCE(b.gemstone_weight, 0)")
        elif rm_type == "Finding":
            fields.append("COALESCE(b.finding_weight_, 0)")
        elif rm_type == "Other":
            fields.append("COALESCE(b.other_weight, 0)")

    return " + ".join(fields) if fields else "COALESCE(b.metal_weight, 0)"


REPORT_NAME = "Branch Stock Summary"
# The report JSON declares no filters, so Desk checks the Company filter only when the
# browser sends its definition (js_filters). Supply that definition here instead.
COMPANY_FILTER = [{"fieldname": "company", "fieldtype": "Link", "options": "Company"}]


def validate_company_access(filters):
    """Desk's check for the Company filter: read or select permission on that Company,
    User Permissions included."""
    validate_filters_permissions(REPORT_NAME, filters, frappe.session.user, COMPANY_FILTER)


def validate_report_access(filters):
    """The whitelisted methods below can be called directly by any logged-in user, so
    they repeat what Desk checks before it runs this report: its roles, report
    permission on Main Slip, and the Company filter."""
    get_report_doc(REPORT_NAME)
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    validate_company_access(filters)


def _escape_like(value):
    """Match %, _ and backslash in a name literally inside a LIKE pattern."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if filters.get("company") == "Gurukrupa Export Private Limited" and not filters.get("branch"):
        frappe.throw(_("Branch is required for Gurukrupa Export Private Limited"))
    if not filters.get("raw_material_type"):
        frappe.throw(_("Raw Material Type is required"))
    validate_company_access(filters)

    return get_branch_stock_summary_optimized(filters)


@frappe.whitelist()
def get_summary_comparison(filters):
    """Compares this report's Grand Total against the standard Stock Balance report
    for the same company/item group/as-on-date, and explains the gap.

    The gap has two structural causes:
    1. Scope gap: Branch Stock Summary only knows about departments that have an
       active Manufacturing Operation. Stock sitting in other departments (e.g.
       Purchase, Refinery) or in warehouses with no department set is invisible
       to it but still counted by Stock Balance.
    2. Ledger reconciliation drift: Stock Balance's engine recalculates balance
       deltas for Stock Reconciliation vouchers from `qty_after_transaction`
       (self-correcting historical ledger drift); Branch Stock Summary sums the
       raw `actual_qty` column, so any such drift shows up as an unexplained
       remainder here.
    """
    filters = json.loads(filters) if isinstance(filters, str) else (filters or {})

    validate_report_access(filters)
    if not filters.get("raw_material_type"):
        frappe.throw(_("Raw Material Type is required"))
    # The comparison runs the standard Stock Balance report and reads the Stock
    # Ledger directly, so that report's own access rules apply as well.
    get_report_doc("Stock Balance")

    company = filters.get("company")
    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()
    raw_material_types = [filters.get("raw_material_type")]
    item_groups = get_item_groups(raw_material_types)

    # Branch Stock Summary's own grand total, using the exact same filters.
    # Work Order/WIP Stock and Finished Goods are only included when their
    # checkboxes are ticked, so their contribution is split out here instead
    # of being silently folded into one combined number.
    WORK_ORDER_WIP_LABELS = {"Work Order Stock", "Employee WIP Stock", "Supplier WIP Stock"}

    _, data = get_branch_stock_summary_optimized(filters)
    core_qty = 0.0
    core_pure_gold = 0.0
    work_order_wip_qty = 0.0
    work_order_wip_pure_gold = 0.0
    finished_goods_qty = 0.0
    finished_goods_pure_gold = 0.0

    for row in data:
        if not row.get("is_stock_type"):
            continue
        label = row.get("section")
        qty = flt(row.get("quantity") or 0)
        pure_gold = flt(row.get("pure_gold_weight") or 0)

        if label in WORK_ORDER_WIP_LABELS:
            work_order_wip_qty += qty
            work_order_wip_pure_gold += pure_gold
        elif label == "Finished Goods":
            finished_goods_qty += qty
            finished_goods_pure_gold += pure_gold
        else:
            core_qty += qty
            core_pure_gold += pure_gold

    branch_qty = core_qty + work_order_wip_qty + finished_goods_qty
    branch_pure_gold = core_pure_gold + work_order_wip_pure_gold + finished_goods_pure_gold

    # Standard Stock Balance report total, for the same item group(s).
    from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance_execute

    stock_balance_qty = 0.0
    for item_group in item_groups:
        _, sb_data = stock_balance_execute(frappe._dict({
            "company": company,
            "from_date": "2000-01-01",
            "to_date": as_on_date,
            "item_group": item_group,
        }))
        for row in sb_data:
            stock_balance_qty += flt(row.get("bal_qty") or 0)

    # Scope gap: same item group(s), but grouped by department, restricted to
    # departments Branch Stock Summary does NOT track (i.e. no active
    # Manufacturing Operation for this company/branch/manufacturer).
    dept_list = [d["db_department"] for d in get_departments_list(filters)]

    scope_gap_breakdown = []
    if item_groups:
        scope_gap_breakdown = frappe.db.sql("""
            SELECT
                COALESCE(NULLIF(w.department, ''), 'Unassigned Warehouse') as department,
                SUM(sle.actual_qty) as qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabItem` i ON sle.item_code = i.item_code
            INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
            WHERE sle.company = %(company)s
              AND i.item_group IN %(item_groups)s
              AND sle.posting_date <= %(as_on_date)s
              AND sle.docstatus < 2
              AND sle.is_cancelled = 0
              AND COALESCE(w.department, '') NOT IN %(departments)s
            GROUP BY COALESCE(NULLIF(w.department, ''), 'Unassigned Warehouse')
            HAVING SUM(sle.actual_qty) != 0
            ORDER BY qty DESC
        """, {
            "company": company,
            "item_groups": tuple(item_groups),
            "as_on_date": as_on_date,
            # NOT IN ('') when no department is tracked, as before
            "departments": tuple(dept_list) or ("",),
        }, as_dict=True)

    scope_gap_total = sum(flt(r.qty) for r in scope_gap_breakdown)
    difference_total = stock_balance_qty - branch_qty
    reconciliation_diff = difference_total - scope_gap_total

    return {
        "company": company,
        "as_on_date": str(as_on_date),
        "raw_material_type": filters.get("raw_material_type"),
        "core_branch_summary_qty": core_qty,
        "core_branch_summary_pure_gold": core_pure_gold,
        "work_order_wip_qty": work_order_wip_qty,
        "work_order_wip_pure_gold": work_order_wip_pure_gold,
        "finished_goods_qty": finished_goods_qty,
        "finished_goods_pure_gold": finished_goods_pure_gold,
        "include_work_order_wip": bool(cint(filters.get("include_work_order_wip", 0))),
        "include_finished_goods_metal": bool(cint(filters.get("include_finished_goods_metal"))),
        "branch_summary_qty": branch_qty,
        "branch_summary_pure_gold": branch_pure_gold,
        "stock_balance_qty": stock_balance_qty,
        "difference_total": difference_total,
        "scope_gap_total": scope_gap_total,
        "scope_gap_breakdown": scope_gap_breakdown,
        "reconciliation_diff": reconciliation_diff,
    }


def get_branch_stock_summary_optimized(filters=None):
    columns = [
        {"fieldname": "section_name", "label": "Department", "fieldtype": "Data", "width": 400},
        {"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "pure_gold_weight", "label": "Pure Gold Weight", "fieldtype": "Float", "width": 170, "precision": 3},
        {"fieldname": "view_details", "label": "View Details", "fieldtype": "Data", "width": 120},
    ]

    raw_material_types = [filters.get("raw_material_type")]
    item_groups = get_item_groups(raw_material_types)
    variant_codes = get_variant_codes(raw_material_types)

    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()
    company = filters.get("company")
    manufacturer = filters.get("manufacturer", "")

    include_finished_goods_metal = bool(cint(filters.get("include_finished_goods_metal")))
    include_work_order_wip = bool(cint(filters.get("include_work_order_wip", 0)))

    departments = get_departments_list(filters)
    if not departments:
        return columns, []

    dept_list = [d["db_department"] for d in departments]

    bulk_stock_data = get_bulk_stock_data(
        company, item_groups, variant_codes,
        as_on_date, manufacturer, raw_material_types, dept_list,
        include_finished_goods_metal, include_work_order_wip
    )

    data = []
    grand_total = 0.0
    grand_total_pure_gold = 0.0

    for dept_info in departments:
        dept_name = dept_info["department"]
        dept_with_suffix = dept_info["db_department"]

        stock_values = extract_dept_stock_from_bulk(dept_with_suffix, bulk_stock_data)
        section_data = build_department_section_simplified(dept_name, stock_values)

        # Skip departments with no non-zero stock rows at all (header only).
        if len(section_data) <= 1:
            continue

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
            "is_grand_total": True,
        })

    return columns, data


def get_bulk_stock_data(company, item_groups, variant_codes, as_on_date, manufacturer, raw_material_types, dept_list, include_finished_goods_metal=False, include_work_order_wip=True):
    bulk_data = {
        "work_order": {},
        "employee_wip": {},
        "supplier_wip": {},
        "employee_msl": {},
        "supplier_msl": {},
        # removed: employee_msl_hold, supplier_msl_hold
        "transit": {},
        "raw_material": {},
        "reserve": {},
        "scrap": {},
        "manufacturing_wh": {},
        "finished_goods": {},
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
    manufacturer_condition = " AND mop.manufacturer = %(manufacturer)s" if manufacturer else ""
    winning_operation_subquery = get_winning_operation_subquery()
    values = {
        "company": company,
        "manufacturer": manufacturer,
        "as_on_date": as_on_date,
        "departments": tuple(dept_list),
        "item_groups": tuple(item_groups),
        "variant_codes": tuple(variant_codes),
    }

    try:
        if include_work_order_wip:
            # Work Order stock
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
                INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
                WHERE mop.status = 'Not Started'
                  AND mop.department IN %(departments)s
                  AND mwo.company = %(company)s
                  AND mwo.docstatus = 1
                  {manufacturer_condition}
                GROUP BY mop.department
            """, values, as_dict=True)

            for row in wo_result:
                bulk_data["work_order"][row.department] = {
                    "quantity": flt(row.total_balance),
                    "pure_gold_weight": flt(row.pure_gold_weight),
                }

            # Employee WIP
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
                INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
                WHERE mop.status = 'WIP'
                  AND mop.for_subcontracting = 0
                  AND mop.department IN %(departments)s
                  AND mwo.company = %(company)s
                  AND mwo.docstatus = 1
                  {manufacturer_condition}
                GROUP BY mop.department
            """, values, as_dict=True)

            for row in emp_wip_result:
                bulk_data["employee_wip"][row.department] = {
                    "quantity": flt(row.total_balance),
                    "pure_gold_weight": flt(row.pure_gold_weight),
                }

            # Supplier WIP
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
                INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
                WHERE mop.status = 'WIP'
                  AND mop.for_subcontracting = 1
                  AND mop.department IN %(departments)s
                  AND mwo.company = %(company)s
                  AND mwo.docstatus = 1
                  {manufacturer_condition}
                GROUP BY mop.department
            """, values, as_dict=True)

            for row in sup_wip_result:
                bulk_data["supplier_wip"][row.department] = {
                    "quantity": flt(row.total_balance),
                    "pure_gold_weight": flt(row.pure_gold_weight),
                }

        # Employee MSL / Supplier MSL
        if variant_codes:
            manufacturer_condition_ms = " AND ms.manufacturer = %(manufacturer)s" if manufacturer else ""

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
                  AND ms.company = %(company)s
                  AND ms.department IN %(departments)s
                  AND mse.variant_of IN %(variant_codes)s
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, values, as_dict=True)

            for row in emp_msl_result:
                bulk_data["employee_msl"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight),
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
                  AND ms.company = %(company)s
                  AND ms.department IN %(departments)s
                  AND mse.variant_of IN %(variant_codes)s
                  AND mse.qty > 0
                  {manufacturer_condition_ms}
                GROUP BY ms.department
            """, values, as_dict=True)

            for row in sup_msl_result:
                bulk_data["supplier_msl"][row.department] = {
                    "quantity": flt(row.total_qty),
                    "pure_gold_weight": flt(row.pure_gold_weight),
                }

        # Raw / Reserve / Transit / Scrap / Manufacturing Warehouse
        # Bulk queries across ALL departments at once (instead of 5 queries per
        # department) to avoid an N+1 query pattern that made this report time
        # out on real data (37 departments x 5 queries each, ~136s).
        if item_groups:
            dept_pairs = [
                (dept_with_suffix, dept_with_suffix.split(" - ")[0].strip())
                for dept_with_suffix in dept_list
            ]
            dept_mapping_values = {}
            for i, (dept, clean) in enumerate(dept_pairs):
                dept_mapping_values[f"dept_{i}"] = dept
                dept_mapping_values[f"dept_clean_{i}"] = clean
            dept_mapping_sql = " UNION ALL ".join(
                f"SELECT %(dept_{i})s AS department, %(dept_clean_{i})s AS dept_clean"
                for i in range(len(dept_pairs))
            )

            def _accumulate(rows):
                grouped = {}
                for row in rows:
                    entry = grouped.setdefault(row.department, {"quantity": 0.0, "pure_gold_weight": 0.0})
                    entry["quantity"] += flt(row.weight)
                    if is_metal:
                        entry["pure_gold_weight"] += get_pure_gold_from_item_code(row.item_code, row.weight)
                return grouped

            def _resolve_warehouses(warehouse_type, name_suffixes, department_match=True):
                """Resolve which warehouses belong to which department for a stock type.

                Runs only against the small `tabWarehouse` table (~1300 rows), so the
                OR/CONCAT name-pattern matching here is cheap. Returns {warehouse_name: department}.
                """
                name_conditions = " OR ".join(
                    f"w.warehouse_name = CONCAT(dm.dept_clean, '{suffix}')" for suffix in name_suffixes
                )
                dept_condition = (
                    f"(w.warehouse_type = '{warehouse_type}' AND w.department = dm.department) OR "
                    if department_match else ""
                )
                rows = frappe.db.sql(f"""
                    SELECT DISTINCT w.name as warehouse, dm.department as department
                    FROM ({dept_mapping_sql}) dm
                    INNER JOIN `tabWarehouse` w ON (
                        {dept_condition}{name_conditions}
                    )
                """, dept_mapping_values, as_dict=True)
                return {row.warehouse: row.department for row in rows}

            def _aggregate_by_warehouse(wh_to_dept):
                """Sum SLE stock for a resolved warehouse->department map using a sargable
                `warehouse IN (...)` filter instead of joining Warehouse with OR/CONCAT."""
                if not wh_to_dept:
                    return {}
                rows = frappe.db.sql("""
                    SELECT
                        sle.warehouse,
                        sle.item_code,
                        SUM(sle.actual_qty) as weight
                    FROM `tabStock Ledger Entry` sle
                    INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                    WHERE sle.company = %(company)s
                      AND sle.warehouse IN %(warehouses)s
                      AND i.item_group IN %(item_groups)s
                      AND sle.posting_date <= %(as_on_date)s
                      AND sle.docstatus < 2
                      AND sle.is_cancelled = 0
                    GROUP BY sle.warehouse, sle.item_code
                    HAVING SUM(sle.actual_qty) > 0
                """, {**values, "warehouses": tuple(wh_to_dept)}, as_dict=True)
                for row in rows:
                    row.department = wh_to_dept.get(row.warehouse)
                return _accumulate(rows)

            # Transit (name-pattern based, no department column on most Warehouses)
            transit_wh_map = _resolve_warehouses(
                "Transit", [" Transit - GEPL", " Transit - KGJPL", " Transit"], department_match=False
            )
            bulk_data["transit"] = _aggregate_by_warehouse(transit_wh_map)

            # Raw Material (direct department match)
            raw_result = frappe.db.sql("""
                SELECT
                    w.department,
                    sle.item_code,
                    SUM(sle.actual_qty) as weight
                FROM `tabStock Ledger Entry` sle
                INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND w.department IN %(departments)s
                  AND w.warehouse_type = 'Raw Material'
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY w.department, sle.item_code
                HAVING SUM(sle.actual_qty) > 0
            """, values, as_dict=True)
            bulk_data["raw_material"] = _accumulate(raw_result)

            # Reserve (department match OR name pattern)
            reserve_wh_map = _resolve_warehouses(
                "Reserve", [" Reserve - GEPL", " Reserve - KGJPL", " Reserve"]
            )
            bulk_data["reserve"] = _aggregate_by_warehouse(reserve_wh_map)

            # Scrap (department match OR name pattern)
            scrap_wh_map = _resolve_warehouses(
                "Scrap", [" Scrap - GEPL", " Scrap - KGJPL", " Scrap"]
            )
            bulk_data["scrap"] = _aggregate_by_warehouse(scrap_wh_map)

            # Manufacturing Warehouse (direct department match)
            manufacturing_wh_result = frappe.db.sql("""
                SELECT
                    w.department,
                    sle.item_code,
                    SUM(sle.actual_qty) as weight
                FROM `tabStock Ledger Entry` sle
                INNER JOIN `tabWarehouse` w ON sle.warehouse = w.name
                INNER JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND w.department IN %(departments)s
                  AND w.warehouse_type = 'Manufacturing'
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY w.department, sle.item_code
                HAVING SUM(sle.actual_qty) > 0
            """, values, as_dict=True)
            bulk_data["manufacturing_wh"] = _accumulate(manufacturing_wh_result)

        # Finished Goods
        bom_weight_sum = get_bom_weight_sum_sql(raw_material_types)
        for dept_with_suffix in (dept_list if include_finished_goods_metal else []):
            dept_clean = dept_with_suffix.replace(" - GEPL", "").replace(" - KGJPL", "")

            fg_result = frappe.db.sql(f"""
                SELECT
                    SUM({bom_weight_sum}) as total_weight,
                    SUM(
                        CASE
                            WHEN {1 if is_metal else 0} = 1
                            THEN COALESCE(b.metal_weight, 0) * COALESCE(b.metal_purity + 0, 0) / 100
                            ELSE 0
                        END
                    ) as pure_gold_weight
                FROM `tabSerial No` sn
                INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
                LEFT JOIN `tabBOM` b ON sn.custom_bom_no = b.name
                WHERE sn.company = %(company)s
                  AND sn.status = 'Active'
                  AND w.warehouse_type = 'Finished Goods'
                  AND w.warehouse_name LIKE %(warehouse_pattern)s
                  AND w.warehouse_name NOT LIKE '%%MU%%'
            """, {"company": company, "warehouse_pattern": f"%{_escape_like(dept_clean)}%"}, as_dict=True)

            if fg_result and fg_result[0].get("total_weight"):
                bulk_data["finished_goods"][dept_with_suffix] = {
                    "quantity": flt(fg_result[0]["total_weight"]),
                    "pure_gold_weight": flt(fg_result[0]["pure_gold_weight"]),
                }

    except Exception:
        frappe.log_error("Bulk stock data error", frappe.get_traceback())

    return bulk_data


def extract_dept_stock_from_bulk(dept_with_suffix, bulk_data):
    return {
        "work_order_stock": bulk_data["work_order"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "employee_wip_stock": bulk_data["employee_wip"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "supplier_wip_stock": bulk_data["supplier_wip"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "employee_msl_stock": bulk_data["employee_msl"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "supplier_msl_stock": bulk_data["supplier_msl"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        # removed: employee_msl_hold_stock, supplier_msl_hold_stock
        "raw_material_stock": bulk_data["raw_material"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "reserve_stock": bulk_data["reserve"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "transit_stock": bulk_data["transit"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "scrap_stock": bulk_data["scrap"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "manufacturing_wh_stock": bulk_data["manufacturing_wh"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
        "finished_goods": bulk_data["finished_goods"].get(dept_with_suffix, {"quantity": 0.0, "pure_gold_weight": 0.0}),
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
        "is_department_header": True,
    }]

    stock_types = [
        {"key": "work_order_stock", "label": "Work Order Stock"},
        {"key": "employee_wip_stock", "label": "Employee WIP Stock"},
        {"key": "supplier_wip_stock", "label": "Supplier WIP Stock"},
        {"key": "employee_msl_stock", "label": "Employee MSL Stock"},
        {"key": "supplier_msl_stock", "label": "Supplier MSL Stock"},
        # removed: employee_msl_hold_stock, supplier_msl_hold_stock
        {"key": "raw_material_stock", "label": "Raw Material Stock"},
        {"key": "reserve_stock", "label": "Reserve Stock"},
        {"key": "transit_stock", "label": "Transit Stock"},
        {"key": "scrap_stock", "label": "Scrap Stock"},
        {"key": "manufacturing_wh_stock", "label": "Manufacturing Warehouse Stock"},
        {"key": "finished_goods", "label": "Finished Goods"},
    ]

    for stock_type in stock_types:
        stock_entry = stock_values.get(stock_type["key"], {"quantity": 0.0, "pure_gold_weight": 0.0})
        stock_value = flt(stock_entry.get("quantity", 0.0))
        pure_gold_weight = flt(stock_entry.get("pure_gold_weight", 0.0))

        if stock_value == 0 and pure_gold_weight == 0:
            continue

        display_value = "" if stock_value == 0 else stock_value
        display_pure_gold = "" if pure_gold_weight == 0 else pure_gold_weight

        view_button = (
            f'<button class="btn btn-xs btn-primary view-stock-details" '
            f'data-department="{dept_name}" '
            f'data-stock-type="{stock_type["label"]}" '
            f'data-stock-key="{stock_type["key"]}">View</button>'
        )

        section_data.append({
            "section_name": stock_type["label"],
            "section": stock_type["label"],
            "parent_section": dept_name,
            "indent": 1.0,
            "quantity": display_value,
            "pure_gold_weight": display_pure_gold,
            "view_details": view_button,
            "is_stock_type": True,
        })

    return section_data


def add_department_total_row_simplified(data, section_data, label):
    total_quantity = sum(
        float(row.get("quantity", 0.0))
        for row in section_data
        if row.get("parent_section") and row.get("quantity") not in ("", 0)
    )

    total_pure_gold = sum(
        float(row.get("pure_gold_weight", 0.0))
        for row in section_data
        if row.get("parent_section") and row.get("pure_gold_weight") not in ("", 0)
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
        "is_department_total": True,
    })

    return total_quantity, total_pure_gold


def extract_purity_from_item_code(item_code):
    if not item_code:
        return 0.0

    match = re.search(r"-(\d+(?:\.\d+)?)($|-)", item_code)
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
    values = {"company": company}

    excluded_departments = ["Canteen", "HR", "Admin", "Security", "Housekeeping", "IT", "Transport", "Maintenance"]
    # Fixed names; %% is a literal % because the query runs with values.
    excluded_condition = " AND " + " AND ".join([f"mop.department NOT LIKE '%%{dept}%%'" for dept in excluded_departments])

    manufacturer_dept_condition = ""
    if manufacturer:
        allowed_departments = get_manufacturer_departments(manufacturer, company)
        if allowed_departments:
            values["allowed_departments"] = tuple(allowed_departments)
            manufacturer_dept_condition = " AND mop.department IN %(allowed_departments)s"

    dept_query = f"""
        SELECT DISTINCT
            REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') as department,
            mop.department as db_department
        FROM `tabManufacturing Operation` mop
        LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
        WHERE mwo.company = %(company)s
          AND mwo.docstatus = 1
          AND mop.department IS NOT NULL
          AND mop.department != ''
          {excluded_condition}
          {manufacturer_dept_condition}
    """

    if company == "Gurukrupa Export Private Limited" and branch:
        values["branch"] = branch
        dept_query += " AND mwo.branch = %(branch)s"

    if department:
        values["department"] = department.replace(" - GEPL", "").replace(" - KGJPL", "").strip()
        dept_query += (
            " AND REPLACE(REPLACE(mop.department, ' - GEPL', ''), ' - KGJPL', '') = "
            "%(department)s"
        )

    dept_query += " ORDER BY mop.department"

    try:
        return frappe.db.sql(dept_query, values, as_dict=True)
    except Exception:
        frappe.log_error("Department query error", frappe.get_traceback())
        return []


def get_manufacturer_departments(manufacturer, company):
    dept_mapping = {
        "Siddhi": ["Nandi"],
        "Service Center": ["Product Repair Center"],
        "Amrut": [
            "Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish",
            "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish",
            "Close Waxing", "Rudraksha",
        ],
        "Mangal": [
            "Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU",
            "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU",
        ],
        "Labh": [
            "Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing",
            "Diamond Setting", "Final Polish", "Manufacturing Plan & Management",
            "Model Making", "Pre Polish", "Product Certification", "Sub Contracting",
            "Tagging", "Waxing",
        ],
        "Shubh": [
            "Accounts", "Administration", "BL - Purchase", "Canteen", "Casting",
            "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting",
            "Close Final Polish", "Close Model Making", "Close Pre Polish",
            "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing",
            "Computer Aided Manufacturing", "Computer Hardware Networking", "Customer Service",
            "D2D Marketing", "Diamond Bagging", "Diamond Setting", "Digital Marketing",
            "Dispatch", "Final Polish", "Gemstone Bagging", "HD - Purchase",
            "Housekeeping", "Human Resources", "Information Technology",
            "Information Technology Data Analysis", "Item Bom Management",
            "Learning Development - GEPL", "Legal", "Management", "Manufacturing",
            "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making",
            "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish",
            "Product Allocation", "Product Certification", "Product Development",
            "Production", "Purchase", "Quality Assessment", "Quality Management",
            "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales",
            "Sales Marketing", "Security - GEPL", "Selling", "Serial Number",
            "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik",
            "Tagging", "Trishul", "Waxing", "Waxing 2",
        ],
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
        elif rm_type == "Alloy":
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
    filters = json.loads(filters) if isinstance(filters, str) else (filters or {})
    validate_report_access(filters)

    company = filters.get("company")
    branch = filters.get("branch", "")
    manufacturer = filters.get("manufacturer", "")
    raw_material_types = [filters.get("raw_material_type")]
    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()

    if company == "Gurukrupa Export Private Limited":
        dept_with_suffix = f"{department} - GEPL" if " - GEPL" not in department else department
    elif company == "KG GK Jewellers Private Limited":
        dept_with_suffix = f"{department} - KGJPL" if " - KGJPL" not in department else department
    else:
        dept_with_suffix = department

    detail_functions = {
        "work_order_stock": get_work_order_details,
        "employee_wip_stock": get_employee_wip_details,
        "supplier_wip_stock": getsupplier_wip_details,
        "employee_msl_stock": get_employee_msl_details,
        "supplier_msl_stock": get_supplier_msl_details,
        # removed: employee_msl_hold_stock, supplier_msl_hold_stock
        "raw_material_stock": get_raw_material_details,
        "reserve_stock": get_reserve_stock_details,
        "transit_stock": get_transit_stock_details,
        "scrap_stock": get_scrap_stock_details,
        "manufacturing_wh_stock": get_manufacturing_warehouse_details,
        "finished_goods": get_finished_goods_details,
    }

    if stock_key == "finished_goods" and not cint(filters.get("include_finished_goods_metal")):
        return []

    if stock_key in ("work_order_stock", "employee_wip_stock", "supplier_wip_stock") and not cint(filters.get("include_work_order_wip", 0)):
        return []

    detail_func = detail_functions.get(stock_key)
    if detail_func:
        return detail_func(dept_with_suffix, company, branch, manufacturer, raw_material_types, as_on_date)
    return []


@frappe.whitelist()
def get_departments_by_manufacturer(manufacturer):
    dept_mapping = {
        "Siddhi": ["Nandi"],
        "Service Center": ["Product Repair Center"],
        "Amrut": [
            "Close Diamond Bagging", "Close Diamond Setting", "Close Final Polish",
            "Close Gemstone Bagging", "Close Model Making", "Close Pre Polish",
            "Close Waxing", "Rudraksha",
        ],
        "Mangal": [
            "Central MU", "Computer Aided Designing MU", "Manufacturing Plan Management MU",
            "Om MU", "Serial Number MU", "Sub Contracting MU", "Tagging MU",
        ],
        "Labh": [
            "Casting", "Central", "Computer Aided Designing", "Computer Aided Manufacturing",
            "Diamond Setting", "Final Polish", "Manufacturing Plan & Management",
            "Model Making", "Pre Polish", "Product Certification", "Sub Contracting",
            "Tagging", "Waxing",
        ],
        "Shubh": [
            "Accounts", "Administration", "BL - Purchase", "Canteen", "Casting",
            "CB - Purchase", "Central", "CH - Purchase", "Close Diamond Setting",
            "Close Final Polish", "Close Model Making", "Close Pre Polish",
            "Close Waxing", "Computer Aided Designing", "Sketch/Computer Aided Designing",
            "Computer Aided Manufacturing", "Computer Hardware Networking",
            "Customer Service", "D2D Marketing", "Diamond Bagging", "Diamond Setting",
            "Digital Marketing", "Dispatch", "Final Polish", "Gemstone Bagging",
            "HD - Purchase", "Housekeeping", "Human Resources", "Information Technology",
            "Information Technology Data Analysis", "Item Bom Management",
            "Learning Development - GEPL", "Legal", "Management", "Manufacturing",
            "Manufacturing Plan Management", "Marketing", "Merchandise", "Model Making",
            "MU - Purchase", "Om", "Operations", "Order Management", "Pre Polish",
            "Product Allocation", "Product Certification", "Product Development",
            "Production", "Purchase", "Quality Assessment", "Quality Management",
            "Refinery", "Research Development", "Rhodium", "Rudraksha", "Sales",
            "Sales Marketing", "Security - GEPL", "Selling", "Serial Number",
            "Stores", "Studio - GEPL", "Sub Contracting", "Sudarshan", "Swastik",
            "Tagging", "Trishul", "Waxing", "Waxing 2",
        ],
    }
    return dept_mapping.get(manufacturer, [])


def get_raw_material_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        as_on_date = as_on_date or getdate()
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            values = {
                "company": company,
                "department": department,
                "item_groups": tuple(item_groups),
                "as_on_date": as_on_date,
            }
            return frappe.db.sql("""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND w.department = %(department)s
                  AND w.warehouse_type = 'Raw Material'
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, values, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Raw material details error", frappe.get_traceback())
        return []


def get_reserve_stock_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        as_on_date = as_on_date or getdate()
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            values = {
                "company": company,
                "department": department,
                "item_groups": tuple(item_groups),
                "as_on_date": as_on_date,
            }
            values["dept_clean"] = department.split(" - ")[0].strip()

            return frappe.db.sql("""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND (
                        (w.warehouse_type = 'Reserve' AND w.department = %(department)s)
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Reserve - GEPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Reserve - KGJPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Reserve')
                      )
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, values, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Reserve stock details error", frappe.get_traceback())
        return []


def get_transit_stock_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        as_on_date = as_on_date or getdate()
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            values = {
                "company": company,
                "department": department,
                "item_groups": tuple(item_groups),
                "as_on_date": as_on_date,
            }
            values["dept_clean"] = department.split(" - ")[0].strip()

            return frappe.db.sql("""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND (
                        w.warehouse_name = CONCAT(%(dept_clean)s, ' Transit - GEPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Transit - KGJPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Transit')
                      )
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, values, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Transit stock details error", frappe.get_traceback())
        return []


def get_scrap_stock_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        as_on_date = as_on_date or getdate()
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            values = {
                "company": company,
                "department": department,
                "item_groups": tuple(item_groups),
                "as_on_date": as_on_date,
            }
            values["dept_clean"] = department.split(" - ")[0].strip()

            return frappe.db.sql("""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND (
                        (w.warehouse_type = 'Scrap' AND w.department = %(department)s)
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Scrap - GEPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Scrap - KGJPL')
                        OR w.warehouse_name = CONCAT(%(dept_clean)s, ' Scrap')
                      )
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, values, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Scrap stock details error", frappe.get_traceback())
        return []


def get_manufacturing_warehouse_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        as_on_date = as_on_date or getdate()
        item_groups = get_item_groups(raw_material_types)
        if item_groups:
            values = {
                "company": company,
                "department": department,
                "item_groups": tuple(item_groups),
                "as_on_date": as_on_date,
            }
            return frappe.db.sql("""
                SELECT
                    sle.item_code as 'Item Code',
                    SUM(sle.actual_qty) as 'Weight'
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                LEFT JOIN `tabItem` i ON sle.item_code = i.item_code
                WHERE sle.company = %(company)s
                  AND w.department = %(department)s
                  AND w.warehouse_type = 'Manufacturing'
                  AND i.item_group IN %(item_groups)s
                  AND sle.posting_date <= %(as_on_date)s
                  AND sle.docstatus < 2
                  AND sle.is_cancelled = 0
                GROUP BY sle.item_code
                HAVING SUM(sle.actual_qty) > 0
                ORDER BY SUM(sle.actual_qty) DESC
            """, values, as_dict=True, debug=0)
        return []
    except Exception:
        frappe.log_error("Manufacturing warehouse details error", frappe.get_traceback())
        return []


def get_work_order_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
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
        manufacturer_condition = " AND mop.manufacturer = %(manufacturer)s" if manufacturer else ""
        winning_operation_subquery = get_winning_operation_subquery()
        values = {"company": company, "department": department, "manufacturer": manufacturer}

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
            WHERE mop.status = 'Not Started'
              AND mop.department = %(department)s
              AND mwo.company = %(company)s
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Work order details error", frappe.get_traceback())
        return []


def get_employee_wip_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
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
        manufacturer_condition = " AND mop.manufacturer = %(manufacturer)s" if manufacturer else ""
        winning_operation_subquery = get_winning_operation_subquery()
        values = {"company": company, "department": department, "manufacturer": manufacturer}

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
            INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 0
              AND mop.department = %(department)s
              AND mwo.company = %(company)s
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Employee WIP details error", frappe.get_traceback())
        return []


def getsupplier_wip_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
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
        manufacturer_condition = " AND mop.manufacturer = %(manufacturer)s" if manufacturer else ""
        winning_operation_subquery = get_winning_operation_subquery()
        values = {"company": company, "department": department, "manufacturer": manufacturer}

        return frappe.db.sql(f"""
            SELECT
                mwo.name as 'Manufacturing Work Order',
                ({weight_sum}) as 'Weight',
                COALESCE(mop.operation, 'N/A') as 'Operation',
                'Supplier Operation' as 'Supplier Name'
            FROM `tabManufacturing Operation` mop
            LEFT JOIN `tabManufacturing Work Order` mwo ON mop.manufacturing_work_order = mwo.name
            INNER JOIN ({winning_operation_subquery}) winner ON winner.name = mop.name
            WHERE mop.status = 'WIP'
              AND mop.for_subcontracting = 1
              AND mop.department = %(department)s
              AND mwo.company = %(company)s
              AND mwo.docstatus = 1
              AND ({weight_sum}) > 0
              {manufacturer_condition}
            ORDER BY ({weight_sum}) DESC
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Supplier WIP details error", frappe.get_traceback())
        return []


def get_employee_msl_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if not variant_codes:
            return []
        manufacturer_condition = " AND ms.manufacturer = %(manufacturer)s" if manufacturer else ""
        values = {
            "company": company,
            "department": department,
            "variant_codes": tuple(variant_codes),
            "manufacturer": manufacturer,
        }

        return frappe.db.sql(f"""
            SELECT
                ms.name as 'Main Slip',
                COALESCE(emp.employee_name, 'Not Assigned') as 'Employee Name',
                ms.department as 'Department',
                COALESCE(
                    (SELECT mop.operation
                     FROM `tabMain Slip Operation` mso
                     INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                     WHERE mso.parent = ms.name LIMIT 1),
                    'N/A'
                ) as 'Operation',
                mse.qty as 'Weight'
            FROM `tabMain Slip` ms
            INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
            LEFT JOIN `tabEmployee` emp ON ms.employee = emp.name
            WHERE ms.workflow_state = 'In Use'
              AND ms.company = %(company)s
              AND ms.department = %(department)s
              AND mse.variant_of IN %(variant_codes)s
              AND mse.qty > 0
              AND ms.for_subcontracting = 0
              {manufacturer_condition}
            ORDER BY mse.qty DESC
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Employee MSL details error", frappe.get_traceback())
        return []


def get_supplier_msl_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        variant_codes = get_variant_codes(raw_material_types)
        if not variant_codes:
            return []
        manufacturer_condition = " AND ms.manufacturer = %(manufacturer)s" if manufacturer else ""
        values = {
            "company": company,
            "department": department,
            "variant_codes": tuple(variant_codes),
            "manufacturer": manufacturer,
        }

        return frappe.db.sql(f"""
            SELECT
                ms.name as 'Main Slip',
                COALESCE(ms.subcontractor, 'Not Assigned') as 'Supplier Name',
                ms.department as 'Department',
                COALESCE(
                    (SELECT mop.operation
                     FROM `tabMain Slip Operation` mso
                     INNER JOIN `tabManufacturing Operation` mop ON mso.manufacturing_operation = mop.name
                     WHERE mso.parent = ms.name LIMIT 1),
                    'N/A'
                ) as 'Operation',
                mse.qty as 'Weight'
            FROM `tabMain Slip` ms
            INNER JOIN `tabMain Slip SE Details` mse ON ms.name = mse.parent
            WHERE ms.workflow_state = 'In Use'
              AND ms.for_subcontracting = 1
              AND ms.company = %(company)s
              AND ms.department = %(department)s
              AND mse.variant_of IN %(variant_codes)s
              AND mse.qty > 0
              {manufacturer_condition}
            ORDER BY mse.qty DESC
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Supplier MSL details error", frappe.get_traceback())
        return []


def get_finished_goods_details(department, company, branch, manufacturer, raw_material_types, as_on_date=None):
    try:
        dept_clean = department.replace(" - GEPL", "").replace(" - KGJPL", "")
        is_metal = "Metal" in raw_material_types
        bom_weight_sum = get_bom_weight_sum_sql(raw_material_types)
        values = {"company": company, "warehouse_pattern": f"%{_escape_like(dept_clean)}%"}

        return frappe.db.sql(f"""
            SELECT
                sn.name as 'Serial No',
                sn.item_code as 'Item Code',
                sn.warehouse as 'Warehouse',
                ({bom_weight_sum}) as 'Weight',
                CASE
                    WHEN {1 if is_metal else 0} = 1
                    THEN COALESCE(b.metal_weight, 0) * COALESCE(b.metal_purity + 0, 0) / 100
                    ELSE 0
                END as 'Pure Gold Weight'
            FROM `tabSerial No` sn
            INNER JOIN `tabWarehouse` w ON sn.warehouse = w.name
            LEFT JOIN `tabBOM` b ON sn.custom_bom_no = b.name
            WHERE sn.company = %(company)s
              AND sn.status = 'Active'
              AND w.warehouse_type = 'Finished Goods'
              AND w.warehouse_name LIKE %(warehouse_pattern)s
              AND w.warehouse_name NOT LIKE '%%MU%%'
            ORDER BY sn.name
        """, values, as_dict=True, debug=0)
    except Exception:
        frappe.log_error("Finished goods details error", frappe.get_traceback())
        return []