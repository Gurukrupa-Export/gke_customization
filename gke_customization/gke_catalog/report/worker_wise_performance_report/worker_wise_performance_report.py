import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    filters = validate_department_access(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


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
        {"label": _("Process"), "fieldname": "process", "fieldtype": "Data", "width": 140},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 180},
        {"label": _("Employee Code"), "fieldname": "employee_code", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": _("Gross WT"), "fieldname": "gross_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Gold WT"), "fieldname": "gold_wt", "fieldtype": "Float", "width": 120},
        {"label": _("Pure WT"), "fieldname": "pure_wt", "fieldtype": "Float", "width": 120},
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

    if filters.get("touch"):
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabEmployee Loss Details` eld1
                INNER JOIN `tabItem Variant Attribute` iva
                    ON iva.parent = eld1.item_code
                WHERE eld1.parent = eir.name
                    AND iva.attribute = 'Metal Touch'
                    AND iva.attribute_value = %(touch)s
            )
        """)
        params["touch"] = filters["touch"]

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    return where_clause, params


def get_data(filters):
    conditions, params = get_conditions(filters)

    return frappe.db.sql(f"""
        SELECT
            eir.operation AS process,
            emp.employee_name AS employee,
            eir.employee AS employee_code,

            ROUND(SUM(IFNULL(op.gross_wt, 0)), 3) AS gross_wt,
            ROUND(SUM(IFNULL(op.net_wt, 0)), 3) AS gold_wt,
            ROUND(SUM(IFNULL(op.pure_wt, 0)), 3) AS pure_wt,

            ROUND(
                SUM(
                    CASE
                        WHEN IFNULL(eir.mop_loss_details_total, 0) > 0
                            THEN eir.mop_loss_details_total
                        ELSE IFNULL(eld.total_proportionally_loss, 0)
                    END
                ), 3
            ) AS total_loss,
            
            ROUND(
                SUM(
                    (
                        CASE
                            WHEN IFNULL(eir.mop_loss_details_total, 0) > 0
                                THEN eir.mop_loss_details_total
                            ELSE IFNULL(eld.total_proportionally_loss, 0)
                        END
                    ) *
                    IFNULL(mp.metal_purity, 0) / 100
                ), 3
            ) AS total_loss_pure,

            ROUND(
                (
                    SUM(
                        CASE
                            WHEN IFNULL(eir.mop_loss_details_total, 0) > 0
                                THEN eir.mop_loss_details_total
                            ELSE IFNULL(eld.total_proportionally_loss, 0)
                        END
                    )
                    /
                    NULLIF(SUM(IFNULL(op.net_wt, 0)), 0)
                ) * 100,
                2
            ) AS final_loss_percent,

            MAX(DATE(eir.creation)) AS to_date

        FROM `tabEmployee IR` eir

        LEFT JOIN `tabEmployee` emp
            ON emp.name = eir.employee

        LEFT JOIN (
            SELECT
                op.parent,
                SUM(IFNULL(op.gross_wt, 0)) AS gross_wt,
                SUM(IFNULL(op.net_wt, 0)) AS net_wt,
                SUM(
                    IFNULL(op.net_wt, 0) *
                    CAST(IFNULL(mwo.metal_purity, 0) AS DECIMAL(10,3)) / 100
                ) AS pure_wt
            FROM `tabEmployee IR Operation` op
            LEFT JOIN `tabManufacturing Work Order` mwo
                ON mwo.name = op.manufacturing_work_order
            GROUP BY op.parent
        ) op
            ON op.parent = eir.name

        LEFT JOIN (
            SELECT
                parent,
                SUM(IFNULL(proportionally_loss, 0)) AS total_proportionally_loss
            FROM `tabEmployee Loss Details`
            GROUP BY parent
        ) eld
            ON eld.parent = eir.name

        LEFT JOIN (
            SELECT parent, metal_purity
            FROM (
                SELECT
                    eld2.parent,
                    CAST(iva2.attribute_value AS DECIMAL(10,3)) AS metal_purity,
                    ROW_NUMBER() OVER (
                        PARTITION BY eld2.parent
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

        WHERE
            eir.docstatus = 1
            {conditions}

        GROUP BY
            eir.operation,
            emp.employee_name,
            eir.employee

        ORDER BY
            eir.operation,
            emp.employee_name
    """, params, as_dict=True)