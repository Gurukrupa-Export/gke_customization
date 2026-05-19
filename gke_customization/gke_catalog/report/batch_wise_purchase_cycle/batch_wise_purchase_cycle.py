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
        {"label": _("PI RETURN QTY"), "fieldname": "pi_return_qty", "fieldtype": "Float", "width": 90},
        {"label": _("PI RETURN RATE"), "fieldname": "pi_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("PI RETURN AMOUNT"), "fieldname": "pi_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("Difference Qty"), "fieldname": "difference_pr_vs_pi", "fieldtype": "Float", "width": 140},
        {"label": _("Difference Rate"), "fieldname": "difference_rate_pr_vs_pi", "fieldtype": "Currency", "width": 160},
        {"label": _("Difference Amount"), "fieldname": "difference_amount_pr_vs_pi", "fieldtype": "Currency", "width": 180},
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
            pr.name         AS pr_id,
            pr.status       AS pr_status,
            pr.company,
            pri.name        AS pr_item_id,
            pri.idx,
            pri.item_code   AS item,
            pri.batch_no,
            pri.qty         AS pr_qty,
            pri.rate        AS pr_rate,
            pri.amount      AS pr_amount,
            pri.purchase_order_item
        FROM `tabPurchase Receipt` pr
        INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE {" AND ".join(pr_conditions)}
        ORDER BY pr.posting_date, pr.name, pri.idx
    """, params, as_dict=1)

    pr_totals_by_batch = {}
    pi_totals_by_batch = {}

    for r in rows:
        key = (r.pr_id, r.batch_no or "")
        if key not in pr_totals_by_batch:
            pr_totals_by_batch[key] = {"pr_qty": 0, "pr_rate": 0, "pr_amount": 0}
        pr_totals_by_batch[key]["pr_qty"] += r.pr_qty or 0
        pr_totals_by_batch[key]["pr_rate"] = max(pr_totals_by_batch[key]["pr_rate"], r.pr_rate or 0)
        pr_totals_by_batch[key]["pr_amount"] += r.pr_amount or 0

        if key not in pi_totals_by_batch:
            pi_totals_by_batch[key] = {"pi_qty": 0, "pi_rate": 0, "pi_amount": 0}
        for pi in (get_pi_rows(r, filters) or []):
            pi_totals_by_batch[key]["pi_qty"] += pi.get("qty") or 0
            pi_totals_by_batch[key]["pi_rate"] += pi.get("rate") or 0
            pi_totals_by_batch[key]["pi_amount"] += pi.get("amount") or 0

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
        "pi_return_qty": 0,
        "pi_return_amount": 0,
        "difference_pr_vs_pi": 0,
        "difference_rate_pr_vs_pi": 0,
        "difference_amount_pr_vs_pi": 0,
    }

    seen_mr_display = set()
    seen_mr_total = set()
    seen_po_display = set()
    seen_po_total = set()
    seen_pr_total = set()
    seen_pr_return_display = set()
    seen_pr_return_total = set()
    seen_pi_display = set()
    seen_pi_total = set()
    seen_pi_return_display = set()
    seen_pi_return_total = set()
    seen_batch_diff = set()
    seen_pii_via_pr = set()

    for r in rows:
        mr = get_mr_row(r)
        po = get_po_row(r)
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
            totals["pr_qty"] += r.pr_qty or 0
            totals["pr_amount"] += r.pr_amount or 0

        po_key = r.purchase_order_item or po.get("po_ids")
        if po_key and po_key not in seen_po_total:
            seen_po_total.add(po_key)
            totals["po_qty"] += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        pi_rows = get_pi_rows(r, filters)
        if not pi_rows:
            pi_rows = [{"name": "", "posting_date": None, "status": "", "qty": 0, "rate": 0, "amount": 0, "pii_name": "", "match_type": ""}]

        ret_rows = get_pr_return_rows(r, filters)
        if not ret_rows:
            ret_rows = [{"name": "", "posting_date": None, "qty": 0, "rate": 0, "amount": 0, "pri_name": ""}]

        po_key = r.purchase_order_item or po.get("po_ids")
        first_po_output = po_key and po_key not in seen_po_display
        if first_po_output:
            seen_po_display.add(po_key)

        first_pr_output = True

        batch_diff_key = (r.pr_id, r.batch_no or "")
        if batch_diff_key not in seen_batch_diff:
            seen_batch_diff.add(batch_diff_key)
            _pr = pr_totals_by_batch.get(batch_diff_key, {})
            _pi = pi_totals_by_batch.get(batch_diff_key, {})
            _pr_return_qty = sum(abs(ret.get("qty") or 0) for ret in get_pr_return_rows(r, filters))
            pr_diff_qty = round(
                _pr.get("pr_qty", 0)
                - _pr_return_qty
                - _pi.get("pi_qty", 0)
                + _pi.get("pi_return_qty", 0),
                9
            )
            if abs(pr_diff_qty) < 1e-9:
                pr_diff_qty = 0
            pr_diff_rate = _pr.get("pr_rate", 0) if pr_diff_qty != 0 else 0
            pr_diff_amount = round(pr_diff_qty * pr_diff_rate, 9)
            if abs(pr_diff_amount) < 1e-9:
                pr_diff_amount = 0
        else:
            pr_diff_qty = pr_diff_rate = pr_diff_amount = ""

        for ret in ret_rows:
            ret_key = ret.get("pri_name") or ret.get("name")

            first_ret_output = False
            if ret.get("name") and ret_key not in seen_pr_return_display:
                seen_pr_return_display.add(ret_key)
                first_ret_output = True

            if ret.get("name") and ret_key not in seen_pr_return_total:
                seen_pr_return_total.add(ret_key)
                totals["pr_return_qty"] += abs(ret.get("qty") or 0)
                totals["pr_return_amount"] += abs(ret.get("amount") or 0)

            for pi in pi_rows:
                pi_key = pi.get("pii_name") or pi.get("name")

                first_pi_output = False
                if pi.get("name") and pi_key not in seen_pi_display:
                    seen_pi_display.add(pi_key)
                    if pi.get("pii_name"):
                        seen_pii_via_pr.add(pi["pii_name"])
                    first_pi_output = True

                if pi.get("name") and pi_key not in seen_pi_total:
                    seen_pi_total.add(pi_key)
                    totals["pi_qty"] += pi.get("qty") or 0
                    totals["pi_amount"] += pi.get("amount") or 0

                pi_return_rows = []
                if pi.get("name"):
                    pi_return_rows = get_pi_return_rows(pi.get("name"), pi.get("pii_name"), filters)
                if not pi_return_rows:
                    pi_return_rows = [{"name": "", "posting_date": None, "qty": 0, "rate": 0, "amount": 0, "pii_return_name": ""}]

                if first_ret_output:
                    pr_return_qty = abs(ret.get("qty") or 0)
                    pr_return_rate = abs(ret.get("rate") or 0)
                    pr_return_amount = abs(ret.get("amount") or 0)
                    pr_return_date = ret.get("posting_date")
                    pr_return_id = ret.get("name") or ""
                else:
                    pr_return_qty = pr_return_rate = pr_return_amount = 0
                    pr_return_date = None
                    pr_return_id = ""

                if first_pi_output:
                    pi_qty = pi.get("qty") or 0
                    pi_rate = pi.get("rate") or 0
                    pi_amount = pi.get("amount") or 0
                    pi_date = pi.get("posting_date")
                    pi_id = pi.get("name") or ""
                    pi_status = pi.get("status") or ""
                else:
                    pi_qty = pi_rate = pi_amount = 0
                    pi_date = None
                    pi_id = pi_status = ""

                for pi_ret in pi_return_rows:
                    pi_ret_key = pi_ret.get("pii_return_name") or pi_ret.get("name")

                    first_pi_ret_output = False
                    if pi_ret.get("name") and pi_ret_key not in seen_pi_return_display:
                        seen_pi_return_display.add(pi_ret_key)
                        first_pi_ret_output = True

                    if pi_ret.get("name") and pi_ret_key not in seen_pi_return_total:
                        seen_pi_return_total.add(pi_ret_key)
                        totals["pi_return_qty"] += abs(pi_ret.get("qty") or 0)
                        totals["pi_return_amount"] += abs(pi_ret.get("amount") or 0)

                    if first_pi_ret_output:
                        pi_return_id = pi_ret.get("name") or ""
                        pi_return_qty = abs(pi_ret.get("qty") or 0)
                        pi_return_rate = abs(pi_ret.get("rate") or 0)
                        pi_return_amount = abs(pi_ret.get("amount") or 0)
                    else:
                        pi_return_id = ""
                        pi_return_qty = pi_return_rate = pi_return_amount = 0

                    diff_qty_value = pr_diff_qty
                    diff_rate_value = pr_diff_rate
                    diff_amount_value = (
                        round(pr_diff_qty * pr_diff_rate, 9)
                        if (pr_diff_qty != "" and pr_diff_rate != "")
                        else ""
                    )

                    if diff_qty_value not in ("", None):
                        totals["difference_pr_vs_pi"] += diff_qty_value
                    if diff_rate_value not in ("", None):
                        totals["difference_rate_pr_vs_pi"] += diff_rate_value
                    if diff_amount_value not in ("", None):
                        totals["difference_amount_pr_vs_pi"] += diff_amount_value

                    out.append({
                        "mr_date": mr.get("mr_date") if first_mr_output else None,
                        "material_request_id": mr.get("material_request_id") if first_mr_output else "",
                        "item": r.item if first_mr_output else "",
                        "qty": mr.get("mr_qty") if first_mr_output else 0,

                        "rfq_creation_date": rfq.get("rfq_creation_date") if first_mr_output else None,
                        "rfq_id": rfq.get("rfq_id") if first_mr_output else "",
                        "rfq_status": rfq.get("rfq_status") if first_mr_output else "",

                        "po_date": po.get("po_date") if first_po_output else None,
                        "po_ids": po.get("po_ids") if first_po_output else "",
                        "po_qty": po.get("po_qty") if first_po_output else 0,
                        "po_rate": po.get("po_rate") if first_po_output else 0,
                        "po_amount": po.get("po_amount") if first_po_output else 0,
                        "po_status": po.get("po_status") if first_po_output else "",

                        "pr_date": r.pr_date if first_pr_output else None,
                        "pr_id": r.pr_id if first_pr_output else "",
                        "batch_no": r.batch_no,
                        "pr_qty": r.pr_qty if first_pr_output else 0,
                        "pr_rate": r.pr_rate if first_pr_output else 0,
                        "pr_amount": r.pr_amount if first_pr_output else 0,
                        "pr_status": r.pr_status if first_pr_output else "",

                        "pr_return_date": pr_return_date,
                        "pr_return_id": pr_return_id,
                        "pr_return_qty": pr_return_qty,
                        "pr_return_rate": pr_return_rate,
                        "pr_return_amount": pr_return_amount,

                        "pi_date": pi_date,
                        "pi_id": pi_id,
                        "pi_qty": pi_qty,
                        "pi_rate": pi_rate,
                        "pi_amount": pi_amount,
                        "pi_status": pi_status,

                        "pi_return_id": pi_return_id,
                        "pi_return_qty": pi_return_qty,
                        "pi_return_rate": pi_return_rate,
                        "pi_return_amount": pi_return_amount,

                        "difference_pr_vs_pi": diff_qty_value,
                        "difference_rate_pr_vs_pi": diff_rate_value,
                        "difference_amount_pr_vs_pi": diff_amount_value,
                    })

                    pr_diff_qty = pr_diff_rate = pr_diff_amount = ""
                    first_pr_output = False
                    first_mr_output = False
                    first_po_output = False
                    pi_qty = pi_rate = pi_amount = 0
                    pi_date = None
                    pi_id = pi_status = ""
                    pr_return_qty = pr_return_rate = pr_return_amount = 0
                    pr_return_date = None
                    pr_return_id = ""


    if not filters.get("pr_id") and not filters.get("batch_no"):
        standalone_rows = _get_standalone_pi_rows(filters)
        standalone_rows = [r for r in standalone_rows if r.pii_name not in seen_pii_via_pr]
        _append_standalone_pi_rows(
            standalone_rows, filters, out, totals,
            seen_mr_display, seen_mr_total,
            seen_po_display, seen_po_total,
            seen_pi_return_display, seen_pi_return_total,
        )

        if diff_qty_value not in ("", None):
            totals["difference_pr_vs_pi"] += diff_qty_value
    

    return out, totals


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
            pi.name         AS pi_name,
            pi.posting_date AS pi_date,
            pi.status       AS pi_status,
            pi.company,
            pii.name        AS pii_name,
            pii.idx,
            pii.item_code   AS item,
            pii.qty         AS pi_qty,
            pii.rate        AS pi_rate,
            pii.amount      AS pi_amount,
            pii.po_detail   AS purchase_order_item
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
        pi_totals_by_poi[poi]["pi_qty"] += r.pi_qty or 0
        pi_totals_by_poi[poi]["pi_amount"] += r.pi_amount or 0

    seen_poi_diff = set()
    seen_pi_display_sa = set()
    seen_pi_total_sa = set()

    for r in standalone_rows:
        poi = r.purchase_order_item
        po = po_totals_by_poi.get(poi, {})
        mr = _get_mr_row_by_poi(poi)

        mr_key = (
            mr.get("material_request_item")
            or f"{mr.get('material_request_id') or ''}::{r.item or ''}"
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
            totals["po_qty"] += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        pi_key = r.pii_name or r.pi_name
        first_pi_output = bool(pi_key and pi_key not in seen_pi_display_sa)
        if first_pi_output:
            seen_pi_display_sa.add(pi_key)

        if pi_key and pi_key not in seen_pi_total_sa:
            seen_pi_total_sa.add(pi_key)
            totals["pi_qty"] += r.pi_qty or 0
            totals["pi_amount"] += r.pi_amount or 0

        if poi not in seen_poi_diff:
            seen_poi_diff.add(poi)
            _po = po_totals_by_poi.get(poi, {})
            _pi = pi_totals_by_poi.get(poi, {})
            diff_qty = round(_po.get("po_qty", 0) - _pi.get("pi_qty", 0), 9)
            diff_amount = round(_po.get("po_amount", 0) - _pi.get("pi_amount", 0), 9)
            if abs(diff_qty) < 1e-9:
                diff_qty = 0
            if abs(diff_amount) < 1e-9:
                diff_amount = 0
            diff_rate = round(diff_amount / diff_qty, 9) if diff_qty else 0
        else:
            diff_qty = diff_rate = diff_amount = ""

        pi_return_rows = get_pi_return_rows(r.pi_name, r.pii_name, filters) or [
            {"name": "", "posting_date": None, "qty": 0, "rate": 0, "amount": 0, "pii_return_name": ""}
        ]

        first_pi_ret_loop = True
        for pi_ret in pi_return_rows:
            pi_ret_key = pi_ret.get("pii_return_name") or pi_ret.get("name")

            first_pi_ret_output = False
            if pi_ret.get("name") and pi_ret_key not in seen_pi_return_display:
                seen_pi_return_display.add(pi_ret_key)
                first_pi_ret_output = True

            if pi_ret.get("name") and pi_ret_key not in seen_pi_return_total:
                seen_pi_return_total.add(pi_ret_key)
                totals["pi_return_qty"] += abs(pi_ret.get("qty") or 0)
                totals["pi_return_amount"] += abs(pi_ret.get("amount") or 0)

            if first_pi_ret_output:
                pi_return_id = pi_ret.get("name") or ""
                pi_return_qty = abs(pi_ret.get("qty") or 0)
                pi_return_rate = abs(pi_ret.get("rate") or 0)
                pi_return_amount = abs(pi_ret.get("amount") or 0)
            else:
                pi_return_id = ""
                pi_return_qty = pi_return_rate = pi_return_amount = 0

            out.append({
                "mr_date": mr.get("mr_date") if first_mr_output else None,
                "material_request_id": mr.get("material_request_id") if first_mr_output else "",
                "item": r.item if first_mr_output else "",
                "qty": mr.get("mr_qty") if first_mr_output else 0,

                "rfq_creation_date": None,
                "rfq_id": "",
                "rfq_status": "",

                "po_date": po.get("po_date") if first_po_output else None,
                "po_ids": po.get("po_ids") if first_po_output else "",
                "po_qty": po.get("po_qty") if first_po_output else 0,
                "po_rate": po.get("po_rate") if first_po_output else 0,
                "po_amount": po.get("po_amount") if first_po_output else 0,
                "po_status": po.get("po_status") if first_po_output else "",

                "pr_date": None,
                "pr_id": "",
                "batch_no": "",
                "pr_qty": 0,
                "pr_rate": 0,
                "pr_amount": 0,
                "pr_status": "",

                "pr_return_date": None,
                "pr_return_id": "",
                "pr_return_qty": 0,
                "pr_return_rate": 0,
                "pr_return_amount": 0,

                "pi_date": r.pi_date if (first_pi_output and first_pi_ret_loop) else None,
                "pi_id": r.pi_name if (first_pi_output and first_pi_ret_loop) else "",
                "pi_qty": r.pi_qty if (first_pi_output and first_pi_ret_loop) else 0,
                "pi_rate": r.pi_rate if (first_pi_output and first_pi_ret_loop) else 0,
                "pi_amount": r.pi_amount if (first_pi_output and first_pi_ret_loop) else 0,
                "pi_status": r.pi_status if (first_pi_output and first_pi_ret_loop) else "",

                "pi_return_id": pi_return_id,
                "pi_return_qty": pi_return_qty,
                "pi_return_rate": pi_return_rate,
                "pi_return_amount": pi_return_amount,

                "difference_pr_vs_pi": 0 if not r.batch_no else diff_qty,
                "difference_rate_pr_vs_pi": 0 if not r.batch_no else diff_rate,
                "difference_amount_pr_vs_pi": 0 if not r.batch_no else diff_amount,
            })

            first_mr_output = False
            first_po_output = False
            first_pi_ret_loop = False


def _get_po_row_by_poi(poi_name):
    if not poi_name:
        return {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}
    po = frappe.db.sql("""
        SELECT
            po.transaction_date AS po_date,
            po.name             AS po_ids,
            poi.qty             AS po_qty,
            poi.rate            AS po_rate,
            poi.amount          AS po_amount,
            po.status           AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": poi_name}, as_dict=1)
    return po[0] if po else {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}


def _get_mr_row_by_poi(poi_name):
    if not poi_name:
        return {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}
    mr = frappe.db.sql("""
        SELECT
            mr.transaction_date AS mr_date,
            mr.name             AS material_request_id,
            mri.name            AS material_request_item,
            mri.qty             AS mr_qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request` mr  ON mr.name  = poi.material_request
        LEFT JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": poi_name}, as_dict=1)
    return mr[0] if mr else {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}


def get_mr_row(r):
    if not r.purchase_order_item:
        return {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}
    mr = frappe.db.sql("""
        SELECT
            mr.transaction_date AS mr_date,
            mr.name             AS material_request_id,
            mri.name            AS material_request_item,
            mri.qty             AS mr_qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request` mr  ON mr.name  = poi.material_request
        LEFT JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)
    return mr[0] if mr else {"mr_date": None, "material_request_id": "", "material_request_item": "", "mr_qty": 0}


def get_po_row(r):
    if not r.purchase_order_item:
        return {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}
    po = frappe.db.sql("""
        SELECT
            po.transaction_date AS po_date,
            po.name             AS po_ids,
            poi.qty             AS po_qty,
            poi.rate            AS po_rate,
            poi.amount          AS po_amount,
            po.status           AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.name = %(poi)s
        LIMIT 1
    """, {"poi": r.purchase_order_item}, as_dict=1)
    return po[0] if po else {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": 0, "po_amount": 0, "po_status": ""}


def get_rfq_row(r):
    return {"rfq_creation_date": None, "rfq_id": "", "rfq_status": ""}


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
        SELECT DISTINCT
            pi.name, pi.posting_date, pi.status,
            pii.name AS pii_name, pii.qty, pii.rate, pii.amount,
            'PR Detail' AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
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
            pi.name, pi.posting_date, pi.status,
            pii.name AS pii_name, pii.qty, pii.rate, pii.amount,
            'PO Detail' AS match_type
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pii.po_detail = %(poi)s
          AND IFNULL(pii.pr_detail, '') = ''
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)


def get_pr_return_rows(r, filters=None):
    filters = filters or {}
    params = {
        "return_against": r.pr_id,
        "item_code": r.item,
        "batch_no": r.batch_no or "",
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


def get_pi_return_rows(pi_name, pii_name=None, filters=None):
    if not pi_name:
        return []
    filters = filters or {}
    params = {"pi_name": pi_name}
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
            ret_i.name AS pii_return_name,
            ret_i.qty, ret_i.rate, ret_i.amount
        FROM `tabPurchase Invoice` ret
        INNER JOIN `tabPurchase Invoice Item` ret_i ON ret_i.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(pi_name)s
          {date_sql}
        ORDER BY ret.posting_date, ret.name, ret_i.idx
    """, params, as_dict=True)


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
        "pi_return_qty": totals["pi_return_qty"],
        "pi_return_rate": "",
        "pi_return_amount": totals["pi_return_amount"],

        "difference_pr_vs_pi": totals["difference_pr_vs_pi"],
        "difference_rate_pr_vs_pi": "",
        "difference_amount_pr_vs_pi": totals["difference_amount_pr_vs_pi"],
    }