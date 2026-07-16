# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    mandatory_filters = ["company", "department"]
    missing = [frappe.bold(_(f.replace("_", " ").title())) for f in mandatory_filters if not filters.get(f)]
    if missing:
        frappe.throw(_("Mandatory filters missing: {0}").format(", ".join(missing)))


def get_columns():
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 220},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Data", "width": 180},
        {"label": _("Shape"), "fieldname": "shape", "fieldtype": "Data", "width": 120},
        {"label": _("Purity"), "fieldname": "purity", "fieldtype": "Data", "width": 120},
        {"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Data", "width": 80},
        {"label": _("Department Stock"), "fieldname": "department_stock", "fieldtype": "Float", "width": 130},
        {"label": _("Batch Stock"), "fieldname": "batch_stock", "fieldtype": "Float", "width": 120},
        {"label": _("Worker Stock"), "fieldname": "worker_stock", "fieldtype": "Float", "width": 120},
        {"label": _("JobWork Stock"), "fieldname": "jobwork_stock", "fieldtype": "Float", "width": 120},
        {"label": _("Bagging Stock"), "fieldname": "bagging_stock", "fieldtype": "Float", "width": 120},
        {"label": _("Assort Stock"), "fieldname": "assort_stock", "fieldtype": "Float", "width": 120},
        {"label": _("Lost"), "fieldname": "lost_stock", "fieldtype": "Float", "width": 100},
        {"label": _("Broken"), "fieldname": "broken_stock", "fieldtype": "Float", "width": 100},
        {"label": _("Total"), "fieldname": "total_stock", "fieldtype": "Float", "width": 120},
        {"label": _("Diff"), "fieldname": "diff_stock", "fieldtype": "Float", "width": 100},
    ]


def get_data(filters):
    department_warehouses = get_department_warehouses(filters)
    reserve_warehouses = get_reserve_warehouses(filters)

    department_stock_map = get_department_stock(filters, department_warehouses)
    batch_stock_map = get_batch_stock(filters)
    worker_stock_map = get_worker_stock(filters)
    jobwork_stock_map = get_jobwork_stock(filters)
    bagging_stock_map = get_bagging_stock(filters, reserve_warehouses)
    assort_stock_map = get_assort_stock(filters)
    lost_stock_map = get_loss_stock(filters, "Lost")
    broken_stock_map = get_loss_stock(filters, "Broken")

    all_item_codes = set()
    all_item_codes.update(department_stock_map.keys())
    all_item_codes.update(batch_stock_map.keys())
    all_item_codes.update(worker_stock_map.keys())
    all_item_codes.update(jobwork_stock_map.keys())
    all_item_codes.update(bagging_stock_map.keys())
    all_item_codes.update(assort_stock_map.keys())
    all_item_codes.update(lost_stock_map.keys())
    all_item_codes.update(broken_stock_map.keys())

    item_details_map = get_item_details(list(all_item_codes))

    data = []
    for item_code in all_item_codes:
        item_details = item_details_map.get(item_code)
        if not item_details:
            continue

        department_stock = flt0(department_stock_map.get(item_code))
        batch_stock = flt0(batch_stock_map.get(item_code))
        worker_stock = flt0(worker_stock_map.get(item_code))
        jobwork_stock = flt0(jobwork_stock_map.get(item_code))
        bagging_stock = flt0(bagging_stock_map.get(item_code))
        assort_stock = flt0(assort_stock_map.get(item_code))
        lost_stock = flt0(lost_stock_map.get(item_code))
        broken_stock = flt0(broken_stock_map.get(item_code))

        total_stock = (
            department_stock
            + batch_stock
            + worker_stock
            + jobwork_stock
            + bagging_stock
            + assort_stock
            + lost_stock
            + broken_stock
        )

        diff_stock = department_stock - (
            batch_stock
            + worker_stock
            + jobwork_stock
            + bagging_stock
            + assort_stock
            + lost_stock
            + broken_stock
        )

        if not any([
            department_stock,
            batch_stock,
            worker_stock,
            jobwork_stock,
            bagging_stock,
            assort_stock,
            lost_stock,
            broken_stock,
            total_stock,
            diff_stock,
        ]):
            continue

        data.append({
            "item_code": item_code,
            "item_name": item_details.get("item_name"),
            "item_group": item_details.get("item_group"),
            "shape": item_details.get("shape"),
            "purity": item_details.get("purity"),
            "stock_uom": item_details.get("stock_uom"),
            "department_stock": department_stock,
            "batch_stock": batch_stock,
            "worker_stock": worker_stock,
            "jobwork_stock": jobwork_stock,
            "bagging_stock": bagging_stock,
            "assort_stock": assort_stock,
            "lost_stock": lost_stock,
            "broken_stock": broken_stock,
            "total_stock": total_stock,
            "diff_stock": diff_stock,
        })

    data.sort(key=lambda d: (cstr0(d.get("item_group")), cstr0(d.get("item_code"))))
    return data


def get_department_warehouses(filters):
    rows = frappe.db.sql("""
        SELECT name
        FROM `tabWarehouse`
        WHERE company = %(company)s
          AND department = %(department)s
          AND is_group = 0
    """, {
        "company": filters.company,
        "department": filters.department,
    }, as_dict=True)

    return [d.name for d in rows]


def get_reserve_warehouses(filters):
    rows = frappe.db.sql("""
        SELECT name
        FROM `tabWarehouse`
        WHERE company = %(company)s
          AND is_group = 0
          AND warehouse_type = 'Reserve'
          AND (
                department LIKE %(diamond_bagging_department)s
                OR department LIKE %(gemstone_bagging_department)s
                OR name LIKE %(diamond_bagging_name)s
                OR name LIKE %(gemstone_bagging_name)s
          )
    """, {
        "company": filters.company,
        "diamond_bagging_department": "%Diamond Bagging%",
        "gemstone_bagging_department": "%Gemstone Bagging%",
        "diamond_bagging_name": "%Diamond Bagging RSV%",
        "gemstone_bagging_name": "%Gemstone Bagging RSV%",
    }, as_dict=True)

    return [d.name for d in rows]


def get_department_stock(filters, warehouses):
    if not warehouses:
        return {}

    placeholders = ", ".join(["%s"] * len(warehouses))
    query = f"""
        SELECT
            sle.item_code,
            SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i
            ON i.name = sle.item_code
        WHERE sle.is_cancelled = 0
          AND sle.warehouse IN ({placeholders})
          AND i.item_group IN ('Diamond - V', 'Diamond - T', 'Diamond - DNU')
    """
    params = list(warehouses)

    if filters.get("manufacturer"):
        query += " AND i.manufacturer = %s"
        params.append(filters.manufacturer)

    query += """
        GROUP BY sle.item_code
        HAVING qty != 0
    """

    rows = frappe.db.sql(query, params, as_dict=True)
    return {d.item_code: flt0(d.qty) for d in rows}


def get_batch_stock(filters):
    return get_mop_bom_diamond_stock(filters, stock_type="batch")


def get_worker_stock(filters):
    return get_mop_bom_diamond_stock(filters, stock_type="worker")


def get_jobwork_stock(filters):
    return get_mop_bom_diamond_stock(filters, stock_type="jobwork")


def get_mop_bom_diamond_stock(filters, stock_type):
    values = {
        "company": filters.company,
        "branch": filters.branch,
        "department": filters.department,
    }

    manufacturer_condition = ""
    extra_condition = ""

    if filters.get("manufacturer"):
        manufacturer_condition = " AND itm.manufacturer = %(manufacturer)s"
        values["manufacturer"] = filters.manufacturer

    if stock_type == "batch":
        extra_condition = """
            AND mop.status = 'Not Started'
        """
    elif stock_type == "worker":
        extra_condition = """
            AND mop.status = 'WIP'
            AND IFNULL(mop.for_subcontracting, 0) = 0
            AND IFNULL(mop.employee, '') != ''
        """
    elif stock_type == "jobwork":
        extra_condition = """
            AND mop.status = 'WIP'
            AND IFNULL(mop.for_subcontracting, 0) = 1
            AND IFNULL(mop.subcontractor, '') != ''
        """

    rows = frappe.db.sql(f"""
        SELECT
            bdd.item_variant AS item_code,
            SUM(IFNULL(bdd.actual_quantity, 0)) AS qty
        FROM `tabManufacturing Operation` mop
        INNER JOIN `tabManufacturing Work Order` mwo
            ON mwo.name = mop.manufacturing_work_order
        INNER JOIN `tabBOM Diamond Detail` bdd
            ON bdd.parent = mop.design_id_bom
        INNER JOIN `tabItem` itm
            ON itm.name = bdd.item_variant
        WHERE mop.company = %(company)s
          AND mop.department = %(department)s
          AND mwo.branch = %(branch)s
          AND IFNULL(mop.design_id_bom, '') != ''
          AND IFNULL(bdd.item_variant, '') != ''
          {extra_condition}
          {manufacturer_condition}
        GROUP BY bdd.item_variant
        HAVING qty != 0
    """, values, as_dict=True)

    return {d.item_code: flt0(d.qty) for d in rows}


def get_bagging_stock(filters, reserve_warehouses):
    if not reserve_warehouses:
        return {}

    placeholders = ", ".join(["%s"] * len(reserve_warehouses))
    query = f"""
        SELECT
            sle.item_code,
            SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i
            ON i.name = sle.item_code
        WHERE sle.is_cancelled = 0
          AND sle.warehouse IN ({placeholders})
          AND i.item_group IN ('Diamond - V', 'Diamond - T', 'Diamond - DNU')
    """
    params = list(reserve_warehouses)

    if filters.get("manufacturer"):
        query += " AND i.manufacturer = %s"
        params.append(filters.manufacturer)

    query += """
        GROUP BY sle.item_code
        HAVING qty != 0
    """

    rows = frappe.db.sql(query, params, as_dict=True)
    return {d.item_code: flt0(d.qty) for d in rows}


def get_assort_stock(filters):
    values = {
        "company": filters.company,
        "branch": filters.branch,
        "department": filters.department,
    }

    manufacturer_condition = ""
    if filters.get("manufacturer"):
        manufacturer_condition = " AND i.manufacturer = %(manufacturer)s"
        values["manufacturer"] = filters.manufacturer

    rows = frappe.db.sql(f"""
        SELECT
            sct.item_code,
            SUM(sct.qty) AS qty
        FROM `tabDiamond Conversion` dc
        INNER JOIN `tabSC Source Table` sct
            ON sct.parent = dc.name
        INNER JOIN `tabItem` i
            ON i.name = sct.item_code
        WHERE dc.docstatus = 1
          AND dc.company = %(company)s
          AND dc.branch = %(branch)s
          AND dc.department = %(department)s
          AND i.item_group IN ('Diamond - V', 'Diamond - T', 'Diamond - DNU')
          {manufacturer_condition}
        GROUP BY sct.item_code
        HAVING qty != 0
    """, values, as_dict=True)

    return {d.item_code: flt0(d.qty) for d in rows}


def get_loss_stock(filters, loss_type):
    values = {
        "company": filters.company,
        "branch": filters.branch,
        "department": filters.department,
        "loss_type": loss_type,
    }

    manufacturer_condition = ""
    if filters.get("manufacturer"):
        manufacturer_condition = " AND i.manufacturer = %(manufacturer)s"
        values["manufacturer"] = filters.manufacturer

    rows = frappe.db.sql(f"""
        SELECT
            eld.item_code,
            SUM(
                CASE
                    WHEN IFNULL(eld.net_weight, 0) != 0 THEN eld.net_weight
                    ELSE IFNULL(eld.pcs, 0)
                END
            ) AS qty
        FROM `tabEmployee IR` eir
        INNER JOIN `tabManufacturing Work Order` mwo
            ON mwo.name = eir.main_slip
        INNER JOIN `tabEmployee Loss Details` eld
            ON eld.parent = eir.name
        INNER JOIN `tabItem` i
            ON i.name = eld.item_code
        WHERE eir.company = %(company)s
          AND eir.department = %(department)s
          AND mwo.branch = %(branch)s
          AND eld.loss_type = %(loss_type)s
          AND i.item_group IN ('Diamond - V', 'Diamond - T', 'Diamond - DNU')
          {manufacturer_condition}
        GROUP BY eld.item_code
        HAVING qty != 0
    """, values, as_dict=True)

    return {d.item_code: flt0(d.qty) for d in rows}


def get_item_details(item_codes):
    if not item_codes:
        return {}

    placeholders = ", ".join(["%s"] * len(item_codes))

    items = frappe.db.sql(f"""
        SELECT
            i.name,
            i.item_name,
            i.item_group,
            i.stock_uom
        FROM `tabItem` i
        WHERE i.name IN ({placeholders})
    """, item_codes, as_dict=True)

    item_map = {
        d.name: {
            "item_name": d.item_name,
            "item_group": d.item_group,
            "stock_uom": d.stock_uom,
            "shape": "",
            "purity": "",
        }
        for d in items
    }

    if not item_map:
        return {}

    valid_item_codes = list(item_map.keys())
    placeholders = ", ".join(["%s"] * len(valid_item_codes))

    attr_rows = frappe.db.sql(f"""
        SELECT
            iva.parent AS item_code,
            iva.attribute,
            iva.attribute_value
        FROM `tabItem Variant Attribute` iva
        WHERE iva.parent IN ({placeholders})
    """, valid_item_codes, as_dict=True)

    for row in attr_rows:
        if row.item_code not in item_map:
            continue

        if row.attribute == "Stone Shape":
            item_map[row.item_code]["shape"] = row.attribute_value
        elif row.attribute == "Diamond Grade":
            item_map[row.item_code]["purity"] = row.attribute_value

    return item_map


def flt0(value):
    return float(value or 0)


def cstr0(value):
    return (value or "").strip()