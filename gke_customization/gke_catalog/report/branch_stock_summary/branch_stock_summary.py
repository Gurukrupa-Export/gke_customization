# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Branch Stock Summary: where every gram of a raw material actually sits, department-wise.

All quantities come from the Stock Ledger (the same source as the standard
Stock Balance report), so the Grand Total always matches Stock Balance.
Each warehouse is placed in exactly one section:

1. Department      - the warehouse's own `department`; else the department of the
                     warehouse's `employee`; else a department whose name the
                     warehouse name starts with (e.g. "Central Scrap" -> Central).
                     Within a department, stock is split by warehouse kind
                     (Raw Material, Manufacturing, Employee WIP, Employee MSL, ...).
2. Supplier / Job Work - warehouses with a `subcontractor`, one row per supplier.
3. Unassigned      - anything that cannot be tied to a department or supplier.

Finished pieces are tracked as Serial Nos of finished items (not as raw
material items). They are shown on the line of the warehouse holding them
(e.g. Tagging FG -> Tagging / Finished Goods, pieces in Central Transit ->
Central / Transit), with their raw material content from each piece's BOM in
the separate "FG Weight (BOM)" / "FG Pure Gold" columns. That BOM weight is not
part of Stock Balance, so it is kept out of Quantity, and the Quantity Grand
Total matches Stock Balance.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

STOCK_TYPES = [
    ("raw_material", "Raw Material"),
    ("manufacturing", "Manufacturing Warehouse"),
    ("employee_wip", "Employee WIP"),
    ("employee_msl", "Employee MSL"),
    ("scrap", "Scrap"),
    ("reserve", "Reserve"),
    ("transit", "Transit"),
    ("finished_goods", "Finished Goods"),
    ("consumables", "Consumables"),
    ("other", "Other Warehouses"),
]

WAREHOUSE_TYPE_TO_STOCK_KEY = {
    "Raw Material": "raw_material",
    "Manufacturing": "manufacturing",
    "Scrap": "scrap",
    "Reserve": "reserve",
    "Transit": "transit",
    "Consumables": "consumables",
    "Finished Goods": "finished_goods",
}

# Finished piece serial numbers that are still physically held by the company.
FINISHED_SERIAL_STATUSES = ("Active", "Reserved")


def execute(filters=None):
    filters = frappe._dict(filters or {})

    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("raw_material_type"):
        frappe.throw(_("Raw Material Type is required"))

    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"fieldname": "section_name", "label": _("Section"), "fieldtype": "Data", "width": 380},
        {"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "Float", "width": 150, "precision": 3},
        {"fieldname": "pure_gold_weight", "label": _("Pure Gold Weight"), "fieldtype": "Float", "width": 170, "precision": 3},
        {"fieldname": "pieces", "label": _("FG Pieces"), "fieldtype": "Int", "width": 90},
        {"fieldname": "fg_weight", "label": _("FG Weight (BOM)"), "fieldtype": "Float", "width": 140, "precision": 3},
        {"fieldname": "fg_pure_gold", "label": _("FG Pure Gold"), "fieldtype": "Float", "width": 130, "precision": 3},
        {"fieldname": "view_details", "label": _("View Details"), "fieldtype": "Data", "width": 110},
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_company_abbr(company):
    return frappe.get_cached_value("Company", company, "abbr") or ""


def strip_company_abbr(department, abbr):
    """'Casting - KGJPL' -> 'Casting' (Department names carry the company abbr as suffix)."""
    suffix = f" - {abbr}"
    if abbr and department.endswith(suffix):
        return department[: -len(suffix)].strip()
    return department.strip()


def get_item_groups(raw_material_types):
    # Both the variant ("- V") and template ("- T") groups: template items can't
    # hold stock, but variants created under the "- T" group do.
    item_groups = []
    for rm_type in raw_material_types:
        if rm_type == "Metal":
            item_groups.extend(["Metal - V", "Metal DNU", "Metal - T"])
        elif rm_type == "Diamond":
            item_groups.extend(["Diamond - V", "Diamond DNU", "Diamond - T"])
        elif rm_type == "Gemstone":
            item_groups.extend(["Gemstone - V", "Gemstone DNU", "Gemstone - T"])
        elif rm_type == "Finding":
            item_groups.extend(["Finding - V", "Finding DNU", "Finding - T"])
        elif rm_type == "Alloy":
            item_groups.extend(["Alloy"])
        elif rm_type == "Other":
            item_groups.extend(["Other Material - V", "Other Material - T", "Other - V", "Other DNU", "Other Material"])
    return item_groups


def get_existing_item_groups(raw_material_type):
    """Item groups for the raw material type that exist on this site, with their
    descendants (Stock Balance also includes child groups)."""
    groups = set()
    for group in get_item_groups([raw_material_type]):
        bounds = frappe.db.get_value("Item Group", group, ["lft", "rgt"])
        if not bounds:
            continue
        groups.update(frappe.get_all(
            "Item Group",
            filters={"lft": [">=", bounds[0]], "rgt": ["<=", bounds[1]]},
            pluck="name",
        ))
    return sorted(groups)


def get_bom_weight_sql(raw_material_type):
    """Weight of a finished piece, sourced from its BOM, for the raw material type.
    Returns None when the BOM does not record that material's weight."""
    return {
        "Metal": "COALESCE(b.metal_weight, 0)",
        "Diamond": "COALESCE(b.diamond_weight, 0)",
        "Gemstone": "COALESCE(b.gemstone_weight, 0)",
    }.get(raw_material_type)


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


def get_manufacturer_departments(manufacturer):
    """Departments belonging to a manufacturer: those linked to it on the
    Department master, plus any where its Manufacturing Operations run."""
    return set(frappe.db.sql_list(
        """
        SELECT d.name FROM `tabDepartment` d WHERE d.manufacturer = %(manufacturer)s
        UNION
        SELECT DISTINCT mop.department FROM `tabManufacturing Operation` mop
        WHERE mop.manufacturer = %(manufacturer)s AND mop.department IS NOT NULL
        """,
        {"manufacturer": manufacturer},
    ))


# ---------------------------------------------------------------------------
# Warehouse classification
# ---------------------------------------------------------------------------

def get_warehouse_map(company, branch=None):
    """Classify every (leaf) warehouse of the company.

    Returns {warehouse: dict(group, key, label, stock_key, department, employee,
    employee_name, supplier_name)} where `group` is 'department',
    'supplier' or 'unassigned' and `key` identifies the row within the group.
    """
    abbr = get_company_abbr(company)
    warehouses = frappe.db.sql(
        """
        SELECT
            w.name, w.warehouse_name, w.warehouse_type, w.department, w.employee,
            w.subcontractor, w.custom_branch,
            e.department as employee_department, e.employee_name,
            s.supplier_name
        FROM `tabWarehouse` w
        LEFT JOIN `tabEmployee` e ON e.name = w.employee
        LEFT JOIN `tabSupplier` s ON s.name = w.subcontractor
        WHERE w.company = %(company)s AND w.is_group = 0
        """,
        {"company": company},
        as_dict=True,
    )

    # Department base names for the name-prefix fallback, longest first so
    # "Diamond Setting" wins over "Diamond".
    departments = frappe.get_all(
        "Department", filters={"company": company, "is_group": 0}, pluck="name"
    )
    prefixes = sorted(
        ((strip_company_abbr(d, abbr).lower() + " ", d) for d in departments),
        key=lambda p: len(p[0]),
        reverse=True,
    )

    def department_from_name(warehouse_name):
        name = (warehouse_name or "").strip().lower()
        for prefix, department in prefixes:
            if name.startswith(prefix):
                return department
        return None

    warehouse_map = {}
    for wh in warehouses:
        # Warehouses tagged to another branch are left out; untagged ones are kept
        # because most employee/supplier warehouses have no branch set.
        if branch and wh.custom_branch and wh.custom_branch != branch:
            continue

        info = frappe._dict(
            warehouse=wh.name,
            employee=wh.employee,
            employee_name=wh.employee_name,
        )

        if wh.subcontractor:
            info.update(
                group="supplier",
                key=wh.subcontractor,
                label=wh.supplier_name or wh.subcontractor,
                stock_key="supplier",
                supplier_name=wh.supplier_name or wh.subcontractor,
            )
            warehouse_map[wh.name] = info
            continue

        department = (
            wh.department
            or wh.employee_department
            or department_from_name(wh.warehouse_name)
        )
        if not department:
            info.update(group="unassigned", key=wh.name, label=wh.name, stock_key="unassigned")
            warehouse_map[wh.name] = info
            continue

        if wh.employee:
            stock_key = "employee_wip" if wh.warehouse_type == "Manufacturing" else "employee_msl"
        else:
            stock_key = WAREHOUSE_TYPE_TO_STOCK_KEY.get(wh.warehouse_type, "other")

        info.update(
            group="department",
            key=department,
            label=strip_company_abbr(department, abbr),
            stock_key=stock_key,
            department=department,
        )
        warehouse_map[wh.name] = info

    return warehouse_map


def get_allowed_departments(filters):
    """None = no department restriction; otherwise the set of allowed departments."""
    allowed = None
    if filters.get("manufacturer"):
        allowed = get_manufacturer_departments(filters.get("manufacturer"))
    if filters.get("department"):
        allowed = {filters.get("department")} if allowed is None else allowed & {filters.get("department")}
    return allowed


def filter_warehouse_map(warehouse_map, allowed_departments):
    """Apply the manufacturer/department filters. When either is set, only
    department sections are shown (suppliers and unassigned have no department)."""
    if allowed_departments is None:
        return warehouse_map
    return {
        wh: info for wh, info in warehouse_map.items()
        if info.group == "department" and info.department in allowed_departments
    }


# ---------------------------------------------------------------------------
# Stock queries
# ---------------------------------------------------------------------------

def get_ledger_balances(company, item_groups, as_on_date, warehouses=None):
    """Balance per (warehouse, item) from the Stock Ledger as on a date."""
    if not item_groups:
        return []

    conditions = ""
    values = {"company": company, "item_groups": item_groups, "as_on_date": as_on_date}
    if warehouses is not None:
        if not warehouses:
            return []
        conditions = " AND sle.warehouse IN %(warehouses)s"
        values["warehouses"] = list(warehouses)

    return frappe.db.sql(
        f"""
        SELECT sle.warehouse, sle.item_code, SUM(sle.actual_qty) as qty
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.company = %(company)s
          AND i.item_group IN %(item_groups)s
          AND sle.posting_date <= %(as_on_date)s
          AND sle.is_cancelled = 0
          AND sle.docstatus < 2
          {conditions}
        GROUP BY sle.warehouse, sle.item_code
        HAVING ABS(SUM(sle.actual_qty)) > 0.0005
        """,
        values,
        as_dict=True,
    )


def get_finished_goods(company, raw_material_type, warehouse_map, serial_detail=False):
    """Finished pieces (Serial Nos) per warehouse with their BOM raw material weight.
    Serial No status is current, so this reflects today regardless of As On Date."""
    weight_sql = get_bom_weight_sql(raw_material_type)
    if not weight_sql or not warehouse_map:
        return []

    pure_sql = (
        "COALESCE(b.metal_weight, 0) * COALESCE(b.metal_purity + 0, 0) / 100"
        if raw_material_type == "Metal" else "0"
    )

    if serial_detail:
        select = f"""
            sn.name as serial_no, sn.item_code, sn.warehouse, sn.status,
            {weight_sql} as qty, {pure_sql} as pure_gold, 1 as pieces
        """
        group_by = "ORDER BY sn.warehouse, sn.name"
    else:
        select = f"""
            sn.warehouse, COUNT(*) as pieces,
            SUM({weight_sql}) as qty, SUM({pure_sql}) as pure_gold
        """
        group_by = "GROUP BY sn.warehouse"

    return frappe.db.sql(
        f"""
        SELECT {select}
        FROM `tabSerial No` sn
        LEFT JOIN `tabBOM` b ON b.name = sn.custom_bom_no
        WHERE sn.company = %(company)s
          AND sn.status IN %(statuses)s
          AND sn.warehouse IN %(warehouses)s
          AND COALESCE(sn.custom_bom_no, '') != ''  -- finished pieces; skips serialised consumables
        {group_by}
        """,
        {"company": company, "statuses": FINISHED_SERIAL_STATUSES, "warehouses": list(warehouse_map)},
        as_dict=True,
    )


def summarise_balances(balances, finished, warehouse_map, is_metal):
    """Accumulate ledger balances and finished pieces into
    {(group, key, stock_key): {qty, pure_gold, pieces, fg_weight, fg_pure_gold, label}}.
    Finished pieces' BOM weight is kept in fg_* and never added to qty."""
    buckets = {}

    def bucket_for(warehouse):
        info = warehouse_map.get(warehouse)
        if not info:
            return None
        return buckets.setdefault(
            (info.group, info.key, info.stock_key),
            {"qty": 0.0, "pure_gold": 0.0, "pieces": 0, "fg_weight": 0.0, "fg_pure_gold": 0.0, "label": info.label},
        )

    for row in balances:
        bucket = bucket_for(row.warehouse)
        if bucket is None:
            continue
        bucket["qty"] += flt(row.qty)
        if is_metal:
            bucket["pure_gold"] += get_pure_gold_from_item_code(row.item_code, row.qty)

    for row in finished:
        bucket = bucket_for(row.warehouse)
        if bucket is None:
            continue
        bucket["fg_weight"] += flt(row.qty)
        bucket["fg_pure_gold"] += flt(row.pure_gold)
        bucket["pieces"] += cint(row.pieces)

    return buckets


def has_stock(bucket):
    return abs(bucket["qty"]) > 0.0005 or bucket["pieces"]


# ---------------------------------------------------------------------------
# Report rows
# ---------------------------------------------------------------------------

def view_button(group, key, stock_key, label):
    return (
        '<button class="btn btn-xs btn-primary view-stock-details" '
        f'data-group="{frappe.utils.escape_html(group)}" '
        f'data-key="{frappe.utils.escape_html(key)}" '
        f'data-stock-key="{frappe.utils.escape_html(stock_key)}" '
        f'data-label="{frappe.utils.escape_html(label)}">View</button>'
    )


def make_row(label, indent, qty="", pure_gold="", pieces="", fg_weight="", fg_pure_gold="", button="", **flags):
    row = {
        "section_name": label,
        "indent": indent,
        "quantity": qty,
        "pure_gold_weight": pure_gold,
        "pieces": pieces,
        "fg_weight": fg_weight,
        "fg_pure_gold": fg_pure_gold,
        "view_details": button,
    }
    row.update(flags)
    return row


def blank_if_zero(value):
    return value if abs(flt(value)) > 0.0005 else ""


def get_data(filters):
    company = filters.company
    raw_material_type = filters.raw_material_type
    is_metal = raw_material_type == "Metal"
    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()

    warehouse_map = get_warehouse_map(company, filters.get("branch"))
    warehouse_map = filter_warehouse_map(warehouse_map, get_allowed_departments(filters))

    item_groups = get_existing_item_groups(raw_material_type)
    balances = get_ledger_balances(company, item_groups, as_on_date, warehouses=list(warehouse_map))
    finished = get_finished_goods(company, raw_material_type, warehouse_map)
    buckets = summarise_balances(balances, finished, warehouse_map, is_metal)

    data = []
    def new_total():
        return {"qty": 0.0, "pure_gold": 0.0, "pieces": 0, "fg_weight": 0.0, "fg_pure_gold": 0.0}

    grand = new_total()

    def add_total(total, bucket):
        for field in total:
            total[field] += bucket[field]

    def amounts(values):
        return dict(
            qty=blank_if_zero(values["qty"]),
            pure_gold=blank_if_zero(values["pure_gold"]),
            pieces=values["pieces"] or "",
            fg_weight=blank_if_zero(values["fg_weight"]),
            fg_pure_gold=blank_if_zero(values["fg_pure_gold"]),
        )

    def stock_row(label, bucket, button):
        return make_row(label, 1, button=button, is_stock_type=True, **amounts(bucket))

    def total_row(label, total, **flags):
        return make_row(label, 0, **amounts(total), **flags)

    # 1. Departments
    departments = sorted({key for (group, key, _sk) in buckets if group == "department"})
    for department in departments:
        label = next(b["label"] for (g, k, _sk), b in buckets.items() if g == "department" and k == department)
        rows = []
        dept_total = new_total()
        for stock_key, stock_label in STOCK_TYPES:
            bucket = buckets.get(("department", department, stock_key))
            if not bucket or not has_stock(bucket):
                continue
            add_total(dept_total, bucket)
            rows.append(stock_row(
                stock_label, bucket,
                view_button("department", department, stock_key, f"{label} - {stock_label}"),
            ))
        if not rows:
            continue
        data.append(make_row(label, 0, is_department_header=True))
        data.extend(rows)
        data.append(total_row(f"{label} Total", dept_total, is_department_total=True))
        add_total(grand, dept_total)

    # 2. Supplier / Job Work, 3. Unassigned
    for group, title in (
        ("supplier", _("Supplier / Job Work")),
        ("unassigned", _("Unassigned Warehouses")),
    ):
        group_buckets = sorted(
            ((key, bucket) for (g, key, _sk), bucket in buckets.items() if g == group and has_stock(bucket)),
            key=lambda kb: -kb[1]["qty"],
        )
        if not group_buckets:
            continue
        data.append(make_row(title, 0, is_department_header=True))
        group_total = new_total()
        for key, bucket in group_buckets:
            add_total(group_total, bucket)
            data.append(stock_row(bucket["label"], bucket, view_button(group, key, group, bucket["label"])))
        data.append(total_row(f"{title} Total", group_total, is_department_total=True))
        add_total(grand, group_total)

    if data:
        data.append(total_row(_("Grand Total"), grand, is_grand_total=True))

    return data


# ---------------------------------------------------------------------------
# Whitelisted endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_stock_details(group, key, stock_key, filters):
    """Rows behind one report line: item-wise balances per warehouse (with the
    employee holding it) plus any finished pieces (serial-wise) in those warehouses."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    company = filters.company
    raw_material_type = filters.raw_material_type
    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()

    warehouse_map = get_warehouse_map(company, filters.get("branch"))

    selected = {
        wh: info for wh, info in warehouse_map.items()
        if info.group == group and info.key == key and info.stock_key == stock_key
    }
    balances = get_ledger_balances(
        company, get_existing_item_groups(raw_material_type), as_on_date, warehouses=list(selected)
    )

    pieces = get_finished_goods(company, raw_material_type, selected, serial_detail=True)

    is_metal = raw_material_type == "Metal"
    show_employee = group == "department" and stock_key in ("employee_wip", "employee_msl")

    def detail_row(warehouse, item_code, serial_no, qty, pure_gold):
        info = selected[warehouse]
        row = {"Warehouse": warehouse}
        if show_employee:
            row["Employee"] = f"{info.employee_name or ''} ({info.employee})"
        row["Item Code"] = item_code
        if pieces:
            row["Serial No"] = serial_no
        row["Weight"] = flt(qty, 3)
        if is_metal:
            row["Pure Gold Weight"] = flt(pure_gold, 3)
        return row

    rows = [
        detail_row(b.warehouse, b.item_code, "", b.qty, get_pure_gold_from_item_code(b.item_code, b.qty))
        for b in sorted(balances, key=lambda r: (r.warehouse, -flt(r.qty)))
    ]
    rows += [detail_row(p.warehouse, p.item_code, p.serial_no, p.qty, p.pure_gold) for p in pieces]
    return rows


@frappe.whitelist()
def get_summary_comparison(filters):
    """Compares the report's Grand Total for the whole company (department,
    manufacturer and branch filters ignored, as Stock Balance has none of them)
    with the standard Stock Balance report for the same item groups. The finished
    pieces' BOM weight is split out, as Stock Balance does not contain it."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else (filters or {}))

    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("raw_material_type"):
        frappe.throw(_("Raw Material Type is required"))

    company = filters.company
    raw_material_type = filters.raw_material_type
    as_on_date = getdate(filters.get("as_on_date")) if filters.get("as_on_date") else getdate()

    warehouse_map = get_warehouse_map(company)
    item_groups = get_existing_item_groups(raw_material_type)
    balances = get_ledger_balances(company, item_groups, as_on_date)

    sections = {"department": 0.0, "supplier": 0.0, "unassigned": 0.0}
    unassigned_rows = {}
    for row in balances:
        info = warehouse_map.get(row.warehouse)
        group = info.group if info else "unassigned"
        sections[group] += flt(row.qty)
        if group == "unassigned":
            unassigned_rows[row.warehouse] = unassigned_rows.get(row.warehouse, 0.0) + flt(row.qty)
    report_total = sum(sections.values())

    from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance_execute

    stock_balance_qty = 0.0
    # Only top-level groups: Stock Balance includes descendants itself.
    for item_group in [g for g in get_item_groups([raw_material_type]) if frappe.db.exists("Item Group", g)]:
        _columns, sb_data = stock_balance_execute(frappe._dict({
            "company": company,
            "from_date": "2000-01-01",
            "to_date": as_on_date,
            "item_group": item_group,
        }))
        for row in sb_data:
            stock_balance_qty += flt(row.get("bal_qty") or 0)

    finished = get_finished_goods(company, raw_material_type, warehouse_map)
    finished_qty = sum(flt(r.qty) for r in finished)

    return {
        "company": company,
        "as_on_date": str(as_on_date),
        "raw_material_type": raw_material_type,
        "department_qty": sections["department"],
        "supplier_qty": sections["supplier"],
        "unassigned_qty": sections["unassigned"],
        "unassigned_breakdown": [
            {"warehouse": wh, "qty": qty}
            for wh, qty in sorted(unassigned_rows.items(), key=lambda kv: -kv[1])
            if abs(qty) > 0.0005
        ],
        "ledger_total": report_total,
        "finished_goods_qty": finished_qty,
        "finished_goods_pieces": sum(cint(r.pieces) for r in finished),
        "report_total": report_total,
        "stock_balance_qty": stock_balance_qty,
        "difference": stock_balance_qty - report_total,
    }


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def department_query(doctype, txt, searchfield, start, page_len, filters):
    """Department filter options: departments of the selected company that hold
    stock warehouses (directly or through their employees), narrowed by manufacturer."""
    company = filters.get("company")
    if not company:
        return []

    warehouse_map = get_warehouse_map(company, filters.get("branch"))
    departments = {info.department for info in warehouse_map.values() if info.group == "department"}
    if filters.get("manufacturer"):
        departments &= get_manufacturer_departments(filters.get("manufacturer"))

    departments = sorted(d for d in departments if not txt or txt.lower() in d.lower())
    return [[d] for d in departments[cint(start): cint(start) + cint(page_len)]]
