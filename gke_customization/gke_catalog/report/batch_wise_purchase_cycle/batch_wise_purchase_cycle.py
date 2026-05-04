import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data, totals = get_data(filters)
    data.append(get_total_row(totals))
    return columns, data


def get_columns():
    return [
        {"label": _("MR Date"), "fieldname": "mr_date", "fieldtype": "Date", "width": 95},
        {"label": _("Material Request ID"), "fieldname": "material_request_id", "fieldtype": "Link", "options": "Material Request", "width": 160},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},

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

    pr_conditions = ["pr.docstatus = 1", "IFNULL(pr.is_return, 0) = 0"]

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
                FROM `tabPurchase Order Item` poi_filter
                INNER JOIN `tabPurchase Order` po_filter ON po_filter.name = poi_filter.parent
                WHERE poi_filter.name = pri.purchase_order_item
                  AND po_filter.name = %(po_id)s
            )
        """)

    if filters.get("material_request_id"):
        pr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Order Item` poi_mr
                WHERE poi_mr.name = pri.purchase_order_item
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
                  AND (pii.pr_detail = pri.name OR pii.po_detail = pri.purchase_order_item)
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

    seen_qty_rows = set()
    seen_po_items = set()
    seen_pr_items = set()
    seen_pr_return_items = set()
    seen_pi_items = set()

    for r in rows:
        mr = get_mr_row(r, filters)
        po = get_po_row(r, filters)
        rfq = get_rfq_row(r, filters)
        pi_rows = get_pi_rows(r, filters)
        ret_rows = get_pr_return_rows(r, filters)

        if r.pr_item_id not in seen_qty_rows:
            seen_qty_rows.add(r.pr_item_id)
            totals["mr_qty"] += r.pr_qty or 0

        if r.pr_item_id not in seen_pr_items:
            seen_pr_items.add(r.pr_item_id)
            totals["pr_qty"] += r.pr_qty or 0
            totals["pr_amount"] += r.pr_amount or 0

        po_key = r.purchase_order_item or po.get("po_ids")
        if po_key and po_key not in seen_po_items:
            seen_po_items.add(po_key)
            totals["po_qty"] += po.get("po_qty") or 0
            totals["po_amount"] += po.get("po_amount") or 0

        if not pi_rows:
            pi_rows = [{
                "name": "",
                "posting_date": None,
                "status": "",
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "pii_name": ""
            }]

        if not ret_rows:
            ret_rows = [{
                "name": "",
                "posting_date": None,
                "qty": 0,
                "rate": 0,
                "amount": 0,
                "pri_name": ""
            }]

        for ret in ret_rows:
            ret_key = ret.get("pri_name") or ret.get("name")
            if ret.get("name") and ret_key not in seen_pr_return_items:
                seen_pr_return_items.add(ret_key)
                totals["pr_return_qty"] += abs(ret.get("qty") or 0)
                totals["pr_return_amount"] += abs(ret.get("amount") or 0)

            for pi in pi_rows:
                pi_key = pi.get("pii_name") or pi.get("name")
                if pi.get("name") and pi_key not in seen_pi_items:
                    seen_pi_items.add(pi_key)
                    totals["pi_qty"] += pi.get("qty") or 0
                    totals["pi_amount"] += pi.get("amount") or 0

                out.append({
                    "mr_date": mr.get("mr_date"),
                    "material_request_id": mr.get("material_request_id"),
                    "item": r.item,
                    "qty": r.pr_qty,

                    "rfq_creation_date": rfq.get("rfq_creation_date"),
                    "rfq_id": rfq.get("rfq_id"),
                    "rfq_status": rfq.get("rfq_status"),

                    "po_date": po.get("po_date"),
                    "po_ids": po.get("po_ids"),
                    "po_qty": po.get("po_qty"),
                    "po_rate": po.get("po_rate"),
                    "po_amount": po.get("po_amount"),
                    "po_status": po.get("po_status"),

                    "pr_date": r.pr_date,
                    "pr_id": r.pr_id,
                    "batch_no": r.batch_no,
                    "pr_qty": r.pr_qty,
                    "pr_rate": r.pr_rate,
                    "pr_amount": r.pr_amount,
                    "pr_status": r.pr_status,

                    "pr_return_date": ret.get("posting_date"),
                    "pr_return_id": ret.get("name") or "",
                    "pr_return_qty": abs(ret.get("qty") or 0),
                    "pr_return_rate": abs(ret.get("rate") or 0),
                    "pr_return_amount": abs(ret.get("amount") or 0),

                    "pi_date": pi.get("posting_date"),
                    "pi_id": pi.get("name") or "",
                    "pi_qty": pi.get("qty") or 0,
                    "pi_rate": pi.get("rate") or 0,
                    "pi_amount": pi.get("amount") or 0,
                    "pi_status": pi.get("status") or "",

                    "pi_return_id": "",
                    "pi_return_qty": 0,
                    "pi_return_rate": 0,
                    "pi_return_amount": 0,

                    "difference_pr_vs_pi": (r.pr_qty or 0) - (abs(ret.get("qty") or 0)) - (pi.get("qty") or 0),
                    "difference_rate_pr_vs_pi": (r.pr_rate or 0) - (abs(ret.get("rate") or 0)) - (pi.get("rate") or 0),
                    "difference_amount_pr_vs_pi": (r.pr_amount or 0) - (abs(ret.get("amount") or 0)) - (pi.get("amount") or 0),
                })

    totals["difference_pr_vs_pi"] = (totals["pr_qty"] - totals["pr_return_qty"]) - totals["pi_qty"]
    totals["difference_amount_pr_vs_pi"] = (totals["pr_amount"] - totals["pr_return_amount"]) - totals["pi_amount"]

    return out, totals


def get_mr_row(r, filters):
    if not r.purchase_order_item:
        return {"mr_date": None, "material_request_id": "", "qty": 0}

    conditions = ["poi.name = %(poi)s"]
    params = {"poi": r.purchase_order_item}

    if filters.get("material_request_id"):
        conditions.append("mr.name = %(material_request_id)s")
        params["material_request_id"] = filters.get("material_request_id")

    mr = frappe.db.sql(f"""
        SELECT
            mr.transaction_date AS mr_date,
            mr.name AS material_request_id,
            mri.qty
        FROM `tabPurchase Order Item` poi
        LEFT JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
        LEFT JOIN `tabMaterial Request` mr ON mr.name = poi.material_request
        WHERE {" AND ".join(conditions)}
        LIMIT 1
    """, params, as_dict=1)

    return mr[0] if mr else {"mr_date": None, "material_request_id": "", "qty": 0}


def get_po_row(r, filters):
    if not r.purchase_order_item:
        return {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": "", "po_amount": 0, "po_status": ""}

    conditions = ["poi.name = %(poi)s"]
    params = {"poi": r.purchase_order_item}

    if filters.get("po_id"):
        conditions.append("po.name = %(po_id)s")
        params["po_id"] = filters.get("po_id")

    po = frappe.db.sql(f"""
        SELECT
            po.transaction_date AS po_date,
            po.name AS po_ids,
            poi.qty AS po_qty,
            poi.rate AS po_rate,
            poi.amount AS po_amount,
            po.status AS po_status
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE {" AND ".join(conditions)}
        LIMIT 1
    """, params, as_dict=1)

    return po[0] if po else {"po_date": None, "po_ids": "", "po_qty": 0, "po_rate": "", "po_amount": 0, "po_status": ""}


def get_rfq_row(r, filters):
    if not r.purchase_order_item:
        return {"rfq_creation_date": None, "rfq_id": "", "rfq_status": ""}

    rfq = frappe.db.sql("""
        SELECT
            MIN(DATE(rfq.creation)) AS rfq_creation_date,
            GROUP_CONCAT(DISTINCT rfq.name ORDER BY rfq.creation SEPARATOR ', ') AS rfq_id,
            GROUP_CONCAT(DISTINCT rfq.status ORDER BY rfq.creation SEPARATOR ', ') AS rfq_status
        FROM `tabRequest for Quotation Item` rfqi
        INNER JOIN `tabRequest for Quotation` rfq ON rfq.name = rfqi.parent
        WHERE rfqi.material_request_item IN (
            SELECT poi.material_request_item
            FROM `tabPurchase Order Item` poi
            WHERE poi.name = %(poi)s
        )
        AND rfq.docstatus = 1
    """, {"poi": r.purchase_order_item}, as_dict=1)

    return rfq[0] if rfq else {"rfq_creation_date": None, "rfq_id": "", "rfq_status": ""}


def get_pi_rows(r, filters):
    params = {"poi": r.purchase_order_item, "pri": r.pr_item_id}
    pi_filter_sql = ""

    if filters.get("pi_id"):
        pi_filter_sql += " AND pi.name = %(pi_id)s "
        params["pi_id"] = filters.get("pi_id")

    if filters.get("item"):
        pi_filter_sql += " AND pii.item_code = %(item)s "
        params["item"] = filters.get("item")

    linked = frappe.db.sql(f"""
        SELECT DISTINCT
            pi.name,
            pi.posting_date,
            pi.status,
            pii.name AS pii_name,
            pii.qty,
            pii.rate,
            pii.amount
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND (
              pii.pr_detail = %(pri)s
              OR pii.po_detail = %(poi)s
          )
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)

    return linked


def get_pr_return_rows(r, filters):
    params = {"return_against": r.pr_id}
    sql = """
        SELECT
            ret.name,
            ret.posting_date,
            reti.name AS pri_name,
            reti.qty,
            reti.rate,
            reti.amount
        FROM `tabPurchase Receipt` ret
        INNER JOIN `tabPurchase Receipt Item` reti ON reti.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(return_against)s
        ORDER BY ret.posting_date, ret.name, reti.idx
    """
    return frappe.db.sql(sql, params, as_dict=1)


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
