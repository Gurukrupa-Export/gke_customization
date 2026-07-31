# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data, totals = get_data(filters)

    if data:
        data.append(get_total_row(totals))

    return columns, data


def get_columns():
    return [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 170},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 170},

        {"label": _("SO Date"), "fieldname": "so_date", "fieldtype": "Date", "width": 95},
        {"label": _("Sales Order ID"), "fieldname": "sales_order_id", "fieldtype": "Link", "options": "Sales Order", "width": 170},
        {"label": _("SO QTY"), "fieldname": "qty", "fieldtype": "Float", "width": 90},

        {"label": _("BATCH NO"), "fieldname": "batch_no", "fieldtype": "Data", "width": 140},

        {"label": _("DN DATE"), "fieldname": "dn_date", "fieldtype": "Date", "width": 95},
        {"label": _("DN IDs"), "fieldname": "dn_id", "fieldtype": "Data", "width": 160},
        {"label": _("DN QTY"), "fieldname": "dn_qty", "fieldtype": "Float", "width": 90},
        {"label": _("DN RATE"), "fieldname": "dn_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("DN AMOUNT"), "fieldname": "dn_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("DN Status"), "fieldname": "dn_status", "fieldtype": "Data", "width": 110},

        {"label": _("DN RETURN DATE"), "fieldname": "dn_return_date", "fieldtype": "Date", "width": 95},
        {"label": _("DN RETURN ID"), "fieldname": "dn_return_id", "fieldtype": "Data", "width": 160},
        {"label": _("DN RETURN QTY"), "fieldname": "dn_return_qty", "fieldtype": "Float", "width": 100},
        {"label": _("DN RETURN RATE"), "fieldname": "dn_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("DN RETURN AMOUNT"), "fieldname": "dn_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("SI DATE"), "fieldname": "si_date", "fieldtype": "Date", "width": 95},
        {"label": _("SI IDs"), "fieldname": "si_id", "fieldtype": "Data", "width": 160},
        {"label": _("SI QTY"), "fieldname": "si_qty", "fieldtype": "Float", "width": 90},
        {"label": _("SI RATE"), "fieldname": "si_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("SI AMOUNT"), "fieldname": "si_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("SI Status"), "fieldname": "si_status", "fieldtype": "Data", "width": 110},

        {"label": _("SI RETURN (CN) NO"), "fieldname": "si_return_id", "fieldtype": "Data", "width": 160},
        {"label": _("SI RETURN QTY"), "fieldname": "si_return_qty", "fieldtype": "Float", "width": 100},
        {"label": _("SI RETURN RATE"), "fieldname": "si_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("SI RETURN AMOUNT"), "fieldname": "si_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("Difference DN vs SI"), "fieldname": "difference_dn_vs_si", "fieldtype": "Float", "width": 140},
        {"label": _("Difference Rate DN vs SI"), "fieldname": "difference_rate_dn_vs_si", "fieldtype": "Currency", "width": 160},
        {"label": _("Difference Amount DN vs SI"), "fieldname": "difference_amount_dn_vs_si", "fieldtype": "Currency", "width": 180},
    ]


def get_data(filters):
    params = dict(filters)

    dn_conditions = [
        "dn.docstatus = 1",
        "IFNULL(dn.is_return, 0) = 0"
    ]

    if filters.get("company"):
        dn_conditions.append("dn.company = %(company)s")

    if filters.get("from_date"):
        dn_conditions.append("dn.posting_date >= %(from_date)s")

    if filters.get("to_date"):
        dn_conditions.append("dn.posting_date <= %(to_date)s")

    if filters.get("dn_id"):
        dn_conditions.append("dn.name = %(dn_id)s")

    if filters.get("batch_no"):
        dn_conditions.append("dni.batch_no = %(batch_no)s")

    if filters.get("item"):
        dn_conditions.append("dni.item_code = %(item)s")

    if filters.get("customer"):
        dn_conditions.append("dn.customer = %(customer)s")

    if filters.get("sales_order_id"):
        dn_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabDelivery Note Item` dni2
                WHERE dni2.parent = dn.name
                  AND dni2.against_sales_order = %(sales_order_id)s
            )
        """)

    if filters.get("si_id"):
        dn_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabSales Invoice Item` sii
                INNER JOIN `tabSales Invoice` si
                    ON si.name = sii.parent
                WHERE si.docstatus = 1
                  AND si.name = %(si_id)s
                  AND (
                        sii.dn_detail = dni.name
                        OR (
                            sii.so_detail = dni.so_detail
                            AND IFNULL(sii.dn_detail, '') = ''
                        )
                  )
            )
        """)

    rows = frappe.db.sql(f"""
        SELECT
            dn.posting_date AS dn_date,
            dn.name AS dn_id,
            dn.status AS dn_status,
            dn.company,
            dn.customer,

            dni.name AS dn_item_id,
            dni.idx,
            dni.item_code AS item,
            dni.batch_no,
            dni.qty AS dn_qty,
            dni.rate AS dn_rate,
            dni.amount AS dn_amount,
            dni.against_sales_order AS sales_order_id,
            dni.so_detail AS so_item_id

        FROM `tabDelivery Note` dn
        INNER JOIN `tabDelivery Note Item` dni
            ON dni.parent = dn.name

        WHERE {" AND ".join(dn_conditions)}

        ORDER BY dn.posting_date, dn.name, dni.idx
    """, params, as_dict=1)

    # ── Pre-aggregate DN and SI totals keyed by (dn_id, batch_no) ──────────────
    # CHANGED (mirrors Purchase Register): used for computing the difference
    # column batch-by-batch so it is shown only once per (dn_id, batch_no) and
    # is not inflated by multiple SI / return sub-rows.
    dn_totals_by_batch = {}
    si_totals_by_batch = {}

    for r in rows:
        key = (r.dn_id, r.batch_no or "")

        if key not in dn_totals_by_batch:
            dn_totals_by_batch[key] = {"dn_qty": 0, "dn_rate": 0, "dn_amount": 0}
        dn_totals_by_batch[key]["dn_qty"]    += r.dn_qty or 0
        # Max rate across all DN items of the same (dn_id, batch_no)
        dn_totals_by_batch[key]["dn_rate"]    = max(dn_totals_by_batch[key]["dn_rate"], r.dn_rate or 0)
        dn_totals_by_batch[key]["dn_amount"] += r.dn_amount or 0

        if key not in si_totals_by_batch:
            si_totals_by_batch[key] = {"si_qty": 0, "si_rate": 0, "si_amount": 0}
        for si in (get_si_rows(r, filters) or []):
            si_totals_by_batch[key]["si_qty"]    += si.get("qty") or 0
            si_totals_by_batch[key]["si_rate"]   += si.get("rate") or 0
            si_totals_by_batch[key]["si_amount"] += si.get("amount") or 0
    # ─────────────────────────────────────────────────────────────────────────────

    out = []

    totals = {
        "so_qty": 0,
        "dn_qty": 0,
        "dn_amount": 0,
        "dn_return_qty": 0,
        "dn_return_amount": 0,
        "si_qty": 0,
        "si_amount": 0,
        # CHANGED: si_return totals were completely missing in the old code,
        # causing the total row to always show 0 for SI Return qty/amount.
        "si_return_qty": 0,
        "si_return_amount": 0,
        # CHANGED (mirrors Purchase Register): difference_amount is accumulated
        # batch-by-batch inside the loop. The old code computed it as
        #   difference_dn_vs_si * difference_rate_dn_vs_si
        # at the very end, but difference_rate_dn_vs_si in totals is always 0,
        # so the result was always 0.
        "difference_dn_vs_si": 0,
        "difference_rate_dn_vs_si": 0,
        "difference_amount_dn_vs_si": 0,
    }

    seen_so_display        = set()
    seen_so_total          = set()
    seen_dn_total          = set()

    # CHANGED (mirrors Purchase Register seen_pr_return_display / _total):
    # split into display + total sets so a return row that appears across
    # multiple SI sub-rows is shown only once in the UI and counted only once
    # in totals. The old single set only prevented display duplicates.
    seen_dn_return_display = set()
    seen_dn_return_total   = set()

    # CHANGED (mirrors Purchase Register seen_pi_display / seen_pi_total):
    # separate display and total sets for SI rows so the same SI item row is
    # not emitted twice in the output and not double-counted in totals when it
    # appears under multiple DN items.
    seen_si_display        = set()
    seen_si_total          = set()

    # CHANGED (mirrors Purchase Register seen_pi_return_display / _total):
    # dedup sets for SI Return (Credit Note) item rows — completely absent in
    # the old code, causing CN amounts to be counted once per
    # (ret × si) cross-product iteration instead of once per CN item row.
    seen_si_return_display = set()
    seen_si_return_total   = set()

    seen_batch_diff        = set()

    for r in rows:
        so = get_so_row(r)

        so_key = (
            r.so_item_id
            or f"{r.sales_order_id or ''}::{r.item or ''}"
        )

        first_so_output = False
        if r.sales_order_id and so_key not in seen_so_display:
            seen_so_display.add(so_key)
            first_so_output = True

        if r.sales_order_id and so_key not in seen_so_total:
            seen_so_total.add(so_key)
            totals["so_qty"] += so.get("so_qty") or 0

        dn_key = r.dn_item_id
        if dn_key and dn_key not in seen_dn_total:
            seen_dn_total.add(dn_key)
            totals["dn_qty"]    += r.dn_qty or 0
            totals["dn_amount"] += r.dn_amount or 0

        si_rows = get_si_rows(r, filters)
        if not si_rows:
            si_rows = [{
                "name": "",
                "posting_date": None,
                "status": "",
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "sii_name": "",
                "match_type": "",
            }]

        # CHANGED (mirrors Purchase Register): pass filters so date range is
        # applied to return posting_date. Old code fetched all returns
        # regardless of the selected date window.
        ret_rows = get_dn_return_rows(r, filters)
        if not ret_rows:
            ret_rows = [{
                "name": "",
                "posting_date": None,
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "dni_name": "",
            }]

        first_dn_output = True

        # ── Difference computed once per (dn_id, batch_no) ───────────────────
        # CHANGED (mirrors Purchase Register): difference is calculated from
        # pre-aggregated batch totals and written to the first output row of
        # each (dn_id, batch_no). Subsequent rows for the same batch get "".
        # The diff_amount is also accumulated into totals here (batch level)
        # so the grand-total is correct even with multiple SI / return sub-rows.
        batch_diff_key = (r.dn_id, r.batch_no or "")
        if batch_diff_key not in seen_batch_diff:
            seen_batch_diff.add(batch_diff_key)
            _dn = dn_totals_by_batch.get(batch_diff_key, {})
            _si = si_totals_by_batch.get(batch_diff_key, {})

            # DN return qty for this batch (all return item rows, abs)
            _dn_return_qty = sum(
                abs(ret.get("qty") or 0)
                for ret in get_dn_return_rows(r, filters)
            )

            dn_diff_qty = round(_dn.get("dn_qty", 0) - _dn_return_qty - _si.get("si_qty", 0), 9)
            if abs(dn_diff_qty) < 1e-9:
                dn_diff_qty = 0

            dn_diff_rate   = _dn.get("dn_rate", 0) if dn_diff_qty != 0 else 0
            dn_diff_amount = round(_dn.get("dn_amount", 0) - _si.get("si_amount", 0), 9)
            if abs(dn_diff_amount) < 1e-9:
                dn_diff_amount = 0

            # Accumulate into grand totals at batch level (only once per batch)
            totals["difference_amount_dn_vs_si"] += dn_diff_amount
        else:
            dn_diff_qty = dn_diff_rate = dn_diff_amount = ""
        # ─────────────────────────────────────────────────────────────────────

        for ret in ret_rows:
            ret_key = ret.get("dni_name") or ret.get("name") or ""

            first_ret_output = False
            if ret.get("name") and ret_key not in seen_dn_return_display:
                seen_dn_return_display.add(ret_key)
                first_ret_output = True

            if ret.get("name") and ret_key not in seen_dn_return_total:
                seen_dn_return_total.add(ret_key)
                totals["dn_return_qty"]    += abs(ret.get("qty") or 0)
                totals["dn_return_amount"] += abs(ret.get("amount") or 0)

            for si in si_rows:
                si_key = si.get("sii_name") or si.get("name") or ""

                # CHANGED (mirrors Purchase Register seen_pi_display):
                # track whether this SI item row has already been emitted so
                # the same SI does not appear twice when there are multiple
                # return sub-rows beneath it.
                first_si_output = False
                if si.get("name") and si_key not in seen_si_display:
                    seen_si_display.add(si_key)
                    first_si_output = True

                if si.get("name") and si_key not in seen_si_total:
                    seen_si_total.add(si_key)
                    totals["si_qty"]    += si.get("qty") or 0
                    totals["si_amount"] += si.get("amount") or 0

                # CHANGED (mirrors Purchase Register): pass filters so that
                # date range is applied to CN posting_date.
                # Old code passed no filters at all.
                si_ret_rows = get_si_return_rows(si, filters)
                if not si_ret_rows:
                    si_ret_rows = [{
                        "name": "",
                        "posting_date": None,
                        "qty": 0,
                        "rate": 0,
                        "amount": 0,
                        "sii_return_name": "",
                    }]

                # DN Return display values — shown only on first ret sub-row
                if first_ret_output:
                    dn_return_qty    = abs(ret.get("qty") or 0)
                    dn_return_rate   = abs(ret.get("rate") or 0)
                    dn_return_amount = abs(ret.get("amount") or 0)
                    dn_return_date   = ret.get("posting_date")
                    dn_return_id     = ret.get("name") or ""
                else:
                    dn_return_qty    = 0
                    dn_return_rate   = 0
                    dn_return_amount = 0
                    dn_return_date   = None
                    dn_return_id     = ""

                # SI display values — shown only on first si_output occurrence
                # CHANGED (mirrors Purchase Register first_pi_output pattern):
                # old code had no first_si_output guard — SI data was always
                # written into every output row of the inner loop.
                if first_si_output:
                    si_qty    = si.get("qty") or 0
                    si_rate   = si.get("rate") or 0
                    si_amount = si.get("amount") or 0
                    si_date   = si.get("posting_date")
                    si_id     = si.get("name") or ""
                    si_status = si.get("status") or ""
                else:
                    si_qty    = 0
                    si_rate   = 0
                    si_amount = 0
                    si_date   = None
                    si_id     = ""
                    si_status = ""

                for si_ret in si_ret_rows:
                    # CHANGED (mirrors Purchase Register seen_pi_return_display /
                    # seen_pi_return_total): completely absent in old code.
                    # Without these sets a single CN item row was counted once
                    # per (ret × si) iteration, inflating si_return totals.
                    si_ret_key = si_ret.get("sii_return_name") or si_ret.get("name") or ""

                    first_si_ret_output = False
                    if si_ret.get("name") and si_ret_key not in seen_si_return_display:
                        seen_si_return_display.add(si_ret_key)
                        first_si_ret_output = True

                    if si_ret.get("name") and si_ret_key not in seen_si_return_total:
                        seen_si_return_total.add(si_ret_key)
                        totals["si_return_qty"]    += abs(si_ret.get("qty") or 0)
                        totals["si_return_amount"] += abs(si_ret.get("amount") or 0)

                    if first_si_ret_output:
                        si_return_id     = si_ret.get("name") or ""
                        si_return_qty    = abs(si_ret.get("qty") or 0)
                        si_return_rate   = abs(si_ret.get("rate") or 0)
                        si_return_amount = abs(si_ret.get("amount") or 0)
                    else:
                        si_return_id     = ""
                        si_return_qty    = 0
                        si_return_rate   = 0
                        si_return_amount = 0

                    # CHANGED: out.append is now correctly INSIDE the
                    # `for si_ret in si_ret_rows` loop. In the old code it sat
                    # at the `for si` level — a structural bug that emitted only
                    # one output row per SI regardless of how many CN rows
                    # existed, and always used the last si_ret value from the
                    # leaked loop variable.
                    out.append({
                        "so_date":        so.get("so_date") if first_so_output else None,
                        "sales_order_id": r.sales_order_id if first_so_output else "",
                        "item":           r.item if first_so_output else "",
                        "qty":            so.get("so_qty") if first_so_output else 0,
                        "customer":       r.customer if first_so_output else "",

                        "dn_date":   r.dn_date if first_dn_output else None,
                        "dn_id":     r.dn_id if first_dn_output else "",
                        "batch_no":  r.batch_no,
                        "dn_qty":    r.dn_qty if first_dn_output else 0,
                        "dn_rate":   r.dn_rate if first_dn_output else 0,
                        "dn_amount": r.dn_amount if first_dn_output else 0,
                        "dn_status": r.dn_status if first_dn_output else "",

                        "dn_return_date":   dn_return_date,
                        "dn_return_id":     dn_return_id,
                        "dn_return_qty":    dn_return_qty if ret.get("name") else 0,
                        "dn_return_rate":   dn_return_rate if ret.get("name") else 0,
                        "dn_return_amount": dn_return_amount if ret.get("name") else 0,

                        "si_date":   si_date,
                        "si_id":     si_id,
                        "si_qty":    si_qty if si.get("name") else 0,
                        "si_rate":   si_rate if si.get("name") else 0,
                        "si_amount": si_amount if si.get("name") else 0,
                        "si_status": si_status,

                        "si_return_id":     si_return_id,
                        "si_return_qty":    si_return_qty if si_ret.get("name") else 0,
                        "si_return_rate":   si_return_rate if si_ret.get("name") else 0,
                        "si_return_amount": si_return_amount if si_ret.get("name") else 0,

                        # Shown once per (dn_id, batch_no), 0 on all subsequent rows
                        "difference_dn_vs_si":        dn_diff_qty if dn_diff_qty != "" else 0,
                        "difference_rate_dn_vs_si":   dn_diff_rate if dn_diff_rate != "" else 0,
                        "difference_amount_dn_vs_si": (
                            round(dn_diff_qty * dn_diff_rate, 9)
                            if (dn_diff_qty != "" and dn_diff_rate != "")
                            else 0
                        ),
                    })

                    # After the very first sub-row of this batch, blank the diff
                    # and all repeating header fields so they don't appear again.
                    dn_diff_qty    = dn_diff_rate = dn_diff_amount = ""
                    first_dn_output  = False
                    first_so_output  = False
                    # SI header shown only on its first si_ret sub-row
                    si_qty    = 0
                    si_rate   = 0
                    si_amount = 0
                    si_date   = None
                    si_id     = ""
                    si_status = ""
                    # DN Return header shown only on its first si_ret sub-row
                    dn_return_qty    = 0
                    dn_return_rate   = 0
                    dn_return_amount = 0
                    dn_return_date   = None
                    dn_return_id     = ""

    # CHANGED (mirrors Purchase Register end-of-function recomputation):
    # difference_dn_vs_si qty is recomputed from deduplicated component totals.
    # difference_amount is already correctly accumulated batch-by-batch above.
    # The old code computed difference_amount as:
    #   difference_dn_vs_si * difference_rate_dn_vs_si
    # but difference_rate_dn_vs_si in totals is always 0, always giving 0.
    totals["difference_dn_vs_si"] = (
        totals["dn_qty"] - totals["dn_return_qty"] - totals["si_qty"]
    )
    # difference_amount_dn_vs_si is already accumulated above — do not overwrite.

    return out, totals


def get_so_row(r):
    if not r.sales_order_id:
        return {
            "so_date": None,
            "so_qty": 0,
        }

    so = frappe.db.sql("""
        SELECT
            so.transaction_date AS so_date,
            soi.qty AS so_qty
        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so
            ON so.name = soi.parent
        WHERE soi.name = %(so_item_id)s
        LIMIT 1
    """, {"so_item_id": r.so_item_id}, as_dict=1)

    return so[0] if so else {
        "so_date": None,
        "so_qty": 0,
    }


def get_si_rows(r, filters):
    params = {
        "so_item_id": r.so_item_id,
        "dni": r.dn_item_id,
    }

    si_filter_sql = ""
    if filters.get("si_id"):
        si_filter_sql += " AND si.name = %(si_id)s "
        params["si_id"] = filters.get("si_id")

    # CHANGED (mirrors Purchase Register get_pi_rows date filtering):
    # apply from_date / to_date to SI posting_date so the report respects
    # the selected date range for invoices, not just for delivery notes.
    if filters.get("from_date"):
        si_filter_sql += " AND si.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        si_filter_sql += " AND si.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    # First try: exact match via DN detail
    exact_rows = frappe.db.sql(f"""
        SELECT DISTINCT
            si.name,
            si.posting_date,
            si.status,
            sii.name AS sii_name,
            sii.qty,
            sii.rate,
            sii.amount,
            'DN Detail' AS match_type
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND IFNULL(si.is_return, 0) = 0
          AND sii.dn_detail = %(dni)s
          {si_filter_sql}
        ORDER BY si.posting_date, si.name, sii.idx
    """, params, as_dict=1)

    if exact_rows:
        return exact_rows

    if not r.so_item_id:
        return []

    # Fallback: match via SO detail where no DN detail is set
    return frappe.db.sql(f"""
        SELECT DISTINCT
            si.name,
            si.posting_date,
            si.status,
            sii.name AS sii_name,
            sii.qty,
            sii.rate,
            sii.amount,
            'SO Detail' AS match_type
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND IFNULL(si.is_return, 0) = 0
          AND sii.so_detail = %(so_item_id)s
          AND IFNULL(sii.dn_detail, '') = ''
          {si_filter_sql}
        ORDER BY si.posting_date, si.name, sii.idx
    """, params, as_dict=1)


def get_dn_return_rows(r, filters=None):
    """
    Fetch DN Return rows matched by batch_no.
    Matches returns where:
      - return_against = this DN
      - item_code matches
      - batch_no matches (batch-wise matching)

    CHANGED (mirrors Purchase Register get_pr_return_rows):
      - Now accepts filters and applies from_date / to_date to ret.posting_date.
        Old code fetched all return rows regardless of the report date window.
      - Uses abs() / `or 0` null-safe pattern consistently.
    """
    filters = filters or {}
    params = {
        "return_against": r.dn_id,
        "item_code":      r.item,
        "batch_no":       r.batch_no or "",
    }

    date_sql = ""
    if filters.get("from_date"):
        date_sql += " AND ret.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        date_sql += " AND ret.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    return frappe.db.sql(f"""
        SELECT
            ret.name,
            ret.posting_date,
            reti.name AS dni_name,
            reti.qty,
            reti.rate,
            reti.amount
        FROM `tabDelivery Note` ret
        INNER JOIN `tabDelivery Note Item` reti
            ON reti.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(return_against)s
          AND reti.item_code = %(item_code)s
          AND IFNULL(reti.batch_no, '') = %(batch_no)s
          {date_sql}
        ORDER BY ret.posting_date, ret.name, reti.idx
    """, params, as_dict=True)


def get_si_return_rows(si_row, filters=None):
    """
    Fetch Sales Invoice Return (Credit Note) item rows linked to a given SI.
    A SI Return in ERPNext is a Sales Invoice with is_return = 1 and
    return_against pointing to the original SI name.

    CHANGED (mirrors Purchase Register get_pi_return_rows):
      - Now accepts filters and applies from_date / to_date to CN posting_date.
        Old code passed no filters at all.
      - Returns sii_return_name (the CN item row name) so the caller can use
        it as a granular dedup key (seen_si_return_display / _total).
        Old code returned sii_name which is an SI *forward* item name and
        collided with the forward-SI dedup keys.
    """
    if not si_row.get("name"):
        return []

    filters = filters or {}
    params = {"si_name": si_row.get("name")}

    date_sql = ""
    if filters.get("from_date"):
        date_sql += " AND cn.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        date_sql += " AND cn.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    return frappe.db.sql(f"""
        SELECT
            cn.name,
            cn.posting_date,
            cni.name AS sii_return_name,
            cni.qty,
            cni.rate,
            cni.amount
        FROM `tabSales Invoice` cn
        INNER JOIN `tabSales Invoice Item` cni
            ON cni.parent = cn.name
        WHERE cn.docstatus = 1
          AND IFNULL(cn.is_return, 0) = 1
          AND cn.return_against = %(si_name)s
          {date_sql}
        ORDER BY cn.posting_date, cn.name, cni.idx
    """, params, as_dict=True)


def get_total_row(totals):
    return {
        "customer": "",
        "item": "",
        "so_date": None,
        "sales_order_id": _("Total"),
        "qty": totals["so_qty"],

        "batch_no": "",
        "dn_date": None,
        "dn_id": "",
        "dn_qty": totals["dn_qty"],
        "dn_rate": 0,
        "dn_amount": totals["dn_amount"],
        "dn_status": "",

        "dn_return_date": None,
        "dn_return_id": "",
        "dn_return_qty": totals["dn_return_qty"],
        "dn_return_rate": 0,
        "dn_return_amount": totals["dn_return_amount"],

        "si_date": None,
        "si_id": "",
        "si_qty": totals["si_qty"],
        "si_rate": 0,
        "si_amount": totals["si_amount"],
        "si_status": "",

        # CHANGED: si_return totals now come from the properly accumulated
        # seen_si_return_total dedup set. Old code hardcoded these to 0.
        "si_return_id": "",
        "si_return_qty":    totals["si_return_qty"],
        "si_return_rate":   0,
        "si_return_amount": totals["si_return_amount"],

        "difference_dn_vs_si":      totals["difference_dn_vs_si"],
        "difference_rate_dn_vs_si": 0,
        # CHANGED: accumulated batch-by-batch (not derived from rate × qty
        # at the end, which always yielded 0 because rate total is always 0).
        "difference_amount_dn_vs_si": totals["difference_amount_dn_vs_si"],
    }