# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

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

        {"label": _("DATE"), "fieldname": "pr_date", "fieldtype": "Date", "width": 95},
        {"label": _("PR IDs"), "fieldname": "pr_id", "fieldtype": "Data", "width": 160},
        {"label": _("Item Code"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("BATCH NO"), "fieldname": "batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("PR QTY"), "fieldname": "pr_qty", "fieldtype": "Float", "width": 90},
        {"label": _("PR RATE"), "fieldname": "pr_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("PR AMOUNT"), "fieldname": "pr_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("PR Status"), "fieldname": "pr_status", "fieldtype": "Data", "width": 110},

        {"label": _("DATE"), "fieldname": "pr_return_date", "fieldtype": "Date", "width": 95},
        {"label": _("PR RETURN ID"), "fieldname": "pr_return_id", "fieldtype": "Data", "width": 160},
        {"label": _("PR RETURN QTY"), "fieldname": "pr_return_qty", "fieldtype": "Float", "width": 100},
        {"label": _("PR RETURN RATE"), "fieldname": "pr_return_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("PR RETURN AMOUNT"), "fieldname": "pr_return_amount", "fieldtype": "Currency", "width": 130},

        {"label": _("DATE"), "fieldname": "pi_date", "fieldtype": "Date", "width": 95},
        {"label": _("PI IDs"), "fieldname": "pi_id", "fieldtype": "Data", "width": 160},
        {"label": _("Item Code"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("BATCH NO"), "fieldname": "batch_no", "fieldtype": "Data", "width": 140},
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

    mr_conditions = ["mr.docstatus = 1", "mr.material_request_type = 'Purchase'"]
    if filters.get("company"):
        mr_conditions.append("mr.company = %(company)s")
    if filters.get("from_date"):
        mr_conditions.append("mr.transaction_date >= %(from_date)s")
    if filters.get("to_date"):
        mr_conditions.append("mr.transaction_date <= %(to_date)s")
    if filters.get("material_request_id"):
        mr_conditions.append("mr.name = %(material_request_id)s")
    if filters.get("item"):
        mr_conditions.append("mri.item_code = %(item)s")

    if filters.get("po_id"):
        mr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Order Item` poi
                INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
                WHERE poi.material_request = mr.name
                  AND poi.material_request_item = mri.name
                  AND po.name = %(po_id)s
                  AND po.docstatus = 1
            )
        """)

    if filters.get("pr_id"):
        mr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Receipt Item` pri
                INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
                WHERE pri.purchase_order_item IN (
                    SELECT poi.name
                    FROM `tabPurchase Order Item` poi
                    WHERE poi.material_request = mr.name
                      AND poi.material_request_item = mri.name
                )
                  AND pr.name = %(pr_id)s
                  AND pr.docstatus = 1
                  AND IFNULL(pr.is_return, 0) = 0
            )
        """)

    if filters.get("batch_no"):
        mr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Receipt Item` pri
                INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
                WHERE pri.purchase_order_item IN (
                    SELECT poi.name
                    FROM `tabPurchase Order Item` poi
                    WHERE poi.material_request = mr.name
                      AND poi.material_request_item = mri.name
                )
                  AND pri.batch_no = %(batch_no)s
                  AND pr.docstatus = 1
                  AND IFNULL(pr.is_return, 0) = 0
            )
        """)

    if filters.get("pi_id"):
        mr_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabPurchase Invoice Item` pii
                INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                WHERE pi.name = %(pi_id)s
                  AND pi.docstatus = 1
                  AND (
                      pii.po_detail IN (
                          SELECT poi.name
                          FROM `tabPurchase Order Item` poi
                          WHERE poi.material_request = mr.name
                            AND poi.material_request_item = mri.name
                      )
                      OR pii.pr_detail IN (
                          SELECT pri.name
                          FROM `tabPurchase Receipt Item` pri
                          WHERE pri.purchase_order_item IN (
                              SELECT poi.name
                              FROM `tabPurchase Order Item` poi
                              WHERE poi.material_request = mr.name
                                AND poi.material_request_item = mri.name
                          )
                      )
                  )
            )
        """)

    mr_items = frappe.db.sql(f"""
        SELECT
            mr.transaction_date AS mr_date,
            mr.name AS material_request_id,
            mri.name AS mri_name,
            mri.item_code AS item,
            mri.qty AS qty,
            mri.schedule_date AS required_by
        FROM `tabMaterial Request` mr
        INNER JOIN `tabMaterial Request Item` mri
            ON mri.parent = mr.name
        WHERE {" AND ".join(mr_conditions)}
        ORDER BY mr.transaction_date DESC, mr.name DESC, mri.idx ASC
    """, params, as_dict=1)

    rows = []
    totals = {
        "mr_qty": 0,
        "po_qty": 0, "po_amount": 0,
        "pr_qty": 0, "pr_amount": 0,
        "pr_return_qty": 0, "pr_return_amount": 0,
        "pi_qty": 0, "pi_amount": 0,
        "difference_pr_vs_pi": 0,
        "difference_rate_pr_vs_pi": 0,
        "difference_amount_pr_vs_pi": 0,
    }

    seen_mr = set()
    seen_po = set()
    seen_pi = set()
    seen_rows = set()
    seen_pr_total_rows = set()
    seen_pr_return_total_rows = set()

    for mr_item in mr_items:
        if mr_item.mri_name not in seen_mr:
            seen_mr.add(mr_item.mri_name)
            totals["mr_qty"] += mr_item.qty or 0

        rfqs = frappe.db.sql("""
            SELECT DISTINCT
                rfq.name,
                rfq.status,
                DATE(rfq.creation) AS creation_date
            FROM `tabRequest for Quotation Item` rfqi
            INNER JOIN `tabRequest for Quotation` rfq ON rfq.name = rfqi.parent
            WHERE rfqi.material_request = %(mr)s
              AND rfqi.material_request_item = %(mri)s
              AND rfq.docstatus = 1
            ORDER BY rfq.creation
        """, {"mr": mr_item.material_request_id, "mri": mr_item.mri_name}, as_dict=1)

        rfq_status = ", ".join(sorted({d.status for d in rfqs if d.status})) if rfqs else ""
        rfq_id = ", ".join([d.name for d in rfqs]) if rfqs else ""
        rfq_creation_date = rfqs[0].creation_date if rfqs else None

        po_conditions = ["poi.material_request = %(mr)s", "poi.material_request_item = %(mri)s", "po.docstatus = 1"]
        if filters.get("po_id"):
            po_conditions.append("po.name = %(po_id)s")
        if filters.get("batch_no"):
            po_conditions.append("""
                EXISTS (
                    SELECT 1
                    FROM `tabPurchase Receipt Item` pri_x
                    INNER JOIN `tabPurchase Receipt` pr_x ON pr_x.name = pri_x.parent
                    WHERE pri_x.purchase_order_item = poi.name
                      AND pri_x.batch_no = %(batch_no)s
                      AND IFNULL(pr_x.is_return, 0) = 0
                )
            """)

        po_list = frappe.db.sql(f"""
            SELECT DISTINCT
                po.name,
                po.status,
                po.transaction_date,
                poi.qty,
                poi.rate,
                poi.amount,
                poi.name AS poi_name
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
            WHERE {" AND ".join(po_conditions)}
            ORDER BY po.transaction_date, po.name
        """, {**params, "mr": mr_item.material_request_id, "mri": mr_item.mri_name}, as_dict=1)

        for po in po_list:
            if po.name not in seen_po:
                seen_po.add(po.name)
                totals["po_qty"] += po.qty or 0
                totals["po_amount"] += po.amount or 0

            pr_conditions = [
                "pri.purchase_order_item = %(poi_name)s",
                "pr.docstatus = 1",
                "IFNULL(pr.is_return, 0) = 0"
            ]
            if filters.get("pr_id"):
                pr_conditions.append("pr.name = %(pr_id)s")
            if filters.get("batch_no"):
                pr_conditions.append("pri.batch_no = %(batch_no)s")

            pr_list = frappe.db.sql(f"""
                SELECT
                    pr.name,
                    pr.status,
                    pr.posting_date,
                    pri.name AS pri_name,
                    pri.batch_no,
                    pri.qty,
                    pri.rate,
                    pri.amount
                FROM `tabPurchase Receipt Item` pri
                INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
                WHERE {" AND ".join(pr_conditions)}
                ORDER BY pr.posting_date, pr.name, pri.idx
            """, {**params, "poi_name": po.poi_name}, as_dict=1)

            for pr in pr_list:
                pr_total_key = (pr.pri_name, pr.batch_no)
                if pr_total_key not in seen_pr_total_rows:
                    seen_pr_total_rows.add(pr_total_key)
                    totals["pr_qty"] += pr.qty or 0
                    totals["pr_amount"] += pr.amount or 0

                pi_rows = get_pi_rows(filters, po, pr)
                pr_return_rows = get_pr_return_rows(filters, pr)

                if not pi_rows:
                    pi_rows = [{
                        "name": "",
                        "status": "",
                        "posting_date": None,
                        "qty": 0,
                        "rate": 0,
                        "amount": 0,
                    }]

                if not pr_return_rows:
                    pr_return_rows = [{
                        "name": "",
                        "posting_date": None,
                        "qty": 0,
                        "rate": 0,
                        "amount": 0,
                    }]

                for ret in pr_return_rows:
                    if ret.get("name"):
                        ret_total_key = (ret.get("pri_name"), ret.get("batch_no"), ret.get("name"))
                        if ret_total_key not in seen_pr_return_total_rows:
                            seen_pr_return_total_rows.add(ret_total_key)
                            totals["pr_return_qty"] += abs(ret.get("qty") or 0)
                            totals["pr_return_amount"] += abs(ret.get("amount") or 0)

                    for pi in pi_rows:
                        if pi.get("name") and pi.name not in seen_pi:
                            seen_pi.add(pi.name)
                            totals["pi_qty"] += pi.qty or 0
                            totals["pi_amount"] += pi.amount or 0

                        row_key = (
                            mr_item.material_request_id,
                            po.name,
                            pr.name,
                            pr.pri_name,
                            pr.batch_no,
                            ret.get("name") or "",
                            pi.get("name") or "",
                        )

                        if row_key in seen_rows:
                            continue
                        seen_rows.add(row_key)

                        difference_pr_vs_pi = (pr.qty or 0) - (abs(ret.get("qty") or 0)) - (pi.get("qty") or 0)
                        difference_rate_pr_vs_pi = (pr.rate or 0) - (abs(ret.get("rate") or 0)) - (pi.get("rate") or 0)
                        difference_amount_pr_vs_pi = (pr.amount or 0) - (abs(ret.get("amount") or 0)) - (pi.get("amount") or 0)

                        rows.append({
                            "mr_date": mr_item.mr_date,
                            "material_request_id": mr_item.material_request_id,
                            "item": mr_item.item,
                            "qty": mr_item.qty,

                            "rfq_creation_date": rfq_creation_date,
                            "rfq_id": rfq_id,
                            "rfq_status": rfq_status,

                            "po_date": po.transaction_date,
                            "po_ids": po.name,
                            "po_qty": po.qty,
                            "po_rate": po.rate,
                            "po_amount": po.amount,
                            "po_status": po.status,

                            "pr_date": pr.posting_date,
                            "pr_id": pr.name,
                            "batch_no": pr.batch_no,
                            "pr_qty": pr.qty,
                            "pr_rate": pr.rate,
                            "pr_amount": pr.amount,
                            "pr_status": pr.status,

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

                            "difference_pr_vs_pi": difference_pr_vs_pi,
                            "difference_rate_pr_vs_pi": difference_rate_pr_vs_pi,
                            "difference_amount_pr_vs_pi": difference_amount_pr_vs_pi,
                        })

    totals["difference_pr_vs_pi"] = (totals["pr_qty"] - totals["pr_return_qty"]) - totals["pi_qty"]
    totals["difference_amount_pr_vs_pi"] = (totals["pr_amount"] - totals["pr_return_amount"]) - totals["pi_amount"]

    return rows, totals


def get_pi_rows(filters, po, pr):
    params = {
        "poi_name": po.poi_name,
        "pri_name": pr.pri_name,
    }

    pi_filter_sql = ""
    if filters.get("pi_id"):
        pi_filter_sql = " AND pi.name = %(pi_id)s "
        params["pi_id"] = filters.get("pi_id")

    pr_linked = frappe.db.sql(f"""
        SELECT DISTINCT
            pi.name,
            pi.status,
            pi.posting_date,
            pii.qty,
            pii.rate,
            pii.amount
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pii.pr_detail = %(pri_name)s
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)

    if pr_linked:
        return pr_linked

    po_linked = frappe.db.sql(f"""
        SELECT DISTINCT
            pi.name,
            pi.status,
            pi.posting_date,
            pii.qty,
            pii.rate,
            pii.amount
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pii.po_detail = %(poi_name)s
          AND (pii.pr_detail IS NULL OR pii.pr_detail = '')
          {pi_filter_sql}
        ORDER BY pi.posting_date, pi.name, pii.idx
    """, params, as_dict=1)

    return po_linked


def get_pr_return_rows(filters, pr):
    params = {"return_against": pr.name}

    pr_return_filter = ""
    if filters.get("from_date"):
        pr_return_filter += " AND ret.posting_date >= %(from_date)s "
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        pr_return_filter += " AND ret.posting_date <= %(to_date)s "
        params["to_date"] = filters.get("to_date")

    return frappe.db.sql(f"""
        SELECT
            ret.name,
            ret.posting_date,
            reti.name AS pri_name,
            reti.batch_no,
            reti.qty,
            reti.rate,
            reti.amount
        FROM `tabPurchase Receipt` ret
        INNER JOIN `tabPurchase Receipt Item` reti ON reti.parent = ret.name
        WHERE ret.docstatus = 1
          AND IFNULL(ret.is_return, 0) = 1
          AND ret.return_against = %(return_against)s
          {pr_return_filter}
        ORDER BY ret.posting_date, ret.name, reti.idx
    """, params, as_dict=1)


def get_total_row(totals):
    return {
        "mr_date": _("Total"),
        "material_request_id": "",
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
