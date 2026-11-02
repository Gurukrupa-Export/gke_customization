import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    filters = validate_department_access(filters)

    columns = get_columns()
    data = get_data(filters)
    data = add_grand_total(data)

    return columns, data


def add_grand_total(data):
    if not data:
        return data

    def total(key):
        return sum((row.get(key) or 0) for row in data)

    total_loss = total("total_loss")
    gold_wt = total("gold_wt")

    total_row = {
        "process": _("Grand Total"),
        "employee_code": "",
        "employee": "",
        "category": "",
        "gross_wt": round(total("gross_wt"), 3),
        "gold_wt": round(gold_wt, 3),
        "pure_wt": round(total("pure_wt"), 3),
        "gemstone_wt": round(total("gemstone_wt"), 3),
        "gemstone_pcs": int(total("gemstone_pcs")),
        "dia_wt": round(total("dia_wt"), 3),
        "dia_pcs": int(total("dia_pcs")),
        "total_loss_pure": round(total("total_loss_pure"), 3),
        "total_loss": round(total_loss, 3),
        "final_loss_percent": round((total_loss / gold_wt) * 100, 2) if gold_wt else 0,
        "to_date": None,
    }

    data.append(total_row)
    return data


def validate_department_access(filters):
    user = frappe.session.user
    is_admin = user == "Administrator" or "System Manager" in frappe.get_roles(user)

    if not is_admin:
        user_department = frappe.defaults.get_user_default("department")

        if not user_department:
            frappe.throw(_("User default Department is not set."))

        filters["department"] = user_department

    return filters


def get_columns():
    return [
        {"label": _("Operation"), "fieldname": "process", "fieldtype": "Data", "width": 140},
        {"label": _("Employee"), "fieldname": "employee_code", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": _("Employee Name"), "fieldname": "employee", "fieldtype": "Data", "width": 180},
        {"label": _("Type"), "fieldname": "category", "fieldtype": "Data", "width": 90},
        {"label": _("Gross WT"), "fieldname": "gross_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Gold WT"), "fieldname": "gold_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Pure WT"), "fieldname": "pure_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Gemstone WT"), "fieldname": "gemstone_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Gemstone Pcs"), "fieldname": "gemstone_pcs", "fieldtype": "Int", "width": 120},
        {"label": _("Dia WT"), "fieldname": "dia_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Dia Pcs"), "fieldname": "dia_pcs", "fieldtype": "Int", "width": 120},
        {"label": _("Total Loss(Pure)"), "fieldname": "total_loss_pure", "fieldtype": "Float", "width": 140},
        {"label": _("Total Loss"), "fieldname": "total_loss", "fieldtype": "Float", "width": 120},
        {"label": _("Final Loss %"), "fieldname": "final_loss_percent", "fieldtype": "Percent", "width": 120},
        {"label": _("To Date"), "fieldname": "to_date", "fieldtype": "Date", "width": 120},
    ]


def get_conditions(filters):
    conditions = []
    params = {}

    if filters.get("company"):
        conditions.append("eir.company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("branch"):
        conditions.append("emp.branch = %(branch)s")
        params["branch"] = filters["branch"]

    if filters.get("department"):
        conditions.append("eir.department = %(department)s")
        params["department"] = filters["department"]

    if filters.get("employee"):
        conditions.append("eir.employee = %(employee)s")
        params["employee"] = filters["employee"]

    if filters.get("from_date"):
        conditions.append("DATE(eir.creation) >= %(from_date)s")
        params["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("DATE(eir.creation) <= %(to_date)s")
        params["to_date"] = filters["to_date"]

    touch = filters.get("touch")

    if touch == "CHAIN":
        # Only the CHA MWO rows
        conditions.append("IFNULL(x.category, 'Regular') = 'Chain'")

    elif touch:
        # Normal touch: only non-CHA rows, and only IRs having that touch on a non-CHA loss item
        conditions.append("IFNULL(x.category, 'Regular') = 'Regular'")
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabEmployee Loss Details` eld1
                INNER JOIN `tabItem Variant Attribute` iva
                    ON iva.parent = eld1.item_code
                WHERE eld1.parent = eir.name
                    AND IFNULL(eld1.manufacturing_work_order, '') NOT LIKE '%%CHA%%'
                    AND iva.attribute = 'Metal Touch'
                    AND iva.attribute_value = %(touch)s
            )
        """)
        params["touch"] = touch

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    return where_clause, params


def chain_case(col):
    return f"CASE WHEN {col} LIKE '%%CHA%%' THEN 'Chain' ELSE 'Regular' END"


def get_data(filters):
    conditions, params = get_conditions(filters)

    cat_plain = chain_case("manufacturing_work_order")
    cat_op = chain_case("op.manufacturing_work_order")
    cat_eld2 = chain_case("eld2.manufacturing_work_order")

    # Loss per (IR, category).
    # If the IR has mop_loss_details_total, it is IR level, so it is split by each
    # category's share of the operation rows' gold_loss (loss_share). Otherwise the loss
    # details of that category are used directly.
    loss_expr = """
        CASE
            WHEN IFNULL(eir.mop_loss_details_total, 0) > 0
                THEN eir.mop_loss_details_total * IFNULL(x.loss_share, 1)
            ELSE IFNULL(x.eld_loss, 0)
        END
    """

    return frappe.db.sql(f"""
        SELECT
            eir.operation AS process,
            emp.employee_name AS employee,
            eir.employee AS employee_code,
            IFNULL(x.category, 'Regular') AS category,

            ROUND(SUM(IFNULL(x.gross_wt, 0)), 3) AS gross_wt,
            ROUND(SUM(IFNULL(x.gold_wt, 0)), 3) AS gold_wt,
            ROUND(SUM(IFNULL(x.pure_wt, 0)), 3) AS pure_wt,

            ROUND(SUM(IFNULL(x.gemstone_wt, 0)), 3) AS gemstone_wt,
            SUM(IFNULL(x.gemstone_pcs, 0)) AS gemstone_pcs,
            ROUND(SUM(IFNULL(x.dia_wt, 0)), 3) AS dia_wt,
            SUM(IFNULL(x.dia_pcs, 0)) AS dia_pcs,

            ROUND(SUM({loss_expr}), 3) AS total_loss,

            ROUND(
                SUM(({loss_expr}) * IFNULL(mp.metal_purity, 0) / 100),
                3
            ) AS total_loss_pure,

            ROUND(
                (
                    SUM({loss_expr})
                    /
                    NULLIF(SUM(IFNULL(x.gold_wt, 0)), 0)
                ) * 100,
                2
            ) AS final_loss_percent,

            MAX(DATE(eir.creation)) AS to_date

        FROM `tabEmployee IR` eir

        LEFT JOIN `tabEmployee` emp
            ON emp.name = eir.employee

        LEFT JOIN (
            SELECT
                b.parent,
                b.category,
                IFNULL(opc.gross_wt, 0) AS gross_wt,
                IFNULL(opc.gold_wt, 0) AS gold_wt,
                IFNULL(opc.pure_wt, 0) AS pure_wt,
                IFNULL(opc.gemstone_wt, 0) AS gemstone_wt,
                IFNULL(opc.gemstone_pcs, 0) AS gemstone_pcs,
                IFNULL(opc.dia_wt, 0) AS dia_wt,
                IFNULL(opc.dia_pcs, 0) AS dia_pcs,
                IFNULL(eldc.total_proportionally_loss, 0) AS eld_loss,
                CASE
                    WHEN SUM(IFNULL(opc.gold_loss, 0)) OVER (PARTITION BY b.parent) > 0
                        THEN IFNULL(opc.gold_loss, 0)
                             / SUM(IFNULL(opc.gold_loss, 0)) OVER (PARTITION BY b.parent)
                    WHEN SUM(IFNULL(opc.gold_wt, 0)) OVER (PARTITION BY b.parent) > 0
                        THEN IFNULL(opc.gold_wt, 0)
                             / SUM(IFNULL(opc.gold_wt, 0)) OVER (PARTITION BY b.parent)
                    ELSE 1 / COUNT(*) OVER (PARTITION BY b.parent)
                END AS loss_share
            FROM (
                SELECT
                    parent,
                    {cat_plain} AS category
                FROM `tabEmployee IR Operation`
                UNION
                SELECT
                    parent,
                    {cat_plain} AS category
                FROM `tabEmployee Loss Details`
            ) b

            LEFT JOIN (
                SELECT
                    op.parent,
                    {cat_op} AS category,
                    SUM(IFNULL(op.gross_wt, 0)) AS gross_wt,
                    SUM(
                        IFNULL(op.net_wt, 0) +
                        CASE WHEN {cat_op} = 'CHAIN' THEN IFNULL(op.finding_wt, 0) ELSE 0 END
                    ) AS gold_wt,
                    SUM(
                        (
                            IFNULL(op.net_wt, 0) +
                            CASE WHEN {cat_op} = 'CHAIN' THEN IFNULL(op.finding_wt, 0) ELSE 0 END
                        ) *
                        CAST(IFNULL(mwo.metal_purity, 0) AS DECIMAL(10,3)) / 100
                    ) AS pure_wt,
                    SUM(IFNULL(op.gold_loss, 0)) AS gold_loss,
                    SUM(IFNULL(op.gemstone_wt, 0)) AS gemstone_wt,
                    SUM(IFNULL(op.gemstone_pcs, 0)) AS gemstone_pcs,
                    SUM(IFNULL(op.diamond_wt, 0)) AS dia_wt,
                    SUM(IFNULL(op.diamond_pcs, 0)) AS dia_pcs
                FROM `tabEmployee IR Operation` op
                LEFT JOIN `tabManufacturing Work Order` mwo
                    ON mwo.name = op.manufacturing_work_order
                GROUP BY
                    op.parent,
                    {cat_op}
            ) opc
                ON opc.parent = b.parent
                AND opc.category = b.category

            LEFT JOIN (
                SELECT
                    parent,
                    {cat_plain} AS category,
                    SUM(IFNULL(proportionally_loss, 0)) AS total_proportionally_loss
                FROM `tabEmployee Loss Details`
                GROUP BY
                    parent,
                    {cat_plain}
            ) eldc
                ON eldc.parent = b.parent
                AND eldc.category = b.category
        ) x
            ON x.parent = eir.name

        LEFT JOIN (
            SELECT parent, category, metal_purity
            FROM (
                SELECT
                    eld2.parent,
                    {cat_eld2} AS category,
                    CAST(iva2.attribute_value AS DECIMAL(10,3)) AS metal_purity,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            eld2.parent,
                            {cat_eld2}
                        ORDER BY CASE
                            WHEN eld2.item_code LIKE 'M-%%' THEN 1
                            WHEN eld2.item_code LIKE 'F-%%' THEN 2
                            ELSE 3
                        END
                    ) AS rn
                FROM `tabEmployee Loss Details` eld2
                INNER JOIN `tabItem Variant Attribute` iva2
                    ON iva2.parent = eld2.item_code
                    AND iva2.attribute = 'Metal Purity'
                WHERE eld2.item_code LIKE 'M-%%' OR eld2.item_code LIKE 'F-%%'
            ) ranked
            WHERE rn = 1
        ) mp
            ON mp.parent = eir.name
            AND mp.category = IFNULL(x.category, 'Regular')

        WHERE
            eir.docstatus = 1
            {conditions}

        GROUP BY
            eir.operation,
            emp.employee_name,
            eir.employee,
            IFNULL(x.category, 'Regular')

        ORDER BY
            eir.operation,
            emp.employee_name,
            IFNULL(x.category, 'Regular')
    """, params, as_dict=True)