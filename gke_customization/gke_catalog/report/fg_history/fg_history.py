import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Stage", "fieldname": "stage", "fieldtype": "Data", "width": 160},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Data", "width": 130},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": "Customer", "fieldname": "party", "fieldtype": "Data", "width": 140},
        {"label": "PMO", "fieldname": "pmo", "fieldtype": "Data", "width": 110},
        {"label": "MWO", "fieldname": "mwo", "fieldtype": "Data", "width": 110},
        {"label": "MOP", "fieldname": "mop", "fieldtype": "Data", "width": 110},
        {"label": "Design Type", "fieldname": "design_type", "fieldtype": "Data", "width": 120},
        {"label": "BOM", "fieldname": "bom", "fieldtype": "Link", "options": "BOM", "width": 130},
        {"label": "Reason", "fieldname": "reason", "fieldtype": "Data", "width": 140},
    ]


def get_data(filters):
    item_code = filters.get("item_code")
    serial_no = filters.get("serial_no")

    values = {"item_code": item_code, "serial_no": serial_no}

    def cond(item_field, serial_field=None):
        """Builds a WHERE clause. If serial_field is None, that source
        has no serial column, so the serial filter is skipped for it."""
        parts = []
        if item_code:
            parts.append(f"{item_field} = %(item_code)s")
        if serial_no and serial_field:
            parts.append(f"{serial_field} = %(serial_no)s")
        return ("WHERE " + " AND ".join(parts)) if parts else ""

    def and_cond(item_field, serial_field, base_condition):
        """Same as cond() but appends to an existing WHERE (docstatus filter)."""
        parts = [base_condition]
        if item_code:
            parts.append(f"{item_field} = %(item_code)s")
        if serial_no and serial_field:
            parts.append(f"{serial_field} = %(serial_no)s")
        return "WHERE " + " AND ".join(parts)

    query = f"""
        SELECT * FROM (

            -- Sketch Order (no serial field)
            SELECT
                'Sketch Order'        AS stage,
                so.item_code          AS item_code,
                NULL                  AS serial_no,
                DATE(so.creation)      AS date,
                so.customer_code        AS party,
                NULL AS pmo, NULL AS mwo, NULL AS mop,
                so.design_by            AS design_type,
                NULL                     AS bom,
                NULL                     AS reason
            FROM `tabSketch Order` so
            {cond("so.item_code")}

            UNION ALL

            -- CAD Order (tabOrder) (no serial field)
            SELECT
                'CAD Order'           AS stage,
                o.item                AS item_code,
                NULL                  AS serial_no,
                DATE(o.creation)       AS date,
                o.customer_code          AS party,
                NULL, NULL, NULL,
                o.design_type            AS design_type,
                o.bom                     AS bom,
                NULL                       AS reason
            FROM `tabOrder` o
            LEFT JOIN `tabOrder Form` ofm ON ofm.name = o.cad_order_form
            {cond("o.item")}

            UNION ALL

            -- Repair Order
            SELECT
                'Repair Order'        AS stage,
                ro.item               AS item_code,
                ro.tag_no             AS serial_no,
                DATE(ro.creation)      AS date,
                NULL                     AS party,
                NULL, NULL, NULL,
                ro.repair_type           AS design_type,
                ro.bom                    AS bom,
                ro.mod_reason              AS reason
            FROM `tabRepair Order` ro
            {cond("ro.item", "ro.tag_no")}

            UNION ALL

            -- Purchase Receipt
            SELECT
                'Purchase Receipt'    AS stage,
                pri.item_code         AS item_code,
                pri.serial_no         AS serial_no,
                pr.posting_date        AS date,
                pr.supplier              AS party,
                NULL, NULL, NULL,
                NULL                     AS design_type,
                NULL                      AS bom,
                NULL                       AS reason
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pri.parent = pr.name AND pri.parenttype = 'Purchase Receipt'
            {cond("pri.item_code", "pri.serial_no")}

            UNION ALL

            -- Stock Entry
            SELECT
                'Stock Entry'         AS stage,
                sed.item_code         AS item_code,
                sed.serial_no         AS serial_no,
                se.posting_date        AS date,
                se._customer             AS party,
                NULL, NULL, NULL,
                NULL                     AS design_type,
                NULL                      AS bom,
                NULL                       AS reason
            FROM `tabStock Entry` se
            INNER JOIN `tabStock Entry Detail` sed
                ON sed.parent = se.name AND sed.parenttype = 'Stock Entry'
            {cond("sed.item_code", "sed.serial_no")}

            UNION ALL

            -- Serial Number Creator
            SELECT
                'Serial Number Creator' AS stage,
                fgd.row_material         AS item_code,
                snc.fg_serial_no          AS serial_no,
                DATE(snc.creation)         AS date,
                NULL                          AS party,
                snc.parent_manufacturing_order AS pmo,
                snc.manufacturing_work_order   AS mwo,
                snc.manufacturing_operation    AS mop,
                NULL                              AS design_type,
                NULL                               AS bom,
                NULL                                AS reason
            FROM `tabSerial Number Creator` snc
            LEFT JOIN `tabSNC FG Details` fgd
                ON fgd.parent = snc.name AND fgd.parenttype = 'Serial Number Creator'
            {and_cond("fgd.row_material", "snc.fg_serial_no", "snc.docstatus = 1")}

            UNION ALL

            -- Product Certification
            SELECT
                'Product Certification' AS stage,
                pd.item_code             AS item_code,
                pd.serial_no              AS serial_no,
                pc.date                     AS date,
                pc.supplier                  AS party,
                NULL, NULL, NULL,
                NULL                          AS design_type,
                NULL                           AS bom,
                NULL                            AS reason
            FROM `tabProduct Certification` pc
            INNER JOIN `tabProduct Details` pd
                ON pd.parent = pc.name AND pd.parenttype = 'Product Certification'
            {and_cond("pd.item_code", "pd.serial_no", "pc.docstatus = 1")}

            UNION ALL

            -- Refining Entry
            SELECT
                'Refining Entry'      AS stage,
                rsnd.item_code          AS item_code,
                rsnd.serial_number       AS serial_no,
                re.posting_date            AS date,
                NULL                          AS party,
                NULL, NULL, NULL,
                NULL                           AS design_type,
                NULL                            AS bom,
                NULL                             AS reason
            FROM `tabRefining Entry` re
            INNER JOIN `tabRefining Serial No Detail` rsnd
                ON rsnd.parent = re.name AND rsnd.parenttype = 'Refining Entry'
            {and_cond("rsnd.item_code", "rsnd.serial_number", "re.docstatus = 1")}

        ) combined
        ORDER BY item_code, date ASC
    """

    return frappe.db.sql(query, values, as_dict=True)