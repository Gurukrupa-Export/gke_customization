# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

SE_ISSUE   = "Material Transfer (WORK ORDER)"
SE_RECEIVE = "Material Receive (WORK ORDER)"

GOLD    = "Metal - V"
DIAMOND = "Diamond - V"
STONE   = "Gemstone - V"


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    return get_columns(), get_data(filters)


def validate_filters(filters):
    if filters.get("from_date") and filters.get("to_date"):
        if getdate(filters["from_date"]) > getdate(filters["to_date"]):
            frappe.throw(_("From Date cannot be greater than To Date"))


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

    period  = _get_all_period(from_date, to_date, department)
    opening = _get_all_opening(from_date, department)

    p = {r["department"]: r for r in period}
    o = {r["department"]: r for r in opening}

    result = []
    for row in dept_list:
        dept = row["department"]
        if not dept:
            continue

        pd = p.get(dept, {})
        od = o.get(dept, {})

        # ── Gold ─────────────────────────────────────────────────────────
        go = flt(od.get("gold_receive")) - flt(od.get("gold_issue"))
        gi = flt(pd.get("gold_issue"))
        gr = flt(pd.get("gold_receive"))
        gc = go + gr - gi

        # ── Diamond ───────────────────────────────────────────────────────
        do_ = flt(od.get("diamond_receive")) - flt(od.get("diamond_issue"))
        di  = flt(pd.get("diamond_issue"))
        dr  = flt(pd.get("diamond_receive"))
        dc  = do_ + dr - di

        # ── Stone ─────────────────────────────────────────────────────────
        so = flt(od.get("stone_receive")) - flt(od.get("stone_issue"))
        si = flt(pd.get("stone_issue"))
        sr = flt(pd.get("stone_receive"))
        sc = so + sr - si

        # ── Count ─────────────────────────────────────────────────────────
        co = flt(od.get("count_open"))
        ci = flt(pd.get("count_issue"))
        cr = flt(pd.get("count_receive"))
        cc = co + ci - cr

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

    return result


# ---------------------------------------------------------------------------
# FIX 1 — Period query: pre-filter Stock Entry before joining Detail
# ---------------------------------------------------------------------------

def _get_all_period(from_date, to_date, department):
    date_clause, date_params = _date_between(from_date, to_date, "se_inner.posting_date")
    dept_clause = "AND mwo.department = %(dept)s" if department else ""

    return frappe.db.sql("""
        SELECT
            mwo.department,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(gold)s    THEN sed.transfer_qty ELSE 0 END) AS gold_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(gold)s    THEN sed.transfer_qty ELSE 0 END) AS gold_receive,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(diamond)s THEN sed.transfer_qty ELSE 0 END) AS diamond_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(diamond)s THEN sed.transfer_qty ELSE 0 END) AS diamond_receive,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(stone)s   THEN sed.transfer_qty ELSE 0 END) AS stone_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(stone)s   THEN sed.transfer_qty ELSE 0 END) AS stone_receive,
            COUNT(DISTINCT CASE WHEN se.stock_entry_type = %(iss)s THEN mwo.name END)    AS count_issue,
            COUNT(DISTINCT CASE WHEN se.stock_entry_type = %(rec)s THEN mwo.name END)    AS count_receive
        FROM `tabManufacturing Work Order` mwo
        JOIN (
            -- Pre-filter on date + docstatus BEFORE the heavy JOIN to Detail
            SELECT se_inner.name,
                   se_inner.manufacturing_work_order,
                   se_inner.stock_entry_type
            FROM   `tabStock Entry` se_inner
            WHERE  se_inner.docstatus = 1
              {date_clause}
        ) se  ON se.manufacturing_work_order = mwo.name
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE IFNULL(mwo.department, '') != ''
          {dept_clause}
        GROUP BY mwo.department
    """.format(dept_clause=dept_clause, date_clause=date_clause),
    {"iss": SE_ISSUE, "rec": SE_RECEIVE,
     "gold": GOLD, "diamond": DIAMOND, "stone": STONE,
     "dept": department, **date_params},
    as_dict=True)


# ---------------------------------------------------------------------------
# FIX 2 — Opening query: remove correlated NOT EXISTS, use LEFT JOIN instead
#          + pre-filter Stock Entry before joining Detail
# ---------------------------------------------------------------------------

def _get_all_opening(from_date, department):
    if not from_date:
        return []

    dept_clause = "AND mwo.department = %(dept)s" if department else ""

    return frappe.db.sql("""
        SELECT
            mwo.department,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(gold)s    THEN sed.transfer_qty ELSE 0 END) AS gold_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(gold)s    THEN sed.transfer_qty ELSE 0 END) AS gold_receive,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(diamond)s THEN sed.transfer_qty ELSE 0 END) AS diamond_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(diamond)s THEN sed.transfer_qty ELSE 0 END) AS diamond_receive,
            SUM(CASE WHEN se.stock_entry_type = %(iss)s AND sed.item_group = %(stone)s   THEN sed.transfer_qty ELSE 0 END) AS stone_issue,
            SUM(CASE WHEN se.stock_entry_type = %(rec)s AND sed.item_group = %(stone)s   THEN sed.transfer_qty ELSE 0 END) AS stone_receive,
            -- FIX: replaced correlated NOT EXISTS with a pre-aggregated LEFT JOIN (rb)
            COUNT(DISTINCT CASE
                WHEN se.stock_entry_type = %(iss)s
                 AND rb.manufacturing_work_order IS NULL
                THEN mwo.name END) AS count_open
        FROM `tabManufacturing Work Order` mwo
        JOIN (
            -- FIX: pre-filter Stock Entry on date + docstatus before joining Detail
            SELECT se_inner.name,
                   se_inner.manufacturing_work_order,
                   se_inner.stock_entry_type
            FROM   `tabStock Entry` se_inner
            WHERE  se_inner.docstatus = 1
              AND  se_inner.posting_date < %(fd)s
        ) se  ON se.manufacturing_work_order = mwo.name
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        -- FIX: single pre-aggregated scan replaces per-row correlated subquery
        LEFT JOIN (
            SELECT DISTINCT manufacturing_work_order
            FROM   `tabStock Entry`
            WHERE  docstatus = 1
              AND  stock_entry_type = %(rec)s
              AND  posting_date < %(fd)s
        ) rb ON rb.manufacturing_work_order = mwo.name
        WHERE IFNULL(mwo.department, '') != ''
          {dept_clause}
        GROUP BY mwo.department
    """.format(dept_clause=dept_clause),
    {"iss": SE_ISSUE, "rec": SE_RECEIVE,
     "gold": GOLD, "diamond": DIAMOND, "stone": STONE,
     "dept": department, "fd": from_date},
    as_dict=True)


# ---------------------------------------------------------------------------
# FIX 3 — Add these indexes once via a Frappe patch or bench execute
# ---------------------------------------------------------------------------
#
# frappe.db.add_index("Stock Entry",        ["manufacturing_work_order", "docstatus", "posting_date"])
# frappe.db.add_index("Stock Entry",        ["stock_entry_type", "docstatus", "posting_date"])
# frappe.db.add_index("Stock Entry Detail", ["parent", "item_group"])
# frappe.db.add_index("Manufacturing Work Order", ["department"])
#
# ---------------------------------------------------------------------------


def _get_departments(dept_filter=None):
    cond   = "WHERE IFNULL(department, '') != ''"
    params = {}
    if dept_filter:
        cond  += " AND department = %(dept_filter)s"
        params = {"dept_filter": dept_filter}

    rows = frappe.db.sql(
        "SELECT DISTINCT department FROM `tabManufacturing Work Order` {cond} ORDER BY department".format(cond=cond),
        params, as_dict=True,
    )
    if not rows:
        rows = frappe.db.sql(
            "SELECT name AS department FROM `tabDepartment` {cond} ORDER BY name".format(
                cond="WHERE name = %(dept_filter)s" if dept_filter else ""
            ),
            params, as_dict=True,
        )
    return rows


# Date helper  (unchanged)

def _date_between(from_date, to_date, col):
    if from_date and to_date:
        return "AND {col} BETWEEN %(fd)s AND %(td)s".format(col=col), {"fd": from_date, "td": to_date}
    if from_date:
        return "AND {col} >= %(fd)s".format(col=col), {"fd": from_date}
    if to_date:
        return "AND {col} <= %(td)s".format(col=col), {"td": to_date}
    return "", {}