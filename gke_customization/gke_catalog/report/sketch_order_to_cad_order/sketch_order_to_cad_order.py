# Copyright (c) 2026, Gurukrupa Export Private Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"fieldname": "sketch_order_id", "label": _("Sketch Order ID"), "fieldtype": "Link", "options": "Sketch Order", "width": 150},
        {"fieldname": "sketch_order_form_id", "label": _("Sketch Order Form ID"), "fieldtype": "Link", "options": "Sketch Order Form", "width": 180},
        {"fieldname": "qty", "label": _("Qty"), "fieldtype": "Int", "width": 80},
        {"fieldname": "docstatus", "label": _("Doc Status"), "fieldtype": "Data", "width": 100},
        {"fieldname": "customer_code", "label": _("Customer Code"), "fieldtype": "Link", "options": "Customer", "width": 120},
        {"fieldname": "order_date", "label": _("Sketch Order Date"), "fieldtype": "Date", "width": 160},
        {"fieldname": "delivery_date", "label": _("Sketch Delivery Date"), "fieldtype": "Date", "width": 160},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_category", "label": _("Item Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "item_sub_category", "label": _("Item Sub Category"), "fieldtype": "Data", "width": 150},
        {"fieldname": "customer_po_number", "label": _("Customer PO Number"), "fieldtype": "Data", "width": 150},
        {"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "item_final_sketch_cmo", "label": _("Item (Final Sketch Approval CMO)"), "fieldtype": "Data", "width": 180},
        {"fieldname": "diamond_wt_approx", "label": _("Diamond Wt Approx (CMO)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "gold_wt_approx", "label": _("Gold Wt Approx (CMO)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "designer_final_sketch_cmo", "label": _("Designer (Final Sketch CMO)"), "fieldtype": "Data", "width": 180},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "flow_type", "label": _("Flow Type"), "fieldtype": "Data", "width": 100},
        {"fieldname": "owner", "label": _("Owner"), "fieldtype": "Data", "width": 200},
        {"fieldname": "loc", "label": _("LOC"), "fieldtype": "Data", "width": 120},
        {"fieldname": "order_no", "label": _("Order No"), "fieldtype": "Link", "options": "Order", "width": 150},
        {"fieldname": "order_form_id", "label": _("Order Form ID"), "fieldtype": "Link", "options": "Order", "width": 150},
        {"fieldname": "order_form_date", "label": _("Order Form Date"), "fieldtype": "Datetime", "width": 160},
        {"fieldname": "order_complete_date", "label": _("Order Complete Date"), "fieldtype": "Datetime", "width": 160},
        {"fieldname": "jewelx_style_no", "label": _("Jewelx Style No"), "fieldtype": "Data", "width": 150}
    ]


def get_data(filters=None):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            base.sketch_order_id,
            base.sketch_order_form_id,
            base.qty,
            base.docstatus,
            base.customer_code,
            base.order_date,
            base.delivery_date,
            base.item_code,
            base.item_category,
            base.item_sub_category,
            base.customer_po_number,
            base.supplier_name,
            base.branch,
            base.flow_type,
            base.loc,
            base.owner,
            base.jewelx_style_no,
            fsa.item                    AS item_final_sketch_cmo,
            fsa.diamond_wt_approx       AS diamond_wt_approx,
            fsa.gold_wt_approx          AS gold_wt_approx,
            fsa.designer                AS designer_final_sketch_cmo,
            ord_data.order_no,
            ord_data.order_form_id,
            ord_data.order_form_date,
            ord_data.order_complete_date
        FROM (
            SELECT
                so.name                                                         AS sketch_order_id,
                so.sketch_order_form                                            AS sketch_order_form_id,
                item_counts.qty,
                CASE
                    WHEN so.docstatus = 0 THEN 'Draft'
                    WHEN so.docstatus = 1 THEN 'Approved'
                    WHEN so.docstatus = 2 THEN 'Cancelled'
                    ELSE 'Unknown'
                END                                                             AS docstatus,
                so.customer_code,
                DATE(so.order_date)                                             AS order_date,
                DATE(so.delivery_date)                                          AS delivery_date,
                COALESCE(NULLIF(i.variant_of, ''), i.name, so.item_code)       AS item_code,
                COALESCE(NULLIF(i.variant_of, ''), i.name, so.item_code)       AS template_item,
                so.category                                                     AS item_category,
                COALESCE(i.item_subcategory, so.subcategory)                   AS item_sub_category,
                so.po_no                                                        AS customer_po_number,
                so.supplier_name,
                so.branch,
                so.flow_type,
                so.order_type                                                   AS loc,
                COALESCE(u.full_name, u.first_name, so.owner)                  AS owner,
                i.stylebio                                                      AS jewelx_style_no,
                so.creation
            FROM `tabSketch Order` so
            LEFT JOIN `tabItem` i
                ON i.custom_sketch_order_id = so.name
            LEFT JOIN `tabUser` u
                ON u.name = so.owner
            LEFT JOIN (
                SELECT
                    custom_sketch_order_id,
                    COUNT(DISTINCT COALESCE(NULLIF(variant_of, ''), name)) AS qty
                FROM `tabItem`
                GROUP BY custom_sketch_order_id
            ) item_counts
                ON item_counts.custom_sketch_order_id = so.name
            WHERE so.workflow_state = 'Approved'
              AND so.docstatus = 1
            {conditions}
            GROUP BY so.name, COALESCE(NULLIF(i.variant_of, ''), i.name, so.item_code)
        ) base
        LEFT JOIN (
            SELECT
                parent,
                item,
                diamond_wt_approx,
                gold_wt_approx,
                designer,
                ROW_NUMBER() OVER (PARTITION BY parent ORDER BY idx ASC) AS rn
            FROM `tabFinal Sketch Approval CMO`
            WHERE parenttype = 'Sketch Order'
        ) fsa
            ON fsa.parent = base.sketch_order_id
            AND fsa.rn = 1
        LEFT JOIN (
            SELECT
                i2.custom_sketch_order_id,
                COALESCE(NULLIF(i2.variant_of, ''), i2.name)   AS template_item,
                ord.name                                        AS order_no,
                ord.cad_order_form                              AS order_form_id,
                ord.order_date                                  AS order_form_date,
                ord.delivery_date                               AS order_complete_date,
                ROW_NUMBER() OVER (
                    PARTITION BY i2.custom_sketch_order_id, COALESCE(NULLIF(i2.variant_of, ''), i2.name)
                    ORDER BY ord.order_date ASC
                ) AS rn
            FROM `tabItem` i2
            INNER JOIN `tabOrder` ord
                ON ord.item = i2.name
                AND ord.design_type = 'Sketch Design'
            WHERE i2.custom_sketch_order_id IS NOT NULL
        ) ord_data
            ON ord_data.custom_sketch_order_id = base.sketch_order_id
            AND ord_data.template_item = base.template_item
            AND ord_data.rn = 1
        ORDER BY base.creation DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)
    return data


def get_conditions(filters):
    conditions = []

    if filters.get("from_date"):
        conditions.append("DATE(so.order_date) >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("DATE(so.order_date) <= %(to_date)s")
    if filters.get("sketch_order_id"):
        conditions.append("so.name = %(sketch_order_id)s")
    if filters.get("order_form_id"):
        conditions.append("""
            EXISTS (
                SELECT 1 FROM `tabOrder` ord_f
                INNER JOIN `tabItem` i_f ON i_f.name = ord_f.item
                WHERE i_f.custom_sketch_order_id = so.name
                AND ord_f.cad_order_form = %(order_form_id)s
            )
        """)
    if filters.get("order_type"):
        conditions.append("so.order_type = %(order_type)s")

    return " AND " + " AND ".join(conditions) if conditions else ""
