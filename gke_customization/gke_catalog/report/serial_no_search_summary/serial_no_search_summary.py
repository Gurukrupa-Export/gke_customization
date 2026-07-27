# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Serial No"), "fieldname": "tag_no", "fieldtype": "Data", "width": 140},
        {"label": _("Material"), "fieldname": "material", "fieldtype": "Data", "width": 120},
        {"label": _("Shape"), "fieldname": "shape", "fieldtype": "Data", "width": 120},
        {"label": _("Quality"), "fieldname": "purity", "fieldtype": "Data", "width": 130},
        {"label": _("Size"), "fieldname": "size", "fieldtype": "Data", "width": 110},
        # {"label": _("Code"), "fieldname": "code", "fieldtype": "Data", "width": 110},
        {"label": _("Pcs"), "fieldname": "pcs", "fieldtype": "Int", "width": 80, "precision": 3},
        {"label": _("Touch Wt"), "fieldname": "weight", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": _("Pure Wt"), "fieldname": "pure_weight", "fieldtype": "Float", "width": 110, "precision": 3},
        {"label": _("Cust Pcs"), "fieldname": "cust_pcs", "fieldtype": "Int", "width": 90, "precision": 3},
        {"label": _("Cust Weight"), "fieldname": "cust_weight", "fieldtype": "Float", "width": 110, "precision": 3},
    ]


def get_data(filters):
    if filters.get("search_mode") == "Single":
        serial_no = (filters.get("serial_no") or "").strip()
        tokens = [serial_no] if serial_no else []
    else:
        search_text = (filters.get("search_text") or "").strip()
        tokens = parse_search_tokens(search_text)

    if not tokens:
        return []

    serial_rows = get_target_serials(tokens)
    if not serial_rows:
        return []

    item_codes = list({d.item_code for d in serial_rows if d.item_code})
    fallback_bom_map = get_default_bom_map(item_codes)

    data = []

    for sr in serial_rows:
        bom_no = sr.custom_bom_no or fallback_bom_map.get(sr.item_code)
        component_rows = get_component_rows_for_bom(bom_no)

        if not component_rows:
            component_rows = [{
                "material": "",
                "shape": "",
                "purity": "",
                "size": "",
                "code": "",
                "pcs": 0,
                "weight": 0,
                "pure_weight": 0,
                "cust_pcs": 0,
                "cust_weight": 0,
                "_sort_weight": 0,
            }]

        component_rows = sorted(
            component_rows,
            key=lambda d: (flt0(d.get("_sort_weight", d.get("weight"))), d.get("material") or ""),
            reverse=True
        )

        first_row = True
        for row in component_rows:
            data.append({
                "tag_no": sr.name if first_row else "",
                "material": row.get("material", ""),
                "shape": row.get("shape", ""),
                "purity": row.get("purity", ""),
                "size": row.get("size", ""),
                "code": row.get("code", ""),
                "pcs": flt0(row.get("pcs")),
                "weight": flt0(row.get("weight")),
                "pure_weight": flt0(row.get("pure_weight")),
                "cust_pcs": flt0(row.get("cust_pcs")),
                "cust_weight": flt0(row.get("cust_weight")),
            })
            first_row = False

    return data


def parse_search_tokens(search_text):
    if not search_text:
        return []

    parts = re.split(r"[\n\r\t,; ]+", search_text.strip())
    out = []
    seen = set()

    for part in parts:
        token = cstr0(part).strip()
        if token and token not in seen:
            out.append(token)
            seen.add(token)

    return out


def get_target_serials(tokens):
    serial_direct = frappe.get_all(
        "Serial No",
        filters={"name": ["in", tokens]},
        fields=["name", "item_code", "custom_bom_no"],
        order_by="name asc"
    )

    serial_from_item = frappe.get_all(
        "Serial No",
        filters={"item_code": ["in", tokens]},
        fields=["name", "item_code", "custom_bom_no"],
        order_by="item_code asc, name asc"
    )

    out = []
    seen = set()

    for row in serial_direct + serial_from_item:
        if row.name not in seen:
            out.append(row)
            seen.add(row.name)

    return out


def get_default_bom_map(item_codes):
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "BOM",
        filters={
            "item": ["in", item_codes],
            "is_active": 1,
            "docstatus": 1
        },
        fields=["name", "item", "is_default"],
        order_by="item asc, is_default desc, modified desc"
    )

    bom_map = {}
    for row in rows:
        if row.item not in bom_map:
            bom_map[row.item] = row.name

    return bom_map


def get_component_rows_for_bom(bom_no):
    if not bom_no:
        return []

    rows = []
    rows.extend(get_metal_rows(bom_no))
    rows.extend(get_finding_rows(bom_no))
    rows.extend(get_diamond_rows(bom_no))
    rows.extend(get_gemstone_rows(bom_no))
    rows.extend(get_other_rows(bom_no))
    return rows


def get_metal_rows(bom_no):
    dt = "BOM Metal Detail"
    fields = get_existing_fields(dt, [
        "metal_type", "shape", "metal_touch", "metal_purity", "purity", "purity_percentage",
        "quantity", "actual_quantity", "weight", "net_weight", "is_customer_item"
    ])

    rows = frappe.get_all(
        dt,
        filters={"parent": bom_no, "parenttype": "BOM"},
        fields=fields,
        order_by="idx asc"
    )

    out = []
    for d in rows:
        weight = pick_first(d, ["quantity", "actual_quantity", "weight", "net_weight"])
        purity_percent = pick_first(d, ["purity_percentage"])
        pure_weight = 0
        if weight and purity_percent:
            pure_weight = (flt0(weight) * flt0(purity_percent)) / 100.0

        out.append({
            "material": "Metal",
            "shape": pick_first(d, ["shape", "metal_type"]),
            "purity": pick_first(d, ["metal_touch", "metal_purity", "purity"]),
            "size": "",
            "code": "Metal",
            "pcs": 0,
            "weight": weight,
            "pure_weight": pure_weight,
            "cust_pcs": 0,
            "cust_weight": weight if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "_sort_weight": flt0(weight),
        })

    return out


def get_finding_rows(bom_no):
    dt = "BOM Finding Detail"
    fields = get_existing_fields(dt, [
        "finding_type", "shape", "finding_size", "size", "metal_touch", "metal_purity", "purity",
        "qty", "pcs", "quantity", "actual_quantity", "weight", "net_weight",
        "purity_percentage", "is_customer_item"
    ])

    rows = frappe.get_all(
        dt,
        filters={"parent": bom_no, "parenttype": "BOM"},
        fields=fields,
        order_by="idx asc"
    )

    out = []
    for d in rows:
        pcs = pick_first(d, ["qty", "pcs"])
        weight = pick_first(d, ["quantity", "actual_quantity", "weight", "net_weight"])
        purity_percent = pick_first(d, ["purity_percentage"])
        pure_weight = 0
        if weight and purity_percent:
            pure_weight = (flt0(weight) * flt0(purity_percent)) / 100.0

        out.append({
            "material": "Finding",
            "shape": pick_first(d, ["shape", "finding_type"]),
            "purity": pick_first(d, ["metal_touch", "metal_purity", "purity"]),
            "size": pick_first(d, ["finding_size", "size"]),
            "code": "Finding",
            "pcs": pcs,
            "weight": weight,
            "pure_weight": pure_weight,
            "cust_pcs": pcs if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "cust_weight": weight if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "_sort_weight": flt0(weight),
        })

    return out


def get_diamond_rows(bom_no):
    dt = "BOM Diamond Detail"
    fields = get_existing_fields(dt, [
        "stone_shape", "shape", "quality", "diamond_grade", "purity",
        "diamond_sieve_size", "size_in_mm", "size",
        "pcs", "quantity", "actual_quantity", "weight_in_gms", "weight",
        "is_customer_item"
    ])

    rows = frappe.get_all(
        dt,
        filters={"parent": bom_no, "parenttype": "BOM"},
        fields=fields,
        order_by="idx asc"
    )

    out = []
    for d in rows:
        pcs = pick_first(d, ["pcs"])
        weight = pick_first(d, ["quantity", "weight_in_gms", "weight", "actual_quantity"])

        out.append({
            "material": "Diamond",
            "shape": pick_first(d, ["stone_shape", "shape"]),
            "purity": pick_first(d, ["quality", "diamond_grade", "purity"]),
            "size": cstr0(pick_first(d, ["diamond_sieve_size", "size_in_mm", "size"])),
            "code": "Diamond",
            "pcs": pcs,
            "weight": weight,
            "pure_weight": 0,
            "cust_pcs": pcs if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "cust_weight": weight if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "_sort_weight": flt0(weight),
        })

    return out


def get_gemstone_rows(bom_no):
    dt = "BOM Gemstone Detail"
    fields = get_existing_fields(dt, [
        "stone_shape", "shape", "gemstone_quality", "gemstone_grade", "purity",
        "gemstone_size", "size", "pcs", "quantity", "actual_quantity",
        "weight_in_gms", "weight", "is_customer_item"
    ])

    rows = frappe.get_all(
        dt,
        filters={"parent": bom_no, "parenttype": "BOM"},
        fields=fields,
        order_by="idx asc"
    )

    out = []
    for d in rows:
        pcs = pick_first(d, ["pcs"])
        weight = pick_first(d, ["quantity", "weight_in_gms", "weight", "actual_quantity"])

        out.append({
            "material": "Gemstone",
            "shape": pick_first(d, ["stone_shape", "shape"]),
            "purity": pick_first(d, ["gemstone_quality", "gemstone_grade", "purity"]),
            "size": pick_first(d, ["gemstone_size", "size"]),
            "code": "Gemstone",
            "pcs": pcs,
            "weight": weight,
            "pure_weight": 0,
            "cust_pcs": pcs if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "cust_weight": weight if cint0(pick_first(d, ["is_customer_item"])) else 0,
            "_sort_weight": flt0(weight),
        })

    return out


def get_other_rows(bom_no):
    return []


def get_existing_fields(doctype, wanted_fields):
    meta = frappe.get_meta(doctype)
    available = {"name", "parent", "parenttype", "parentfield", "idx", "owner", "creation", "modified", "modified_by", "docstatus"}
    for df in meta.fields:
        available.add(df.fieldname)
    return [f for f in wanted_fields if f in available]


def pick_first(row, fieldnames):
    for fieldname in fieldnames:
        if fieldname in row and row.get(fieldname) not in (None, ""):
            return row.get(fieldname)
    return ""


def flt0(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def cint0(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def cstr0(value):
    if value is None:
        return ""
    return str(value)