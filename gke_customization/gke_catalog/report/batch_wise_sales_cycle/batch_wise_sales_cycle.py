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
        {"label": _("SO Date"), "fieldname": "so_date", "fieldtype": "Date", "width": 95},
        {"label": _("SO ID"), "fieldname": "so_id", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("SO Item Code"), "fieldname": "so_item_code", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("SO Batch"), "fieldname": "so_batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("SO Qty"), "fieldname": "so_qty", "fieldtype": "Float", "width": 90},
        {"label": _("SO Rate"), "fieldname": "so_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("SO Amount"), "fieldname": "so_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("SO Status"), "fieldname": "so_status", "fieldtype": "Data", "width": 110},

        {"label": _("DN Date"), "fieldname": "dn_date", "fieldtype": "Date", "width": 95},
        {"label": _("DN ID"), "fieldname": "dn_id", "fieldtype": "Link", "options": "Delivery Note", "width": 150},
        {"label": _("DN Item Code"), "fieldname": "dn_item_code", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("DN Batch"), "fieldname": "dn_batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("DN Qty"), "fieldname": "dn_qty", "fieldtype": "Float", "width": 90},
        {"label": _("DN Rate"), "fieldname": "dn_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("DN Amount"), "fieldname": "dn_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("DN Status"), "fieldname": "dn_status", "fieldtype": "Data", "width": 110},

        {"label": _("SI Date"), "fieldname": "si_date", "fieldtype": "Date", "width": 95},
        {"label": _("SI ID"), "fieldname": "si_id", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("SI Item Code"), "fieldname": "si_item_code", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("SI Batch"), "fieldname": "si_batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("SI Qty"), "fieldname": "si_qty", "fieldtype": "Float", "width": 90},
        {"label": _("SI Rate"), "fieldname": "si_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("SI Amount"), "fieldname": "si_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("SI Status"), "fieldname": "si_status", "fieldtype": "Data", "width": 110},

        {"label": _("SI RET Date"), "fieldname": "si_ret_date", "fieldtype": "Date", "width": 95},
        {"label": _("SI RET ID"), "fieldname": "si_ret_id", "fieldtype": "Data", "width": 160},
        {"label": _("SI RET Item Code"), "fieldname": "si_ret_item_code", "fieldtype": "Link", "options": "Item", "width": 170},
        {"label": _("SI RET Batch"), "fieldname": "si_ret_batch_no", "fieldtype": "Data", "width": 140},
        {"label": _("SI RET Qty"), "fieldname": "si_ret_qty", "fieldtype": "Float", "width": 90},
        {"label": _("SI RET Rate"), "fieldname": "si_ret_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("SI RET Amount"), "fieldname": "si_ret_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("SI RET Status"), "fieldname": "si_ret_status", "fieldtype": "Data", "width": 110},

        {"label": _("DN-SI DIFF QTY"), "fieldname": "dn_si_diff_qty", "fieldtype": "Float", "width": 120},
        {"label": _("DN-SI DIFF RATE"), "fieldname": "dn_si_diff_rate", "fieldtype": "Currency", "width": 130},
        {"label": _("DN-SI DIFF AMOUNT"), "fieldname": "dn_si_diff_amount", "fieldtype": "Currency", "width": 140},
    ]


def get_data(filters):
    params = dict(filters)

    so_conditions = ["so.docstatus = 1", "IFNULL(soi.batch_no, '') != ''"]

    if filters.get("company"):
        so_conditions.append("so.company = %(company)s")

    if filters.get("from_date"):
        so_conditions.append("so.transaction_date >= %(from_date)s")

    if filters.get("to_date"):
        so_conditions.append("so.transaction_date <= %(to_date)s")

    if filters.get("sales_order"):
        so_conditions.append("so.name = %(sales_order)s")

    if filters.get("batch_no"):
        so_conditions.append("soi.batch_no = %(batch_no)s")

    if filters.get("item_code"):
        so_conditions.append("soi.item_code = %(item_code)s")

    if filters.get("customer"):
        so_conditions.append("so.customer = %(customer)s")

    if filters.get("delivery_note"):
        so_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabDelivery Note Item` dni_f
                INNER JOIN `tabDelivery Note` dn_f ON dn_f.name = dni_f.parent
                WHERE dni_f.so_detail = soi.name
                  AND dni_f.parent = %(delivery_note)s
                  AND dn_f.docstatus = 1
                  AND IFNULL(dn_f.is_return, 0) = 0
            )
        """)

    if filters.get("sales_invoice"):
        so_conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabSales Invoice Item` sii_f
                INNER JOIN `tabSales Invoice` si_f ON si_f.name = sii_f.parent
                WHERE sii_f.so_detail = soi.name
                  AND sii_f.parent = %(sales_invoice)s
                  AND si_f.docstatus = 1
                  AND IFNULL(si_f.is_return, 0) = 0
            )
        """)

    rows = frappe.db.sql(f"""
        SELECT
            so.transaction_date AS so_date,
            so.name AS so_id,
            soi.item_code AS so_item_code,
            soi.batch_no AS so_batch_no,
            soi.qty AS so_qty,
            soi.rate AS so_rate,
            soi.amount AS so_amount,
            so.status AS so_status,

            dn_link.dn_date,
            dn_link.dn_id,
            dn_link.dn_item_code,
            dn_link.dn_batch_no,
            dn_link.dn_qty,
            dn_link.dn_rate,
            dn_link.dn_amount,
            dn_link.dn_status,

            si_link.si_date,
            si_link.si_id,
            si_link.si_item_code,
            si_link.si_batch_no,
            si_link.si_qty,
            si_link.si_rate,
            si_link.si_amount,
            si_link.si_status,

            ret_link.si_ret_date,
            ret_link.si_ret_id,
            ret_link.si_ret_item_code,
            ret_link.si_ret_batch_no,
            ret_link.si_ret_qty,
            ret_link.si_ret_rate,
            ret_link.si_ret_amount,
            ret_link.si_ret_status,

            (IFNULL(dn_link.dn_qty, 0) - IFNULL(si_link.si_qty, 0)) AS dn_si_diff_qty,
            (IFNULL(dn_link.dn_rate, 0) - IFNULL(si_link.si_rate, 0)) AS dn_si_diff_rate,
            (IFNULL(dn_link.dn_amount, 0) - IFNULL(si_link.si_amount, 0)) AS dn_si_diff_amount,

            soi.name AS so_row_name

        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so
            ON so.name = soi.parent

        LEFT JOIN (
            SELECT
                dni.so_detail,
                dni.batch_no,
                dn.posting_date AS dn_date,
                dn.name AS dn_id,
                dni.item_code AS dn_item_code,
                dni.batch_no AS dn_batch_no,
                dni.qty AS dn_qty,
                dni.rate AS dn_rate,
                dni.amount AS dn_amount,
                dn.status AS dn_status
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn
                ON dn.name = dni.parent
            WHERE dn.docstatus = 1
              AND IFNULL(dn.is_return, 0) = 0
        ) dn_link
            ON dn_link.so_detail = soi.name
           AND dn_link.batch_no = soi.batch_no

        LEFT JOIN (
            SELECT
                sii.so_detail,
                sii.batch_no,
                si.posting_date AS si_date,
                si.name AS si_id,
                sii.item_code AS si_item_code,
                sii.batch_no AS si_batch_no,
                sii.qty AS si_qty,
                sii.rate AS si_rate,
                sii.amount AS si_amount,
                si.status AS si_status
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE si.docstatus = 1
              AND IFNULL(si.is_return, 0) = 0
        ) si_link
            ON si_link.so_detail = soi.name
           AND si_link.batch_no = soi.batch_no

        LEFT JOIN (
            SELECT
                cni.batch_no AS si_ret_batch_no,
                cni.item_code AS si_ret_item_code,
                MAX(cn.posting_date) AS si_ret_date,
                GROUP_CONCAT(DISTINCT cn.name ORDER BY cn.posting_date SEPARATOR ', ') AS si_ret_id,
                ABS(SUM(COALESCE(cni.qty, 0))) AS si_ret_qty,
                CASE
                    WHEN ABS(SUM(COALESCE(cni.qty, 0))) > 0
                    THEN ABS(SUM(COALESCE(cni.amount, 0))) / ABS(SUM(COALESCE(cni.qty, 0)))
                    ELSE 0
                END AS si_ret_rate,
                ABS(SUM(COALESCE(cni.amount, 0))) AS si_ret_amount,
                'Return' AS si_ret_status
            FROM `tabSales Invoice Item` cni
            INNER JOIN `tabSales Invoice` cn
                ON cn.name = cni.parent
            WHERE cn.docstatus = 1
              AND IFNULL(cn.is_return, 0) = 1
              AND IFNULL(cni.batch_no, '') != ''
            GROUP BY cni.batch_no, cni.item_code
        ) ret_link
            ON ret_link.si_ret_batch_no = soi.batch_no
           AND ret_link.si_ret_item_code = soi.item_code

        WHERE {" AND ".join(so_conditions)}
        ORDER BY so.transaction_date DESC, so.name DESC, soi.idx ASC
    """, params, as_dict=1)

    data = []
    totals = {
        "so_qty": 0, "so_amount": 0,
        "dn_qty": 0, "dn_amount": 0,
        "si_qty": 0, "si_amount": 0,
        "si_ret_qty": 0, "si_ret_amount": 0,
        "dn_si_diff_qty": 0,
        "dn_si_diff_rate": 0,
        "dn_si_diff_amount": 0,
    }

    seen_so = set()
    seen_dn = set()
    seen_si = set()
    seen_ret = set()

    for row in rows:
        so_key = row.get("so_row_name")
        if so_key and so_key not in seen_so:
            seen_so.add(so_key)
            totals["so_qty"] += row.get("so_qty") or 0
            totals["so_amount"] += row.get("so_amount") or 0

        dn_key = (row.get("dn_id"), row.get("dn_batch_no"), row.get("dn_item_code"))
        if row.get("dn_id") and dn_key not in seen_dn:
            seen_dn.add(dn_key)
            totals["dn_qty"] += row.get("dn_qty") or 0
            totals["dn_amount"] += row.get("dn_amount") or 0

        si_key = (row.get("si_id"), row.get("si_batch_no"), row.get("si_item_code"))
        if row.get("si_id") and si_key not in seen_si:
            seen_si.add(si_key)
            totals["si_qty"] += row.get("si_qty") or 0
            totals["si_amount"] += row.get("si_amount") or 0

        ret_key = (row.get("si_ret_id"), row.get("si_ret_batch_no"), row.get("si_ret_item_code"))
        if row.get("si_ret_id") and ret_key not in seen_ret:
            seen_ret.add(ret_key)
            totals["si_ret_qty"] += row.get("si_ret_qty") or 0
            totals["si_ret_amount"] += row.get("si_ret_amount") or 0

        totals["dn_si_diff_qty"] += row.get("dn_si_diff_qty") or 0
        totals["dn_si_diff_rate"] += row.get("dn_si_diff_rate") or 0
        totals["dn_si_diff_amount"] += row.get("dn_si_diff_amount") or 0

        row.pop("so_row_name", None)
        data.append(row)

    return data, totals


def get_total_row(totals):
    return {
        "so_date": None,
        "so_id": _("Total"),
        "so_item_code": "",
        "so_batch_no": "",
        "so_qty": totals["so_qty"],
        "so_rate": "",
        "so_amount": totals["so_amount"],
        "so_status": "",

        "dn_date": None,
        "dn_id": "",
        "dn_item_code": "",
        "dn_batch_no": "",
        "dn_qty": totals["dn_qty"],
        "dn_rate": "",
        "dn_amount": totals["dn_amount"],
        "dn_status": "",

        "si_date": None,
        "si_id": "",
        "si_item_code": "",
        "si_batch_no": "",
        "si_qty": totals["si_qty"],
        "si_rate": "",
        "si_amount": totals["si_amount"],
        "si_status": "",

        "si_ret_date": None,
        "si_ret_id": "",
        "si_ret_item_code": "",
        "si_ret_batch_no": "",
        "si_ret_qty": totals["si_ret_qty"],
        "si_ret_rate": "",
        "si_ret_amount": totals["si_ret_amount"],
        "si_ret_status": "",

        "dn_si_diff_qty": totals["dn_si_diff_qty"],
        "dn_si_diff_rate": totals["dn_si_diff_rate"],
        "dn_si_diff_amount": totals["dn_si_diff_amount"],
        "is_total_row": 1,
    }
