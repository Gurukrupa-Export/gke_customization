# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    if not filters:
        filters = {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Shape"), "fieldname": "shape", "fieldtype": "Data", "width": 120},
        {"label": _("Purity"), "fieldname": "purity", "fieldtype": "Data", "width": 100},
        {"label": _("Size"), "fieldname": "size", "fieldtype": "Data", "width": 120},
        {"label": _("Pending Wt"), "fieldname": "pending_wt", "fieldtype": "Float", "width": 120, "precision": 3},
        {"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    company = filters.get("company")
    branch = filters.get("branch")
    from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
    to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

    warehouse_names = get_branch_warehouses(company, branch)

    if not warehouse_names:
        frappe.msgprint(_("No warehouses found for the selected Company/Branch."), alert=True)
        return []

    item_codes = get_diamond_variant_items()
    if not item_codes:
        return []

    item_attrs = get_item_attributes(item_codes)

    all_lots_by_item = get_all_inbound_lots_by_item(item_codes, warehouse_names, company)

    tagged_qty_map = get_tagged_qty_map(item_codes, company=company)
    returned_qty_map = get_purchase_return_qty_map(item_codes, warehouse_names, company=company)
    sales_qty_map = get_sales_qty_map(item_codes, company=company)
    material_issue_map = get_material_issue_qty_map(item_codes, warehouse_names, company=company)
    process_loss_map = get_process_loss_qty_map(item_codes, warehouse_names, company=company)
    cgi_map = get_customer_goods_issue_qty_map(item_codes, warehouse_names, company=company)

    total_deduction_map = {}
    for item_code in item_codes:
        total_deduction_map[item_code] = (
            tagged_qty_map.get(item_code, 0.0)
            + returned_qty_map.get(item_code, 0.0)
            + sales_qty_map.get(item_code, 0.0)
            + material_issue_map.get(item_code, 0.0)
            + process_loss_map.get(item_code, 0.0)
            + cgi_map.get(item_code, 0.0)
        )

    pending_by_lot = {}
    for item_code, lots in all_lots_by_item.items():
        remaining_to_deduct = total_deduction_map.get(item_code, 0.0)
        for lot in lots:
            lot_qty = flt(lot.qty)
            if remaining_to_deduct > 0:
                deduct_here = min(lot_qty, remaining_to_deduct)
                remaining_to_deduct -= deduct_here
            else:
                deduct_here = 0.0
            pending_wt = lot_qty - deduct_here
            key = (item_code, lot.source_key)
            pending_by_lot[key] = pending_wt

    data = []
    for item_code, lots in all_lots_by_item.items():
        attrs = item_attrs.get(item_code, {})
        shape = attrs.get("Stone Shape") or "-"
        purity = attrs.get("Diamond Grade") or "-"
        size = attrs.get("Diamond Sieve Size") or attrs.get("Diamond Sieve Size Range") or "-"

        for lot in lots:
            if from_date and to_date:
                if not (from_date <= lot.posting_date <= to_date):
                    continue

            key = (item_code, lot.source_key)
            pending_wt = pending_by_lot.get(key, 0.0)

            if pending_wt > 0:
                data.append({
                    "shape": shape,
                    "purity": purity,
                    "size": size,
                    "pending_wt": pending_wt,
                    "rate": lot.rate,
                })

    data.sort(key=lambda r: (r["shape"], r["purity"], r["size"]))
    return data


def get_branch_warehouses(company, branch=None):
    filters = {"disabled": 0}
    if company:
        filters["company"] = company
    if branch:
        filters["custom_branch"] = branch
    warehouses = frappe.get_all("Warehouse", fields=["name"], filters=filters)
    return [w.name for w in warehouses]


def get_diamond_variant_items():
    """Returns all specific diamond variant items, excluding generic items that only
    have a 'Diamond Type' attribute set and no Shape/Purity/Size (e.g. D-Polished Diamonds,
    D-AD) - these represent bulk/generic stock buckets, not specific diamond types."""
    items = frappe.get_all(
        "Item",
        fields=["name"],
        filters={"item_group": "Diamond - V", "variant_of": ["is", "set"]},
    )

    item_names = [i.name for i in items]

    attr_rows = frappe.db.sql("""
        SELECT parent, attribute
        FROM `tabItem Variant Attribute`
        WHERE parent IN %(items)s
    """, {"items": tuple(item_names)}, as_dict=True)

    attrs_by_item = {}
    for row in attr_rows:
        attrs_by_item.setdefault(row.parent, set()).add(row.attribute)

    specific_items = []
    for name in item_names:
        item_attrs = attrs_by_item.get(name, set())
        if item_attrs != {"Diamond Type"}:
            specific_items.append(name)

    return specific_items


def get_item_attributes(item_codes):
    if not item_codes:
        return {}

    rows = frappe.db.sql("""
        SELECT parent, attribute, attribute_value
        FROM `tabItem Variant Attribute`
        WHERE parent IN %(items)s
    """, {"items": tuple(item_codes)}, as_dict=True)

    attr_map = {}
    for row in rows:
        attr_map.setdefault(row.parent, {})[row.attribute] = row.attribute_value
    return attr_map


def get_all_inbound_lots_by_item(item_codes, warehouse_names, company=None):
    if not item_codes or not warehouse_names:
        return {}

    all_lots = []

    purchase_rows = frappe.db.sql("""
        SELECT pri.item_code, pri.qty, pri.rate, pri.parent, pr.posting_date
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE pr.docstatus = 1
        AND pri.item_code IN %(items)s
        AND pri.warehouse IN %(warehouses)s
        AND pri.qty > 0
    """, {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}, as_dict=True)
    for row in purchase_rows:
        row["source_key"] = "PR-" + row.parent + "-" + str(row.rate)
        all_lots.append(row)

    cgr_conditions = ["se.docstatus = 1", "sed.item_code IN %(items)s", "sed.t_warehouse IN %(warehouses)s",
                       "se.stock_entry_type = 'Customer Goods Received'", "sed.qty > 0"]
    cgr_params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        cgr_conditions.append("se.company = %(company)s")
        cgr_params["company"] = company
    cgr_where = " AND ".join(cgr_conditions)
    cgr_rows = frappe.db.sql(f"""
        SELECT sed.item_code, sed.qty, sed.basic_rate as rate, sed.parent, se.posting_date
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {cgr_where}
    """, cgr_params, as_dict=True)
    for row in cgr_rows:
        row["source_key"] = "CGR-" + row.parent + "-" + str(row.rate)
        all_lots.append(row)

    sr_conditions = ["sr.docstatus = 1", "sri.item_code IN %(items)s", "sri.qty > 0"]
    sr_params = {"items": tuple(item_codes)}
    if company:
        sr_conditions.append("sr.company = %(company)s")
        sr_params["company"] = company
    sr_where = " AND ".join(sr_conditions)
    sr_rows = frappe.db.sql(f"""
        SELECT sri.item_code, sri.qty, sri.valuation_rate as rate, sri.parent, sr.posting_date
        FROM `tabStock Reconciliation` sr
        LEFT JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
        WHERE {sr_where}
    """, sr_params, as_dict=True)
    for row in sr_rows:
        row["source_key"] = "SR-" + row.parent + "-" + str(row.rate)
        all_lots.append(row)

    mr_conditions = ["se.docstatus = 1", "sed.item_code IN %(items)s", "sed.t_warehouse IN %(warehouses)s",
                      "se.stock_entry_type = 'Material Receipt'", "sed.qty > 0"]
    mr_params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        mr_conditions.append("se.company = %(company)s")
        mr_params["company"] = company
    mr_where = " AND ".join(mr_conditions)
    mr_rows = frappe.db.sql(f"""
        SELECT sed.item_code, sed.qty, sed.basic_rate as rate, sed.parent, se.posting_date
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {mr_where}
    """, mr_params, as_dict=True)
    for row in mr_rows:
        row["source_key"] = "MR-" + row.parent + "-" + str(row.rate)
        all_lots.append(row)

    sret_conditions = ["si.docstatus = 1", "sii.item_code IN %(items)s", "si.is_return = 1"]
    sret_params = {"items": tuple(item_codes)}
    if company:
        sret_conditions.append("si.company = %(company)s")
        sret_params["company"] = company
    sret_where = " AND ".join(sret_conditions)
    sret_rows = frappe.db.sql(f"""
        SELECT sii.item_code, ABS(sii.qty) as qty, sii.rate, sii.parent, si.posting_date
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE {sret_where}
    """, sret_params, as_dict=True)
    for row in sret_rows:
        row["source_key"] = "SRET-" + row.parent + "-" + str(row.rate)
        all_lots.append(row)

    lots_by_item = {}
    for row in all_lots:
        lots_by_item.setdefault(row.item_code, []).append(row)

    for item_code in lots_by_item:
        lots_by_item[item_code].sort(key=lambda r: r.posting_date)

    return lots_by_item


def get_tagged_qty_map(item_codes, company=None):
    if not item_codes:
        return {}
    conditions = ["snc.docstatus = 1", "fgd.row_material IN %(items)s"]
    params = {"items": tuple(item_codes)}
    if company:
        conditions.append("snc.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT fgd.row_material, SUM(fgd.qty) as total_qty
        FROM `tabSerial Number Creator` snc
        LEFT JOIN `tabSNC FG Details` fgd ON fgd.parent = snc.name
        WHERE {where_clause}
        GROUP BY fgd.row_material
    """, params, as_dict=True)
    return {row.row_material: flt(row.total_qty) for row in result}


def get_purchase_return_qty_map(item_codes, warehouse_names, company=None):
    if not item_codes or not warehouse_names:
        return {}
    conditions = ["pr.docstatus = 1", "pri.item_code IN %(items)s", "pri.warehouse IN %(warehouses)s",
                  "pri.qty < 0"]
    params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        conditions.append("pr.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT pri.item_code, SUM(ABS(pri.qty)) as total_returned
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE {where_clause}
        GROUP BY pri.item_code
    """, params, as_dict=True)
    return {row.item_code: flt(row.total_returned) for row in result}


def get_sales_qty_map(item_codes, company=None):
    if not item_codes:
        return {}
    conditions = ["si.docstatus = 1", "sii.item_code IN %(items)s", "si.is_return = 0"]
    params = {"items": tuple(item_codes)}
    if company:
        conditions.append("si.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT sii.item_code, SUM(sii.qty) as total_sold
        FROM `tabSales Invoice Item` sii
        LEFT JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE {where_clause}
        GROUP BY sii.item_code
    """, params, as_dict=True)
    return {row.item_code: flt(row.total_sold) for row in result}


def get_material_issue_qty_map(item_codes, warehouse_names, company=None):
    if not item_codes or not warehouse_names:
        return {}
    conditions = ["se.docstatus = 1", "sed.item_code IN %(items)s", "sed.s_warehouse IN %(warehouses)s",
                  "se.stock_entry_type = 'Material Issue'"]
    params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        conditions.append("se.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT sed.item_code, SUM(sed.qty) as total_qty
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {where_clause}
        GROUP BY sed.item_code
    """, params, as_dict=True)
    return {row.item_code: flt(row.total_qty) for row in result}


def get_process_loss_qty_map(item_codes, warehouse_names, company=None):
    if not item_codes or not warehouse_names:
        return {}
    conditions = ["se.docstatus = 1", "sed.item_code IN %(items)s", "sed.s_warehouse IN %(warehouses)s",
                  "se.stock_entry_type = 'Process Loss'"]
    params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        conditions.append("se.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT sed.item_code, SUM(sed.qty) as total_qty
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {where_clause}
        GROUP BY sed.item_code
    """, params, as_dict=True)
    return {row.item_code: flt(row.total_qty) for row in result}


def get_customer_goods_issue_qty_map(item_codes, warehouse_names, company=None):
    if not item_codes or not warehouse_names:
        return {}
    conditions = ["se.docstatus = 1", "sed.item_code IN %(items)s", "sed.s_warehouse IN %(warehouses)s",
                  "se.stock_entry_type = 'Customer Goods Issue'"]
    params = {"items": tuple(item_codes), "warehouses": tuple(warehouse_names)}
    if company:
        conditions.append("se.company = %(company)s")
        params["company"] = company
    where_clause = " AND ".join(conditions)
    result = frappe.db.sql(f"""
        SELECT sed.item_code, SUM(sed.qty) as total_qty
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE {where_clause}
        GROUP BY sed.item_code
    """, params, as_dict=True)
    return {row.item_code: flt(row.total_qty) for row in result}