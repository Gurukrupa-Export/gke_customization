# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

# ── DATA SOURCE MAPPING
#   Tag No            → Repair Order.tag_no        (display field, NOT the document name)
#   Document Name     → Repair Order.name           (actual primary key — used for popups)
#   Customer           → Repair Order.customer_code
#   Entry Date         → Repair Order.order_date
#   Category/SubCateg  → Repair Order.order_details (child table, DocType: "Repair Order Form Detail") → category, subcategory
#   Style Bio          → Repair Order.item
#   Batch No           → Repair Order.serial_and_design_code_order_form
#   Status             → Repair Order.workflow_state
#   Repair Type        → Repair Order.product_type
#   Old BOM            → Repair Order.bom      → BOM.name   (state BEFORE repair)
#   New BOM            → Repair Order.new_bom  → BOM.name   (state AFTER repair)
#   Touch              → Repair Order.metal_touch
#   Gross Wt           → new_bom.gross_weight                       (diff = new - old)
#   Dia Wt             → new_bom.total_diamond_weight_in_gms         (diff = new - old)
#   Stone Wt           → new_bom.total_gemstone_weight_in_gms        (diff = new - old)
#   Other Wt           → new_bom.other_weight                        (diff = new - old)
#   Gold Wt            → new_bom.metal_weight                        (diff = new - old)
#   Chain Wt           → new_bom.finding_weight_                     (diff = new - old)
#   Dia Pcs / Pure Wt / Alloy / Total Loss / Stone Gram / Repair Charges → left blank for now
#
# The "Diff." button in the grid opens a popup (handled in JS) showing a
# material-wise comparison: Prv Wt (old bom) | Diff Wt (new-old) | Weight (new bom)
# for: Metal, Diamond, Stone, Other, Chain.
#
# IMPORTANT: `tag_no` is just a display field on Repair Order — it is NOT
# guaranteed to equal the document's actual `name` (primary key). The popups
# (Detail / Diff buttons) must use the real `name` to fetch the document via
# frappe.client.get, so we expose it as a hidden `docname` column.

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


# ── COLUMNS ───────────────────────────────────────────────────────────────────
def get_columns():
    return [
        {"fieldname": "btn_detail",  "label": _("Detail"), "fieldtype": "Data", "width": 50},
        {"fieldname": "btn_diff",    "label": _("Diff."),  "fieldtype": "Data", "width": 50},

        {"fieldname": "tag_no",     "label": _("Tag No"),     "fieldtype": "Data", "width": 130},
        {"fieldname": "style_bio",  "label": _("Style Bio"),  "fieldtype": "Data", "width": 120},
        {"fieldname": "entry_date", "label": _("Entry Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "category",     "label": _("Category"),     "fieldtype": "Data", "width": 110},
        {"fieldname": "sub_category", "label": _("Sub Category"), "fieldtype": "Data", "width": 110},
        {"fieldname": "customer",  "label": _("Customer"), "fieldtype": "Data", "width": 140},

        {"fieldname": "touch", "label": _("Touch"), "fieldtype": "Data", "width": 70},

        {"fieldname": "gross_wt", "label": _("Gross Wt"), "fieldtype": "Float", "precision": 3, "width": 85},
        {"fieldname": "dia_wt",   "label": _("Dia Wt"),   "fieldtype": "Float", "precision": 3, "width": 78},
        {"fieldname": "dia_pcs",  "label": _("Dia Pcs"),  "fieldtype": "Int",   "width": 70},
        {"fieldname": "stone_wt", "label": _("Stone Wt"), "fieldtype": "Float", "precision": 3, "width": 82},
        {"fieldname": "other_wt", "label": _("Other Wt"), "fieldtype": "Float", "precision": 3, "width": 82},
        {"fieldname": "gold_wt",  "label": _("Gold Wt"),  "fieldtype": "Float", "precision": 3, "width": 78},
        {"fieldname": "chain_wt", "label": _("Chain Wt"), "fieldtype": "Float", "precision": 3, "width": 82},
        {"fieldname": "pure_wt",  "label": _("Pure Wt"),  "fieldtype": "Float", "precision": 3, "width": 78},
        {"fieldname": "alloy",    "label": _("Alloy"),    "fieldtype": "Float", "precision": 3, "width": 72},

        {"fieldname": "batch_no",     "label": _("Batch No"),     "fieldtype": "Data", "width": 110},
        {"fieldname": "status",       "label": _("Status"),       "fieldtype": "Data", "width": 90},
        {"fieldname": "repair_type",  "label": _("Repair Type"),  "fieldtype": "Data", "width": 110},

        {"fieldname": "total_loss",      "label": _("Total Loss"),      "fieldtype": "Float", "precision": 3, "width": 90},
        {"fieldname": "stone_gram",      "label": _("Stone Gram"),      "fieldtype": "Float", "precision": 6, "width": 100},
        {"fieldname": "repair_charges",  "label": _("Repair Charges"),  "fieldtype": "Float", "precision": 2, "width": 110},

        # Hidden helper fields used by JS to open popups
        {"fieldname": "docname",  "label": _("Doc Name"), "fieldtype": "Data", "width": 0, "hidden": 1},
        {"fieldname": "bom",      "label": _("BOM"),      "fieldtype": "Data", "width": 0, "hidden": 1},
        {"fieldname": "new_bom",  "label": _("New BOM"),  "fieldtype": "Data", "width": 0, "hidden": 1},
    ]


# ── DATA ───────────────────────────────────────────────────────────────────────
def get_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql("""
        SELECT
            ''                                              AS btn_detail,
            ''                                              AS btn_diff,
            ro.name                                         AS docname,
            ro.tag_no                                        AS tag_no,
            ro.item                                         AS style_bio,
            ro.order_date                                   AS entry_date,
            (SELECT od.category FROM `tabRepair Order Form Detail` od
                WHERE od.parent = ro.name ORDER BY od.idx ASC LIMIT 1)     AS category,
            (SELECT od.subcategory FROM `tabRepair Order Form Detail` od
                WHERE od.parent = ro.name ORDER BY od.idx ASC LIMIT 1)     AS sub_category,
            ro.customer_code                                AS customer,
            ro.serial_and_design_code_order_form            AS batch_no,
            ro.workflow_state                                AS status,
            ro.product_type                                 AS repair_type,
            ro.bom                                           AS bom,
            ro.new_bom                                       AS new_bom,

            ro.metal_touch                                  AS touch,

            new_bom.gross_weight                            AS gross_wt,
            new_bom.total_diamond_weight_in_gms             AS dia_wt,
            new_bom.total_gemstone_weight_in_gms            AS stone_wt,
            new_bom.other_weight                            AS other_wt,
            new_bom.metal_weight                            AS gold_wt,
            new_bom.finding_weight_                         AS chain_wt,

            (new_bom.gross_weight - old_bom.gross_weight)   AS diff
        FROM
            `tabRepair Order` ro
        LEFT JOIN
            `tabBOM` old_bom ON old_bom.name = ro.bom
        LEFT JOIN
            `tabBOM` new_bom ON new_bom.name = ro.new_bom
        WHERE
            {conditions}
        ORDER BY
            ro.order_date ASC, ro.name ASC
    """.format(conditions=conditions), values, as_dict=True)

    for row in rows:
        # Buttons must carry the real document name (docname), not tag_no,
        # since tag_no is only a display field and may not match `name`.
        row["btn_detail"] = row["docname"]
        row["btn_diff"]   = row["docname"]
        row["diff"]       = flt(row.get("diff") or 0, 3)

        # blank-for-now fields
        row["dia_pcs"]        = None
        row["pure_wt"]        = None
        row["alloy"]          = None
        row["total_loss"]     = None
        row["stone_gram"]     = None
        row["repair_charges"] = None

        # Format touch nicely if numeric (e.g. 92 -> "92 %")
        # if row.get("touch") not in (None, ""):
        #     try:
        #         t = flt(row["touch"])
        #         row["touch"] = "{:.0f} %".format(t * 100 if t <= 1 else t)
        #     except (ValueError, TypeError):
        #         pass

    return rows


# ── CONDITIONS ────────────────────────────────────────────────────────────────
def build_conditions(filters):
    conditions = ["ro.docstatus < 2"]
    values     = {}

    if filters.get("from_date"):
        conditions.append("ro.order_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("ro.order_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("tag_no"):
        conditions.append("ro.tag_no = %(tag_no)s")
        values["tag_no"] = filters["tag_no"]

    if filters.get("party"):
        conditions.append("ro.customer_code = %(party)s")
        values["party"] = filters["party"]

    return " AND ".join(conditions), values