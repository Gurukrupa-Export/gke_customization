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
        {"label": _("MR Date"), "fieldname": "mr_date", "fieldtype": "Date", "width": 95},
        {"label": _("Material Request ID"), "fieldname": "material_request_id", "fieldtype": "Link", "options": "Material Request", "width": 170},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},

        {"label": _("RFQ Creation Date"), "fieldname": "rfq_creation_date", "fieldtype": "Date", "width": 140},
        {"label": _("RFQ ID"), "fieldname": "rfq_id", "fieldtype": "Data", "width": 180},
        {"label": _("RFQ Status"), "fieldname": "rfq_status", "fieldtype": "Data", "width": 110},

        {"label": _("PO DATE"), "fieldname": "po_date", "fieldtype": "Date", "width": 95},
        {"label": _("PO IDs"), "fieldname": "po_ids", "fieldtype": "Data", "width": 180},
        {"label": _("PO QTY"), "fieldname": "po_qty", "fieldtype": "Float", "width": 90},
        {"label": _("PO RATE"), "fieldname": "po_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("PO AMOUNT"), "fieldname": "po_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PO Status"), "fieldname": "po_status", "fieldtype": "Data", "width": 110},

        {"label": _("PR DATE"), "fieldname": "pr_date", "fieldtype": "Date", "width": 95},
        {"label": _("PR IDs"), "fieldname": "pr_id", "fieldtype": "Data", "width": 160},
        {"label": _("BATCH NO"), "fieldname": "batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("PR QTY"), "fieldname": "pr_qty", "fieldtype": "Float", "width": 90},
        {"label": _("PR RATE"), "fieldname": "pr_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("PR AMOUNT"), "fieldname": "pr_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PR Status"), "fieldname": "pr_status", "fieldtype": "Data", "width": 110},

        {"label": _("PR RETURN DATE"), "fieldname": "pr_return_date", "fieldtype": "Date", "width": 95},
        {"label": _("PR RETURN ID"), "fieldname": "pr_return_id", "fieldtype": "Data", "width": 160},
        {"label": _("PR RETURN QTY"), "fieldname": "pr_return_qty", "fieldtype": "Float", "width": 100},
        {"label": _("PR RETURN RATE"), "fieldname": "pr_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("PR RETURN AMOUNT"), "fieldname": "pr_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("PI DATE"), "fieldname": "pi_date", "fieldtype": "Date", "width": 95},
        {"label": _("PI IDs"), "fieldname": "pi_id", "fieldtype": "Data", "width": 160},
        {"label": _("PI QTY"), "fieldname": "pi_qty", "fieldtype": "Float", "width": 90},
        {"label": _("PI RATE"), "fieldname": "pi_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("PI AMOUNT"), "fieldname": "pi_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PI Status"), "fieldname": "pi_status", "fieldtype": "Data", "width": 110},

        {"label": _("PI RETURN (DN) NO"), "fieldname": "pi_return_id", "fieldtype": "Data", "width": 160},
        {"label": _("PI RETURN QTY"), "fieldname": "pi_return_qty", "fieldtype": "Float", "width": 100},
        {"label": _("PI RETURN RATE"), "fieldname": "pi_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("PI RETURN AMOUNT"), "fieldname": "pi_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("Difference PR vs PI"), "fieldname": "difference_pr_vs_pi", "fieldtype": "Float", "width": 140},
        {"label": _("Difference Rate PR vs PI"), "fieldname": "difference_rate_pr_vs_pi", "fieldtype": "Currency", "width": 160},
        {"label": _("Difference Amount PR vs PI"), "fieldname": "difference_amount_pr_vs_pi", "fieldtype": "Currency", "width": 180},
    ]


def get_data(filters):
    params = dict(filters)

    pr_conditions = [
        "pr.docstatus = 1",
        "IFNULL(pr.is_return, 0) = 0"
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
                INNER JOIN `tabPurchase Invoice` pi
                    ON pi.name = pii.parent
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
            pr.name AS pr_id,
            pr.status AS pr_status,
            pr.company,

            pri.name AS pr_item_id,
            pri.idx,
            pri.item_code AS item,
            pri.batch_no,
            pri.qty AS pr_qty,
            pri.rate AS pr_rate,
            pri.amount AS pr_amount,
            pri.purchase_order_item

        FROM `tabPurchase Receipt` pr
        INNER JOIN `tabPurchase Receipt Item` pri
            ON pri.parent = pr.name

        WHERE {" AND ".join(pr_conditions)}

        ORDER BY pr.posting_date, pr.name, pri.idx
    """, params, as_dict=1)

    # ── Pre-aggregate PR qty/rate/amount and PI qty/rate/amount keyed by (pr_id, batch_no) ──
    # PR side: sum all PR item rows that share the same (pr_id, batch_no)
    # PI side: sum all PI rows linked to any PR item under the same (pr_id, batch_no)
    pr_totals_by_batch = {}   # (pr_id, batch_no) → {pr_qty, pr_rate, pr_amount}
    pi_totals_by_batch = {}   # (pr_id, batch_no) → {pi_qty, pi_rate, pi_amount}

    for r in rows:
        key = (r.pr_id, r.batch_no or "")

        if key not in pr_totals_by_batch:
            pr_totals_by_batch[key] = {"pr_qty": 0, "pr_rate": 0, "pr_amount": 0}
        pr_totals_by_batch[key]["pr_qty"]    += r.pr_qty or 0
        # max rate across all PR items of the same (pr_id, batch_no)
        pr_totals_by_batch[key]["pr_rate"]    = max(pr_totals_by_batch[key]["pr_rate"], r.pr_rate or 0)
        pr_totals_by_batch[key]["pr_amount"] += r.pr_amount or 0

        if key not in pi_totals_by_batch:
            pi_totals_by_batch[key] = {"pi_qty": 0, "pi_rate": 0, "pi_amount": 0}
        for pi in (get_pi_rows(r, filters) or []):
            pi_totals_by_batch[key]["pi_qty"]    += pi.get("qty") or 0
            pi_totals_by_batch[key]["pi_rate"]   += pi.get("rate") or 0
            pi_totals_by_batch[key]["pi_amount"] += pi.get("amount") or 0
    # ─────────────────────────────────────────────────────────────────────────────

    out = []

    totals = {
        "mr_qty": 0,
        "po_qty": 0,
        "po_amount": 0,
        "pr_qty": 0,
        "pr_amount": 0,
        "pr_return_qty": 0,
        "pr_return_amount": 0,
        "pi_qty": 0,
        "pi_amount": 0,
        "difference_pr_vs_pi": 0,
        "difference_rate_pr_vs_pi": 0,
        "difference_amount_pr_vs_pi": 0,
    }

    seen_mr_display        = set()
    seen_mr_total          = set()
    seen_po_display        = set()
    seen_po_total          = set()
    seen_pr_total          = set()
    seen_pr_return_display = set()
    seen_pr_return_total   = set()
    seen_pi_total          = set()
    seen_batch_diff        = set()  # tracks which (pr_id, batch_no) has already shown its difference

    for r in rows:
        mr  = get_mr_row(r)
        po  = get_po_row(r)
        rfq = get_rfq_row(r)

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

        pr_key = r.pr_item_id
        if pr_key and pr_key not in seen_pr_total:
            seen_pr_total.add(pr_key)
            totals["pr_qty"]    += r.pr_qty or 0
            totals["pr_amount"] += r.pr_amount or 0

        po_key = r.purchase_order_item or po.get("po_ids")
        if po_key and po_key not in seen_po_total:
            seen_po_total.add(po_key)
            totals["po_qty"]    += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        pi_rows = get_pi_rows(r, filters)
        if not pi_rows:
            pi_rows = [{
                "name": "",
                "posting_date": None,
                "status": "",
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "pii_name": "",
                "match_type": "",
            }]

        # ── PR Return rows fetched batch_no wise ──────────────────────────────
        ret_rows = get_pr_return_rows(r)
        if not ret_rows:
            ret_rows = [{
                "name": "",
                "posting_date": None,
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "pri_name": "",
            }]
        # ─────────────────────────────────────────────────────────────────────

        po_key = r.purchase_order_item or po.get("po_ids")
        first_po_output = po_key and po_key not in seen_po_display
        if first_po_output:
            seen_po_display.add(po_key)

        first_pr_output = True

        # ── Difference computed batch_no wise: SUM(PR items for this batch) - SUM(PI items for this batch)
        # Rate = max PR rate for this batch; shown only on the first output row of each (pr_id, batch_no)
        batch_diff_key = (r.pr_id, r.batch_no or "")
        if batch_diff_key not in seen_batch_diff:
            seen_batch_diff.add(batch_diff_key)
            _pr = pr_totals_by_batch.get(batch_diff_key, {})
            _pi = pi_totals_by_batch.get(batch_diff_key, {})
            _pr_return_qty = sum(
                abs(ret.get("qty") or 0)
                for ret in get_pr_return_rows(r)
            )
            pr_diff_qty    = round(_pr.get("pr_qty", 0) - _pr_return_qty - _pi.get("pi_qty", 0), 9)
            if abs(pr_diff_qty) < 1e-9:
                pr_diff_qty = 0
            pr_diff_rate   = _pr.get("pr_rate", 0) if pr_diff_qty != 0 else 0
            pr_diff_amount = round(_pr.get("pr_amount", 0) - _pi.get("pi_amount", 0), 9)
            if abs(pr_diff_amount) < 1e-9:
                pr_diff_amount = 0
        else:
            pr_diff_qty = pr_diff_rate = pr_diff_amount = ""
        # ─────────────────────────────────────────────────────────────────────

        for ret in ret_rows:
            ret_key = ret.get("pri_name") or ret.get("name")

            first_ret_output = False
            if ret.get("name") and ret_key not in seen_pr_return_display:
                seen_pr_return_display.add(ret_key)
                first_ret_output = True

            if ret.get("name") and ret_key not in seen_pr_return_total:
                seen_pr_return_total.add(ret_key)
                totals["pr_return_qty"]    += abs(ret.get("qty") or 0)
                totals["pr_return_amount"] += abs(ret.get("amount") or 0)

            for pi in pi_rows:
                pi_key = pi.get("pii_name") or pi.get("name")
                if pi.get("name") and pi_key not in seen_pi_total:
                    seen_pi_total.add(pi_key)
                    totals["pi_qty"]    += pi.get("qty") or 0
                    totals["pi_amount"] += pi.get("amount") or 0

                if first_ret_output:
                    pr_return_qty    = abs(ret.get("qty") or 0)
                    pr_return_rate   = abs(ret.get("rate") or 0)
                    pr_return_amount = abs(ret.get("amount") or 0)
                else:
                    pr_return_qty = pr_return_rate = pr_return_amount = 0

                pi_qty    = pi.get("qty") or 0
                pi_rate   = pi.get("rate") or 0
                pi_amount = pi.get("amount") or 0

                out.append({
                    "mr_date":             mr.get("mr_date") if first_mr_output else None,
                    "material_request_id": mr.get("material_request_id") if first_mr_output else "",
                    "item":                r.item if first_mr_output else "",
                    "qty":                 mr.get("mr_qty") if first_mr_output else "",

                    "rfq_creation_date":   rfq.get("rfq_creation_date") if first_mr_output else None,
                    "rfq_id":              rfq.get("rfq_id") if first_mr_output else "",
                    "rfq_status":          rfq.get("rfq_status") if first_mr_output else "",

                    "po_date":   po.get("po_date") if first_po_output else None,
                    "po_ids":    po.get("po_ids") if first_po_output else "",
                    "po_qty":    po.get("po_qty") if first_po_output else "",
                    "po_rate":   po.get("po_rate") if first_po_output else "",
                    "po_amount": po.get("po_amount") if first_po_output else "",
                    "po_status": po.get("po_status") if first_po_output else "",

                    "pr_date":   r.pr_date if first_pr_output else None,
                    "pr_id":     r.pr_id if first_pr_output else "",
                    "batch_no":  r.batch_no,
                    "pr_qty":    r.pr_qty if first_pr_output else "",
                    "pr_rate":   r.pr_rate if first_pr_output else "",
                    "pr_amount": r.pr_amount if first_pr_output else "",
                    "pr_status": r.pr_status if first_pr_output else "",

                    "pr_return_date":   ret.get("posting_date") if first_ret_output else None,
                    "pr_return_id":     ret.get("name") if first_ret_output else "",
                    "pr_return_qty":    pr_return_qty if first_ret_output else "",
                    "pr_return_rate":   pr_return_rate if first_ret_output else "",
                    "pr_return_amount": pr_return_amount if first_ret_output else "",

                    "pi_date":   pi.get("posting_date"),
                    "pi_id":     pi.get("name") or "",
                    "pi_qty":    pi_qty if pi.get("name") else "",
                    "pi_rate":   pi_rate if pi.get("name") else "",
                    "pi_amount": pi_amount if pi.get("name") else "",
                    "pi_status": pi.get("status") or "",

                    "pi_return_id":     "",
                    "pi_return_qty":    0,
                    "pi_return_rate":   0,
                    "pi_return_amount": 0,

                    # Shown once on the first row of each (pr_id, batch_no), blank on all others
                    "difference_pr_vs_pi":        pr_diff_qty,
                    "difference_rate_pr_vs_pi":   pr_diff_rate,
                    "difference_amount_pr_vs_pi": (round(pr_diff_qty * pr_diff_rate, 9) if (pr_diff_qty != "" and pr_diff_rate != "") else ""),
                })

                # After the very first cell of this batch, blank the diff out
                pr_diff_qty = pr_diff_rate = pr_diff_amount = ""
                first_pr_output = False
                first_mr_output = False
                first_po_output = False

    totals["difference_pr_vs_pi"] = (
        totals["pr_qty"] - totals["pr_return_qty"] - totals["pi_qty"]
    )
    totals["difference_amount_pr_vs_pi"] = (
        totals["difference_pr_vs_pi"] * totals["difference_rate_pr_vs_pi"]
    )

    return out, totals


def get_mr_row(r):
    if not r.purchase_order_item:
        return {
            "mr_date": None,
            "material_request_id": "",
            "material_request_item": "",
            "mr_qty": 0,
        }

    mr = frappe.db.sql("""
        SELECT
            mr.transaction_date AS mr_date,
            mr.name AS material_request_id,
            mri.name AS material_request_item,
            mri.qty AS mr_qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request` mr
            ON mr.name = poi.material_request
        LEFT JOIN `tabMaterial Request Item` mri
            ON mri.name = poi.material_request_item
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)

    return mr[0] if mr else {
        "mr_date": None,
        "material_request_id": "",
        "material_request_item": "",
        "mr_qty": 0,
    }


def get_po_row(r):
    if not r.purchase_order_item:
        return {
            "po_date": None,
            "po_ids": "",
            "po_qty": 0,
            "po_rate": 0,
            "po_amount": 0,
            "po_status": "",
        }

    po = frappe.db.sql("""
        SELECT
            po.transaction_date AS po_date,
            po.name AS po_ids,
            poi.qty AS po_qty,
            poi.rate AS po_rate,
            poi.amount AS po_amount,
            po.status AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po
            ON po.name = poi.parent
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)

    return po[0] if po else {
        "po_date": None,
        "po_ids": "",
        "po_qty": 0,
        "po_rate": 0,
        "po_amount": 0,
        "po_status": "",
    }


def get_rfq_row(r):
    return {
        "rfq_creation_date": None,
        "rfq_id": "",
        "rfq_status": "",
    }


def get_pi_rows(r, filters):
    params = {
        "poi": r.purchase_order_item,
        "pri": r.pr_item_id,
    }

    pi_filter_sql = ""
    if filters.get("pi_id"):
        pi_filter_sql += " AND pi.name = %(pi_id)s "
        params["pi_id"] = filters.get("pi_id")

    exact_rows = frappe.db.sql(f"""
        SELECT DISTINCT
            pi.name,
            pi.posting_date,
            pi.status,
            pii.name AS pii_name,
            pii.qty,
            pii.rate,
            pii.amount,
            'PR Detail' AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pii.pr_detail = %(pri)s
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)

    if exact_rows:
        return exact_rows

    if not r.purchase_order_item:
        return []

    return frappe.db.sql(f"""
        SELECT DISTINCT
            pi.name,
            pi.posting_date,
            pi.status,
            pii.name AS pii_name,
            pii.qty,
            pii.rate,
            pii.amount,
            'PO Detail' AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pii.po_detail = %(poi)s
          AND IFNULL(pii.pr_detail, '') = ''
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)


def get_pr_return_rows(r):
    """
    Fetch PR Return rows matched by batch_no (instead of PR ID only).
    Matches returns where:
      - return_against = this PR
      - item_code matches
      - batch_no matches (batch-wise matching)
    """
    return frappe.db.sql("""
        SELECT
            ret.name,
            ret.posting_date,
            reti.name AS pri_name,
            reti.qty,
            reti.rate,
            reti.amount
        FROM `tabPurchase Receipt` ret
        INNER JOIN `tabPurchase Receipt Item` reti
            ON reti.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(return_against)s
          AND reti.item_code = %(item_code)s
          AND IFNULL(reti.batch_no, '') = %(batch_no)s
        ORDER BY ret.posting_date, ret.name, reti.idx
    """, {
        "return_against": r.pr_id,
        "item_code": r.item,
        "batch_no": r.batch_no or "",
    }, as_dict=True)


def get_total_row(totals):
    return {
        "mr_date": None,
        "material_request_id": _("Total"),
        "item": "",
        "qty": totals["mr_qty"],

        "rfq_creation_date": None,
        "rfq_id": "",
        "rfq_status": "",

        "po_date": None,
        "po_ids": "",
        "po_qty": totals["po_qty"],
        "po_rate": "",
        "po_amount": totals["po_amount"],
        "po_status": "",

        "pr_date": None,
        "pr_id": "",
        "batch_no": "",
        "pr_qty": totals["pr_qty"],
        "pr_rate": "",
        "pr_amount": totals["pr_amount"],
        "pr_status": "",

        "pr_return_date": None,
        "pr_return_id": "",
        "pr_return_qty": totals["pr_return_qty"],
        "pr_return_rate": "",
        "pr_return_amount": totals["pr_return_amount"],

        "pi_date": None,
        "pi_id": "",
        "pi_qty": totals["pi_qty"],
        "pi_rate": "",
        "pi_amount": totals["pi_amount"],
        "pi_status": "",

        "pi_return_id": "",
        "pi_return_qty": 0,
        "pi_return_rate": 0,
        "pi_return_amount": 0,

        "difference_pr_vs_pi": totals["difference_pr_vs_pi"],
        "difference_rate_pr_vs_pi": "",
        "difference_amount_pr_vs_pi": totals["difference_amount_pr_vs_pi"],
    }