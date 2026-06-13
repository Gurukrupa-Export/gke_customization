import frappe
from frappe import _
from collections import OrderedDict


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data, totals = get_data(filters)

    if data:
        data.append(get_total_row(totals))

    return columns, data


def get_columns():
    return [
        # ── MR ──────────────────────────────────────────────────────────────
        {"label": _("MR Date"),             "fieldname": "mr_date",             "fieldtype": "Date",     "width": 95},
        {"label": _("Material Request ID"), "fieldname": "material_request_id", "fieldtype": "Link",
         "options": "Material Request", "width": 170},
        {"label": _("Item"),                "fieldname": "item",                "fieldtype": "Link",
         "options": "Item", "width": 170},
        {"label": _("Qty"),                 "fieldname": "qty",                 "fieldtype": "Float",    "width": 90},

        # ── RFQ ─────────────────────────────────────────────────────────────
        {"label": _("RFQ Creation Date"), "fieldname": "rfq_creation_date", "fieldtype": "Date", "width": 140},
        {"label": _("RFQ ID"),            "fieldname": "rfq_id",            "fieldtype": "Data", "width": 180},
        {"label": _("RFQ Status"),        "fieldname": "rfq_status",        "fieldtype": "Data", "width": 110},

        # ── PO ──────────────────────────────────────────────────────────────
        {"label": _("PO DATE"),   "fieldname": "po_date",   "fieldtype": "Date",     "width": 95},
        {"label": _("PO IDs"),    "fieldname": "po_ids",    "fieldtype": "Data",     "width": 180},
        {"label": _("PO QTY"),    "fieldname": "po_qty",    "fieldtype": "Float",    "width": 90},
        {"label": _("PO RATE"),   "fieldname": "po_rate",   "fieldtype": "Currency", "width": 100},
        {"label": _("PO AMOUNT"), "fieldname": "po_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PO Status"), "fieldname": "po_status", "fieldtype": "Data",     "width": 110},

        # ── PR ──────────────────────────────────────────────────────────────
        {"label": _("PR DATE"),   "fieldname": "pr_date",   "fieldtype": "Date",     "width": 95},
        {"label": _("PR IDs"),    "fieldname": "pr_id",     "fieldtype": "Data",     "width": 160},
        {"label": _("BATCH NO"),  "fieldname": "batch_no",  "fieldtype": "Data",     "width": 140},
        {"label": _("PR QTY"),    "fieldname": "pr_qty",    "fieldtype": "Float",    "width": 90},
        {"label": _("PR RATE"),   "fieldname": "pr_rate",   "fieldtype": "Currency", "width": 100},
        {"label": _("PR AMOUNT"), "fieldname": "pr_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PR Status"), "fieldname": "pr_status", "fieldtype": "Data",     "width": 110},

        # ── PR Return ───────────────────────────────────────────────────────
        {"label": _("PR RETURN DATE"),   "fieldname": "pr_return_date",   "fieldtype": "Date",     "width": 110},
        {"label": _("PR RETURN ID"),     "fieldname": "pr_return_id",     "fieldtype": "Data",     "width": 160},
        {"label": _("PR RETURN QTY"),    "fieldname": "pr_return_qty",    "fieldtype": "Float",    "width": 110},
        {"label": _("PR RETURN RATE"),   "fieldname": "pr_return_rate",   "fieldtype": "Currency", "width": 110},
        {"label": _("PR RETURN AMOUNT"), "fieldname": "pr_return_amount", "fieldtype": "Currency", "width": 130},

        # ── Repack ──────────────────────────────────────────────────────────
        {"label": _("Repack Date"),   "fieldname": "repack_date",   "fieldtype": "Date",     "width": 110},
        {"label": _("Repack Batch"),  "fieldname": "repack_batch",  "fieldtype": "Data",     "width": 140},
        {"label": _("Repack ID"),     "fieldname": "repack_id",     "fieldtype": "Link",
         "options": "Stock Entry", "width": 180},
        {"label": _("Repack QTY"),    "fieldname": "repack_qty",    "fieldtype": "Float",    "width": 100},
        {"label": _("Repack Rate"),   "fieldname": "repack_rate",   "fieldtype": "Currency", "width": 100},
        {"label": _("Repack Amount"), "fieldname": "repack_amount", "fieldtype": "Currency", "width": 120},

        # ── PI ──────────────────────────────────────────────────────────────
        {"label": _("PI DATE"),     "fieldname": "pi_date",     "fieldtype": "Date",     "width": 95},
        {"label": _("PI IDs"),      "fieldname": "pi_id",       "fieldtype": "Data",     "width": 160},
        {"label": _("PI BATCH NO"), "fieldname": "pi_batch_no", "fieldtype": "Data",     "width": 140},
        {"label": _("PI QTY"),      "fieldname": "pi_qty",      "fieldtype": "Float",    "width": 90},
        {"label": _("PI RATE"),     "fieldname": "pi_rate",     "fieldtype": "Currency", "width": 100},
        {"label": _("PI AMOUNT"),   "fieldname": "pi_amount",   "fieldtype": "Currency", "width": 110},
        {"label": _("PI Status"),   "fieldname": "pi_status",   "fieldtype": "Data",     "width": 110},

        # ── PI Return ───────────────────────────────────────────────────────
        {"label": _("PI RETURN (DN) NO"), "fieldname": "pi_return_id",     "fieldtype": "Data",     "width": 160},
        {"label": _("PI RETURN QTY"),     "fieldname": "pi_return_qty",    "fieldtype": "Float",    "width": 100},
        {"label": _("PI RETURN RATE"),    "fieldname": "pi_return_rate",   "fieldtype": "Currency", "width": 110},
        {"label": _("PI RETURN AMOUNT"),  "fieldname": "pi_return_amount", "fieldtype": "Currency", "width": 130},

        # ── Difference ──────────────────────────────────────────────────────
        {"label": _("Difference Qty"),    "fieldname": "difference_qty",    "fieldtype": "Float",    "width": 130},
        {"label": _("Difference Rate"),   "fieldname": "difference_rate",   "fieldtype": "Currency", "width": 140},
        {"label": _("Difference Amount"), "fieldname": "difference_amount", "fieldtype": "Currency", "width": 160},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# main data builder
# ─────────────────────────────────────────────────────────────────────────────

def get_data(filters):
    params = dict(filters)

    pr_conditions = [
        "pr.docstatus = 1",
        "IFNULL(pr.is_return, 0) = 0",
    ]

    if filters.get("company"):
        pr_conditions.append("pr.company = %(company)s")
    if filters.get("from_date"):
        pr_conditions.append("pr.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        pr_conditions.append("pr.posting_date <= %(to_date)s")
    if filters.get("pr_id"):
        pr_conditions.append("pr.name = %(pr_id)s")
    if filters.get("batch_no"):
        pr_conditions.append("pri.batch_no = %(batch_no)s")
    if filters.get("item"):
        pr_conditions.append("pri.item_code = %(item)s")
    if filters.get("po_id"):
        pr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Receipt Item` pri2
                LEFT JOIN `tabPurchase Order Item` poi_filter
                    ON poi_filter.name = pri2.purchase_order_item
                LEFT JOIN `tabPurchase Invoice Item` pii_filter
                    ON pii_filter.pr_detail = pri2.name
                WHERE pri2.parent = pr.name
                  AND (
                        poi_filter.parent = %(po_id)s
                        OR pii_filter.purchase_order = %(po_id)s
                  )
            )
        """)
    if filters.get("material_request_id"):
        pr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Receipt Item` pri2
                LEFT JOIN `tabPurchase Order Item` poi_mr
                    ON poi_mr.name = pri2.purchase_order_item
                WHERE pri2.parent = pr.name
                  AND poi_mr.material_request = %(material_request_id)s
            )
        """)
    if filters.get("pi_id"):
        pr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Invoice Item` pii
                INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                WHERE pi.docstatus = 1
                  AND pi.name = %(pi_id)s
                  AND (
                        pii.pr_detail = pri.name
                        OR (
                            pii.po_detail = pri.purchase_order_item
                            AND IFNULL(pii.pr_detail, '') = ''
                        )
                  )
            )
        """)

    rows = frappe.db.sql(f"""
        SELECT
            pr.posting_date AS pr_date,
            pr.name         AS pr_id,
            pr.status       AS pr_status,
            pr.company,
            pri.name        AS pr_item_id,
            pri.idx,
            pri.item_code   AS item,
            pri.batch_no,
            pri.qty         AS pr_qty,
            pri.rate        AS pr_rate,
            pri.base_amount AS pr_amount,
            pri.purchase_order_item
        FROM `tabPurchase Receipt` pr
        INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE {" AND ".join(pr_conditions)}
        ORDER BY pr.posting_date, pr.name, pri.idx
    """, params, as_dict=1)

    # ── accumulators ──────────────────────────────────────────────────────────
    out    = []
    totals = {
        "mr_qty": 0, "po_qty": 0, "po_amount": 0,
        "pr_qty": 0, "pr_amount": 0,
        "pr_return_qty": 0, "pr_return_amount": 0,
        "repack_qty": 0,    "repack_amount": 0,
        "pi_qty": 0,        "pi_amount": 0,
        "pi_return_qty": 0, "pi_return_amount": 0,
        "difference_qty": 0, "difference_rate": 0, "difference_amount": 0,
    }

    seen_mr_display        = set()
    seen_mr_total          = set()
    seen_po_display        = set()
    seen_po_total          = set()
    seen_pr_total          = set()
    seen_pr_return_display = set()
    seen_pr_return_total   = set()
    seen_repack_display    = set()
    seen_repack_total      = set()
    seen_pi_display        = set()
    seen_pi_total          = set()
    seen_pi_return_display = set()
    seen_pi_return_total   = set()
    seen_pii_via_pr        = set()
    seen_pr_item_diff      = set()

    # sentinel for an empty pi_group used when padding the zip
    _empty_pi_group_sentinel = {
        "name": "", "posting_date": None, "status": "", "batches": []
    }

    for r in rows:
        mr  = get_mr_row(r)
        po  = get_po_row(r)
        rfq = get_rfq_row(r)

        # ── MR dedup ──────────────────────────────────────────────────────────
        mr_key = (
            mr.get("material_request_item")
            or f"{mr.get('material_request_id') or ''}::{r.item or ''}"
        )
        first_mr_output = False
        if mr.get("material_request_id") and mr_key not in seen_mr_display:
            seen_mr_display.add(mr_key)
            first_mr_output = True
        if mr.get("material_request_id") and mr_key not in seen_mr_total:
            seen_mr_total.add(mr_key)
            totals["mr_qty"] += mr.get("mr_qty") or 0

        # ── PR totals (once per pr_item_id) ───────────────────────────────────
        if r.pr_item_id and r.pr_item_id not in seen_pr_total:
            seen_pr_total.add(r.pr_item_id)
            totals["pr_qty"]    += r.pr_qty or 0
            totals["pr_amount"] += r.pr_amount or 0

        # ── PO totals ─────────────────────────────────────────────────────────
        po_key = r.purchase_order_item or po.get("po_ids")
        if po_key and po_key not in seen_po_total:
            seen_po_total.add(po_key)
            totals["po_qty"]    += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        # ── fetch all child rows for this PR item ─────────────────────────────
        ret_rows    = get_pr_return_rows(r, filters) or [_empty_pr_return()]
        repack_rows = get_repack_rows(r, filters)    or [_empty_repack()]

        pi_rows_flat = get_pi_rows(r, filters) or [_empty_pi()]
        grouped_pi   = group_pi_rows_by_pi(pi_rows_flat)

        # ── pre-sum totals needed for diff (all child rows of this pr_item) ───
        total_pr_return_qty    = sum(abs(x.get("qty")    or 0) for x in ret_rows    if x.get("name"))
        total_pr_return_amount = sum(abs(x.get("amount") or 0) for x in ret_rows    if x.get("name"))
        total_repack_amount = 0
        for repack in repack_rows:
            if repack.get("repack_id"):
                repack_qty = repack.get("repack_qty") or 0
                pi_rate = 0
                if grouped_pi:
                    first_batch = grouped_pi[0]["batches"][0] if grouped_pi[0]["batches"] else {}
                    pi_rate = first_batch.get("rate") or 0
                repack_rate = (r.pr_rate or 0) - pi_rate
                total_repack_amount += repack_qty * repack_rate

        total_pi_qty    = 0
        total_pi_amount = 0
        total_pi_return_qty    = 0
        total_pi_return_amount = 0
        for grp in grouped_pi:
            for b in grp["batches"]:
                if b.get("pii_name"):
                    total_pi_qty    += b.get("qty")    or 0
                    total_pi_amount += b.get("amount") or 0
                    for pi_ret in get_pi_return_rows(
                        grp["name"], b["pii_name"], filters,
                        b.get("pi_batch_no") or None
                    ):
                        total_pi_return_qty    += abs(pi_ret.get("qty")    or 0)
                        total_pi_return_amount += abs(pi_ret.get("amount") or 0)

        # ── difference calculations (shown only on first output row of this pr_item) ──
        if r.pr_item_id not in seen_pr_item_diff:
            seen_pr_item_diff.add(r.pr_item_id)

            diff_qty = round(
                (r.pr_qty or 0)
                - total_pr_return_qty
                - total_pi_qty
                + total_pi_return_qty,
                9
            )
            if abs(diff_qty) < 1e-9:
                diff_qty = 0

            diff_rate = (r.pr_rate or 0) if diff_qty != 0 else 0

            diff_amount = round(
                (r.pr_amount or 0)
                - total_pr_return_amount
                - total_repack_amount
                - total_pi_amount
                + total_pi_return_amount,
                9
            )
            if abs(diff_amount) < 1e-9:
                diff_amount = 0

            totals["difference_qty"]    += diff_qty
            totals["difference_rate"]   += diff_rate
            totals["difference_amount"] += diff_amount
        else:
            diff_qty = diff_rate = diff_amount = ""

        # ── PO display dedup ──────────────────────────────────────────────────
        first_po_output = bool(po_key and po_key not in seen_po_display)
        if first_po_output:
            seen_po_display.add(po_key)

        first_pr_output = True

        # ── Flatten PI into (pi_group, batch, pi_ret) tuples ─────────────────
        # This collapses what was previously four nested loops into a single
        # indexed sequence so we can zip it with ret_rows and repack_rows,
        # producing exactly max(len(ret), len(repack), len(pi_flat)) rows
        # instead of len(ret) × len(repack) × len(pi_flat) rows.
        pi_flat = []
        for pi_group in grouped_pi:
            batches = pi_group["batches"] or [_empty_pi_batch()]
            for batch in batches:
                pii_name_inner = batch.get("pii_name") or ""
                pi_rets = []
                if pi_group["name"]:
                    pi_rets = get_pi_return_rows(
                        pi_group["name"],
                        pii_name_inner or None,
                        filters,
                        batch.get("pi_batch_no") or None,
                    )
                if not pi_rets:
                    pi_rets = [_empty_pi_return()]
                for pi_ret in pi_rets:
                    pi_flat.append((pi_group, batch, pi_ret))

        if not pi_flat:
            pi_flat = [(_empty_pi_group_sentinel, _empty_pi_batch(), _empty_pi_return())]

        n_rows = max(len(ret_rows), len(repack_rows), len(pi_flat))

        for row_idx in range(n_rows):
            ret    = ret_rows[row_idx]    if row_idx < len(ret_rows)    else _empty_pr_return()
            repack = repack_rows[row_idx] if row_idx < len(repack_rows) else _empty_repack()
            pi_group_z, batch_z, pi_ret_z = (
                pi_flat[row_idx] if row_idx < len(pi_flat)
                else (_empty_pi_group_sentinel, _empty_pi_batch(), _empty_pi_return())
            )

            pi_name_z  = pi_group_z.get("name") or ""
            pii_name_z = batch_z.get("pii_name") or ""
            ret_key    = ret.get("pri_name") or ret.get("name") or ""
            rp_key     = repack.get("repack_id") or ""
            pi_ret_key = pi_ret_z.get("pii_return_name") or pi_ret_z.get("name") or ""

            # ── PR Return display / totals ────────────────────────────────────
            first_ret_output = False
            if ret.get("name") and ret_key not in seen_pr_return_display:
                seen_pr_return_display.add(ret_key)
                first_ret_output = True
            if ret.get("name") and ret_key not in seen_pr_return_total:
                seen_pr_return_total.add(ret_key)
                totals["pr_return_qty"]    += abs(ret.get("qty") or 0)
                totals["pr_return_amount"] += abs(ret.get("amount") or 0)

            # ── Repack display / totals ───────────────────────────────────────
            first_rp_output = False
            if rp_key and rp_key not in seen_repack_display:
                seen_repack_display.add(rp_key)
                first_rp_output = True
            if rp_key and rp_key not in seen_repack_total:
                seen_repack_total.add(rp_key)
                totals["repack_qty"]    += repack.get("repack_qty") or 0
                totals["repack_amount"] += repack.get("repack_amount") or 0

            # ── PI display / totals ───────────────────────────────────────────
            first_pi_output = False
            if pi_name_z and pi_name_z not in seen_pi_display:
                seen_pi_display.add(pi_name_z)
                # mark every batch of this PI as reached via a PR
                for _b in pi_group_z.get("batches") or []:
                    if _b.get("pii_name"):
                        seen_pii_via_pr.add(_b["pii_name"])
                first_pi_output = True
            if pii_name_z and pii_name_z not in seen_pi_total:
                seen_pi_total.add(pii_name_z)
                totals["pi_qty"]    += batch_z.get("qty") or 0
                totals["pi_amount"] += batch_z.get("amount") or 0

            # ── PI Return display / totals ────────────────────────────────────
            first_pi_ret_output = False
            if pi_ret_z.get("name") and pi_ret_key not in seen_pi_return_display:
                seen_pi_return_display.add(pi_ret_key)
                first_pi_ret_output = True
            if pi_ret_z.get("name") and pi_ret_key not in seen_pi_return_total:
                seen_pi_return_total.add(pi_ret_key)
                totals["pi_return_qty"]    += abs(pi_ret_z.get("qty") or 0)
                totals["pi_return_amount"] += abs(pi_ret_z.get("amount") or 0)

            # ── Build column values ───────────────────────────────────────────
            if first_ret_output:
                pr_return_date_out   = ret.get("posting_date")
                pr_return_id_out     = ret.get("name") or ""
                pr_return_qty_out    = abs(ret.get("qty") or 0)
                pr_return_rate_out   = abs(ret.get("rate") or 0)
                pr_return_amount_out = abs(ret.get("amount") or 0)
            else:
                pr_return_date_out   = None
                pr_return_id_out     = ""
                pr_return_qty_out    = pr_return_rate_out = pr_return_amount_out = 0

            if first_rp_output:
                repack_date_out   = repack.get("posting_date")
                repack_id_out     = repack.get("repack_id") or ""
                repack_batch_out  = repack.get("repack_batch") or ""
                repack_qty_out    = repack.get("repack_qty") or 0
                repack_rate_out   = (r.pr_rate or 0) - (batch_z.get("rate") or 0)
                repack_amount_out = repack_qty_out * repack_rate_out
            else:
                repack_date_out   = None
                repack_id_out     = repack_batch_out = ""
                repack_qty_out    = repack_rate_out = repack_amount_out = 0

            if first_pi_output:
                pi_date_out   = pi_group_z.get("posting_date")
                pi_id_out     = pi_name_z
                pi_status_out = pi_group_z.get("status") or ""
            else:
                pi_date_out = None
                pi_id_out   = pi_status_out = ""

            pi_batch_no_out = batch_z.get("pi_batch_no") or ""
            pi_qty_out      = batch_z.get("qty") or 0
            pi_rate_out     = batch_z.get("rate") or 0
            pi_amount_out   = batch_z.get("amount") or 0

            if first_pi_ret_output:
                pi_return_id_out     = pi_ret_z.get("name") or ""
                pi_return_qty_out    = abs(pi_ret_z.get("qty") or 0)
                pi_return_rate_out   = abs(pi_ret_z.get("rate") or 0)
                pi_return_amount_out = abs(pi_ret_z.get("amount") or 0)
            else:
                pi_return_id_out = ""
                pi_return_qty_out = pi_return_rate_out = pi_return_amount_out = 0

            out.append({
                # MR
                "mr_date":             mr.get("mr_date") if first_mr_output else None,
                "material_request_id": mr.get("material_request_id") if first_mr_output else "",
                "item":                r.item if first_mr_output else "",
                "qty":                 mr.get("mr_qty") if first_mr_output else 0,
                # RFQ
                "rfq_creation_date": rfq.get("rfq_creation_date") if first_mr_output else None,
                "rfq_id":            rfq.get("rfq_id") if first_mr_output else "",
                "rfq_status":        rfq.get("rfq_status") if first_mr_output else "",
                # PO
                "po_date":   po.get("po_date") if first_po_output else None,
                "po_ids":    po.get("po_ids") if first_po_output else "",
                "po_qty":    po.get("po_qty") if first_po_output else 0,
                "po_rate":   po.get("po_rate") if first_po_output else 0,
                "po_amount": po.get("po_amount") if first_po_output else 0,
                "po_status": po.get("po_status") if first_po_output else "",
                # PR
                "pr_date":   r.pr_date if first_pr_output else None,
                "pr_id":     r.pr_id,
                "batch_no":  r.batch_no,
                "pr_qty":    r.pr_qty if first_pr_output else 0,
                "pr_rate":   r.pr_rate if first_pr_output else 0,
                "pr_amount": r.pr_amount if first_pr_output else 0,
                "pr_status": r.pr_status if first_pr_output else "",
                # PR Return
                "pr_return_date":   pr_return_date_out,
                "pr_return_id":     pr_return_id_out,
                "pr_return_qty":    pr_return_qty_out,
                "pr_return_rate":   pr_return_rate_out,
                "pr_return_amount": pr_return_amount_out,
                # Repack
                "repack_date":   repack_date_out,
                "repack_id":     repack_id_out,
                "repack_batch":  repack_batch_out,
                "repack_qty":    repack_qty_out,
                "repack_rate":   repack_rate_out,
                "repack_amount": repack_amount_out,
                # PI
                "pi_date":     pi_date_out,
                "pi_id":       pi_id_out,
                "pi_batch_no": pi_batch_no_out,
                "pi_qty":      pi_qty_out,
                "pi_rate":     pi_rate_out,
                "pi_amount":   pi_amount_out,
                "pi_status":   pi_status_out,
                # PI Return
                "pi_return_id":     pi_return_id_out,
                "pi_return_qty":    pi_return_qty_out,
                "pi_return_rate":   pi_return_rate_out,
                "pi_return_amount": pi_return_amount_out,
                # Difference (only on the first row of this pr_item)
                "difference_qty":    diff_qty,
                "difference_rate":   diff_rate,
                "difference_amount": diff_amount,
            })

            # clear one-time flags after the first row is written
            diff_qty        = diff_rate = diff_amount = ""
            first_pr_output = False
            first_mr_output = False
            first_po_output = False

    # ── standalone PI rows (no PR) ────────────────────────────────────────────
    if not filters.get("pr_id") and not filters.get("batch_no"):
        standalone_rows = _get_standalone_pi_rows(filters)
        standalone_rows = [r for r in standalone_rows if r.pii_name not in seen_pii_via_pr]
        _append_standalone_pi_rows(
            standalone_rows, filters, out, totals,
            seen_mr_display, seen_mr_total,
            seen_po_display, seen_po_total,
            seen_pi_return_display, seen_pi_return_total,
        )

    return out, totals


# ─────────────────────────────────────────────────────────────────────────────
# empty-row sentinels
# ─────────────────────────────────────────────────────────────────────────────

def _empty_pr_return():
    return {"name": "", "posting_date": None, "qty": 0, "rate": 0, "amount": 0, "pri_name": ""}

def _empty_repack():
    return {"repack_id": "", "posting_date": None, "repack_batch": "",
            "repack_qty": 0, "repack_rate": 0, "repack_amount": 0}

def _empty_pi():
    return {"name": "", "posting_date": None, "status": "",
            "qty": 0, "rate": 0, "amount": 0, "pii_name": "", "pi_batch_no": "", "match_type": ""}

def _empty_pi_batch():
    return {"pii_name": "", "pi_batch_no": "", "qty": 0, "rate": 0, "amount": 0}

def _empty_pi_return():
    return {"name": "", "posting_date": None, "qty": 0, "rate": 0, "amount": 0, "pii_return_name": ""}


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def group_pi_rows_by_pi(pi_rows):
    grouped = OrderedDict()
    for row in pi_rows:
        pi_name = row.get("name") or ""
        if pi_name not in grouped:
            grouped[pi_name] = {
                "name":         pi_name,
                "posting_date": row.get("posting_date"),
                "status":       row.get("status") or "",
                "batches":      []
            }
        grouped[pi_name]["batches"].append({
            "pii_name":    row.get("pii_name") or "",
            "pi_batch_no": row.get("pi_batch_no") or "",
            "qty":         row.get("qty") or 0,
            "rate":        row.get("rate") or 0,
            "amount":      row.get("amount") or 0,
        })
    return list(grouped.values())


def get_pi_rows(r, filters):
    params = {"poi": r.purchase_order_item, "pri": r.pr_item_id}
    pi_filter_sql = ""
    if filters.get("pi_id"):
        pi_filter_sql += " AND pi.name = %(pi_id)s "
        params["pi_id"] = filters.get("pi_id")
    if filters.get("from_date"):
        pi_filter_sql += " AND pi.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        pi_filter_sql += " AND pi.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    exact_rows = frappe.db.sql(f"""
        SELECT
            pi.name, pi.posting_date, pi.status,
            pii.name                 AS pii_name,
            IFNULL(pii.batch_no, '') AS pi_batch_no,
            pii.qty, pii.rate,
            pii.base_amount          AS amount,
            'PR Detail'              AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND IFNULL(pi.is_return, 0) = 0
          AND pii.pr_detail = %(pri)s
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)

    if exact_rows:
        return exact_rows

    if not r.purchase_order_item:
        return []

    return frappe.db.sql(f"""
        SELECT
            pi.name, pi.posting_date, pi.status,
            pii.name                 AS pii_name,
            IFNULL(pii.batch_no, '') AS pi_batch_no,
            pii.qty, pii.rate,
            pii.base_amount          AS amount,
            'PO Detail'              AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND IFNULL(pi.is_return, 0) = 0
          AND pii.po_detail = %(poi)s
          AND IFNULL(pii.pr_detail, '') = ''
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)


def get_pr_return_rows(r, filters=None):
    filters = filters or {}
    params  = {
        "return_against": r.pr_id,
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
            ret.name, ret.posting_date,
            reti.name AS pri_name,
            reti.qty, reti.rate, reti.amount
        FROM `tabPurchase Receipt` ret
        INNER JOIN `tabPurchase Receipt Item` reti ON reti.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(return_against)s
          AND reti.item_code = %(item_code)s
          AND IFNULL(reti.batch_no, '') = %(batch_no)s
          {date_sql}
        ORDER BY ret.posting_date, ret.name, reti.idx
    """, params, as_dict=True)


def get_repack_rows(r, filters=None):
    """
    Stock Entry (type=Repack) whose source item+batch matches this PR item.
    Returns the finished-item (output) side: new batch, qty, valuation_rate, amount.
    """
    filters = filters or {}
    if not r.batch_no:
        return []

    params   = {"item_code": r.item, "batch_no": r.batch_no}
    date_sql = ""
    if filters.get("from_date"):
        date_sql += " AND se.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        date_sql += " AND se.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    return frappe.db.sql(f"""
        SELECT
            se.name                AS repack_id,
            se.posting_date,
            sed_out.batch_no       AS repack_batch,
            sed_out.qty            AS repack_qty,
            sed_out.amount         AS repack_amount
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` sed_in
            ON  sed_in.parent    = se.name
            AND sed_in.item_code = %(item_code)s
            AND IFNULL(sed_in.batch_no, '') = %(batch_no)s
            AND IFNULL(sed_in.t_warehouse, '') = ''
        INNER JOIN `tabStock Entry Detail` sed_out
            ON  sed_out.parent = se.name
            AND IFNULL(sed_out.is_finished_item, 0) = 1
        WHERE se.docstatus = 1
          AND se.stock_entry_type = 'Repack'
          {date_sql}
        ORDER BY se.posting_date, se.name, sed_out.idx
    """, params, as_dict=True)


def get_pi_return_rows(pi_name, pii_name=None, filters=None, pi_batch_no=None):
    if not pi_name:
        return []
    filters   = filters or {}
    params    = {"pi_name": pi_name}
    date_sql  = ""
    batch_sql = ""
    if filters.get("from_date"):
        date_sql += " AND ret.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        date_sql += " AND ret.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")
    if pi_batch_no is not None:
        batch_sql = " AND IFNULL(ret_i.batch_no, '') = %(pi_batch_no)s "
        params["pi_batch_no"] = pi_batch_no

    return frappe.db.sql(f"""
        SELECT
            ret.name, ret.posting_date,
            ret_i.name                 AS pii_return_name,
            IFNULL(ret_i.batch_no, '') AS pi_batch_no,
            ret_i.qty, ret_i.rate,
            ret_i.base_amount          AS amount
        FROM `tabPurchase Invoice` ret
        INNER JOIN `tabPurchase Invoice Item` ret_i ON ret_i.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(pi_name)s
          {date_sql}
          {batch_sql}
        ORDER BY ret.posting_date, ret.name, ret_i.idx
    """, params, as_dict=True)


def get_mr_row(r):
    if not r.purchase_order_item:
        return {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}
    mr = frappe.db.sql("""
        SELECT mr.transaction_date AS mr_date, mr.name AS material_request_id,
               mri.name AS material_request_item, mri.qty AS mr_qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request`      mr  ON mr.name  = poi.material_request
        LEFT JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
        WHERE poi.name = %(poi)s LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)
    return mr[0] if mr else {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}


def get_po_row(r):
    if not r.purchase_order_item:
        return {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}
    po = frappe.db.sql("""
        SELECT po.transaction_date AS po_date, po.name AS po_ids,
               poi.qty AS po_qty, poi.rate AS po_rate, poi.amount AS po_amount, po.status AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.name = %(poi)s LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)
    return po[0] if po else {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}


def get_rfq_row(r):
    return {"rfq_creation_date": None, "rfq_id": "", "rfq_status": ""}


# ─────────────────────────────────────────────────────────────────────────────
# standalone PI rows (no PR)
# ─────────────────────────────────────────────────────────────────────────────

def _get_standalone_pi_rows(filters):
    conditions = [
        "pi.docstatus = 1",
        "IFNULL(pi.is_return, 0) = 0",
        "IFNULL(pii.pr_detail, '') = ''",
    ]
    params = {}

    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
        params["company"] = filters["company"]
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    if filters.get("pi_id"):
        conditions.append("pi.name = %(pi_id)s")
        params["pi_id"] = filters["pi_id"]
    if filters.get("item"):
        conditions.append("pii.item_code = %(item)s")
        params["item"] = filters["item"]
    if filters.get("po_id"):
        conditions.append(
            "(pii.purchase_order = %(po_id)s OR pii.po_detail IN "
            "(SELECT name FROM `tabPurchase Order Item` WHERE parent = %(po_id)s))"
        )
        params["po_id"] = filters["po_id"]
    if filters.get("material_request_id"):
        conditions.append("""
            EXISTS (
                SELECT 1 FROM `tabPurchase Order Item` poi_mr2
                WHERE poi_mr2.name = pii.po_detail
                  AND poi_mr2.material_request = %(material_request_id)s
            )
        """)
        params["material_request_id"] = filters["material_request_id"]

    return frappe.db.sql(f"""
        SELECT
            pi.name AS pi_name, pi.posting_date AS pi_date, pi.status AS pi_status, pi.company,
            pii.name AS pii_name, pii.idx, pii.item_code AS item,
            IFNULL(pii.batch_no, '') AS pi_batch_no,
            pii.qty AS pi_qty, pii.rate AS pi_rate, pii.base_amount AS pi_amount,
            pii.po_detail AS purchase_order_item
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE {" AND ".join(conditions)}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)


def _append_standalone_pi_rows(
    standalone_rows, filters, out, totals,
    seen_mr_display, seen_mr_total,
    seen_po_display, seen_po_total,
    seen_pi_return_display, seen_pi_return_total,
):
    if not standalone_rows:
        return

    po_totals_by_poi = {}
    pi_totals_by_poi = {}

    for r in standalone_rows:
        poi = r.purchase_order_item
        if poi not in po_totals_by_poi:
            po_totals_by_poi[poi] = _get_po_row_by_poi(poi)
        if poi not in pi_totals_by_poi:
            pi_totals_by_poi[poi] = {"pi_qty": 0, "pi_amount": 0}
        pi_totals_by_poi[poi]["pi_qty"]    += r.pi_qty or 0
        pi_totals_by_poi[poi]["pi_amount"] += r.pi_amount or 0

    seen_poi_diff      = set()
    seen_pi_display_sa = set()
    seen_pi_total_sa   = set()

    grouped_sa = OrderedDict()
    for r in standalone_rows:
        key = r.pi_name
        if key not in grouped_sa:
            grouped_sa[key] = {
                "pi_name": r.pi_name, "pi_date": r.pi_date,
                "pi_status": r.pi_status, "item": r.item,
                "company": r.company, "purchase_order_item": r.purchase_order_item,
                "batches": []
            }
        grouped_sa[key]["batches"].append({
            "pii_name": r.pii_name, "pi_batch_no": r.pi_batch_no,
            "pi_qty": r.pi_qty, "pi_rate": r.pi_rate, "pi_amount": r.pi_amount,
        })

    for pi_name, pi_group in grouped_sa.items():
        poi = pi_group["purchase_order_item"]
        po  = po_totals_by_poi.get(poi, {})
        mr  = _get_mr_row_by_poi(poi)

        mr_key = (
            mr.get("material_request_item")
            or f"{mr.get('material_request_id') or ''}::{pi_group['item'] or ''}"
        )
        po_key = poi or po.get("po_ids", "")

        first_mr_output = False
        if mr.get("material_request_id") and mr_key not in seen_mr_display:
            seen_mr_display.add(mr_key)
            first_mr_output = True
        if mr.get("material_request_id") and mr_key not in seen_mr_total:
            seen_mr_total.add(mr_key)
            totals["mr_qty"] += mr.get("mr_qty") or 0

        first_po_output = bool(po_key and po_key not in seen_po_display)
        if first_po_output:
            seen_po_display.add(po_key)
        if po_key and po_key not in seen_po_total:
            seen_po_total.add(po_key)
            totals["po_qty"]    += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        # ── standalone diff ───────────────────────────────────────────────────
        if poi not in seen_poi_diff:
            seen_poi_diff.add(poi)
            _po = po_totals_by_poi.get(poi, {})
            _pi = pi_totals_by_poi.get(poi, {})

            diff_qty = round((_po.get("po_qty", 0) - _pi.get("pi_qty", 0)), 9)
            if abs(diff_qty) < 1e-9:
                diff_qty = 0

            diff_amount = round((_po.get("po_amount", 0) - _pi.get("pi_amount", 0)), 9)
            if abs(diff_amount) < 1e-9:
                diff_amount = 0

            if diff_qty != 0:
                _pi_qty      = _pi.get("pi_qty", 0)
                _pi_eff_rate = (_pi.get("pi_amount", 0) / _pi_qty) if _pi_qty else 0
                diff_rate    = round((_po.get("po_rate", 0) - _pi_eff_rate), 9)
                if abs(diff_rate) < 1e-9:
                    diff_rate = 0
            else:
                diff_rate = 0

            totals["difference_qty"]    += diff_qty
            totals["difference_rate"]   += diff_rate
            totals["difference_amount"] += diff_amount
        else:
            diff_qty = diff_rate = diff_amount = ""

        pi_key = pi_name
        first_pi_output = bool(pi_key and pi_key not in seen_pi_display_sa)
        if first_pi_output:
            seen_pi_display_sa.add(pi_key)
        if pi_key and pi_key not in seen_pi_total_sa:
            seen_pi_total_sa.add(pi_key)
            for b in pi_group["batches"]:
                totals["pi_qty"]    += b["pi_qty"] or 0
                totals["pi_amount"] += b["pi_amount"] or 0

        for batch_idx, batch in enumerate(pi_group["batches"]):
            pii_name = batch["pii_name"]

            pi_return_rows = get_pi_return_rows(
                pi_name, pii_name, filters, batch.get("pi_batch_no") or None
            ) or [_empty_pi_return()]

            if first_pi_output and batch_idx == 0:
                pi_date_out   = pi_group["pi_date"]
                pi_id_out     = pi_name
                pi_status_out = pi_group["pi_status"]
            else:
                pi_date_out = None
                pi_id_out   = ""
                pi_status_out = ""

            pi_batch_no_out = batch["pi_batch_no"]
            pi_qty_out      = batch["pi_qty"] or 0
            pi_rate_out     = batch["pi_rate"] or 0
            pi_amount_out   = batch["pi_amount"] or 0

            for pi_ret in pi_return_rows:
                pi_ret_key = pi_ret.get("pii_return_name") or pi_ret.get("name")

                first_pi_ret_output = False
                if pi_ret.get("name") and pi_ret_key not in seen_pi_return_display:
                    seen_pi_return_display.add(pi_ret_key)
                    first_pi_ret_output = True
                if pi_ret.get("name") and pi_ret_key not in seen_pi_return_total:
                    seen_pi_return_total.add(pi_ret_key)
                    totals["pi_return_qty"]    += abs(pi_ret.get("qty") or 0)
                    totals["pi_return_amount"] += abs(pi_ret.get("amount") or 0)

                if first_pi_ret_output:
                    pi_return_id_out     = pi_ret.get("name") or ""
                    pi_return_qty_out    = abs(pi_ret.get("qty") or 0)
                    pi_return_rate_out   = abs(pi_ret.get("rate") or 0)
                    pi_return_amount_out = abs(pi_ret.get("amount") or 0)
                else:
                    pi_return_id_out = ""
                    pi_return_qty_out = pi_return_rate_out = pi_return_amount_out = 0

                out.append({
                    # MR
                    "mr_date":             mr.get("mr_date") if first_mr_output else None,
                    "material_request_id": mr.get("material_request_id") if first_mr_output else "",
                    "item":                pi_group["item"] if first_mr_output else "",
                    "qty":                 mr.get("mr_qty") if first_mr_output else 0,
                    # RFQ
                    "rfq_creation_date": None, "rfq_id": "", "rfq_status": "",
                    # PO
                    "po_date":   po.get("po_date") if first_po_output else None,
                    "po_ids":    po.get("po_ids") if first_po_output else "",
                    "po_qty":    po.get("po_qty") if first_po_output else 0,
                    "po_rate":   po.get("po_rate") if first_po_output else 0,
                    "po_amount": po.get("po_amount") if first_po_output else 0,
                    "po_status": po.get("po_status") if first_po_output else "",
                    # PR — blank
                    "pr_date": None, "pr_id": "", "batch_no": "",
                    "pr_qty": 0, "pr_rate": 0, "pr_amount": 0, "pr_status": "",
                    # PR Return — blank
                    "pr_return_date": None, "pr_return_id": "",
                    "pr_return_qty": 0, "pr_return_rate": 0, "pr_return_amount": 0,
                    # Repack — blank
                    "repack_date": None, "repack_id": "", "repack_batch": "",
                    "repack_qty": 0, "repack_rate": 0, "repack_amount": 0,
                    # PI
                    "pi_date": pi_date_out, "pi_id": pi_id_out,
                    "pi_batch_no": pi_batch_no_out,
                    "pi_qty": pi_qty_out, "pi_rate": pi_rate_out,
                    "pi_amount": pi_amount_out, "pi_status": pi_status_out,
                    # PI Return
                    "pi_return_id":     pi_return_id_out,
                    "pi_return_qty":    pi_return_qty_out,
                    "pi_return_rate":   pi_return_rate_out,
                    "pi_return_amount": pi_return_amount_out,
                    # Diff
                    "difference_qty":    diff_qty,
                    "difference_rate":   diff_rate,
                    "difference_amount": diff_amount,
                })

                first_mr_output  = False
                first_po_output  = False
                pi_date_out      = None
                pi_id_out        = ""
                pi_status_out    = ""
                pi_batch_no_out  = ""
                pi_qty_out       = pi_rate_out = pi_amount_out = 0
                diff_qty         = diff_rate = diff_amount = ""


def _get_po_row_by_poi(poi_name):
    if not poi_name:
        return {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}
    po = frappe.db.sql("""
        SELECT po.transaction_date AS po_date, po.name AS po_ids,
               poi.qty AS po_qty, poi.rate AS po_rate, poi.amount AS po_amount, po.status AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.name = %(poi)s LIMIT 1
    """, {"poi": poi_name}, as_dict=1)
    return po[0] if po else {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}


def _get_mr_row_by_poi(poi_name):
    if not poi_name:
        return {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}
    mr = frappe.db.sql("""
        SELECT mr.transaction_date AS mr_date, mr.name AS material_request_id,
               mri.name AS material_request_item, mri.qty AS mr_qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request`      mr  ON mr.name  = poi.material_request
        LEFT JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
        WHERE poi.name = %(poi)s LIMIT 1
    """, {"poi": poi_name}, as_dict=1)
    return mr[0] if mr else {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}


# ─────────────────────────────────────────────────────────────────────────────
# total row
# ─────────────────────────────────────────────────────────────────────────────

def get_total_row(totals):
    return {
        "mr_date": None, "material_request_id": _("Total"), "item": "", "qty": totals["mr_qty"],
        "rfq_creation_date": None, "rfq_id": "", "rfq_status": "",
        "po_date": None, "po_ids": "", "po_qty": totals["po_qty"],
        "po_rate": "", "po_amount": totals["po_amount"], "po_status": "",
        "pr_date": None, "pr_id": "", "batch_no": "",
        "pr_qty": totals["pr_qty"], "pr_rate": "", "pr_amount": totals["pr_amount"], "pr_status": "",
        "pr_return_date": None, "pr_return_id": "",
        "pr_return_qty": totals["pr_return_qty"], "pr_return_rate": "",
        "pr_return_amount": totals["pr_return_amount"],
        "repack_date": None, "repack_id": "", "repack_batch": "",
        "repack_qty": totals["repack_qty"], "repack_rate": "",
        "repack_amount": totals["repack_amount"],
        "pi_date": None, "pi_id": "", "pi_batch_no": "",
        "pi_qty": totals["pi_qty"], "pi_rate": "", "pi_amount": totals["pi_amount"], "pi_status": "",
        "pi_return_id": "",
        "pi_return_qty": totals["pi_return_qty"], "pi_return_rate": "",
        "pi_return_amount": totals["pi_return_amount"],
        "difference_qty":    totals["difference_qty"],
        "difference_rate":   totals["difference_rate"],
        "difference_amount": totals["difference_amount"],
    }