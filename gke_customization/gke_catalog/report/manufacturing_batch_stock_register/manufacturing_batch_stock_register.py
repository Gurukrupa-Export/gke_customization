# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, getdate

from gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary import (
    OPERATION_STOCK_CONDITIONS,
    OPERATION_WEIGHT_FIELDS,
    get_existing_item_groups,
    get_operation_stock,
    get_warehouse_map,
)

# Report tab (field prefix) -> Branch Stock Summary raw material type. The
# item groups of each come from that report, so both count the same items.
MATERIALS = (
    ("gold",    "Metal"),
    ("diamond", "Diamond"),
    ("stone",   "Gemstone"),
    ("finding", "Finding"),
)


def _item_group_field():
    """{item_group: material prefix} for every material tab, cached per request."""
    if not hasattr(frappe.local, "mbsr_item_group_field"):
        frappe.local.mbsr_item_group_field = {
            group: label
            for label, raw_material_type in MATERIALS
            for group in get_existing_item_groups(raw_material_type)
        }
    return frappe.local.mbsr_item_group_field

UNASSIGNED = "Unassigned"
FINISHED   = "Finished Goods"
CLOSED     = "Closed Work Order"

DEPARTMENT_OVERRIDE_ROLES = {"System Manager", "Administrator"}

# ---------------------------------------------------------------------------
# Department access control — same pattern as department_stock_issue_report.py:
# anyone without an override role is locked to their own Employee department
# and cannot view/change it to another one, even by calling execute() directly.
# ---------------------------------------------------------------------------

def enforce_department_restriction(filters):
    if DEPARTMENT_OVERRIDE_ROLES & set(frappe.get_roles()):
        return
    filters["department"] = get_employee_department(frappe.session.user)


def get_employee_department(user):
    return frappe.db.get_value("Employee", {"user_id": user}, "department")


@frappe.whitelist()
def get_user_department_filter():
    """Used by the report's JS to prefill/lock 'Department' without requiring
    the caller to have read permission on Employee (a plain report user usually won't)."""
    can_change_department = bool(DEPARTMENT_OVERRIDE_ROLES & set(frappe.get_roles()))
    return {
        "can_change_department": can_change_department,
        "department": None if can_change_department else get_employee_department(frappe.session.user),
    }

# ---------------------------------------------------------------------------
# Gold/Diamond/Stone ledger — sourced from Stock Ledger Entry (the ground
# truth Frappe maintains for EVERY stock-affecting doctype, not just Stock
# Entry). Balances are SUM(actual_qty), the same as Stock Balance and Branch
# Stock Summary — NOT the "latest" qty_after_transaction row, since several
# SLEs of one voucher share a posting_datetime and SLE names are random
# hashes, so there is no reliable "last" row to pick.
#
# Warehouse -> department uses Branch Stock Summary's classification
# (Warehouse.department, else the warehouse employee's department, else a
# department whose name the warehouse name starts with; subcontractor
# warehouses excluded), so employee WIP/MSL warehouses with a blank
# Warehouse.department are counted.
#
# Opening/Issue/Receive are ledger figures: Issue/Receive are that ledger's
# negative/positive legs in the period. Closing is the department total of
# Branch Stock Summary (As On Date = To Date): the ledger closing, with the
# Manufacturing Warehouse / Employee WIP lines replaced by the weight on
# Manufacturing Operations (see _get_operation_line_adjustment). So Closing =
# Opening + Receive - Issue + that adjustment, not the bare ledger sum. "Count" (distinct
# work orders) is NOT part of this — it stays on the Stock-Entry-based logic
# below, since SLE has no work-order identity and most other voucher types
# (Purchase Receipt, Delivery Note, ...) have no work order at all.
# ---------------------------------------------------------------------------

def _get_department_warehouse_map(department):
    """{warehouse: department} for every department-owned warehouse of the
    department's company, classified the same way as Branch Stock Summary."""
    company = frappe.db.get_value("Department", department, "company")
    companies = [company] if company else frappe.get_all("Company", pluck="name")

    wh_map = {}
    for c in companies:
        for wh, info in get_warehouse_map(c).items():
            if info.group == "department":
                wh_map[wh] = info.department
    return wh_map


def _department_warehouses(wh_map, department):
    return [wh for wh, dept in wh_map.items() if dept == department]


def _sle_base(warehouses, extra_clause=""):
    return """
        SELECT
            sle.name          AS sle_name,
            sle.item_code     AS item_code,
            sle.warehouse     AS warehouse,
            sle.actual_qty    AS actual_qty,
            sle.posting_date  AS posting_date,
            sle.voucher_type  AS voucher_type,
            sle.voucher_no    AS voucher_no,
            i.item_group      AS item_group
        FROM `tabStock Ledger Entry` sle
        JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.is_cancelled = 0
          AND sle.warehouse IN %(warehouses)s
          AND i.item_group IN %(item_groups)s
          {extra_clause}
    """.format(extra_clause=extra_clause)


def _sle_period_clause(from_date, to_date):
    """Date bounds on sle.posting_datetime rather than posting_date, so the
    (item_code, warehouse, posting_datetime) index narrows the scan instead
    of every SLE of the item since the beginning being read and filtered."""
    clause, params = "", {}
    if from_date:
        clause += " AND sle.posting_datetime >= %(from_dt)s"
        params["from_dt"] = "{} 00:00:00".format(getdate(from_date))
    if to_date:
        clause += " AND sle.posting_datetime < %(to_dt)s"
        params["to_dt"] = "{} 00:00:00".format(add_days(getdate(to_date), 1))
    return clause, params


def _pivot_item_group(rows, department, value_cols, suffixes):
    """rows: dicts with item_group, <value_cols...> for one department.
    Returns {department: {"<material>_<suffix>": value, ...}}."""
    d = {}
    for r in rows:
        label = _item_group_field().get(r["item_group"])
        if not label:
            continue
        for col, suffix in zip(value_cols, suffixes):
            field = "{}_{}".format(label, suffix)
            d[field] = d.get(field, 0) + flt(r.get(col))
    return {department: d}


def _get_material_opening(from_date, department, wh_map):
    warehouses = _department_warehouses(wh_map, department)
    if not from_date or not warehouses:
        return {}

    date_clause, date_params = _sle_period_clause(None, add_days(getdate(from_date), -1))

    rows = frappe.db.sql("""
        SELECT item_group, SUM(actual_qty) AS balance
        FROM ({base}) sle_f
        GROUP BY item_group
    """.format(base=_sle_base(warehouses, date_clause)),
    {"item_groups": list(_item_group_field()),
     "warehouses": warehouses, **date_params},
    as_dict=True)

    return _pivot_item_group(rows, department, ["balance"], ["opening"])


def _get_operation_line_adjustment(to_date, department):
    """{material: operation weight - ledger balance} of the department's
    Manufacturing Warehouse / Employee WIP lines, the change Branch Stock
    Summary makes to those lines (its apply_operation_stock). The ledger part
    is as on To Date; operation weight is current, as in that report."""
    company = frappe.db.get_value("Department", department, "company")
    companies = [company] if company else frappe.get_all("Company", pluck="name")

    operation_labels = {label for label, rmt in MATERIALS if rmt in OPERATION_WEIGHT_FIELDS}
    adjustment = {}
    warehouses = []
    for c in companies:
        warehouses += [
            wh for wh, info in get_warehouse_map(c).items()
            if info.group == "department" and info.department == department
            and info.stock_key in OPERATION_STOCK_CONDITIONS
        ]
        for label, raw_material_type in MATERIALS:
            if label not in operation_labels:
                continue
            for stock_key in OPERATION_STOCK_CONDITIONS:
                for r in get_operation_stock(c, raw_material_type, frappe._dict(), stock_key, department=department):
                    adjustment[label] = adjustment.get(label, 0) + flt(r.qty)

    if warehouses:
        date_clause, date_params = _sle_period_clause(None, to_date)
        rows = frappe.db.sql("""
            SELECT item_group, SUM(actual_qty) AS balance
            FROM ({base}) sle_f
            GROUP BY item_group
        """.format(base=_sle_base(warehouses, date_clause)),
        {"item_groups": list(_item_group_field()),
         "warehouses": warehouses, **date_params},
        as_dict=True)

        for r in rows:
            label = _item_group_field().get(r["item_group"])
            if label in operation_labels:
                adjustment[label] = adjustment.get(label, 0) - flt(r["balance"])

    return adjustment


def _get_material_period(from_date, to_date, department, wh_map):
    warehouses = _department_warehouses(wh_map, department)
    if not warehouses:
        return {}

    date_clause, date_params = _sle_period_clause(from_date, to_date)

    rows = frappe.db.sql("""
        SELECT item_group,
            SUM(CASE WHEN actual_qty > 0 THEN actual_qty  ELSE 0 END) AS receive,
            SUM(CASE WHEN actual_qty < 0 THEN -actual_qty ELSE 0 END) AS issue
        FROM ({base}) sle_f
        GROUP BY item_group
    """.format(base=_sle_base(warehouses, date_clause)),
    {"item_groups": list(_item_group_field()),
     "warehouses": warehouses, **date_params},
    as_dict=True)

    return _pivot_item_group(rows, department, ["issue", "receive"], ["issue", "receive"])


def _loss_variant_map():
    """{loss template prefix: source template prefix} from Variant Loss Table
    (ML -> M, FL -> F, DL -> D, GB -> G, ...), cached per request."""
    if not hasattr(frappe.local, "mbsr_loss_variant_map"):
        frappe.local.mbsr_loss_variant_map = {
            r.loss_variant: r.variant
            for r in frappe.db.sql(
                "SELECT DISTINCT variant, loss_variant FROM `tabVariant Loss Table` "
                "WHERE IFNULL(variant, '') != '' AND IFNULL(loss_variant, '') != ''",
                as_dict=True)
        }
    return frappe.local.mbsr_loss_variant_map


def _source_item_code(item_code):
    """ML-G-22KT-91.75-Y -> M-G-22KT-91.75-Y; non-loss items unchanged."""
    prefix, sep, rest = (item_code or "").partition("-")
    source = _loss_variant_map().get(prefix)
    return "{}-{}".format(source, rest) if sep and source else item_code


def _loss_twin_item_codes(item_code):
    """The item itself, its source item and every loss variant of that source."""
    source = _source_item_code(item_code)
    prefix, sep, rest = source.partition("-")
    codes = {item_code, source}
    if sep:
        codes.update("{}-{}".format(loss, rest)
                     for loss, src in _loss_variant_map().items() if src == prefix)
    return codes


def _get_material_counterparty_breakdown(from_date, to_date, department, wh_map):
    warehouses = _department_warehouses(wh_map, department)
    if not warehouses:
        return []

    date_clause, date_params = _sle_period_clause(from_date, to_date)
    params = {"item_groups": list(_item_group_field()), "warehouses": warehouses, **date_params}

    self_rows = frappe.db.sql("SELECT * FROM ({base}) self".format(base=_sle_base(warehouses, date_clause)),
                              params, as_dict=True)
    if not self_rows:
        return []

    # Each leg's counterparty is the other warehouse of the same voucher that
    # moved the same item by the opposite qty (first by SLE name if several);
    # failing that, the first other warehouse that moved the same item the
    # opposite way at all (a Process Loss books many small legs into one
    # combined loss leg, so their qtys never match one-to-one).
    # Every voucher's ledger rows are fetched once and paired in Python — a
    # SQL self-join re-scans the whole voucher for every leg, which on large
    # manufacturing vouchers ran for over an hour on a 20-day range. Paired
    # legs share the posting_date, so `pair` is bounded by the same dates.
    # A Process Loss moves the source item (M-G-...) out and its loss variant
    # (ML-G-..., per Variant Loss Table) into a scrap warehouse, so both legs
    # are keyed by the source item code to pair them.
    def key(voucher_type, voucher_no, item_code, qty):
        return (voucher_type, voucher_no, _source_item_code(item_code), flt(qty, 6))

    def item_key(voucher_type, voucher_no, item_code, qty):
        return (voucher_type, voucher_no, _source_item_code(item_code), flt(qty) > 0)

    candidates, item_candidates = {}, {}
    vouchers = sorted({r["voucher_no"] for r in self_rows})
    items    = sorted({twin for r in self_rows for twin in _loss_twin_item_codes(r["item_code"])})
    for i in range(0, len(vouchers), 1000):
        for p in frappe.db.sql("""
            SELECT sle.name, sle.voucher_type, sle.voucher_no, sle.item_code, sle.warehouse, sle.actual_qty
            FROM `tabStock Ledger Entry` sle
            WHERE sle.voucher_no IN %(vouchers)s
              AND sle.item_code IN %(items)s
              AND sle.is_cancelled = 0
              {date_clause}
            ORDER BY sle.name
        """.format(date_clause=date_clause),
        {"vouchers": vouchers[i:i + 1000], "items": items, **date_params}, as_dict=True):
            args = (p["voucher_type"], p["voucher_no"], p["item_code"], p["actual_qty"])
            candidates.setdefault(key(*args), []).append(p["warehouse"])
            if flt(p["actual_qty"]):
                item_candidates.setdefault(item_key(*args), []).append(p["warehouse"])

    paired = []
    for r in self_rows:
        label = _item_group_field().get(r["item_group"])
        if not label or not flt(r["actual_qty"]):
            continue
        args = (r["voucher_type"], r["voucher_no"], r["item_code"], -flt(r["actual_qty"]))
        pair_warehouse = next(
            (wh for wh in candidates.get(key(*args), []) + item_candidates.get(item_key(*args), [])
             if wh != r["warehouse"]),
            None,
        )
        paired.append((r, label, pair_warehouse))

    # Loss booked into a Scrap warehouse gets its own row (the scrap warehouse)
    # instead of being merged into that warehouse's department. A department's
    # own scrap warehouse receiving from the department shows on the same row.
    scrap_warehouses = set(frappe.get_all("Warehouse", pluck="name", filters={
        "warehouse_type": "Scrap",
        "name": ["in", list({w for r, _, pw in paired for w in (r["warehouse"], pw) if w})],
    })) if paired else set()

    # Legs that pair with no department warehouse are classified instead of
    # being left Unassigned:
    # - paired with a warehouse of no department -> that warehouse;
    # - a Repack (any Repack-purpose type except Process Loss) converts one
    #   material into another inside the warehouse -> a row named after the
    #   conversion, e.g. "Repack (Gold → Finding)";
    # - a Manufacture consumes the material into the finished item ->
    #   "Finished Goods" (the same row the PMO count uses);
    # - any other Stock Entry -> its Stock Entry Type; any other voucher
    #   (Purchase Receipt, Delivery Note, ...) -> its voucher type.
    unpaired = [(r, pw) for r, _, pw in paired if not wh_map.get(pw)]
    unpaired_entries = {se.name: se for se in frappe.get_all("Stock Entry",
        fields=["name", "purpose", "stock_entry_type"],
        filters={"name": ["in", list({r["voucher_no"] for r, _ in unpaired if r["voucher_type"] == "Stock Entry"})]},
    )} if unpaired else {}
    repack_vouchers = [name for name, se in unpaired_entries.items()
                       if se.purpose == "Repack" and se.stock_entry_type != "Process Loss"]

    # Both sides of a Repack, named by material tab or, for items outside the
    # material tabs (e.g. "Metal Unused/Loose Material"), by item group.
    repack_sides = {}
    for i in range(0, len(repack_vouchers), 1000):
        for p in frappe.db.sql("""
            SELECT sle.voucher_no, sle.actual_qty, i.item_group
            FROM `tabStock Ledger Entry` sle
            JOIN `tabItem` i ON i.name = sle.item_code
            WHERE sle.voucher_no IN %(vouchers)s
              AND sle.warehouse IN %(warehouses)s
              AND sle.is_cancelled = 0
              {date_clause}
        """.format(date_clause=date_clause),
        {"vouchers": repack_vouchers[i:i + 1000], "warehouses": warehouses, **date_params}, as_dict=True):
            if flt(p["actual_qty"]):
                sides = repack_sides.setdefault(p["voucher_no"], ({}, {}))
                material = _item_group_field().get(p["item_group"])
                name = material.title() if material else (p["item_group"] or "").rsplit(" - ", 1)[0]
                sides[0 if flt(p["actual_qty"]) < 0 else 1][name] = True

    material_order = [m.title() for m, _ in MATERIALS]
    def side_names(names):
        ordered = [m for m in material_order if m in names] + sorted(n for n in names if n not in material_order)
        return "/".join(ordered) or "-"

    def repack_label(voucher_no):
        out, into = repack_sides.get(voucher_no, ({}, {}))
        return "Repack ({} → {})".format(side_names(out), side_names(into))

    def unpaired_label(r, pair_warehouse):
        if pair_warehouse:
            return pair_warehouse
        se = unpaired_entries.get(r["voucher_no"]) if r["voucher_type"] == "Stock Entry" else None
        if not se:
            return r["voucher_type"] or UNASSIGNED
        if r["voucher_no"] in repack_sides:
            return repack_label(r["voucher_no"])
        if se.purpose == "Manufacture":
            return FINISHED
        return se.stock_entry_type or se.purpose or UNASSIGNED

    merged = {}
    for r, label, pair_warehouse in paired:
        if pair_warehouse in scrap_warehouses:
            counterparty = pair_warehouse
        elif r["warehouse"] in scrap_warehouses and wh_map.get(pair_warehouse) == department:
            counterparty = r["warehouse"]
        else:
            counterparty = wh_map.get(pair_warehouse) or unpaired_label(r, pair_warehouse)
        d = merged.setdefault(counterparty, {})
        qty = flt(r["actual_qty"])
        if qty > 0:
            field = "{}_receive".format(label)
            d[field] = d.get(field, 0) + qty
        else:
            field = "{}_issue".format(label)
            d[field] = d.get(field, 0) + (-qty)

    return [dict(department=department, counterparty=cp, **vals) for cp, vals in merged.items()]


def execute(filters=None):
    filters = filters or {}
    enforce_department_restriction(filters)
    validate_filters(filters)
    return get_columns(), get_data(filters)


def validate_filters(filters):
    if filters.get("from_date") and filters.get("to_date"):
        if getdate(filters["from_date"]) > getdate(filters["to_date"]):
            frappe.throw(_("From Date cannot be greater than To Date"))

    if not filters.get("department"):
        # The no-filter (all-departments) view scans the whole Stock Ledger
        # at once and takes ~17 minutes; per-department it's ~80s. Require
        # a department rather than let the slow path run.
        frappe.throw(_("Department is required for this report"))


def get_columns():
    return [
        {"fieldname": "department", "label": _("Department"), "fieldtype": "Data",  "width": 220},
        {"fieldname": "opening",    "label": _("Opening"),    "fieldtype": "Float", "width": 130},
        {"fieldname": "issue",      "label": _("Issue"),      "fieldtype": "Float", "width": 130},
        {"fieldname": "receive",    "label": _("Receive"),    "fieldtype": "Float", "width": 130},
        {"fieldname": "closing",    "label": _("Closing"),    "fieldtype": "Float", "width": 130},
    ]


def get_data(filters):
    from_date  = filters.get("from_date")
    to_date    = filters.get("to_date")
    department = filters.get("department")

    dept_list = _get_departments(department)
    if not dept_list:
        return []

    # Gold/Diamond/Stone — ground truth from Stock Ledger Entry.
    wh_map             = _get_department_warehouse_map(department)
    period_material    = _get_material_period(from_date, to_date, department, wh_map)
    opening_material   = _get_material_opening(from_date, department, wh_map)
    breakdown_material = _get_material_counterparty_breakdown(from_date, to_date, department, wh_map)
    operation_adjustment = _get_operation_line_adjustment(to_date, department)

    bm = {}
    for r in breakdown_material:
        bm.setdefault(r["department"], []).append(r)

    def counterparty_rows(dept):
        """Merge the material (SLE-based) and PMO count (Department IR-based)
        counterparty breakdowns for one department into one row per
        counterparty — material columns from bm, count columns from pmo."""
        merged = {}
        for r in bm.get(dept, []):
            merged.setdefault(r["counterparty"], {}).update(
                {k: v for k, v in r.items() if k not in ("department", "counterparty")}
            )
        for cp_name, vals in pmo["counterparty"].items():
            merged.setdefault(cp_name, {}).update(vals)
        return merged

    result = []
    for row in dept_list:
        dept = row["department"]
        if not dept:
            continue

        pd_mat = period_material.get(dept, {})
        od_mat = opening_material.get(dept, {})
        pmo = _get_pmo_counts(from_date, to_date, dept)

        # ── Gold/Diamond/Stone/Finding ────────────────────────────────────
        # Opening is the department's stock-on-hand from the Stock Ledger;
        # Issue/Receive are that same ledger's negative/positive legs in the
        # period. Closing is that ledger closing (Opening + Receive - Issue)
        # with the Manufacturing Warehouse / Employee WIP lines taken from
        # Manufacturing Operations, so it matches Branch Stock Summary.
        values = {}
        for label, _raw_material_type in MATERIALS:
            o = flt(od_mat.get(label + "_opening"))
            i = flt(pd_mat.get(label + "_issue"))
            r = flt(pd_mat.get(label + "_receive"))
            closing = o + r - i + flt(operation_adjustment.get(label))
            values.update({label + "_opening": o, label + "_issue": i,
                           label + "_receive": r, label + "_closing": closing})

        # ── Count (PMOs) ──────────────────────────────────────────────────
        values.update(pmo["totals"])

        result.append(_report_row(dept, values))

        # ── Level-2: department-to-department breakdown ────────────────────
        # One row per counterparty department this department transacted
        # with in the period. "issue" = qty sent out to that counterparty,
        # "receive" = qty taken in from that counterparty, "closing" = net
        # for that pair only — period-only, no opening carried at this level.
        for cp_name, cp in sorted(counterparty_rows(dept).items()):
            values = {}
            for label in [m[0] for m in MATERIALS] + ["count"]:
                i = flt(cp.get(label + "_issue"))
                r = flt(cp.get(label + "_receive"))
                values.update({label + "_opening": 0, label + "_issue": i,
                               label + "_receive": r, label + "_closing": r - i})
            # A PMO count has no "net" per counterparty — left blank, not r - i.
            values["count_closing"] = None

            result.append(_report_row("    " + cp_name, values))

    return result


def _report_row(department, values):
    """The display columns default to Gold; the JS tabs swap them for
    another material's own <material>_* fields client-side."""
    return frappe._dict(
        department = department,
        opening    = values["gold_opening"],
        issue      = values["gold_issue"],
        receive    = values["gold_receive"],
        closing    = values["gold_closing"],
        **values,
    )


def _get_departments(dept_filter=None):
    cond   = "WHERE IFNULL(name, '') != ''"
    params = {}
    if dept_filter:
        cond  += " AND name = %(dept_filter)s"
        params = {"dept_filter": dept_filter}

    return frappe.db.sql(
        "SELECT name AS department FROM `tabDepartment` {cond} ORDER BY name".format(cond=cond),
        params, as_dict=True,
    )


# ---------------------------------------------------------------------------
# Batch Count — number of PMOs (Parent Manufacturing Orders) in a department.
#
# What moves between departments is the Manufacturing Work Order, through a
# Department IR: an Issue takes it out of `current_department` (in transit to
# `next_department`), the matching Receive brings it into `current_department`
# (from `previous_department`). Several work orders belong to one PMO, and a
# PMO is one batch, so every figure counts distinct PMOs:
#
#   Opening / Closing - PMOs with at least one work order sitting in the
#                       department at the start of From Date / end of To Date
#   Receive / Issue   - PMOs received into / issued out of the department in
#                       the period
#
# Each figure is a count of PMOs, so Closing is NOT Opening + Receive - Issue:
# a PMO whose work orders are partly issued is "issued" and still "in" the
# department. Closing is the real position, never a running total, so it
# can't go negative.
#
# Where a work order sits at a point in time is its last Department IR before
# it. Every work order starts in the department of its first Issue (Manufacturing
# Plan & Management) and stays there from creation until that Issue. After the
# final Receive (Tagging) the work order is Completed with no further movement,
# so a Completed work order leaves the flow at its last Receive (issued to
# "Finished Goods"), and a Closed one when it was closed (last modified).
# An active work order with no Department IR at all has never moved: it sits in
# the department of its current Manufacturing Operation since its creation.
# ---------------------------------------------------------------------------

def _get_pmo_counts(from_date, to_date, department):
    start = get_datetime(getdate(from_date)) if from_date else None
    end   = get_datetime(add_days(getdate(to_date), 1)) if to_date else None

    def in_period(dt):
        return (start is None or dt >= start) and (end is None or dt < end)

    # Full history of every work order that ever passed through the department
    # (an Issue from it or a Receive into it — both carry it as current_department).
    events = frappe.db.sql("""
        SELECT op.manufacturing_work_order AS mwo, ir.type AS type,
               ir.current_department AS cur, ir.next_department AS nxt,
               ir.previous_department AS prev, ir.date_time AS dt
        FROM `tabDepartment IR` ir
        JOIN `tabDepartment IR Operation` op ON op.parent = ir.name
        WHERE ir.docstatus = 1
          AND op.manufacturing_work_order IN (
              SELECT op2.manufacturing_work_order
              FROM `tabDepartment IR` ir2
              JOIN `tabDepartment IR Operation` op2 ON op2.parent = ir2.name
              WHERE ir2.docstatus = 1 AND ir2.current_department = %(dept)s
          )
        ORDER BY ir.date_time, ir.name
    """, {"dept": department}, as_dict=True)

    by_mwo = {}
    for e in events:
        by_mwo.setdefault(e.mwo, []).append(e)

    work_orders = {
        w.name: w for w in frappe.get_all(
            "Manufacturing Work Order",
            filters={"name": ["in", list(by_mwo)], "docstatus": 1},
            fields=["name", "manufacturing_order", "status", "creation", "modified"],
        )
    } if by_mwo else {}

    never_moved = frappe.db.sql("""
        SELECT w.name, w.manufacturing_order, w.creation
        FROM `tabManufacturing Work Order` w
        JOIN `tabManufacturing Operation` mop ON mop.name = w.manufacturing_operation
        WHERE w.docstatus = 1
          AND w.status IN ('Not Started', 'In Process', 'Stopped')
          AND mop.department = %(dept)s
          AND NOT EXISTS (
              SELECT 1
              FROM `tabDepartment IR Operation` op
              JOIN `tabDepartment IR` ir ON ir.name = op.parent AND ir.docstatus = 1
              WHERE op.manufacturing_work_order = w.name
          )
    """, {"dept": department}, as_dict=True)

    opening, closing = set(), set()
    for wo in never_moved:
        if not wo.manufacturing_order:
            continue
        if start is not None and wo.creation < start:
            opening.add(wo.manufacturing_order)
        if end is None or wo.creation < end:
            closing.add(wo.manufacturing_order)

    issued, received = set(), set()
    cp_issued, cp_received = {}, {}

    for mwo, evs in by_mwo.items():
        wo = work_orders.get(mwo)
        if not wo or not wo.manufacturing_order:
            continue
        pmo = wo.manufacturing_order

        # (when, department now holding it or None, counterparty) — in order.
        moves = []
        if evs[0].type == "Issue":
            moves.append((wo.creation, evs[0].cur, None))
        for e in evs:
            if e.type == "Receive":
                moves.append((e.dt, e.cur, e.prev))
                if e.cur == department and in_period(e.dt):
                    received.add(pmo)
                    cp_received.setdefault(e.prev or UNASSIGNED, set()).add(pmo)
            else:
                moves.append((e.dt, None, e.nxt))
                if e.cur == department and in_period(e.dt):
                    issued.add(pmo)
                    cp_issued.setdefault(e.nxt or UNASSIGNED, set()).add(pmo)

        last = evs[-1]
        if last.type == "Receive" and wo.status in ("Completed", "Closed"):
            exit_at = last.dt if wo.status == "Completed" else max(wo.modified, last.dt)
            moves.append((exit_at, None, None))
            if last.cur == department and in_period(exit_at):
                issued.add(pmo)
                cp_issued.setdefault(FINISHED if wo.status == "Completed" else CLOSED, set()).add(pmo)

        def location(at):
            loc = None
            for when, dept, _cp in moves:
                if at is not None and when >= at:
                    break
                loc = dept
            return loc

        if start is not None and location(start) == department:
            opening.add(pmo)
        if location(end) == department:
            closing.add(pmo)

    counterparty = {}
    for cp_name, pmos in cp_issued.items():
        counterparty.setdefault(cp_name, {})["count_issue"] = len(pmos)
    for cp_name, pmos in cp_received.items():
        counterparty.setdefault(cp_name, {})["count_receive"] = len(pmos)

    return {
        "totals": {
            "count_opening": len(opening),
            "count_issue":   len(issued),
            "count_receive": len(received),
            "count_closing": len(closing),
        },
        "counterparty": counterparty,
    }
