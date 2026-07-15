# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    data = group_duplicate_rows(data)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Serial No"),
            "fieldname": "serial_no",
            "fieldtype": "Link",
            "options": "Serial No",
            "width": 140,
        },
        {
            "label": _("StyleBio"),
            "fieldname": "stylebio",
            "fieldtype": "Link",
            "options": "Item",
            "width": 170,
        },
        {
            "label": _("Category"),
            "fieldname": "category",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Sub Category"),
            "fieldname": "sub_category",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Setting"),
            "fieldname": "setting",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Gross Wt"),
            "fieldname": "gross_wt",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Material"),
            "fieldname": "material",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Shape"),
            "fieldname": "shape",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Purity"),
            "fieldname": "purity",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Size"),
            "fieldname": "size",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Code"),
            "fieldname": "code",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            # Changed from Float -> Int so Pcs always renders as a whole number
            "label": _("Pcs"),
            "fieldname": "pcs",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": _("Weight"),
            "fieldname": "weight",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Pure Weight"),
            "fieldname": "pure_weight",
            "fieldtype": "Float",
            "width": 110,
        },
        {
            "label": _("Metal Ratio"),
            "fieldname": "metal_ratio",
            "fieldtype": "Float",
            "width": 100,
        },
    ]


def get_conditions(filters):
    conditions = []
    values = {}

    # Only Submitted BOM
    conditions.append("bom.docstatus = 1")

    if filters.get("serial_no"):
        conditions.append("sn.name = %(serial_no)s")
        values["serial_no"] = filters.get("serial_no")

    # StyleBio = BOM Item
    if filters.get("stylebio"):
        conditions.append("bom.item = %(stylebio)s")
        values["stylebio"] = filters.get("stylebio")

    if filters.get("category"):
        conditions.append("bom.item_category = %(category)s")
        values["category"] = filters.get("category")

    if filters.get("sub_category"):
        conditions.append("bom.item_subcategory = %(sub_category)s")
        values["sub_category"] = filters.get("sub_category")

    if filters.get("setting"):
        conditions.append("bom.setting_type = %(setting)s")
        values["setting"] = filters.get("setting")

    if filters.get("from_date"):
        conditions.append("DATE(sn.creation) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(sn.creation) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("company"):
        conditions.append("bom.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("emp.branch = %(branch)s")
        values["branch"] = filters.get("branch")

    if filters.get("department"):
        conditions.append("eir.department = %(department)s")
        values["department"] = filters.get("department")

    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    return where_clause, values


def get_data(filters):
    where_clause, values = get_conditions(filters)

    sql = f"""
    SELECT
        *
    FROM
    (

        /* ===========================
           METAL
           =========================== */

        SELECT
            sn.name AS serial_no,
            bom.item AS stylebio,
            bom.item_category AS category,
            bom.item_subcategory AS sub_category,
            bom.setting_type AS setting,
            bom.gross_weight AS gross_wt,

            'Metal' AS material,

            '' AS shape,
            bmd.metal_purity AS purity,
            '' AS size,
            '' AS code,
            1 AS pcs,
            IFNULL(bmd.quantity,0) AS weight,

        ROUND(
            IFNULL(bmd.quantity,0) * (IFNULL(bmd.metal_purity,0) / 100),
            3
        ) AS pure_weight,

    ROUND(
            IFNULL(bmd.metal_purity,0) / 100,
            3
        ) AS metal_ratio,
            1 AS sort_order

        FROM `tabSerial No` sn
        INNER JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no
        INNER JOIN `tabBOM Metal Detail` bmd
            ON bmd.parent = bom.name

        {where_clause}

        UNION ALL

        /* ===========================
           DIAMOND
           =========================== */

        SELECT
            sn.name AS serial_no,
            bom.item AS stylebio,
            bom.item_category AS category,
            bom.item_subcategory AS sub_category,
            bom.setting_type AS setting,
            NULL AS gross_wt,

            'Diamond' AS material,

            IFNULL(bdd.stone_shape,'') AS shape,
            IFNULL(bdd.quality,'') AS purity,
            IFNULL(bdd.diamond_sieve_size,'') AS size,
            '' AS code,
            CAST(IFNULL(bdd.pcs,0) AS SIGNED) AS pcs,
            IFNULL(bdd.quantity,0) AS weight,

    ROUND(
        IFNULL(bdd.quantity,0) / 5,
        3
    ) AS pure_weight,

    0  AS metal_ratio,
            2 AS sort_order

        FROM `tabSerial No` sn
        INNER JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no
        INNER JOIN `tabBOM Diamond Detail` bdd
            ON bdd.parent = bom.name

        {where_clause}
    UNION ALL

/* ===========================
   FINDING
   =========================== */

SELECT

    sn.name AS serial_no,
    bom.item AS stylebio,
    bom.item_category AS category,
    bom.item_subcategory AS sub_category,
    bom.setting_type AS setting,
    bom.gross_weight AS gross_wt,

    'Finding' AS material,

    IFNULL(bfd.finding_type,'') AS shape,
    IFNULL(bfd.metal_purity,'') AS purity,
    IFNULL(bfd.finding_size,'') AS size,
    IFNULL(bfd.item,'') AS code,

    CAST(IFNULL(bfd.qty,0) AS SIGNED) AS pcs,
   IFNULL(bfd.quantity,0) AS weight,

ROUND(
    IFNULL(bfd.quantity,0) * (IFNULL(bfd.metal_purity,0) / 100),
    3
) AS pure_weight,

ROUND(
    IFNULL(bfd.metal_purity,0) / 100,
    3
) AS metal_ratio,

    3 AS sort_order

FROM `tabSerial No` sn

INNER JOIN `tabBOM` bom
    ON bom.name = sn.custom_bom_no

INNER JOIN `tabBOM Finding Detail` bfd
    ON bfd.parent = bom.name

{where_clause}
UNION ALL

/* ===========================
   GEMSTONE
   =========================== */

SELECT

    sn.name AS serial_no,
    bom.item AS stylebio,
    bom.item_category AS category,
    bom.item_subcategory AS sub_category,
    bom.setting_type AS setting,
    NULL AS gross_wt,

    'Gemstone' AS material,

    IFNULL(bgd.stone_shape,'') AS shape,

    IFNULL(bgd.gemstone_quality,'') AS purity,

    IFNULL(bgd.gemstone_size,'') AS size,

    IFNULL(bgd.gemstone_code,'') AS code,

    CAST(IFNULL(bgd.pcs,0) AS SIGNED) AS pcs,

    IFNULL(bgd.quantity,0) AS weight,

ROUND(
    IFNULL(bgd.quantity,0) / 5,
    3
) AS pure_weight,

0 AS metal_ratio,

    4 AS sort_order

FROM `tabSerial No` sn

INNER JOIN `tabBOM` bom
    ON bom.name = sn.custom_bom_no

INNER JOIN `tabBOM Gemstone Detail` bgd
    ON bgd.parent = bom.name

{where_clause}
UNION ALL

/* ===========================
   OTHER DETAIL
   =========================== */

SELECT

    sn.name AS serial_no,

    bom.item AS stylebio,

    bom.item_category AS category,

    bom.item_subcategory AS sub_category,

    bom.setting_type AS setting,

    NULL AS gross_wt,

    'Other' AS material,

    '' AS shape,

    '' AS purity,

    '' AS size,

    IFNULL(bod.item_code,'') AS code,

    CAST(IFNULL(bod.qty,0) AS SIGNED) AS pcs,

    IFNULL(bod.quantity,0) AS weight,

    IFNULL(bod.quantity,0) AS pure_weight,

    0 AS metal_ratio,

    5 AS sort_order

FROM `tabSerial No` sn

INNER JOIN `tabBOM` bom
    ON bom.name = sn.custom_bom_no

INNER JOIN `tabBOM Other Detail` bod
    ON bod.parent = bom.name

{where_clause}


    ) t

    ORDER BY
        serial_no,
        sort_order,
        shape,
        size
    """

    return frappe.db.sql(sql, values, as_dict=True)


def group_duplicate_rows(data):
    """
    Group duplicate rows by Serial No.
    Display parent values only once (Jewlex style).
    """

    if not data:
        return []

    grouped_data = []
    previous_serial = None

    for row in data:

        # Skip rows where no material exists
        if not row.get("material"):
            continue

        # Skip empty metal rows
        if row["material"] == "Metal":
            if not row.get("weight") and not row.get("pure_weight"):
                continue

        # Skip empty diamond rows
        if row["material"] == "Diamond":
            if not row.get("weight") and not row.get("pcs"):
                continue

        # Ensure Pcs is always a clean integer (no decimals)
        try:
            row["pcs"] = int(row.get("pcs") or 0)
        except (TypeError, ValueError):
            row["pcs"] = 0

        # Replace None values with blanks, but keep gross_wt as None
        # (None renders as a true blank in a Float column; "" gets
        # coerced back to 0.000 by the report renderer)
        for key, value in row.items():
            if value is None and key not in ("gross_wt",):
                row[key] = ""

        # Hide duplicate parent values
        if previous_serial == row["serial_no"]:

            row["serial_no"] = ""
            row["stylebio"] = ""
            row["category"] = ""
            row["sub_category"] = ""
            row["setting"] = ""
            row["gross_wt"] = None  # keep as None, not "", so it stays blank

        else:
            previous_serial = row["serial_no"]

        grouped_data.append(row)

    return grouped_data
