# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

GOLD    = "Metal - V"
DIAMOND = "Diamond - V"
STONE   = "Gemstone - V"

ITEM_GROUP_FIELD = {GOLD: "gold", DIAMOND: "diamond", STONE: "stone"}

UNASSIGNED = "Unassigned"

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
# Department attribution — derived from the ACTUAL warehouse on each Stock
# Entry Detail row, not from Manufacturing Work Order.department (which is
# the work order's final/destination department, not where stock currently
# sits — a work order parked in "Diamond Setting" can carry legs that only
# ever moved between e.g. Casting and Waxing warehouses).
#
# Same from/to convention as department_stock_issue_report.py:
#   from_dept = COALESCE(Warehouse(s_warehouse).department, se.department)
#   to_dept   = COALESCE(se.to_department, Warehouse(t_warehouse).department)
# Both sides are nullable (shared/central stores, reserve stock, subcontractor/
# employee/customer warehouses have no department owner); an unresolved side
# is surfaced as "Unassigned" rather than dropped.
#
# No stock_entry_type restriction — department resolution itself is the
# filter: ANY submitted Stock Entry whose source or target warehouse maps to
# a department counts (Material Transfer (WORK ORDER)/(DEPARTMENT), Material
# Transfer From Reserve, Material Receipt, Material Transfer to Employee,
# etc.) so every real movement into/out of a department is covered, not just
# the work-order-linked legs. Legs where both sides resolve to the SAME
# department (pure internal moves, e.g. Manufacture/Repack within one dept's
# own warehouses) are excluded downstream, not here.
# ---------------------------------------------------------------------------

_LEG_SQL = """
    SELECT
        se.manufacturing_work_order AS mwo,
        se.name                     AS se_name,
        sed.item_group              AS item_group,
        sed.transfer_qty            AS transfer_qty,
        COALESCE(NULLIF(whs.department, ''), NULLIF(se.department, ''))    AS from_dept,
        COALESCE(NULLIF(se.to_department, ''), NULLIF(wht.department, '')) AS to_dept
    FROM `tabStock Entry` se
    JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
    LEFT JOIN `tabWarehouse` whs ON whs.name = sed.s_warehouse
    LEFT JOIN `tabWarehouse` wht ON wht.name = sed.t_warehouse
    WHERE se.docstatus = 1
      {date_clause}
"""


# ---------------------------------------------------------------------------
# Gold/Diamond/Stone ledger — sourced from Stock Ledger Entry (the ground
# truth running balance Frappe maintains for EVERY stock-affecting doctype,
# not just Stock Entry), so Opening is the department's actual stock on
# hand at the start of the period, and Closing = Opening + Receive - Issue
# is an exact identity rather than an approximation: Issue/Receive are
# literally the same ledger's negative/positive legs in the period, so
# their net equals the balance's real change. "Count" (distinct work
# orders) is NOT part of this — it stays on the Stock-Entry-based logic
# above, since SLE has no work-order identity and most other voucher types
# (Purchase Receipt, Delivery Note, ...) have no work order at all.
# ---------------------------------------------------------------------------

def _sle_base(extra_clause="", department=None):
    dept_clause = "AND NULLIF(wh.department, '') = %(dept)s" if department else ""
    return """
        SELECT
            sle.name                 AS sle_name,
            sle.item_code             AS item_code,
            sle.warehouse              AS warehouse,
            sle.actual_qty              AS actual_qty,
            sle.qty_after_transaction    AS qty_after_transaction,
            sle.posting_date              AS posting_date,
            sle.posting_datetime            AS posting_datetime,
            sle.voucher_type                 AS voucher_type,
            sle.voucher_no                    AS voucher_no,
            i.item_group                       AS item_group,
            NULLIF(wh.department, '')          AS department
        FROM `tabStock Ledger Entry` sle
        JOIN `tabItem` i ON i.name = sle.item_code
        JOIN `tabWarehouse` wh ON wh.name = sle.warehouse
        WHERE sle.is_cancelled = 0
          AND NULLIF(wh.department, '') IS NOT NULL
          AND i.item_group IN (%(gold)s, %(diamond)s, %(stone)s)
          {dept_clause}
          {extra_clause}
    """.format(dept_clause=dept_clause, extra_clause=extra_clause)


def _pivot_item_group(rows, value_cols, suffixes):
    """rows: dicts with department, item_group, <value_cols...>.
    Returns {department: {"<material>_<suffix>": value, ...}}."""
    merged = {}
    for r in rows:
        label = ITEM_GROUP_FIELD.get(r["item_group"])
        if not label:
            continue
        d = merged.setdefault(r["department"], {})
        for col, suffix in zip(value_cols, suffixes):
            d["{}_{}".format(label, suffix)] = flt(r.get(col))
    return merged


def _get_material_opening(from_date, department):
    if not from_date:
        return {}

    base = _sle_base(department=department)

    rows = frappe.db.sql("""
        SELECT department, item_group, SUM(qty_after_transaction) AS balance
        FROM (
            SELECT department, item_group, qty_after_transaction,
                   ROW_NUMBER() OVER (
                       PARTITION BY item_code, warehouse
                       ORDER BY posting_datetime DESC, sle_name DESC
                   ) AS rn
            FROM ({base}) sle_f
            WHERE posting_datetime < %(from_dt)s
        ) ranked
        WHERE rn = 1
        GROUP BY department, item_group
    """.format(base=base),
    {"gold": GOLD, "diamond": DIAMOND, "stone": STONE, "dept": department,
     "from_dt": "{} 00:00:00".format(from_date)},
    as_dict=True)

    return _pivot_item_group(rows, ["balance"], ["opening"])


def _get_material_period(from_date, to_date, department):
    date_clause, date_params = _date_between(from_date, to_date, "sle.posting_date")
    base = _sle_base(extra_clause=date_clause, department=department)

    rows = frappe.db.sql("""
        SELECT department, item_group,
            SUM(CASE WHEN actual_qty > 0 THEN actual_qty  ELSE 0 END) AS receive,
            SUM(CASE WHEN actual_qty < 0 THEN -actual_qty ELSE 0 END) AS issue
        FROM ({base}) sle_f
        GROUP BY department, item_group
    """.format(base=base),
    {"gold": GOLD, "diamond": DIAMOND, "stone": STONE, "dept": department, **date_params},
    as_dict=True)

    return _pivot_item_group(rows, ["issue", "receive"], ["issue", "receive"])


def _get_material_counterparty_breakdown(from_date, to_date, department):
    date_clause, date_params = _date_between(from_date, to_date, "sle.posting_date")
    self_base = _sle_base(extra_clause=date_clause, department=department)

    # Paired legs of one transaction always share the same posting_date, so
    # bounding `pair` the same way too lets the self-join use the
    # (item_code, warehouse, posting_datetime) index instead of scanning
    # unbounded history for a match.
    pair_date_clause, pair_date_params = _date_between(from_date, to_date, "pair.posting_date")

    rows = frappe.db.sql("""
        SELECT department, item_group, actual_qty,
               COALESCE(pair_department, %(unassigned)s) AS counterparty
        FROM (
            SELECT self.department AS department, self.item_group AS item_group, self.actual_qty AS actual_qty,
                   NULLIF(pairwh.department, '') AS pair_department,
                   ROW_NUMBER() OVER (PARTITION BY self.sle_name ORDER BY pair.name) AS rn
            FROM ({self_base}) self
            LEFT JOIN `tabStock Ledger Entry` pair
                   ON pair.voucher_type = self.voucher_type
                  AND pair.voucher_no   = self.voucher_no
                  AND pair.item_code    = self.item_code
                  AND pair.actual_qty   = -self.actual_qty
                  AND pair.warehouse   != self.warehouse
                  AND pair.is_cancelled = 0
                  {pair_date_clause}
            LEFT JOIN `tabWarehouse` pairwh ON pairwh.name = pair.warehouse
        ) ranked
        WHERE rn = 1
    """.format(self_base=self_base, pair_date_clause=pair_date_clause),
    {"gold": GOLD, "diamond": DIAMOND, "stone": STONE, "dept": department,
     "unassigned": UNASSIGNED, **date_params, **pair_date_params},
    as_dict=True)

    merged = {}
    for r in rows:
        label = ITEM_GROUP_FIELD.get(r["item_group"])
        if not label:
            continue
        key = (r["department"], r["counterparty"])
        d = merged.setdefault(key, {})
        qty = flt(r["actual_qty"])
        if qty > 0:
            field = "{}_receive".format(label)
            d[field] = d.get(field, 0) + qty
        elif qty < 0:
            field = "{}_issue".format(label)
            d[field] = d.get(field, 0) + (-qty)

    return [dict(department=dept, counterparty=cp, **vals) for (dept, cp), vals in merged.items()]


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

    # "Count" (distinct work orders) — unchanged, Stock-Entry-based.
    period_count     = _get_all_period(from_date, to_date, department)
    opening_count    = _get_all_opening(from_date, department)
    breakdown_count  = _get_counterparty_breakdown(from_date, to_date, department)

    # Gold/Diamond/Stone — ground truth from Stock Ledger Entry.
    period_material    = _get_material_period(from_date, to_date, department)
    opening_material   = _get_material_opening(from_date, department)
    breakdown_material = _get_material_counterparty_breakdown(from_date, to_date, department)

    pc = {r["department"]: r for r in period_count}
    oc = {r["department"]: r for r in opening_count}

    bc = {}
    for r in breakdown_count:
        bc.setdefault(r["department"], []).append(r)
    bm = {}
    for r in breakdown_material:
        bm.setdefault(r["department"], []).append(r)

    def counterparty_rows(dept):
        """Merge the material (SLE-based) and count (Stock-Entry-based)
        counterparty breakdowns for one department into one row per
        counterparty — material columns from bm, count columns from bc."""
        merged = {}
        for r in bm.get(dept, []):
            merged.setdefault(r["counterparty"], {}).update(
                {k: v for k, v in r.items() if k not in ("department", "counterparty")}
            )
        for r in bc.get(dept, []):
            merged.setdefault(r["counterparty"], {}).update(
                {k: v for k, v in r.items() if k.startswith("count_")}
            )
        return merged

    result = []
    for row in dept_list:
        dept = row["department"]
        if not dept:
            continue

        pd_mat = period_material.get(dept, {})
        od_mat = opening_material.get(dept, {})
        pd_cnt = pc.get(dept, {})
        od_cnt = oc.get(dept, {})

        # ── Gold/Diamond/Stone ───────────────────────────────────────────
        # Opening/Closing are the department's actual stock-on-hand from the
        # Stock Ledger (ground truth); Issue/Receive are that same ledger's
        # negative/positive legs in the period, so Closing = Opening +
        # Receive - Issue holds exactly, not approximately.
        go = flt(od_mat.get("gold_opening"))
        gi = flt(pd_mat.get("gold_issue"))
        gr = flt(pd_mat.get("gold_receive"))
        gc = go + gr - gi

        do_ = flt(od_mat.get("diamond_opening"))
        di  = flt(pd_mat.get("diamond_issue"))
        dr  = flt(pd_mat.get("diamond_receive"))
        dc  = do_ + dr - di

        so = flt(od_mat.get("stone_opening"))
        si = flt(pd_mat.get("stone_issue"))
        sr = flt(pd_mat.get("stone_receive"))
        sc = so + sr - si

        # ── Count ─────────────────────────────────────────────────────────
        co = flt(od_cnt.get("count_receive")) - flt(od_cnt.get("count_issue"))
        ci = flt(pd_cnt.get("count_issue"))
        cr = flt(pd_cnt.get("count_receive"))
        cc = co + cr - ci

        result.append(frappe._dict(
            department = dept,
            opening    = go,
            issue      = gi,
            receive    = gr,
            closing    = gc,
            gold_opening    = go,  gold_issue    = gi,  gold_receive    = gr,  gold_closing    = gc,
            diamond_opening = do_, diamond_issue = di,  diamond_receive = dr,  diamond_closing = dc,
            stone_opening   = so,  stone_issue   = si,  stone_receive   = sr,  stone_closing   = sc,
            count_opening   = co,  count_issue   = ci,  count_receive   = cr,  count_closing   = cc,
        ))

        # ── Level-2: department-to-department breakdown ────────────────────
        # One row per counterparty department this department transacted
        # with in the period. "issue" = qty sent out to that counterparty,
        # "receive" = qty taken in from that counterparty, "closing" = net
        # for that pair only — period-only, no opening carried at this level.
        for cp_name, cp in sorted(counterparty_rows(dept).items()):
            cgi = flt(cp.get("gold_issue"));    cgr = flt(cp.get("gold_receive"));    cgc = cgr - cgi
            cdi = flt(cp.get("diamond_issue")); cdr = flt(cp.get("diamond_receive")); cdc = cdr - cdi
            csi = flt(cp.get("stone_issue"));   csr = flt(cp.get("stone_receive"));   csc = csr - csi
            cci = flt(cp.get("count_issue"));   ccr = flt(cp.get("count_receive"));   ccc = ccr - cci

            result.append(frappe._dict(
                department = "    " + cp_name,
                opening    = 0,
                issue      = cgi,
                receive    = cgr,
                closing    = cgc,
                gold_opening    = 0, gold_issue    = cgi, gold_receive    = cgr, gold_closing    = cgc,
                diamond_opening = 0, diamond_issue = cdi, diamond_receive = cdr, diamond_closing = cdc,
                stone_opening   = 0, stone_issue   = csi, stone_receive   = csr, stone_closing   = csc,
                count_opening   = 0, count_issue   = cci, count_receive   = ccr, count_closing   = ccc,
            ))

    return result


def _run_direction_aggregate(date_clause, date_params, department, direction_col, label):
    """
    Aggregate the leg subquery by one side (from_dept = outgoing/Issue,
    to_dept = incoming/Receive), excluding internal same-department moves
    and legs unattributable on this side.
    """
    dept_clause = "AND {col} = %(dept)s".format(col=direction_col) if department else ""

    rows = frappe.db.sql("""
        SELECT
            {direction_col} AS department,
            SUM(CASE WHEN item_group = %(gold)s    THEN transfer_qty ELSE 0 END) AS gold_{label},
            SUM(CASE WHEN item_group = %(diamond)s THEN transfer_qty ELSE 0 END) AS diamond_{label},
            SUM(CASE WHEN item_group = %(stone)s   THEN transfer_qty ELSE 0 END) AS stone_{label},
            COUNT(DISTINCT COALESCE(mwo, se_name)) AS count_{label}
        FROM (
            {leg_sql}
        ) leg
        WHERE {direction_col} IS NOT NULL
          AND ({direction_col} != {other_col} OR {other_col} IS NULL)
          {dept_clause}
        GROUP BY {direction_col}
    """.format(
        direction_col=direction_col,
        other_col="to_dept" if direction_col == "from_dept" else "from_dept",
        label=label,
        leg_sql=_LEG_SQL.format(date_clause=date_clause),
        dept_clause=dept_clause,
    ),
    {"gold": GOLD, "diamond": DIAMOND, "stone": STONE,
     "dept": department, **date_params},
    as_dict=True)

    return rows


def _get_all_period(from_date, to_date, department):
    date_clause, date_params = _date_between(from_date, to_date, "se.posting_date")

    issue_rows   = _run_direction_aggregate(date_clause, date_params, department, "from_dept", "issue")
    receive_rows = _run_direction_aggregate(date_clause, date_params, department, "to_dept",   "receive")

    merged = {}
    for r in issue_rows:
        merged.setdefault(r["department"], {}).update({k: v for k, v in r.items() if k != "department"})
    for r in receive_rows:
        merged.setdefault(r["department"], {}).update({k: v for k, v in r.items() if k != "department"})

    return [dict(department=dept, **vals) for dept, vals in merged.items()]


def _get_all_opening(from_date, department):
    if not from_date:
        return []

    date_clause, date_params = "AND se.posting_date < %(fd)s", {"fd": from_date}

    issue_rows   = _run_direction_aggregate(date_clause, date_params, department, "from_dept", "issue")
    receive_rows = _run_direction_aggregate(date_clause, date_params, department, "to_dept",   "receive")

    merged = {}
    for r in issue_rows:
        merged.setdefault(r["department"], {}).update({k: v for k, v in r.items() if k != "department"})
    for r in receive_rows:
        merged.setdefault(r["department"], {}).update({k: v for k, v in r.items() if k != "department"})

    return [dict(department=dept, **vals) for dept, vals in merged.items()]


def _get_counterparty_breakdown(from_date, to_date, department):
    date_clause, date_params = _date_between(from_date, to_date, "se.posting_date")

    def side(direction_col, other_col, label):
        dept_clause = "AND {col} = %(dept)s".format(col=direction_col) if department else ""
        return frappe.db.sql("""
            SELECT
                {direction_col} AS department,
                COALESCE({other_col}, %(unassigned)s) AS counterparty,
                SUM(CASE WHEN item_group = %(gold)s    THEN transfer_qty ELSE 0 END) AS gold_{label},
                SUM(CASE WHEN item_group = %(diamond)s THEN transfer_qty ELSE 0 END) AS diamond_{label},
                SUM(CASE WHEN item_group = %(stone)s   THEN transfer_qty ELSE 0 END) AS stone_{label},
                COUNT(DISTINCT COALESCE(mwo, se_name)) AS count_{label}
            FROM (
                {leg_sql}
            ) leg
            WHERE {direction_col} IS NOT NULL
              AND ({direction_col} != {other_col} OR {other_col} IS NULL)
              {dept_clause}
            GROUP BY {direction_col}, counterparty
        """.format(
            direction_col=direction_col,
            other_col=other_col,
            label=label,
            leg_sql=_LEG_SQL.format(date_clause=date_clause),
            dept_clause=dept_clause,
        ),
        {"gold": GOLD, "diamond": DIAMOND, "stone": STONE,
         "dept": department, "unassigned": UNASSIGNED, **date_params},
        as_dict=True)

    issue_rows   = side("from_dept", "to_dept", "issue")
    receive_rows = side("to_dept",   "from_dept", "receive")

    merged = {}
    for r in issue_rows:
        key = (r["department"], r["counterparty"])
        merged.setdefault(key, {}).update({k: v for k, v in r.items() if k not in ("department", "counterparty")})
    for r in receive_rows:
        key = (r["department"], r["counterparty"])
        merged.setdefault(key, {}).update({k: v for k, v in r.items() if k not in ("department", "counterparty")})

    return [dict(department=dept, counterparty=cp, **vals) for (dept, cp), vals in merged.items()]


# ---------------------------------------------------------------------------
# Add these indexes once via a Frappe patch or bench execute
# ---------------------------------------------------------------------------
#
# frappe.db.add_index("Stock Entry",        ["docstatus", "posting_date"])
# frappe.db.add_index("Stock Entry Detail", ["parent", "item_group"])
# frappe.db.add_index("Stock Entry Detail", ["s_warehouse"])
# frappe.db.add_index("Stock Entry Detail", ["t_warehouse"])
# (Warehouse.department and Stock Entry.department/to_department are plain
#  columns on small tables — no dedicated index needed.)
#
# ---------------------------------------------------------------------------


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


# Date helper  (unchanged)

def _date_between(from_date, to_date, col):
    if from_date and to_date:
        return "AND {col} BETWEEN %(fd)s AND %(td)s".format(col=col), {"fd": from_date, "td": to_date}
    if from_date:
        return "AND {col} >= %(fd)s".format(col=col), {"fd": from_date}
    if to_date:
        return "AND {col} <= %(td)s".format(col=col), {"td": to_date}
    return "", {}
